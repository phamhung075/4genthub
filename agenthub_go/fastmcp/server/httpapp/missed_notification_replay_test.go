package httpapp

import (
	"bufio"
	"bytes"
	"context"
	"database/sql"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"
	"time"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// newMissedNotificationAppEnv creates a throwaway database (AGENTHUB_TEST_PG_URL, see
// tools/testpg) with all tables and returns a session manager over it.
func newMissedNotificationAppEnv(t *testing.T) *database.SessionManager {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("AGENTHUB_TEST_PG_URL not set")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	name := fmt.Sprintf("agenthub_httpapp_missed_%d", time.Now().UnixNano())
	if _, err := adm.Exec("CREATE DATABASE " + name); err != nil {
		t.Fatal(err)
	}
	adm.Close()
	u, _ := url.Parse(admin)
	u.Path = "/" + name
	env := map[string]string{"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "x", "DATABASE_PASSWORD": "x"}
	database.ResetInstance()
	deps := database.Deps{
		Getenv: func(k string) (string, bool) { v, ok := env[k]; return v, ok },
		Sleep:  func(time.Duration) {},
		Open: func(string, database.EngineOptions) (*sql.DB, error) {
			return database.PgxOpener(u.String(), database.EngineOptions{PoolSize: 4, MaxOverflow: 4, PoolRecycle: 60})
		},
	}
	cfg, err := database.GetInstance(context.Background(), deps)
	if err != nil {
		t.Fatal(err)
	}
	if err := cfg.CreateTables(context.Background()); err != nil {
		t.Fatal(err)
	}
	database.SetupTimestampEvents()
	t.Cleanup(func() {
		database.ResetInstance()
		adm, err := sql.Open("pgx", admin)
		if err == nil {
			_, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)")
			adm.Close()
		}
	})
	return database.NewSessionManager(cfg)
}

func missedNotificationCount(t *testing.T, sm *database.SessionManager, userID string) int {
	t.Helper()
	count := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM "missed_notifications" WHERE "user_id" = $1`, userID).Scan(&count)
	}); err != nil {
		t.Fatal(err)
	}
	return count
}

func missedNotificationDelivered(t *testing.T, sm *database.SessionManager, userID string) bool {
	t.Helper()
	delivered := false
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(context.Background(),
			`SELECT "delivered" FROM "missed_notifications" WHERE "user_id" = $1`, userID).Scan(&delivered)
	}); err != nil {
		t.Fatal(err)
	}
	return delivered
}

// wsTryReadFrame is wsTestReadFrame that returns the read error instead of failing, so a test can
// assert that no frame arrives within a deadline.
func wsTryReadFrame(br *bufio.Reader) (byte, []byte, error) {
	header := make([]byte, 2)
	if _, err := io.ReadFull(br, header); err != nil {
		return 0, nil, err
	}
	opcode := header[0] & 0x0f
	length := int64(header[1] & 0x7f)
	switch length {
	case 126:
		ext := make([]byte, 2)
		if _, err := io.ReadFull(br, ext); err != nil {
			return 0, nil, err
		}
		length = int64(binary.BigEndian.Uint16(ext))
	case 127:
		ext := make([]byte, 8)
		if _, err := io.ReadFull(br, ext); err != nil {
			return 0, nil, err
		}
		length = int64(binary.BigEndian.Uint64(ext))
	}
	payload := make([]byte, length)
	if _, err := io.ReadFull(br, payload); err != nil {
		return 0, nil, err
	}
	return opcode, payload, nil
}

// TestMissedNotificationStoredOfflineAndReplayedOnce is the store -> replay proof on a real
// database through the production wiring: NewApp assigns routes.MissedStore, a POST while no socket
// is connected stores a row for the target user (and only that user), the next connect replays the
// frame, and a second connect does not deliver it again.
func TestMissedNotificationStoredOfflineAndReplayedOnce(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	ctx := context.Background()
	previous := routes.MissedStore
	t.Cleanup(func() { routes.MissedStore = previous })

	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	if routes.MissedStore == nil {
		t.Fatal("NewApp did not assign routes.MissedStore: offline notifications would be dropped")
	}

	const target = "user-target-1"
	const other = "user-other-2"
	targetToken := wsTestTokenFor(t, target, nil)
	otherToken := wsTestTokenFor(t, other, nil)

	// ac2d6106: the notify ingress takes the user token and the target user is that token's user,
	// never the body's. The token below belongs to `target`; the body posted below names `other`
	// in its user_id field to prove that field cannot move the write.

	server := httptest.NewServer(app.Handler())
	defer server.Close()

	// No websocket is connected, so the target is offline and the payload must be persisted.
	// The producer puts the notification payload in `data`; BroadcastDataChange copies it to
	// payload.data.primary, which is the frame the frontend consumer reads.
	body := `{"event_type":"notification","entity_type":"notification","entity_id":"msg-live-1",` +
		`"user_id":"` + other + `","data":{"id":"msg-live-1","title":"live notification"},` +
		`"metadata":{"user_id":"` + target + `"}}`
	req, err := http.NewRequest(http.MethodPost, server.URL+"/api/v2/broadcast/notify", bytes.NewBufferString(body))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	// The token names `target`; the body's user_id names `other` and must not move it.
	req.Header.Set("Authorization", "Bearer "+targetToken)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	respBody, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("POST /api/v2/broadcast/notify status = %d body=%s", resp.StatusCode, respBody)
	}
	var sent map[string]any
	if err := json.Unmarshal(respBody, &sent); err != nil {
		t.Fatal(err)
	}
	if sent["status"] != "broadcast_sent" {
		t.Fatalf("notify body = %s, want broadcast_sent", respBody)
	}

	if got := missedNotificationCount(t, sm, target); got != 1 {
		t.Fatalf("rows stored for %s = %d, want 1 (with MissedStore wired the offline POST persists)", target, got)
	}
	if got := missedNotificationCount(t, sm, other); got != 0 {
		t.Fatalf("rows stored for %s = %d, want 0", other, got)
	}

	// First reconnect as the target: the welcome frame, then the replayed notification frame.
	conn, br := wsTestDial(t, server.URL, "/ws/realtime?token="+url.QueryEscape(targetToken))
	opcode, payload := wsTestReadFrame(t, br)
	if opcode != wsOpText {
		t.Fatalf("welcome opcode = %d", opcode)
	}
	if welcome := wsTestJSON(t, payload); welcome["type"] != "sync" {
		t.Fatalf("welcome type = %v", welcome["type"])
	}
	conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	opcode, payload = wsTestReadFrame(t, br)
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
	if primary["id"] != "msg-live-1" || primary["title"] != "live notification" {
		t.Fatalf("replayed data.primary = %v, want the posted primary", primary)
	}
	meta, _ := frame["metadata"].(map[string]any)
	if meta["entity_id"] != "msg-live-1" {
		t.Fatalf("replayed metadata.entity_id = %v, want msg-live-1", meta["entity_id"])
	}
	conn.Close()

	// The replay marks the row delivered.
	deadline := time.Now().Add(2 * time.Second)
	for !missedNotificationDelivered(t, sm, target) {
		if time.Now().After(deadline) {
			t.Fatal("replayed notification was not marked delivered")
		}
		time.Sleep(20 * time.Millisecond)
	}

	// Second reconnect as the target: welcome only, the notification must NOT replay again.
	conn2, br2 := wsTestDial(t, server.URL, "/ws/realtime?token="+url.QueryEscape(targetToken))
	if _, payload, err := wsTryReadFrame(br2); err != nil {
		t.Fatalf("second reconnect welcome: %v", err)
	} else if welcome := wsTestJSON(t, payload); welcome["type"] != "sync" {
		t.Fatalf("second reconnect welcome type = %v", welcome["type"])
	}
	_ = conn2.SetReadDeadline(time.Now().Add(700 * time.Millisecond))
	if opcode, payload, err := wsTryReadFrame(br2); err == nil {
		t.Fatalf("second reconnect replayed a notification again (opcode=%d): %s", opcode, payload)
	}
	conn2.Close()

	// A different user must receive nothing: welcome only, and no frame for them in the database.
	conn3, br3 := wsTestDial(t, server.URL, "/ws/realtime?token="+url.QueryEscape(otherToken))
	if _, payload, err := wsTryReadFrame(br3); err != nil {
		t.Fatalf("other user welcome: %v", err)
	} else if welcome := wsTestJSON(t, payload); welcome["type"] != "sync" {
		t.Fatalf("other user welcome type = %v", welcome["type"])
	}
	_ = conn3.SetReadDeadline(time.Now().Add(700 * time.Millisecond))
	if opcode, payload, err := wsTryReadFrame(br3); err == nil {
		t.Fatalf("other user received a frame (opcode=%d): %s", opcode, payload)
	}
	conn3.Close()

	if got := missedNotificationCount(t, sm, other); got != 0 {
		t.Fatalf("rows for %s after the round trip = %d, want 0", other, got)
	}
}
