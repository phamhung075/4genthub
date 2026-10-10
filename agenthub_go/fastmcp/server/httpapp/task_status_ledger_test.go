package httpapp

// O1b, the REST status path: the status write and its status_changed entry are ONE transaction.
//
// IT SKIPS WITHOUT AGENTHUB_TEST_PG_URL, like its neighbours in this package, and the skip says so
// loudly. Two of the four claims here cannot be made against a fake at all:
//
//   - the parity query (the last status_changed.new against tasks.status) is a claim about rows, so
//     only a real database can answer it;
//   - the rollback claim needs a failure the fake transaction cannot produce. Here the failure is
//     real: a trigger refuses the task_events insert, and the assertion is that tasks.status did not
//     move - which is only true if the status write and the entry really share one transaction.
//
// The route is driven through app.Handler(), so the path under test is the production one:
// PUT /api/v2/tasks/{id} -> routes.UpdateUserTask -> the task API controller -> the facade -> the
// UpdateTask use case wired with the ledger in task_wiring.go.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 -run TestTaskStatusRouteWritesTheLedger ./fastmcp/server/httpapp/

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/mcpblock"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ledgerSeedTask inserts the row the route will move, with the branch and project it needs: tasks
// carries a foreign key to project_git_branchs, which carries one to projects. The columns are the
// ones the tasks DDL declares as NOT NULL, and the three inserts follow the same shape as
// websocket_notification_service_test.go's seed.
func ledgerSeedTask(t *testing.T, sm *database.SessionManager, taskID, userID, status string) {
	t.Helper()
	const projectID = "11111111-1111-4111-8111-111111111111"
	const branchID = "22222222-2222-4222-8222-222222222222"
	ledgerExec(t, sm, `INSERT INTO projects (id,name,description,created_at,updated_at,user_id,status,metadata)
		VALUES ($1,'ledger project','',now(),now(),$2,'active','{}') ON CONFLICT (id) DO NOTHING`, projectID, userID)
	ledgerExec(t, sm, `INSERT INTO project_git_branchs (id, project_id, name, description, created_at, updated_at, priority, status, metadata, task_count, completed_task_count, user_id)
		VALUES ($1,$2,'ledger branch','',now(),now(),'medium','todo','{}',0,0,$3) ON CONFLICT (id) DO NOTHING`, branchID, projectID, userID)
	ledgerExec(t, sm, `
		INSERT INTO tasks (id, title, description, git_branch_id, status, priority, progress_history,
			progress_count, estimated_effort, created_at, updated_at, completion_summary, testing_notes,
			progress_percentage, progress_state, user_id)
		VALUES ($1::uuid, 'ledger subject', 'what the task is for', $2::uuid, $3, 'medium', '{}'::json,
			0, '', now(), now(), '', '', 0, 'INITIAL', $4)`, taskID, branchID, status, userID)
}

func ledgerExec(t *testing.T, sm *database.SessionManager, sql string, args ...any) {
	t.Helper()
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, sql, args...)
		return err
	}); err != nil {
		t.Fatalf("exec failed: %v\nSQL: %s", err, sql)
	}
}

