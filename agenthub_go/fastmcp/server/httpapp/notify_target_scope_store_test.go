package httpapp

import (
	"bytes"
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
)

// TestNotifyRouteStoresNothingForAnotherUser is the 338fe3a0 acceptance end to end on a real
// database, through the production wiring: the frame the finding's reproduction used to plant a
// toast in another user's inbox is refused, that user's store stays empty and their next connect
// replays nothing from it, while in the same run the caller's own notification is stored and
// replayed exactly once.
func TestNotifyRouteStoresNothingForAnotherUser(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	ctx := context.Background()
	previous := routes.MissedStore
	t.Cleanup(func() { routes.MissedStore = previous })

	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	if routes.MissedStore == nil {
		t.Fatal("NewApp did not assign routes.MissedStore: this case would pass vacuously")
	}
	server := httptest.NewServer(app.Handler())
	defer server.Close()

	const attacker = "user-attacker-1"
	const victim = "user-victim-2"
	attackerToken := wsTestTokenFor(t, attacker, nil)
	victimToken := wsTestTokenFor(t, victim, nil)

	// The reproduction: the caller's token, the victim named in metadata, the message and the sender
	// chosen by the caller.
	planted := `{"event_type":"notification","entity_type":"notification","entity_id":"spoof-338fe3a0",` +
		`"data":{"message":"rotate the production token that leaked in the standup notes",` +
		`"from":"4genthub-min-lead@4genthub-min"},"metadata":{"user_id":"` + victim + `"}}`
	status, respBody := postNotify(t, server.URL, attackerToken, planted)
	if status != http.StatusForbidden {
		t.Fatalf("the plant status = %d, want 403 (body=%s)", status, respBody)
	}
	if got := missedNotificationCount(t, sm, victim); got != 0 {
		t.Fatalf("rows stored for the victim = %d, want 0", got)
	}
	if got := missedNotificationCount(t, sm, attacker); got != 0 {
		t.Fatalf("rows stored for the caller = %d, want 0 (the frame was refused, not re-addressed)", got)
	}

	// The caller's own notification still works in the same run: addressed to itself through metadata.
	own := `{"event_type":"notification","entity_type":"notification","entity_id":"own-1",` +
		`"data":{"message":"your own notice","from":"go-dev"},` +
		`"metadata":{"user_id":"` + attacker + `"}}`
	status, respBody = postNotify(t, server.URL, attackerToken, own)
	if status != http.StatusOK {
		t.Fatalf("the caller's own notification status = %d, want 200 (body=%s)", status, respBody)
	}
	if got := missedNotificationCount(t, sm, attacker); got != 1 {
		t.Fatalf("rows stored for the caller = %d, want 1", got)
	}
	if got := missedNotificationCount(t, sm, victim); got != 0 {
		t.Fatalf("rows stored for the victim after the caller's own notification = %d, want 0", got)
	}

	// The victim connects: welcome only, nothing from the refused frame.
	victimConn, victimBR := wsTestDial(t, server.URL, "/ws/realtime?token="+url.QueryEscape(victimToken))
	if _, payload, err := wsTryReadFrame(victimBR); err != nil {
		t.Fatalf("victim welcome: %v", err)
	} else if welcome := wsTestJSON(t, payload); welcome["type"] != "sync" {
		t.Fatalf("victim welcome type = %v", welcome["type"])
	}
	_ = victimConn.SetReadDeadline(time.Now().Add(700 * time.Millisecond))
	if opcode, payload, err := wsTryReadFrame(victimBR); err == nil {
		t.Fatalf("the victim received a frame from the refused notification (opcode=%d): %s", opcode, payload)
	}
	victimConn.Close()

	// The caller connects: welcome, then exactly one replay of its own notification.
	callerConn, callerBR := wsTestDial(t, server.URL, "/ws/realtime?token="+url.QueryEscape(attackerToken))
	if _, payload, err := wsTryReadFrame(callerBR); err != nil {
		t.Fatalf("caller welcome: %v", err)
	} else if welcome := wsTestJSON(t, payload); welcome["type"] != "sync" {
		t.Fatalf("caller welcome type = %v", welcome["type"])
	}
	_ = callerConn.SetReadDeadline(time.Now().Add(3 * time.Second))
	opcode, payload := wsTestReadFrame(t, callerBR)
	if opcode != wsOpText {
		t.Fatalf("replay opcode = %d, want text", opcode)
	}
	frame := wsTestJSON(t, payload)
	if frame["type"] != "update" {
		t.Fatalf("replayed frame type = %v, want update: %s", frame["type"], payload)
	}
	payloadObj, _ := frame["payload"].(map[string]any)
	if payloadObj["entity"] != "notification" || payloadObj["action"] != "notification" {
		t.Fatalf("replayed payload = %v, want entity/action notification", payloadObj)
	}
	data, _ := payloadObj["data"].(map[string]any)
	primary, _ := data["primary"].(map[string]any)
	if primary["message"] != "your own notice" {
		t.Fatalf("replayed data.primary = %v, want the caller's own message", primary)
	}
	_ = callerConn.SetReadDeadline(time.Now().Add(700 * time.Millisecond))
	if opcode, payload, err := wsTryReadFrame(callerBR); err == nil {
		t.Fatalf("the caller received a second frame (opcode=%d): %s", opcode, payload)
	}
	callerConn.Close()
}

