package mcptoolpath

// O4 slice 1, the acceptance the row states as "a round-trip THROUGH BOTH TOOLS": manage_task and
// manage_subtask set acceptance_criteria (a JSON string array) and scope (a JSON glob array), and a
// later read through the same tool returns them unchanged - on CREATE and on UPDATE.
//
// It drives the production wire, not a seam: POST /mcp with a JSON-RPC tools/call (mcp_routes.go:76,
// handleJSONRPC -> App.dispatchMCPTool), over a database built by the production schema
// (testdb.NewSessions). A fake repository would only write this comment's hypothesis back to its
// author, so the case uses the real one.
//
// It owns its test binary on purpose - see doc.go - because httpapp's suite caches a repository
// provider against whichever App is composed first.
//
// It skips loudly without AGENTHUB_TEST_PG_URL, like its neighbours. To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres go test -count=1 ./fastmcp/server/mcptoolpath/

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"maps"
	"net/http"
	"net/http/httptest"
	"slices"
	"testing"
	"time"

	"agenthub/fastmcp/server/httpapp"
	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// findMapWith returns the object in the response that carries key. The field under test appears
// only inside the task/subtask payload the tool returns, so its presence identifies that payload
// without hard-coding the formatter's nesting.
//
// Two rules keep the answer stable across runs of one revision. A plain map range is randomized,
// and a create or update response carries the field TWICE: under data.task (the entity, which has
// an id) and under meta.operation_context (the echo of the request, which does not). So keys are
// visited in sorted order, and a match that carries an id wins over one that does not. When no
// match carries an id the first one in that order is returned, which is the old answer made stable.
func findMapWith(v any, key string) (map[string]any, bool) {
	var firstMatch map[string]any
	var walk func(any) (map[string]any, bool)
	walk = func(v any) (map[string]any, bool) {
		switch t := v.(type) {
		case *entities.OrderedMap[any]:
			return walk(orderedToMap(t))
		case map[string]any:
			if item, ok := t[key]; ok && item != nil {
				if id, hasID := t["id"]; hasID && id != nil {
					return t, true
				}
				if firstMatch == nil {
					firstMatch = t
				}
			}
			for _, k := range slices.Sorted(maps.Keys(t)) {
				if m, ok := walk(t[k]); ok {
					return m, true
				}
			}
		case []any:
			for _, item := range t {
				if m, ok := walk(item); ok {
					return m, true
				}
			}
		}
		return nil, false
	}
	if m, ok := walk(v); ok {
		return m, true
	}
	return firstMatch, firstMatch != nil
}

func orderedToMap(o *entities.OrderedMap[any]) map[string]any {
	out := map[string]any{}
	for _, k := range o.Keys() {
		v, _ := o.Get(k)
		out[k] = v
	}
	return out
}

func stringListOf(v any) []string {
	switch t := v.(type) {
	case []string:
		return append([]string{}, t...)
	case []any:
		out := make([]string, 0, len(t))
		for _, item := range t {
			out = append(out, fmt.Sprint(item))
		}
		return out
	}
	return nil
}

func sameStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

// seedBranch writes the project and branch rows a task needs; the task itself is created by the tool
// under test.
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

// callTool drives one tools/call over POST /mcp and returns the tool's payload, decoded from the
// JSON-RPC content text, plus whether the envelope reported an error.
func callTool(t *testing.T, app *httpapp.App, name string, args map[string]any) (any, bool) {
	t.Helper()
	body, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{"name": name, "arguments": args},
	})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/mcp", bytes.NewReader(body))
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

