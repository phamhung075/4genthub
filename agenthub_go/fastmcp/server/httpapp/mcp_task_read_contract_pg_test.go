package httpapp

// manage_task's READ filters and its READ-ONLY address form, against a real database through the
// real MCP route. Both halves are contracts a seat depends on:
//
//   - ONE published spelling per concept. list and search filter by `assignees` and `labels` - the
//     same keys create and update take - and the singular `assignee`/`tag` are NOT published and NOT
//     honoured. The defect this pins: the filter allowlist dropped the plural keys before the handler
//     saw them, so `assignees` answered with the whole board while the schema offered it.
//   - The room cites tasks by an 8-hex prefix. get/resume RESOLVE a unique prefix; an ambiguous one
//     REFUSES and names the candidates; writes stay canonical, so a prefix can never change a row.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -run 'TestMCPListFiltersByThePublishedSpellings|TestMCPGetResolvesAPrefixAndWritesDoNot' ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	readFilterUserID   = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
	readFilterBranchID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
	readFilterProject  = "ffffffff-ffff-4fff-8fff-ffffffffffff"
	readFilterLabelID  = "label-red"
)

// readFilterRows are seeded OLDEST FIRST. The fourth row SHARES its first eight hex characters with
// the first, so `11111111` is exactly the ambiguous prefix the refusal is about.
var readFilterRows = []struct{ id, title, seat string }{
	{"11111111-1111-4111-8111-111111111111", "filter a1", "@seat-a"},
	{"11111111-9999-4999-8999-999999999999", "filter a1 twin", "@seat-a"},
	{"22222222-2222-4222-8222-222222222222", "filter b1", "@seat-b"},
	{"33333333-3333-4333-8333-333333333333", "filter b2", "@seat-b"},
}

func readFilterSeed(t *testing.T, sm *database.SessionManager) {
	t.Helper()
	now := time.Now().UTC().Truncate(time.Microsecond)
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'read filter','',$2,$2,$3,'active','{}') ON CONFLICT (id) DO NOTHING`,
		readFilterProject, now.Add(-time.Hour), readFilterUserID)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'read filter branch','',$3,$3,'medium','todo','{}',0,0,$4) ON CONFLICT (id) DO NOTHING`,
		readFilterBranchID, readFilterProject, now.Add(-time.Hour), readFilterUserID)
	for i, row := range readFilterRows {
		created := now.Add(time.Duration(i) * time.Minute)
		ledgerExec(t, sm, `INSERT INTO tasks (id, title, description, git_branch_id, status, priority,
			estimated_effort, created_at, updated_at, completion_summary, testing_notes,
			progress_percentage, progress_state, user_id)
			VALUES ($1::uuid, $2, 'read filter seed', $3::uuid, 'todo', 'medium', '',
			$4, $4, '', '', 0, 'INITIAL', $5)`,
			row.id, row.title, readFilterBranchID, created, readFilterUserID)
		ledgerExec(t, sm, `INSERT INTO task_assignees (id, task_id, assignee_id, role, user_id, assigned_at)
			VALUES (gen_random_uuid(), $1::uuid, $2, 'assignee', $3, $4)`,
			row.id, row.seat, readFilterUserID, created)
	}
	// One label on ONE row, so a label filter that is ignored is visible as four rows rather than one.
	ledgerExec(t, sm, `INSERT INTO labels (id, name, color, description, user_id, created_at, updated_at)
		VALUES ($1,'red','','',$2,$3,$3) ON CONFLICT (id) DO NOTHING`,
		readFilterLabelID, readFilterUserID, now.Add(-time.Hour))
	ledgerExec(t, sm, `INSERT INTO task_labels (task_id, label_id, user_id, applied_at)
		VALUES ($1::uuid, $2, $3, $4)`,
		readFilterRows[0].id, readFilterLabelID, readFilterUserID, now)
}

