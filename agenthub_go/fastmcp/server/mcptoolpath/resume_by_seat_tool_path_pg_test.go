package mcptoolpath

// 4/8's hub half through the production seam: `manage_task action=resume` with NO task_id resolves
// the task held in_progress by the CALLER SEAT - the seat is the request's own X-Agenthub-Seat
// header, exactly the attribution the ledger writes under - and answers `no_task_for_seat`, naming
// the two fixes, when there is none. The seat key is never a parameter, so another seat's header
// cannot reach this seat's task.

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/server/httpapp"
	"agenthub/fastmcp/session_stream/testdb"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// callToolSeat is callTool with the seat header the rendered MCP block carries
// (mcpblock.SeatHeader); an empty seat sends no header at all.
func callToolSeat(t *testing.T, app *httpapp.App, name string, args map[string]any, seat string) (any, bool) {
	t.Helper()
	body, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{"name": name, "arguments": args},
	})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest("POST", "/mcp", strings.NewReader(string(body)))
	req.Header.Set("Content-Type", "application/json")
	if seat != "" {
		req.Header.Set("X-Agenthub-Seat", seat)
	}
	req.RemoteAddr = "127.0.0.1:1234"
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)

	var envelope struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
			IsError bool `json:"isError"`
		} `json:"result"`
		Error *struct {
			Message string `json:"message"`
		} `json:"error"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &envelope); err != nil {
		t.Fatalf("decoding the JSON-RPC response: %v (body=%s)", err, rec.Body.String())
	}
	if envelope.Error != nil {
		t.Fatalf("%s returned a JSON-RPC error: %s", name, envelope.Error.Message)
	}
	if len(envelope.Result.Content) == 0 {
		t.Fatalf("%s returned no content: %s", name, rec.Body.String())
	}
	var payload any
	if err := json.Unmarshal([]byte(envelope.Result.Content[0].Text), &payload); err != nil {
		t.Fatalf("decoding %s's payload: %v (payload=%s)", name, err, envelope.Result.Content[0].Text)
	}
	return payload, envelope.Result.IsError
}

// resumeErrorText is the message of a refused tool call, or "" when the call succeeded. The MCP
// payload nests it as {"error":{"code","message"}}; the walk covers that shape and a flat one.
func resumeErrorText(payload any) string {
	switch v := payload.(type) {
	case map[string]any:
		if errObj, ok := v["error"].(map[string]any); ok {
			if msg, ok := errObj["message"].(string); ok {
				return msg
			}
		}
		if msg, ok := v["error"].(string); ok {
			return msg
		}
		for _, child := range v {
			if msg := resumeErrorText(child); msg != "" {
				return msg
			}
		}
	case []any:
		for _, child := range v {
			if msg := resumeErrorText(child); msg != "" {
				return msg
			}
		}
	}
	return ""
}

func TestResumeWithoutTaskIDResolvesTheRequestSeat(t *testing.T) {
	sessions := testdb.NewSessions(t)
	user := tmvo.NewUUIDv4()
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("DEFAULT_USER_ID", user)

	app, err := httpapp.NewApp(context.Background(), sessions)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	branchID := seedBranch(t, sessions, user)

	createRes, isErr := callTool(t, app, "manage_task", map[string]any{
		"action": "create", "git_branch_id": branchID, "title": "4/8 resume-by-seat",
		"assignees":           "@go-dev",
		"acceptance_criteria": []string{"the seat's own task comes back"},
	})
	if isErr {
		t.Fatalf("manage_task create reported an error: %v", createRes)
	}
	created, ok := findMapWith(createRes, "acceptance_criteria")
	if !ok {
		t.Fatalf("create returned no task: %v", createRes)
	}
	taskID := fmt.Sprint(created["id"])
	if taskID == "" || taskID == "<nil>" {
		t.Fatalf("create returned no task id: %v", createRes)
	}
	if _, isErr := callTool(t, app, "manage_task", map[string]any{
		"action": "update", "task_id": taskID, "status": "in_progress",
		"details": "in_progress so the resume-by-seat resolution has a candidate",
	}); isErr {
		t.Fatalf("moving the task to in_progress failed")
	}

	// The seat's own call, with NO task_id: the brief is the task above.
	payload, isErr := callToolSeat(t, app, "manage_task", map[string]any{"action": "resume"},
		"4genthub-min/go-dev")
	if isErr {
		t.Fatalf("resume with no task_id reported an error: %v", payload)
	}
	if text := resumeErrorText(payload); text != "" {
		t.Fatalf("resume refused the seat: %s", text)
	}
	brief, ok := findMapWith(payload, "acceptance_criteria")
	if !ok {
		t.Fatalf("resume returned no brief: %v", payload)
	}
	taskSection, ok := brief["task"].(map[string]any)
	if !ok {
		t.Fatalf("the brief carries no task section: %v", brief)
	}
	if got := fmt.Sprint(taskSection["id"]); got != taskID {
		t.Fatalf("resolved task = %s, want the seat's own %s", got, taskID)
	}
	if got := brief["next_action"]; got == nil || fmt.Sprint(got) == "" {
		t.Fatalf("the brief carries no next_action: %v", brief)
	}

	// ANOTHER SEAT cannot reach this task by naming it: its own header resolves nothing.
	payload, _ = callToolSeat(t, app, "manage_task", map[string]any{"action": "resume"},
		"4genthub-min/fe-dev")
	if raw, err := json.Marshal(payload); err == nil {
		t.Logf("OBSERVED another seat's resume payload: %s", raw)
	}
	text := resumeErrorText(payload)
	if !strings.Contains(text, "no_task_for_seat") {
		t.Fatalf("another seat's resume error = %q, want the no_task_for_seat token", text)
	}
	for _, want := range []string{"claim a queue item", "pass task_id"} {
		if !strings.Contains(text, want) {
			t.Fatalf("the refusal names no %q fix: %q", want, text)
		}
	}

	// NO SEAT HEADER is not a seat: the same refusal, never a guessed identity.
	payload, _ = callTool(t, app, "manage_task", map[string]any{"action": "resume"})
	if text := resumeErrorText(payload); !strings.Contains(text, "no_task_for_seat") {
		t.Fatalf("an unattributed resume error = %q, want the no_task_for_seat token", text)
	}
}