func ledgerStatus(t *testing.T, sm *database.SessionManager, taskID string) string {
	t.Helper()
	status := ""
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT "status" FROM tasks WHERE id = $1::uuid`, taskID).Scan(&status)
	}); err != nil {
		t.Fatalf("reading tasks.status: %v", err)
	}
	return status
}

// ledgerStatusEntries returns the payload of every status_changed entry for the task, oldest first,
// as the pair the entry records.
func ledgerStatusEntries(t *testing.T, sm *database.SessionManager, taskID string) [][2]string {
	t.Helper()
	out := [][2]string{}
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, `
			SELECT COALESCE(payload->>'old', ''), COALESCE(payload->>'new', '')
			FROM task_events WHERE task_id = $1::uuid AND kind = 'status_changed'
			ORDER BY seq ASC`, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var old, new string
			if err := rows.Scan(&old, &new); err != nil {
				return err
			}
			out = append(out, [2]string{old, new})
		}
		return rows.Err()
	}); err != nil {
		t.Fatalf("reading task_events: %v", err)
	}
	return out
}

// ledgerParityMismatches counts the tasks whose last status_changed entry disagrees with the status
// the row holds. The ledger's own claim is that this is always zero.
func ledgerParityMismatches(t *testing.T, sm *database.SessionManager) int {
	t.Helper()
	mismatches := 0
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `
			SELECT count(*) FROM tasks t
			JOIN LATERAL (
				SELECT payload->>'new' AS new_status
				FROM task_events e
				WHERE e.task_id = t.id AND e.kind = 'status_changed'
				ORDER BY e.seq DESC LIMIT 1
			) last ON TRUE
			WHERE last.new_status IS DISTINCT FROM t.status`).Scan(&mismatches)
	}); err != nil {
		t.Fatalf("parity query: %v", err)
	}
	return mismatches
}

// ledgerPutStatus drives the REST status route and returns its status code and body.
func ledgerPutStatus(t *testing.T, app *App, token, taskID, status string) (int, string) {
	t.Helper()
	body := `{"task_id":"` + taskID + `","status":"` + status + `","details":"moved by the REST status route"}`
	req := httptest.NewRequest(http.MethodPut, "/api/v2/tasks/"+taskID, strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

func TestTaskStatusRouteWritesTheLedgerInTheSameTransaction(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	// Auth on, so the route resolves the caller from the minted token (the ws tests set this for
	// the same reason). With it off the development fallback identity is used and the task, which
	// carries the token's user id, is outside that user's scope.
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)

	ctx := context.Background()
	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}

	const minted = "user-status-ledger"
	const taskID = "8f1b1f0e-6f1a-4a3e-9a5f-2f5b3c7d9e01"
	token := wsTestTokenFor(t, minted, nil)

	// The identity the REST layer resolves for this token, asked through the same dependency every
	// REST route reaches, so the seeded row sits inside the caller's scope rather than the scope the
	// test assumed it would.
	authCode, user := wsRESTUser(t, "Bearer "+token)
	if authCode != http.StatusOK || user == "" {
		t.Fatalf("the REST bearer dependency resolved no user: status = %d", authCode)
	}
	t.Logf("OBSERVED the REST layer resolved the minted token %q as user %q", minted, user)
	// The repository scope is not the token's subject verbatim: the composition maps it through
	// domain.ValidateUserID, so a row the route can see carries the mapped id.
	scoped, mapErr := domain.ValidateUserID(&user, "seeding the task this test moves")
	if mapErr != nil {
		t.Fatalf("mapping the user id: %v", mapErr)
	}
	t.Logf("OBSERVED the composition maps user %q to the scoped id %q", user, scoped)
	ledgerSeedTask(t, sm, taskID, scoped, "todo")

	// The status the row holds before the route runs, observed rather than assumed.
	before := ledgerStatus(t, sm, taskID)
	code, body := ledgerPutStatus(t, app, token, taskID, "in_progress")
	after := ledgerStatus(t, sm, taskID)
	entries := ledgerStatusEntries(t, sm, taskID)
	t.Logf("OBSERVED PUT %s -> %d; task %s status before=%q after=%q; entries=%v",
		"/api/v2/tasks/{id}", code, taskID, before, after, entries)

	if code != http.StatusOK {
		t.Fatalf("PUT status route = %d, want 200: %s", code, body)
	}
	var reply map[string]any
	if err := json.Unmarshal([]byte(body), &reply); err != nil {
		t.Fatalf("decoding the route's body: %v (%s)", err, body)
	}
	if success, _ := reply["success"].(bool); !success {
		t.Fatalf("the route reported failure: %s", body)
	}
	if before != "todo" || after != "in_progress" {
		t.Fatalf("status before=%q after=%q, want todo -> in_progress", before, after)
	}
	if len(entries) != 1 || entries[0] != [2]string{"todo", "in_progress"} {
		t.Fatalf("status_changed entries = %v, want one entry todo -> in_progress", entries)
	}
	if got := ledgerParityMismatches(t, sm); got != 0 {
		t.Fatalf("parity: %d task(s) whose last status_changed.new disagrees with tasks.status, want 0", got)
	}

	// The negative, with a real failure rather than a simulated one: a trigger refuses every
	// task_events insert. If the status write were not in the entry's transaction, the status would
	// move anyway and the ledger would be left describing a transition that never happened.
	ledgerExec(t, sm, `CREATE OR REPLACE FUNCTION ledger_refuse_insert() RETURNS trigger AS $$
		BEGIN RAISE EXCEPTION 'ledger insert refused by the test'; END; $$ LANGUAGE plpgsql`)
	ledgerExec(t, sm, `CREATE TRIGGER ledger_refuse_insert BEFORE INSERT ON task_events
		FOR EACH ROW EXECUTE FUNCTION ledger_refuse_insert()`)
	t.Cleanup(func() {
		ledgerExec(t, sm, `DROP TRIGGER IF EXISTS ledger_refuse_insert ON task_events`)
		ledgerExec(t, sm, `DROP FUNCTION IF EXISTS ledger_refuse_insert()`)
	})

	code, body = ledgerPutStatus(t, app, token, taskID, "blocked")
	afterRefusal := ledgerStatus(t, sm, taskID)
	entriesAfterRefusal := ledgerStatusEntries(t, sm, taskID)
	t.Logf("OBSERVED with the ledger insert refused: PUT -> %d; status=%q; entries=%v; body=%.200s",
		code, afterRefusal, entriesAfterRefusal, body)

	if code == http.StatusOK {
		t.Fatalf("the route reported success while the ledger insert was refused: %s", body)
	}
	if afterRefusal != "in_progress" {
		t.Fatalf("status = %q after the refused entry, want in_progress: a refused entry left the status changed", afterRefusal)
	}
	if len(entriesAfterRefusal) != 1 {
		t.Fatalf("entries = %v after the refused insert, want the one committed entry only", entriesAfterRefusal)
	}
	if got := ledgerParityMismatches(t, sm); got != 0 {
		t.Fatalf("parity after the refusal: %d mismatch(es), want 0", got)
	}
}

// TestMCPStatusCallWithAnUnusableSeatHeaderIsRefusedBeforeTheWrite is the O2 gate's ONE MINOR as a
// test. The header is read into task_events.actor_id VARCHAR(255), so an over-long value used to
// fail the INSERT - and the INSERT shares the caller's transaction, so a HEADER could roll back the
// CALLER'S OWN status write. It must be refused at the boundary instead, with an error the caller can
// read, and the task must not have moved and nothing may have been recorded.
//
// No access consequence is claimed or implied: the header is attribution only, and this is about a
// write being lost, not about one being allowed.
func TestMCPStatusCallWithAnUnusableSeatHeaderIsRefusedBeforeTheWrite(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)

	ctx := context.Background()
	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}

	const minted = "user-status-ledger-long-header"
	token := wsTestTokenFor(t, minted, []string{"tasks:update", "tasks:read"})
	authCode, user := wsRESTUser(t, "Bearer "+token)
	if authCode != http.StatusOK || user == "" {
		t.Fatalf("the bearer dependency resolved no user: status = %d", authCode)
	}
	scoped, mapErr := domain.ValidateUserID(&user, "seeding the task this test does not move")
	if mapErr != nil {
		t.Fatalf("mapping the user id: %v", mapErr)
	}

	const taskID = "8f1b1f0e-6f1a-4a3e-9a5f-2f5b3c7d9e50"
	ledgerSeedTask(t, sm, taskID, scoped, "todo")

	// One byte past what the column holds: the boundary case, not a conveniently large number.
	overlong := strings.Repeat("a", mcpblock.SeatValueMaxLen+1)
	code, body := ledgerMCPUpdateStatus(t, app, token, overlong, taskID, "in_progress")
	t.Logf("OBSERVED POST /mcp with a %d-byte seat header -> %d, body = %.300s", len(overlong), code, body)

	if code != http.StatusOK {
		t.Fatalf("the JSON-RPC envelope answered %d, want 200 with an error RESULT: %.300s", code, body)
	}
	if !strings.Contains(body, "INVALID_SEAT_HEADER") {
		t.Fatalf("the refusal does not name itself, so a caller cannot tell why: %.300s", body)
	}
	if got := ledgerStatus(t, sm, taskID); got != "todo" {
		t.Fatalf("the task moved to %q on a refused call: the header must be refused BEFORE the write", got)
	}
	entries := 0
	if err := sm.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT count(*) FROM task_events WHERE task_id = $1::uuid`, taskID).Scan(&entries)
	}); err != nil {
		t.Fatalf("counting entries: %v", err)
	}
	if entries != 0 {
		t.Fatalf("entries = %d, want 0: a refused call must write nothing at all", entries)
	}
}

