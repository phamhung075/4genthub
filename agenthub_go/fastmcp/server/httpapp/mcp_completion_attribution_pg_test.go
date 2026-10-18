package httpapp

// A SECOND `manage_task complete` ON A DONE TASK: no silent rewrite, an author on the line, and the
// line it replaces still legible (board task ca541a97).
//
// The measured defect: a seat completing an already-done task purely to test idempotence replaced the
// row's result line - another seat's evidence - answered success, and left no record of who wrote the
// new sentence or when. The write was defensible; the SILENCE was not.
//
// This is the endpoint-level proof, because the three properties it asserts live in three layers: the
// gate is in the use case, the attribution is a column the read path must now carry, and the
// superseded line is a ledger entry served by /api/v2/tasks/{id}/events.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -run 'TestMCPCompleteOnADoneTask' ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/mcpblock"
)

const (
	attributionSeatA = "4genthub-min/go-dev"
	attributionSeatB = "4genthub-min/fe-dev"

	attributionFirst  = "the first result line, written by go-dev"
	attributionSecond = "fe-dev replacing the line without a flag, which must be refused"
	attributionThird  = "the corrected result line, written by fe-dev with correction=true"
)

// mcpTaskCall drives manage_task with an optional seat header and returns the decoded payload, so a
// refusal can be inspected instead of failing the test.
func mcpTaskCall(t *testing.T, app *App, token, seat, action, args string) (task map[string]any, text string, success bool) {
	t.Helper()
	mux := newMCPMux(app)
	rec := postMCPWithSeat(t, mux, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"`+action+`",`+args+`}}}`, token, seat)
	if rec.Code != 200 {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode: %v\n%s", err, rec.Body.String())
	}
	if len(wire.Result.Content) == 0 {
		t.Fatalf("no content: %s", rec.Body.String())
	}
	text = wire.Result.Content[0].Text
	var payload struct {
		Success bool `json:"success"`
		Data    struct {
			Task map[string]any `json:"task"`
		} `json:"data"`
		Task map[string]any `json:"task"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("decode payload: %v\n%s", err, text)
	}
	if payload.Data.Task != nil {
		return payload.Data.Task, text, payload.Success
	}
	return payload.Task, text, payload.Success
}

func newMCPMux(app *App) *http.ServeMux {
	mux := http.NewServeMux()
	app.registerMCPRoutes(mux)
	return mux
}

