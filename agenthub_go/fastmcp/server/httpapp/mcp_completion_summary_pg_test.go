package httpapp

// `manage_task complete` stores a completion summary; `manage_task get` must return it verbatim.
//
// The defect (board task 5420da8e): the repository read the summary back onto the entity, but the
// response DTO had no field for it, so ToDict dropped it and a closure whose only record is the
// summary could not be read back - the board is this pod's system of record.
//
// This is the endpoint-level proof, because the defect lived between two layers that each looked
// right: complete writes, get reads from the same table, and the key is missing from the answer.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -run 'TestMCPCompleteSummaryIsReadableFromGet' ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	completionUserID   = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
	completionBranchID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
	completionProject  = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"

	// Long enough for the completion validator (20 chars) and distinctive, so a match cannot be
	// an accident of a shared prefix.
	completionText = "landed the schema guard; 12 rows audited; no drift found"
)

func completionSeed(t *testing.T, sm *database.SessionManager) {
	t.Helper()
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'completion project','',now(),now(),$2,'active','{}')`,
		completionProject, completionUserID)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'completion branch','',now(),now(),'medium','todo','{}',0,0,$3)`,
		completionBranchID, completionProject, completionUserID)
}

// mcpTaskField calls manage_task with the given action/arguments and returns data.task.
func mcpTaskField(t *testing.T, app *App, action, args string) map[string]any {
	t.Helper()
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"`+action+`",`+args+`}}}`, "")
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
	// The MCP envelope standardizes every tool result as {success, operation, data}; the facade's
	// own `task` key lives one level down for get and complete alike.
	var payload struct {
		Success bool `json:"success"`
		Data    struct {
			Task map[string]any `json:"task"`
		} `json:"data"`
		Task map[string]any `json:"task"`
	}
	if err := json.Unmarshal([]byte(wire.Result.Content[0].Text), &payload); err != nil {
		t.Fatalf("decode payload: %v\n%s", err, wire.Result.Content[0].Text)
	}
	if !payload.Success {
		t.Fatalf("%s did not succeed: %s", action, wire.Result.Content[0].Text)
	}
	if payload.Data.Task != nil {
		return payload.Data.Task
	}
	return payload.Task
}

func TestMCPCompleteSummaryIsReadableFromGet(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("ENV", "dev")
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("DEFAULT_USER_ID", completionUserID)
	app, err := NewApp(context.Background(), sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	completionSeed(t, sm)
	created := mcpTaskField(t, app, "create",
		`"git_branch_id":"`+completionBranchID+`","title":"completion row","assignees":["@go-dev"]`)
	rawID, ok := created["id"].(string)
	if !ok {
		t.Fatalf("create answered no id; task = %v", created)
	}
	taskID := rawID

	mcpTaskField(t, app, "complete",
		`"task_id":"`+taskID+`","completion_summary":`+jsonLiteral(completionText))

	got := mcpTaskField(t, app, "get", `"task_id":"`+taskID+`"`)
	summary, ok := got["completion_summary"]
	if !ok {
		t.Fatalf("get answered no completion_summary key; keys = %v", keysOf(got))
	}
	if summary != completionText {
		t.Fatalf("completion_summary = %#v, want %q verbatim", summary, completionText)
	}

	// An un-completed task carries no summary, and the optimizer's documented rule is that an
	// empty string is dropped rather than served as a placeholder - "no summary" is expressed by
	// the key's absence, never by a value that could be mistaken for a stored one.
	ledgerExec(t, sm, `UPDATE tasks SET completion_summary = '' WHERE id = $1::uuid`, taskID)
	got = mcpTaskField(t, app, "get", `"task_id":"`+taskID+`"`)
	if v, ok := got["completion_summary"]; ok {
		t.Fatalf("cleared completion_summary = %#v, want the key absent", v)
	}
}

func jsonLiteral(s string) string {
	b, _ := json.Marshal(s)
	return string(b)
}

func keysOf(m map[string]any) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}