func TestAcceptanceScopeRoundTripsThroughBothTools(t *testing.T) {
	sessions := testdb.NewSessions(t) // skips loudly when AGENTHUB_TEST_PG_URL is unset
	user := tmvo.NewUUIDv4()
	t.Setenv("AUTH_ENABLED", "false")
	t.Setenv("DEFAULT_USER_ID", user)

	app, err := httpapp.NewApp(context.Background(), sessions)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}

	branchID := seedBranch(t, sessions, user)

	wantCriteria := []string{"the round trip returns every criterion", "scope survives unchanged"}
	wantScope := []string{"internal/**", "cmd/*.go"}

	// manage_task create: both fields set on a task.
	createRes, isErr := callTool(t, app, "manage_task", map[string]any{
		"action": "create", "git_branch_id": branchID, "title": "O4 acceptance scope round trip",
		"assignees":           "@lead",
		"acceptance_criteria": wantCriteria,
		"scope":               wantScope,
	})
	if isErr {
		t.Fatalf("manage_task create reported an error: %v", createRes)
	}
	taskPayload, ok := findMapWith(createRes, "acceptance_criteria")
	if !ok {
		t.Fatalf("manage_task create returned no payload carrying acceptance_criteria: %v", createRes)
	}
	taskID := fmt.Sprint(taskPayload["id"])
	if taskID == "" || taskID == "<nil>" {
		t.Fatalf("manage_task create returned no task id: %v", createRes)
	}

	// manage_task get: the read returns both fields unchanged.
	getRes, _ := callTool(t, app, "manage_task", map[string]any{"action": "get", "task_id": taskID})
	gotTask, ok := findMapWith(getRes, "acceptance_criteria")
	if !ok {
		t.Fatalf("manage_task get returned no payload carrying acceptance_criteria: %v", getRes)
	}
	gotCriteria := stringListOf(gotTask["acceptance_criteria"])
	gotScope := stringListOf(gotTask["scope"])
	t.Logf("OBSERVED manage_task: created task=%s; acceptance_criteria=%q; scope=%q", taskID, gotCriteria, gotScope)
	if !sameStrings(gotCriteria, wantCriteria) {
		t.Errorf("manage_task round trip lost acceptance_criteria: got %q, want %q", gotCriteria, wantCriteria)
	}
	if !sameStrings(gotScope, wantScope) {
		t.Errorf("manage_task round trip lost scope: got %q, want %q", gotScope, wantScope)
	}

	// manage_task update: both fields are settable on update too, and the read returns the NEW values.
	updatedCriteria := []string{"the update path replaces them"}
	updatedScope := []string{"docs/**"}
	callTool(t, app, "manage_task", map[string]any{
		"action": "update", "task_id": taskID,
		"acceptance_criteria": updatedCriteria,
		"scope":               updatedScope,
	})
	updRes, _ := callTool(t, app, "manage_task", map[string]any{"action": "get", "task_id": taskID})
	gotTask2, ok := findMapWith(updRes, "acceptance_criteria")
	if !ok {
		t.Fatalf("manage_task get after update carried no acceptance_criteria: %v", updRes)
	}
	gotUpdCriteria := stringListOf(gotTask2["acceptance_criteria"])
	gotUpdScope := stringListOf(gotTask2["scope"])
	t.Logf("OBSERVED manage_task update: acceptance_criteria=%q; scope=%q", gotUpdCriteria, gotUpdScope)
	if !sameStrings(gotUpdCriteria, updatedCriteria) {
		t.Errorf("manage_task update lost acceptance_criteria: got %q, want %q", gotUpdCriteria, updatedCriteria)
	}
	if !sameStrings(gotUpdScope, updatedScope) {
		t.Errorf("manage_task update lost scope: got %q, want %q", gotUpdScope, updatedScope)
	}

	// manage_subtask create: both fields set on a subtask, then read back through the same tool.
	wantSubCriteria := []string{"the subtask states its own criteria"}
	wantSubScope := []string{"fastmcp/task_management/**"}
	subCreateRes, isErr := callTool(t, app, "manage_subtask", map[string]any{
		"action": "create", "task_id": taskID, "title": "O4 subtask acceptance scope round trip",
		"acceptance_criteria": wantSubCriteria,
		"scope":               wantSubScope,
	})
	if isErr {
		t.Fatalf("manage_subtask create reported an error: %v", subCreateRes)
	}
	subPayload, ok := findMapWith(subCreateRes, "acceptance_criteria")
	if !ok {
		t.Fatalf("manage_subtask create returned no payload carrying acceptance_criteria: %v", subCreateRes)
	}
	subID := fmt.Sprint(subPayload["id"])
	if subID == "" || subID == "<nil>" {
		t.Fatalf("manage_subtask create returned no subtask id: %v", subCreateRes)
	}

	subGetRes, _ := callTool(t, app, "manage_subtask", map[string]any{"action": "get", "task_id": taskID, "subtask_id": subID})
	gotSub, ok := findMapWith(subGetRes, "acceptance_criteria")
	if !ok {
		t.Fatalf("manage_subtask get returned no payload carrying acceptance_criteria: %v", subGetRes)
	}
	gotSubCriteria := stringListOf(gotSub["acceptance_criteria"])
	gotSubScope := stringListOf(gotSub["scope"])
	t.Logf("OBSERVED manage_subtask: created subtask=%s; acceptance_criteria=%q; scope=%q", subID, gotSubCriteria, gotSubScope)
	if !sameStrings(gotSubCriteria, wantSubCriteria) {
		t.Errorf("manage_subtask round trip lost acceptance_criteria: got %q, want %q", gotSubCriteria, wantSubCriteria)
	}
	if !sameStrings(gotSubScope, wantSubScope) {
		t.Errorf("manage_subtask round trip lost scope: got %q, want %q", gotSubScope, wantSubScope)
	}

	// manage_subtask update: both fields are settable on update too.
	updSubCriteria := []string{"the subtask update replaces them"}
	updSubScope := []string{"cmd/**"}
	callTool(t, app, "manage_subtask", map[string]any{
		"action": "update", "task_id": taskID, "subtask_id": subID,
		"progress_notes":      "updating the subtask scope and criteria",
		"acceptance_criteria": updSubCriteria,
		"scope":               updSubScope,
	})
	subGetRes2, _ := callTool(t, app, "manage_subtask", map[string]any{"action": "get", "task_id": taskID, "subtask_id": subID})
	gotSub2, ok := findMapWith(subGetRes2, "acceptance_criteria")
	if !ok {
		t.Fatalf("manage_subtask get after update carried no acceptance_criteria: %v", subGetRes2)
	}
	gotUpdSubCriteria := stringListOf(gotSub2["acceptance_criteria"])
	gotUpdSubScope := stringListOf(gotSub2["scope"])
	t.Logf("OBSERVED manage_subtask update: acceptance_criteria=%q; scope=%q", gotUpdSubCriteria, gotUpdSubScope)
	if !sameStrings(gotUpdSubCriteria, updSubCriteria) {
		t.Errorf("manage_subtask update lost acceptance_criteria: got %q, want %q", gotUpdSubCriteria, updSubCriteria)
	}
	if !sameStrings(gotUpdSubScope, updSubScope) {
		t.Errorf("manage_subtask update lost scope: got %q, want %q", gotUpdSubScope, updSubScope)
	}
}
