package httpapp

// THE DELETE CASCADE MUST REMOVE THE TASK'S LEDGER ENTRIES.
//
// task_events.task_id is the ONE foreign key into tasks that carries no ON DELETE CASCADE: the
// ledger's hand-written table declares none by design ("the application layer cascades"), while the
// tables this schema generated from Python's metadata cascade in the database. The application layer
// is therefore the only thing that can remove those rows, and `ORMTaskRepository.DeleteTask` - the
// manual cascade that already deletes task_contexts, subtasks, task_assignees, task_dependencies and
// task_labels in ONE transaction - did not know about the ledger, which O1a added after that function
// was ported.
//
// The observable, measured on production at 20:32:46Z and again at 20:33:10Z: a task that has any
// event row (a status change is enough, and since a0313d5f a status change always writes one) could
// not be deleted at all. The foreign key refused the DELETE, DeleteTask swallowed the repository
// error into `false` (Python parity), and the tool answered OPERATION_FAILED with no reason at all -
// which is why the cause had to be read out of the code rather than out of the response.
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, loudly, and there is no fake version of this case: the
// refusal comes from a foreign key in a real database. A test over a fake repository would only
// write this comment's hypothesis back to its author.
//
// Every step is a production path, driven through app.Handler():
//
//	POST   /api/v2/tasks/      -> routes.CreateUserTask    -> the controller -> the facade
//	PUT    /api/v2/tasks/{id}  -> routes.UpdateUserTask    -> the same facade, wired with the ledger
//	DELETE /api/v2/tasks/{id}  -> routes.DeleteUserTask    -> facade.DeleteTask -> DeleteTaskUseCase
//	                                                        -> CascadeDeletionService
//	                                                        -> ORMTaskRepository.DeleteTask
//
// The task is created through the route rather than inserted by hand on purpose: a hand-written row
// carries the database session's local `now()` while the application writes UTC, and the task entity
// refuses a row whose updated_at is earlier than its created_at (base_timestamp_entity.go:100) -
// which GetTask swallows into "not found". A hand-seeded task therefore fails this test for a reason
// that has nothing to do with the cascade.
//
// The MCP tool `manage_task action=delete` (the call the finding used) reaches the SAME facade method
// from crud_handler.go, so both entry points carry this cascade.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -run TestTaskDeleteSucceedsForATaskThatHasLedgerEntries ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// The project and branch the created task hangs off. Only these two rows are written by hand.
const (
	deleteTestProjectID = "11111111-1111-4111-8111-111111111111"
	deleteTestBranchID  = "22222222-2222-4222-8222-222222222222"
)

func deleteTestSeedBranch(t *testing.T, sm *database.SessionManager, userID string) {
	t.Helper()
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'delete cascade project','',now(),now(),$2,'active','{}') ON CONFLICT (id) DO NOTHING`, deleteTestProjectID, userID)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'delete cascade branch','',now(),now(),'medium','todo','{}',0,0,$3) ON CONFLICT (id) DO NOTHING`, deleteTestBranchID, deleteTestProjectID, userID)
}

// taskCreate drives POST /api/v2/tasks/ and returns the status code, the created task's id and the
// raw body.
func taskCreate(t *testing.T, app *App, token, title, branchID string) (int, string, string) {
	t.Helper()
	body := `{"title":"` + title + `","description":"created so that its ledger outlives it","git_branch_id":"` + branchID + `"}`
	req := httptest.NewRequest(http.MethodPost, "/api/v2/tasks/", strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	var parsed struct {
		Task struct {
			ID string `json:"id"`
		} `json:"task"`
	}
	_ = json.Unmarshal([]byte(rec.Body.String()), &parsed)
	return rec.Code, parsed.Task.ID, rec.Body.String()
}

// taskDelete drives the REST delete route and returns its status code and body.
func taskDelete(t *testing.T, app *App, token, taskID string) (int, string) {
	t.Helper()
	req := httptest.NewRequest(http.MethodDelete, "/api/v2/tasks/"+taskID, nil)
	req.Header.Set("Authorization", "Bearer "+token)
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// taskRowCount counts the tasks row itself.
func taskRowCount(t *testing.T, sm *database.SessionManager, taskID string) int {
	t.Helper()
	n := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM tasks WHERE id = $1::uuid`, taskID).Scan(&n)
	}); err != nil {
		t.Fatalf("counting the tasks row: %v", err)
	}
	return n
}

// taskEventRowCount counts the ledger entries the task still owns. A task_events row whose task is
// gone is a history nobody can read.
func taskEventRowCount(t *testing.T, sm *database.SessionManager, taskID string) int {
	t.Helper()
	n := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM task_events WHERE task_id = $1::uuid`, taskID).Scan(&n)
	}); err != nil {
		t.Fatalf("counting task_events rows: %v", err)
	}
	return n
}

func TestTaskDeleteSucceedsForATaskThatHasLedgerEntries(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)

	ctx := context.Background()
	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}

	const minted = "user-delete-ledger"
	token := wsTestTokenFor(t, minted, nil)
	authCode, user := wsRESTUser(t, "Bearer "+token)
	if authCode != http.StatusOK || user == "" {
		t.Fatalf("the REST bearer dependency resolved no user: status = %d", authCode)
	}
	scoped, mapErr := domain.ValidateUserID(&user, "creating the task this test deletes")
	if mapErr != nil {
		t.Fatalf("mapping the user id: %v", mapErr)
	}
	deleteTestSeedBranch(t, sm, scoped)

	code, taskID, body := taskCreate(t, app, token, "the task the ledger cannot outlive", deleteTestBranchID)
	if code != http.StatusOK || taskID == "" {
		t.Fatalf("POST /api/v2/tasks/ = %d, id = %q, want 200 and an id: %s", code, taskID, body)
	}

	// The new variable the finding names: a status change. It writes a status_changed entry, and
	// without one the delete would never reach the foreign key - which is why this looked fine until
	// the ledger's insert was fixed.
	putCode, putBody := ledgerPutStatus(t, app, token, taskID, "in_progress")
	if putCode != http.StatusOK {
		t.Fatalf("PUT status route = %d, want 200: %s", putCode, putBody)
	}
	if entries := ledgerStatusEntries(t, sm, taskID); len(entries) != 1 {
		t.Fatalf("status_changed entries = %v, want the one entry the delete has to carry", entries)
	}

	delCode, delBody := taskDelete(t, app, token, taskID)
	t.Logf("OBSERVED DELETE /api/v2/tasks/%s -> %d; body=%.200s", taskID, delCode, delBody)
	if delCode != http.StatusOK {
		t.Fatalf("DELETE = %d, want 200: %s", delCode, delBody)
	}
	if rows := taskRowCount(t, sm, taskID); rows != 0 {
		t.Fatalf("tasks rows = %d after a successful delete, want 0", rows)
	}
	if rows := taskEventRowCount(t, sm, taskID); rows != 0 {
		t.Fatalf("task_events rows = %d after deleting their task, want 0", rows)
	}
}