// readFilterApp builds the app the same way the list-paging case does: dev mode, no auth, one user.
func readFilterApp(t *testing.T, sm *database.SessionManager) *App {
	t.Helper()
	t.Setenv("ENV", "dev")
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("DEFAULT_USER_ID", readFilterUserID)
	app, err := NewApp(context.Background(), sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	return app
}

// TestMCPListFiltersByThePublishedSpellings is the contract for the plural spelling. The array and
// the comma-separated string reach the same filter, the label filter selects, and the singular the
// schema no longer publishes filters NOTHING rather than acting as an alias.
func TestMCPListFiltersByThePublishedSpellings(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	app := readFilterApp(t, sm)
	readFilterSeed(t, sm)

	// The schema publishes one spelling. Reading the tool list is how a caller learns the surface, so
	// a singular that still appears there is a published promise the handler does not keep.
	schema := mcpToolsListBody(t, app)
	manageTask := schema["manage_task"].(map[string]any)
	schemaKey := "parameters"
	if _, ok := manageTask[schemaKey].(map[string]any); !ok {
		schemaKey = "inputSchema"
	}
	properties, ok := manageTask[schemaKey].(map[string]any)["properties"].(map[string]any)
	if !ok {
		t.Fatalf("manage_task's published schema has no properties under %q: %v", schemaKey, manageTask)
	}
	for _, gone := range []string{"assignee", "tag"} {
		if _, present := properties[gone]; present {
			t.Errorf("manage_task still publishes %q; the filter's one spelling is assignees/labels", gone)
		}
	}
	for _, present := range []string{"assignees", "labels"} {
		if _, ok := properties[present]; !ok {
			t.Errorf("manage_task does not publish %q, which list and search filter by", present)
		}
	}

	cases := []struct {
		name  string
		args  string
		want  []string
		whole bool
	}{
		{name: "array", args: `"assignees":["@seat-a"]`, want: []string{readFilterRows[0].id, readFilterRows[1].id}},
		{name: "comma string", args: `"assignees":"@seat-a"`, want: []string{readFilterRows[0].id, readFilterRows[1].id}},
		{name: "two seats", args: `"assignees":["@seat-a","@seat-b"]`, want: []string{
			readFilterRows[0].id, readFilterRows[1].id, readFilterRows[2].id, readFilterRows[3].id}},
		{name: "labels", args: `"labels":["red"]`, want: []string{readFilterRows[0].id}},
		// The removed spelling is NOT an alias: the key is dropped before the handler, so the request
		// is answered unfiltered. That is why the schema must not offer it.
		{name: "removed singular", args: `"assignee":"@seat-a"`, whole: true},
	}
	for _, c := range cases {
		page := mcpListPage(t, app, c.args+`,"limit":50`)
		if c.whole {
			if len(page.ids) != len(readFilterRows) {
				t.Errorf("%s: filtered to %v; a key the schema does not publish must not filter", c.name, page.ids)
			}
			continue
		}
		if len(page.ids) != len(c.want) {
			t.Errorf("%s: %d rows %v, want %d %v", c.name, len(page.ids), page.ids, len(c.want), c.want)
			continue
		}
		for _, id := range c.want {
			if !containsID(page.ids, id) {
				t.Errorf("%s: %v is missing from %v", c.name, id, page.ids)
			}
		}
		if page.total != len(c.want) {
			t.Errorf("%s: total = %d, want the %d rows the filter selects", c.name, page.total, len(c.want))
		}
	}
}

// TestMCPGetResolvesAPrefixAndWritesDoNot is the read-only address form: a unique prefix names its
// task, an ambiguous one REFUSES with the candidates named, and a write still needs the canonical id.
func TestMCPGetResolvesAPrefixAndWritesDoNot(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	app := readFilterApp(t, sm)
	readFilterSeed(t, sm)

	unique := mcpGet(t, app, readFilterRows[2].id[:8])
	if !unique.success {
		t.Fatalf("a unique prefix did not resolve: %s", unique.raw)
	}
	if got := unique.id; got != readFilterRows[2].id {
		t.Fatalf("prefix resolved to %q, want %q", got, readFilterRows[2].id)
	}

	ambiguous := mcpGet(t, app, readFilterRows[0].id[:8])
	if ambiguous.success {
		t.Fatalf("an ambiguous prefix resolved: %s", ambiguous.raw)
	}
	for _, id := range []string{readFilterRows[0].id, readFilterRows[1].id} {
		if !strings.Contains(ambiguous.raw, id) {
			t.Errorf("the refusal does not name %s: %s", id, ambiguous.raw)
		}
	}

	// WRITES STAY CANONICAL. A complete by prefix must not resolve; the row's status is untouched.
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"complete","task_id":"`+
		readFilterRows[2].id[:8]+`","completion_summary":"a prefix must not complete a task"}}}`, "")
	if rec.Code != 200 {
		t.Fatalf("complete status = %d", rec.Code)
	}
	var wire struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil || len(wire.Result.Content) == 0 {
		t.Fatalf("complete decode: %v %s", err, rec.Body.String())
	}
	var wrote struct {
		Success bool `json:"success"`
	}
	if err := json.Unmarshal([]byte(wire.Result.Content[0].Text), &wrote); err != nil {
		t.Fatalf("complete answer is not JSON: %v %s", err, wire.Result.Content[0].Text)
	}
	if wrote.Success {
		t.Errorf("a prefix completed a task: %s", wire.Result.Content[0].Text)
	}
	page := mcpListPage(t, app, `"status":"todo","limit":50`)
	if !containsID(page.ids, readFilterRows[2].id) {
		t.Errorf("the row left todo, so a prefix write landed: %v", page.ids)
	}
}

type mcpGetResult struct {
	success bool
	id      string
	raw     string
}

// mcpGet posts one manage_task get and reports the envelope's answer, keeping the raw text because
// the ambiguity refusal is read from it.
func mcpGet(t *testing.T, app *App, taskID string) mcpGetResult {
	t.Helper()
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"get","task_id":"`+taskID+`"}}}`, "")
	if rec.Code != 200 {
		t.Fatalf("get status = %d", rec.Code)
	}
	var wire struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil || len(wire.Result.Content) == 0 {
		t.Fatalf("get decode: %v %s", err, rec.Body.String())
	}
	text := wire.Result.Content[0].Text
	out := mcpGetResult{raw: text}
	var payload struct {
		Success bool `json:"success"`
		Data    struct {
			Task struct {
				ID string `json:"id"`
			} `json:"task"`
		} `json:"data"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err == nil {
		out.success = payload.Success
		out.id = payload.Data.Task.ID
	}
	return out
}

// mcpToolsListBody returns tools/list's manage_task entry, keyed by tool name.
func mcpToolsListBody(t *testing.T, app *App) map[string]any {
	t.Helper()
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")
	if rec.Code != 200 {
		t.Fatalf("tools/list status = %d", rec.Code)
	}
	var wire struct {
		Result struct {
			Tools []map[string]any `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("tools/list decode: %v", err)
	}
	out := map[string]any{}
	for _, tool := range wire.Result.Tools {
		if name, ok := tool["name"].(string); ok {
			out[name] = tool
		}
	}
	if _, ok := out["manage_task"]; !ok {
		t.Fatalf("tools/list does not carry manage_task: %d tools", len(out))
	}
	return out
}

func containsID(ids []string, id string) bool {
	for _, have := range ids {
		if have == id {
			return true
		}
	}
	return false
}
