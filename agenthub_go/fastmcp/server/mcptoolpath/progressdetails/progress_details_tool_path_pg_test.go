// Package progressdetails holds the black-box wire test for the progress-note DATA LOSS the row
// reports: a task write answers SUCCESS with the note in its own reply, while the read of the SAME
// row returns details "\n\n". Row 87c58552 lost two notes that way, and the consequence is why it is
// HIGH: a seat that records progress only in details records nothing.
//
// WHY ITS OWN PACKAGE (the same reason mcptoolpath/doc.go records): services.RepositoryProviderService
// .GetInstance caches a provider built from the FIRST composition's repository backend, process-wide,
// and httpapp.NewApp sets that backend to the SessionManager it was handed. A second App composed in
// the same test binary therefore serves its tool calls from the FIRST test's database - which that
// test's cleanup already dropped, so the context write fails with `sql: database is closed`. One App
// composition per binary, so this one is its own binary.
//
// It drives the production wire (POST /mcp, tools/call), not a seam. The three carriers of a progress
// note, and what this test measures for each:
//
//	(a) manage_task action=update with a `details` string -> entity.AppendProgress ->
//	    tasks.progress_history, read back by manage_task action=get as the joined `details`.
//	(b) a dedicated progress action on manage_task - DOES NOT EXIST. The action list is
//	    create|update|get|delete|complete|list|search|next|add_dependency|remove_dependency|resume|
//	    ai_*, and the factory answers "Unknown operation: add_progress". Asserted so the absence is
//	    measured rather than assumed.
//	(c) manage_context action=add_progress -> the task-level context's implementation_notes
//	    .progress_updates, read back by manage_context action=get. A SEPARATE carrier (the context
//	    store, not tasks.progress_history).
//
// Every case asserts the CONTENT the read returns, never that the call reported success, and logs the
// stored column / ledger it is about so a pass is evidence rather than a green light over an empty row.
//
// To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 ./fastmcp/server/mcptoolpath/progressdetails/
package progressdetails

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	authdomain "agenthub/fastmcp/auth/domain"
	"agenthub/fastmcp/server/httpapp"
	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// seedBranch writes the project, branch and branch-context rows a task needs; the task itself is
// created by the tool under test.
func seedBranch(t *testing.T, sessions *database.SessionManager, user string) string {
	t.Helper()
	ctx := context.Background()
	now := time.Now().UTC()

	projects, err := infrarepos.NewORMRepository[database.Project]("projects", sessions)
	if err != nil {
		t.Fatal(err)
	}
	projectID := tmvo.NewUUIDv4()
	if _, err := projects.Create(ctx, infrarepos.NewKwargs("id", projectID, "name", "p",
		"user_id", user, "created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create project: %v", err)
	}

	branches, err := infrarepos.NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		t.Fatal(err)
	}
	branchID := tmvo.NewUUIDv4()
	if _, err := branches.Create(ctx, infrarepos.NewKwargs("id", branchID, "project_id", projectID, "name", "main",
		"user_id", user, "created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create branch: %v", err)
	}

	branchRepo, err := infrarepos.NewBranchContextRepository(sessions, &user)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := branchRepo.Create(ctx, &entities.BranchContext{ID: branchID, BranchInfo: map[string]any{}, Metadata: map[string]any{}}); err != nil {
		t.Fatalf("create branch context: %v", err)
	}
	return branchID
}

// contextPermissionCtx is what the request-context middleware leaves on an authenticated MCP call:
// the permission checker manage_context's gate reads off the request context. dispatchMCPTool keeps
// the request's own context when no bearer validates, so a request built over this context reaches
// the gate already authorised - the same arrangement httpapp's add_progress tool-path case uses.
func contextPermissionCtx() context.Context {
	return context.WithValue(context.Background(), authdomain.PermissionsContextKey,
		authdomain.NewPermissionChecker(map[string]any{"scope": "contexts:create contexts:read contexts:update"}))
}