// ledgerLastStatusActor reads the actor of the newest status_changed entry for a task, as the row
// records it.
func ledgerLastStatusActor(t *testing.T, sm *database.SessionManager, taskID string) (string, string) {
	t.Helper()
	kind, actorID := "", ""
	if err := sm.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `
			SELECT actor_kind, actor_id FROM task_events
			WHERE task_id = $1::uuid AND kind = 'status_changed'
			ORDER BY seq DESC LIMIT 1`, taskID).Scan(&kind, &actorID)
	}); err != nil {
		t.Fatalf("reading the entry's actor: %v", err)
	}
	return kind, actorID
}

// ledgerMCPUpdateStatus drives the MCP tools/call the seat's rendered client actually makes -
// manage_task update - with the header the renderer stamps, or with none.
func ledgerMCPUpdateStatus(t *testing.T, app *App, token, seat, taskID, status string) (int, string) {
	t.Helper()
	body := `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"update","task_id":"` +
		taskID + `","status":"` + status + `","details":"moved by the seat's MCP call"}}}`
	req := httptest.NewRequest(http.MethodPost, "/mcp", strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")
	if seat != "" {
		req.Header.Set(mcpblock.SeatHeader, seat)
	}
	rec := httptest.NewRecorder()
	app.Handler().ServeHTTP(rec, req)
	return rec.Code, rec.Body.String()
}

// WHO an MCP status call is attributed to, read from the ROW rather than from the response: the seat
// the header names is that seat acting on the caller's behalf, and a call that names no seat belongs
// to the user the caller resolves to. Every status write used to be stamped `system`/`system` no
// matter who made it, which is the gap this closes: an entry names whoever acted, in the two classes
// architecture 2.5 defines for it.
func TestMCPStatusCallIsAttributedToTheSeatThatMadeIt(t *testing.T) {
	sm := newMissedNotificationAppEnv(t)
	t.Setenv("AUTH_ENABLED", "true")
	wsWireRESTAuth(t)

	ctx := context.Background()
	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}

	const minted = "user-status-ledger-mcp"
	// The MCP tool path authorizes the operation, so this token needs the scope the REST route did
	// not ask for; without it the call answers 200 with a PERMISSION_DENIED payload and not a single
	// row moves, which is exactly what the first run of this case showed.
	token := wsTestTokenFor(t, minted, []string{"tasks:update", "tasks:read"})
	authCode, user := wsRESTUser(t, "Bearer "+token)
	if authCode != http.StatusOK || user == "" {
		t.Fatalf("the bearer dependency resolved no user: status = %d", authCode)
	}
	scoped, mapErr := domain.ValidateUserID(&user, "seeding the tasks this test moves")
	if mapErr != nil {
		t.Fatalf("mapping the user id: %v", mapErr)
	}

	// A call carrying the header the renderer stamps: a seat, named by its identity.
	const withSeat = "8f1b1f0e-6f1a-4a3e-9a5f-2f5b3c7d9e02"
	ledgerSeedTask(t, sm, withSeat, scoped, "todo")
	code, body := ledgerMCPUpdateStatus(t, app, token, "alpha/beta", withSeat, "in_progress")
	t.Logf("OBSERVED MCP call with the seat header: POST /mcp -> %d, status = %q, body = %.400s",
		code, ledgerStatus(t, sm, withSeat), body)
	if code != http.StatusOK {
		t.Fatalf("MCP tools/call = %d, want 200: %s", code, body)
	}
	kind, actorID := ledgerLastStatusActor(t, sm, withSeat)
	t.Logf("OBSERVED with the seat header: entry actor = %s/%q, want seat/%q", kind, actorID, "alpha/beta")
	if kind != "seat" || actorID != "alpha/beta" {
		t.Fatalf("entry actor = %s/%q, want seat/%q", kind, actorID, "alpha/beta")
	}
	if got := ledgerStatus(t, sm, withSeat); got != "in_progress" {
		t.Fatalf("status = %q, want in_progress", got)
	}

	// A call with no header: the user, named by the id the composition scoped the row to.
	const noSeat = "8f1b1f0e-6f1a-4a3e-9a5f-2f5b3c7d9e03"
	ledgerSeedTask(t, sm, noSeat, scoped, "todo")
	code, body = ledgerMCPUpdateStatus(t, app, token, "", noSeat, "in_progress")
	t.Logf("OBSERVED MCP call without the header: POST /mcp -> %d, status = %q, body = %.400s",
		code, ledgerStatus(t, sm, noSeat), body)
	if code != http.StatusOK {
		t.Fatalf("MCP tools/call without the header = %d, want 200: %s", code, body)
	}
	kind, actorID = ledgerLastStatusActor(t, sm, noSeat)
	t.Logf("OBSERVED without the header: entry actor = %s/%q, want human/%q", kind, actorID, scoped)
	if kind != "human" || actorID != scoped {
		t.Fatalf("entry actor = %s/%q, want human/%q", kind, actorID, scoped)
	}

	if got := ledgerParityMismatches(t, sm); got != 0 {
		t.Fatalf("parity after the attributed calls: %d mismatch(es), want 0", got)
	}
}
