package httpapp

// manage_task action=list against a REAL database through the REAL MCP route: the enumeration
// contract is a claim about SQL, the paging window and the response block at once, and a fake would
// write its own hypothesis back.
//
// What only this test can answer, and the unit cases cannot:
//   - two consecutive tools/call list pages share NO row (the defect: page 2 was page 1, because
//     offset was echoed into pagination but never bound into the query);
//   - the OLDEST row is reachable by paging, so the board can be enumerated;
//   - pagination.total is the count the filters select, not the length of the page.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -run 'TestMCPListPagingPagesThroughTheBoard' ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	listPagingUserID   = "77777777-7777-4777-8777-777777777777"
	listPagingBranchID = "88888888-8888-4888-8888-888888888888"
	listPagingProject  = "99999999-9999-4999-8999-999999999999"
)

// listPagingTaskIDs are seeded OLDEST FIRST; updated_at ascends with them, so the default ordering
// (updated_at DESC) returns them reversed and the last page carries the first id.
var listPagingTaskIDs = []string{
	"aaaaaaa1-0000-4000-8000-000000000001",
	"aaaaaaa1-0000-4000-8000-000000000002",
	"aaaaaaa1-0000-4000-8000-000000000003",
	"aaaaaaa1-0000-4000-8000-000000000004",
	"aaaaaaa1-0000-4000-8000-000000000005",
}

func listPagingSeed(t *testing.T, sm *database.SessionManager) {
	t.Helper()
	now := time.Now().UTC().Truncate(time.Microsecond)
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'paging project','',$2,$2,$3,'active','{}') ON CONFLICT (id) DO NOTHING`,
		listPagingProject, now.Add(-time.Hour), listPagingUserID)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'paging branch','',$3,$3,'medium','todo','{}',0,0,$4) ON CONFLICT (id) DO NOTHING`,
		listPagingBranchID, listPagingProject, now.Add(-time.Hour), listPagingUserID)
	for i, id := range listPagingTaskIDs {
		created := now.Add(time.Duration(i-10) * time.Minute)
		ledgerExec(t, sm, `INSERT INTO tasks (id, title, description, git_branch_id, status, priority,
			estimated_effort, created_at, updated_at, completion_summary, testing_notes,
			progress_percentage, progress_state, user_id)
			VALUES ($1::uuid, $2, 'paging seed', $3::uuid, 'todo', 'medium', '', $4, $5, '', '', 0, 'INITIAL', $6)`,
			id, "paging row "+id[len(id)-1:], listPagingBranchID, created, created, listPagingUserID)
	}
}

type listPage struct {
	ids     []string
	total   int
	limit   int
	offset  int
	hasMore bool
}

func mcpListPage(t *testing.T, app *App, args string) listPage {
	t.Helper()
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"list",`+args+`}}}`, "")
	if rec.Code != 200 {
		t.Fatalf("status = %d, body = %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
		Error any `json:"error"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode: %v\n%s", err, rec.Body.String())
	}
	if len(wire.Result.Content) == 0 {
		t.Fatalf("no content: %s", rec.Body.String())
	}
	var payload struct {
		Success bool `json:"success"`
		Data    struct {
			Tasks      []map[string]any `json:"tasks"`
			Pagination struct {
				Total   int  `json:"total"`
				Limit   int  `json:"limit"`
				Offset  int  `json:"offset"`
				HasMore bool `json:"has_more"`
			} `json:"pagination"`
		} `json:"data"`
	}
	if err := json.Unmarshal([]byte(wire.Result.Content[0].Text), &payload); err != nil {
		t.Fatalf("decode payload: %v\n%s", err, wire.Result.Content[0].Text)
	}
	if !payload.Success {
		t.Fatalf("list did not succeed: %s", wire.Result.Content[0].Text)
	}
	page := listPage{
		total:   payload.Data.Pagination.Total,
		limit:   payload.Data.Pagination.Limit,
		offset:  payload.Data.Pagination.Offset,
		hasMore: payload.Data.Pagination.HasMore,
	}
	for _, task := range payload.Data.Tasks {
		page.ids = append(page.ids, task["id"].(string))
	}
	return page
}

func TestMCPListPagingPagesThroughTheBoard(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("ENV", "dev")
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("DEFAULT_USER_ID", listPagingUserID)
	app, err := NewApp(context.Background(), sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	listPagingSeed(t, sm)

	first := mcpListPage(t, app, `"limit":2,"offset":0`)
	second := mcpListPage(t, app, `"limit":2,"offset":2`)
	third := mcpListPage(t, app, `"limit":2,"offset":4`)

	if first.total != len(listPagingTaskIDs) {
		t.Fatalf("pagination.total = %d, want the board's %d", first.total, len(listPagingTaskIDs))
	}
	if !first.hasMore || first.hasMore != second.hasMore {
		t.Fatalf("has_more: page1=%v page2=%v, want true then true", first.hasMore, second.hasMore)
	}
	if third.hasMore {
		t.Fatalf("last page says has_more: %d rows from offset 4 of %d", len(third.ids), first.total)
	}
	if first.offset != 0 || second.offset != 2 || third.offset != 4 {
		t.Fatalf("pagination offsets = %d,%d,%d", first.offset, second.offset, third.offset)
	}

	seen := map[string]bool{}
	for _, id := range append(append(append([]string{}, first.ids...), second.ids...), third.ids...) {
		if seen[id] {
			t.Fatalf("a row appeared on two pages: paging overlaps at %s (pages: %v %v %v)", id, first.ids, second.ids, third.ids)
		}
		seen[id] = true
	}
	if len(seen) != len(listPagingTaskIDs) {
		t.Fatalf("paging reached %d of %d rows: %v", len(seen), len(listPagingTaskIDs), seen)
	}
	// The oldest row is only reachable past the first page, which is the row the default ordering
	// pushes last: proof that offset moved the window rather than repeating it.
	if third.ids[0] != listPagingTaskIDs[0] {
		t.Fatalf("last page starts at %s, want the oldest row %s", third.ids[0], listPagingTaskIDs[0])
	}

	// An explicit ordering is honoured, not replaced by the default: created_at ASC puts the oldest
	// row first, on the FIRST page.
	oldestFirst := mcpListPage(t, app, `"limit":1,"offset":0,"sort_by":"created_at","sort_order":"asc"`)
	if len(oldestFirst.ids) != 1 || oldestFirst.ids[0] != listPagingTaskIDs[0] {
		t.Fatalf("sort_by=created_at asc page = %v, want the oldest row %s first", oldestFirst.ids, listPagingTaskIDs[0])
	}
}