// TestNotifyRouteStoresNothingWhenAnotherUserIsNamedForAnyEntityType is the widened rule on a real
// store, and it is the request the old rule got wrong: this EXACT body - a task frame naming two
// other users - used to answer 200 and store one row for each of them, so a caller could plant a task
// toast, with a title of its own choosing, in two other users' dashboards. The recipients never
// resolve now: the refusal stores nothing for them and nothing for the caller either, because the
// route returns before the broadcast is reached - a refusal is not a re-address.
func TestNotifyRouteStoresNothingWhenAnotherUserIsNamedForAnyEntityType(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	ctx := context.Background()
	previous := routes.MissedStore
	t.Cleanup(func() { routes.MissedStore = previous })

	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	server := httptest.NewServer(app.Handler())
	defer server.Close()

	const actor = "user-actor-1"
	const one = "user-one-1"
	const two = "user-two-2"
	token := wsTestTokenFor(t, actor, nil)

	body := `{"event_type":"updated","entity_type":"task","entity_id":"task-9","metadata":{"user_ids":["` + one + `","` + two + `"]}}`
	status, respBody := postNotify(t, server.URL, token, body)
	if status != http.StatusForbidden {
		t.Fatalf("status = %d, want 403 (body=%s)", status, respBody)
	}
	for _, u := range []string{one, two, actor} {
		if got := missedNotificationCount(t, sm, u); got != 0 {
			t.Fatalf("rows stored for %s = %d, want 0 (a refusal stores nothing, not even for the caller)", u, got)
		}
	}
}

// TestTheFanOutStillStoresForEveryUserMetadataNames pins the capability the route did NOT take away,
// and it is driven DIRECTLY because no HTTP client may reach it any more: the internal producers call
// routes.BroadcastDataChange with no metadata (seatBroadcastFn) or with the camelCase actor stamp
// metadata.userId (the task/subtask facades), and the ported multi-recipient fan-out is theirs. Delete
// this case and a later tidy-up of the recipient keys would look safe.
func TestTheFanOutStillStoresForEveryUserMetadataNames(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	ctx := context.Background()
	previous := routes.MissedStore
	t.Cleanup(func() { routes.MissedStore = previous })

	if _, err := NewApp(ctx, sm); err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	if routes.MissedStore == nil {
		t.Fatal("NewApp did not assign routes.MissedStore: this case would pass vacuously")
	}

	const actor = "user-actor-1"
	const one = "user-one-1"
	const two = "user-two-2"

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("user_ids", []any{one, two})
	if err := routes.BroadcastDataChange(ctx, "updated", "task", "task-9", actor, nil, metadata); err != nil {
		t.Fatalf("BroadcastDataChange: %v", err)
	}
	for _, u := range []string{one, two, actor} {
		// The actor is here deliberately: the top-level user_id is ALWAYS a target (the offline store
		// adds it before it reads metadata), which is why a caller addressing only itself needs no
		// metadata at all - and why the route's refusal is about the extra recipient, not about the
		// caller's own inbox.
		if got := missedNotificationCount(t, sm, u); got != 1 {
			t.Fatalf("rows stored for %s = %d, want 1", u, got)
		}
	}
}

// postNotify posts a notify body with a bearer token and returns the status and the response body.
func postNotify(t *testing.T, serverURL, token, body string) (int, string) {
	t.Helper()
	req, err := http.NewRequest(http.MethodPost, serverURL+"/api/v2/broadcast/notify", bytes.NewBufferString(body))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(resp.Body)
	return resp.StatusCode, string(b)
}