func postMCPWithSeat(t *testing.T, mux *http.ServeMux, payload, token, seat string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest("POST", "/mcp", strings.NewReader(payload))
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	if seat != "" {
		req.Header.Set(mcpblock.SeatHeader, seat)
	}
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

func TestMCPCompleteOnADoneTaskIsAttributedAndGated(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("ENV", "dev")
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)
	token := wsTestTokenFor(t, completionUserID, []string{"tasks:create", "tasks:update", "tasks:read"})
	app, err := NewApp(context.Background(), sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	completionSeed(t, sm)

	created, createText, ok := mcpTaskCall(t, app, token, "", "create",
		`"git_branch_id":"`+completionBranchID+`","title":"attribution row","assignees":["@go-dev"]`)
	if !ok {
		t.Fatalf("create failed: %s", createText)
	}
	taskID, _ := created["id"].(string)
	if taskID == "" {
		t.Fatalf("create answered no id; task = %v", created)
	}

	// 1. The first completion records WHO wrote the line and WHEN.
	if _, text, ok := mcpTaskCall(t, app, token, attributionSeatA, "complete",
		`"task_id":"`+taskID+`","completion_summary":`+jsonLiteral(attributionFirst)); !ok {
		t.Fatalf("the first completion failed: %s", text)
	}
	got, _, _ := mcpTaskCall(t, app, token, "", "get", `"task_id":"`+taskID+`"`)
	if got["completion_summary"] != attributionFirst {
		t.Fatalf("completion_summary = %#v", got["completion_summary"])
	}
	if got["completed_by"] != attributionSeatA {
		t.Fatalf("completed_by = %#v, want %q", got["completed_by"], attributionSeatA)
	}
	if at, _ := got["completed_at"].(string); at == "" {
		t.Fatalf("completed_at is absent: %v", keysOf(got))
	}

	// 2. ANOTHER SEAT, no flag: refused, and the line is untouched.
	_, text, ok := mcpTaskCall(t, app, token, attributionSeatB, "complete",
		`"task_id":"`+taskID+`","completion_summary":`+jsonLiteral(attributionSecond))
	if ok {
		t.Fatalf("a second seat replaced the result line without the flag: %s", text)
	}
	for _, want := range []string{attributionSeatA, "correction=true"} {
		if !strings.Contains(text, want) {
			t.Fatalf("the refusal does not name %q: %s", want, text)
		}
	}
	got, _, _ = mcpTaskCall(t, app, token, "", "get", `"task_id":"`+taskID+`"`)
	if got["completion_summary"] != attributionFirst {
		t.Fatalf("a refused call changed the line: %#v", got["completion_summary"])
	}
	if got["completed_by"] != attributionSeatA {
		t.Fatalf("a refused call changed the author: %#v", got["completed_by"])
	}

	// 3. WITH the flag: replaced, and the replacing seat is the author of record.
	if _, text, ok := mcpTaskCall(t, app, token, attributionSeatB, "complete",
		`"task_id":"`+taskID+`","completion_summary":`+jsonLiteral(attributionThird)+`,"correction":true`); !ok {
		t.Fatalf("the corrected completion failed: %s", text)
	}
	got, _, _ = mcpTaskCall(t, app, token, "", "get", `"task_id":"`+taskID+`"`)
	if got["completion_summary"] != attributionThird {
		t.Fatalf("completion_summary = %#v", got["completion_summary"])
	}
	if got["completed_by"] != attributionSeatB {
		t.Fatalf("completed_by = %#v, want the replacing seat", got["completed_by"])
	}

	// 4. THE OLD LINE IS STILL LEGIBLE: the replacement left a progress entry carrying it, attributed
	// to the seat that made the replacement.
	code, body := evidenceEventsGet(t, app, token, taskID)
	if code != 200 {
		t.Fatalf("GET /api/v2/tasks/{id}/events = %d: %s", code, body)
	}
	var read struct {
		Events []map[string]any `json:"events"`
	}
	if err := json.Unmarshal([]byte(body), &read); err != nil {
		t.Fatalf("decoding the events read: %v (%s)", err, body)
	}
	var superseded map[string]any
	for _, e := range read.Events {
		payload, _ := e["payload"].(map[string]any)
		if content, _ := payload["content"].(string); strings.Contains(content, "superseded") {
			superseded = e
		}
	}
	if superseded == nil {
		t.Fatalf("no superseded entry in the ledger: %s", body)
	}
	payload, _ := superseded["payload"].(map[string]any)
	content, _ := payload["content"].(string)
	for _, want := range []string{attributionFirst, attributionSeatA, attributionSeatB} {
		if !strings.Contains(content, want) {
			t.Fatalf("the superseded entry does not name %q: %s", want, content)
		}
	}
	if superseded["actor_id"] != attributionSeatB {
		t.Fatalf("the superseded entry is attributed to %#v, want %q", superseded["actor_id"], attributionSeatB)
	}

	// 5. NOTHING NEW IS A NO-OP: repeating the completion writes no second entry.
	before := len(read.Events)
	if _, text, ok := mcpTaskCall(t, app, token, attributionSeatB, "complete",
		`"task_id":"`+taskID+`","completion_summary":`+jsonLiteral(attributionThird)); !ok {
		t.Fatalf("the repeated completion failed: %s", text)
	}
	code, body = evidenceEventsGet(t, app, token, taskID)
	if code != 200 {
		t.Fatalf("the second events read = %d: %s", code, body)
	}
	var again struct {
		Events []map[string]any `json:"events"`
	}
	if err := json.Unmarshal([]byte(body), &again); err != nil {
		t.Fatalf("decoding the second events read: %v (%s)", err, body)
	}
	if len(again.Events) != before {
		t.Fatalf("a repeated completion wrote %d new entries, want none: %s", len(again.Events)-before, body)
	}
}