// callTool drives one tools/call over POST /mcp and returns the tool's payload, decoded from the
// JSON-RPC content text, plus whether the envelope reported an error. ctx is the request context the
// tools read; the tool path must not be reached with one that has been scrubbed of the auth state the
// production middleware stamps on it.
func callTool(t *testing.T, ctx context.Context, app *httpapp.App, name string, args map[string]any) (any, bool) {
	t.Helper()
	body, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{"name": name, "arguments": args},
	})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/mcp", bytes.NewReader(body)).WithContext(ctx)
	req.Header.Set("Content-Type", "application/json")
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
	text := envelope.Result.Content[0].Text
	var payload any
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("decoding %s's payload: %v (payload=%s)", name, err, text)
	}
	return payload, envelope.Result.IsError
}

// taskPayload reaches the task the success envelope carries under data.task - the one place the
// create/update/get facade responses agree on. findMapWith is deliberately NOT used for this: the
// workflow-hint maps the same envelope carries can repeat a field NAME, so a key-only search is not
// deterministic.
func taskPayload(t *testing.T, res any) map[string]any {
	t.Helper()
	root, ok := res.(map[string]any)
	if !ok {
		t.Fatalf("response is not an object: %v", res)
	}
	data, ok := root["data"].(map[string]any)
	if !ok {
		t.Fatalf("response carries no data object: %s", jsonText(res))
	}
	task, ok := data["task"].(map[string]any)
	if !ok {
		t.Fatalf("response carries no data.task object: %s", jsonText(res))
	}
	return task
}

// createTask creates a task through the tool and returns its id.
func createTask(t *testing.T, ctx context.Context, app *httpapp.App, branchID, title string) string {
	t.Helper()
	res, isErr := callTool(t, ctx, app, "manage_task", map[string]any{
		"action": "create", "git_branch_id": branchID, "title": title, "assignees": "@lead",
	})
	if isErr {
		t.Fatalf("manage_task create reported an error: %v", res)
	}
	taskID := fmt.Sprint(taskPayload(t, res)["id"])
	if taskID == "" || taskID == "<nil>" {
		t.Fatalf("manage_task create returned no task id: %s", jsonText(res))
	}
	return taskID
}

// rawProgressHistory reads the stored column straight from the database, so a case can say whether
// the write landed even when the read does not return it.
func rawProgressHistory(t *testing.T, sessions *database.SessionManager, taskID string) string {
	t.Helper()
	var raw string
	err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT progress_history::text FROM tasks WHERE id = $1::uuid`, taskID).Scan(&raw)
	})
	if err != nil {
		return "query error: " + err.Error()
	}
	return raw
}

// ledgerKinds reads the kinds the append-only record holds for the task.
func ledgerKinds(t *testing.T, sessions *database.SessionManager, taskID string) string {
	t.Helper()
	out := []string{}
	err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT kind FROM task_events WHERE task_id = $1::uuid ORDER BY seq`, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var kind string
			if err := rows.Scan(&kind); err != nil {
				return err
			}
			out = append(out, kind)
		}
		return rows.Err()
	})
	if err != nil {
		return "query error: " + err.Error()
	}
	if len(out) == 0 {
		return "(no task_events rows)"
	}
	return strings.Join(out, ", ")
}

func jsonText(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		return fmt.Sprintf("<unmarshalable: %v>", err)
	}
	return string(b)
}

// TestProgressDetailsRoundTripThroughTheTools composes production ONCE (the cache in
// repository_provider_service.go makes a second composition serve the first database) and runs the
// three carriers as subtests over that one App.
func TestProgressDetailsRoundTripThroughTheTools(t *testing.T) {
	sessions := testdb.NewSessions(t) // skips loudly when AGENTHUB_TEST_PG_URL is unset
	user := tmvo.NewUUIDv4()
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("DEFAULT_USER_ID", user)

	app, err := httpapp.NewApp(context.Background(), sessions)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	branchID := seedBranch(t, sessions, user)

	// plainCtx reaches the tools without a permission checker: manage_task needs none, and reaching
	// it any other way would test a context the production middleware does not produce.
	plainCtx := context.Background()

	// (a) manage_task update's `details` must be readable back as `details` by the SAME tool.
	t.Run("manage_task_update_details_read_by_get", func(t *testing.T) {
		taskID := createTask(t, plainCtx, app, branchID, "progress details round trip")

		note1 := "wired the progress writer into the update path"
		note2 := "verified the round trip against the stored row"

		upd1, isErr := callTool(t, plainCtx, app, "manage_task", map[string]any{
			"action": "update", "task_id": taskID, "status": "in_progress", "details": note1,
		})
		if isErr {
			t.Fatalf("manage_task update #1 reported an error: %v", upd1)
		}
		t.Logf("OBSERVED update #1 answer details=%q", fmt.Sprint(taskPayload(t, upd1)["details"]))

		upd2, isErr := callTool(t, plainCtx, app, "manage_task", map[string]any{
			"action": "update", "task_id": taskID, "details": note2,
		})
		if isErr {
			t.Fatalf("manage_task update #2 reported an error: %v", upd2)
		}
		t.Logf("OBSERVED update #2 answer details=%q", fmt.Sprint(taskPayload(t, upd2)["details"]))

		t.Logf("OBSERVED stored tasks.progress_history=%s", rawProgressHistory(t, sessions, taskID))
		t.Logf("OBSERVED ledger task_events kinds=%s", ledgerKinds(t, sessions, taskID))

		getRes, isErr := callTool(t, plainCtx, app, "manage_task", map[string]any{"action": "get", "task_id": taskID})
		if isErr {
			t.Fatalf("manage_task get reported an error: %s", jsonText(getRes))
		}
		details := fmt.Sprint(taskPayload(t, getRes)["details"])
		t.Logf("OBSERVED manage_task get details=%q", details)
		if !strings.Contains(details, note1) {
			t.Errorf("manage_task get lost progress note 1: details=%q, want it to contain %q", details, note1)
		}
		if !strings.Contains(details, note2) {
			t.Errorf("manage_task get lost progress note 2: details=%q, want it to contain %q", details, note2)
		}
	})

	// (b) There is no dedicated progress action on manage_task; the only task-progress writer is
	// update's details. Pinned so the case above cannot be dismissed as "the other action".
	t.Run("manage_task_has_no_dedicated_progress_action", func(t *testing.T) {
		taskID := createTask(t, plainCtx, app, branchID, "no dedicated progress action")
		res, isErr := callTool(t, plainCtx, app, "manage_task", map[string]any{
			"action": "add_progress", "task_id": taskID, "content": "a progress note",
		})
		answer := jsonText(res)
		t.Logf("OBSERVED manage_task action=add_progress isError=%v payload=%s", isErr, answer)
		// The refusal is in the payload's success/error, not the envelope flag: this pins that no
		// dedicated progress action exists, so the only task-progress writer is update's details.
		if !strings.Contains(answer, "Unknown operation: add_progress") {
			t.Errorf("manage_task did not refuse action=add_progress as unknown (%s); a dedicated progress action may exist and then needs its own round-trip case", answer)
		}
	})

	// (c) manage_context add_progress is the separate context carrier; its note must be readable back
	// by manage_context get.
	t.Run("manage_context_add_progress_read_by_get", func(t *testing.T) {
		taskID := createTask(t, plainCtx, app, branchID, "context progress round trip")
		ctx := contextPermissionCtx()

		note := "context carrier note: recorded through add_progress"
		addRes, isErr := callTool(t, ctx, app, "manage_context", map[string]any{
			"action": "add_progress", "level": "task", "context_id": taskID, "content": note,
		})
		if isErr {
			t.Fatalf("manage_context add_progress reported an error: %s", jsonText(addRes))
		}

		getRes, isErr := callTool(t, ctx, app, "manage_context", map[string]any{
			"action": "get", "level": "task", "context_id": taskID,
		})
		if isErr {
			t.Fatalf("manage_context get reported an error: %s", jsonText(getRes))
		}
		all := jsonText(getRes)
		t.Logf("OBSERVED manage_context get payload=%s", all)
		if !strings.Contains(all, note) {
			t.Errorf("manage_context lost the progress note: the read does not contain %q", note)
		}
	})
}
