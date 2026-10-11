package httpapp

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ITEM B's ACCEPTANCE, DRIVEN WHERE THE ITEM SAID IT MUST BE. The acceptance is "a note written through
// manage_context add_progress is read back where the entity reads its notes". The unit case beside this
// package drove the service against a fake repository, and the case beside this one drove the service
// against the real one - both are the seam path. This case drives the TOOL path: App.dispatchMCPTool,
// which is the function the wire reaches for tools/call (mcp_routes.go:233), over a database built by the
// production schema, and reads the note back with the entity's own reader,
// TaskContextRepository.Get. The tool path is not the seam path and has to exercise itself.
//
// THE CALL SENT IS THE ONE THE TOOL ADVERTISES. manage_context publishes `level` and `context_id`
// (tool_input_schemas.go; testdata/tools_golden.json), with `context_id` required for every action except
// list, and the handler defaults an absent level to "task" (context_operation_handler.go:52). The case
// sends exactly that shape, and it also measures the `task_id`-only shape side by side, in the same case
// against the same context, so the parameter is the only thing that differs between landing and not.
func TestAddProgressThroughTheToolPathLandsWhereTheEntityReads(t *testing.T) {
	sm := newMissedNotificationAppEnv(t) // skips loudly when AGENTHUB_TEST_PG_URL is unset
	t.Setenv("AUTH_ENABLED", "false")
	// A UUID passes through ValidateUserID unchanged, so the id the tool resolves is the id that owns
	// the fixture rows below.
	user := tmvo.NewUUIDv4()
	t.Setenv("TEST_USER_ID", user)

	// The permission checker the request-context middleware stores (auth/domain), scoped to the actions
	// this case drives. Without it the controller refuses every action at the permission gate, which is a
	// different refusal than the one under test.
	ctx := context.WithValue(context.Background(), authdomain.PermissionsContextKey,
		authdomain.NewPermissionChecker(map[string]any{"scope": "contexts:create contexts:read contexts:update"}))

	app, err := NewApp(ctx, sm)
	if err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	req := httptest.NewRequest(http.MethodPost, "/mcp", nil)

	taskID, branchID := ctxPgFixtures(t, sm, user)

	// The task context, created through the same adapters the server composes.
	global, project, branch, task, err := unifiedContextRepositories(sm, &user)
	if err != nil {
		t.Fatalf("unifiedContextRepositories: %v", err)
	}
	svc := services.NewUnifiedContextService(global, project, branch, task, nil, nil, nil, nil, &user)
	created, _ := svc.CreateContext(ctx, "task", taskID, ctxPgOM("branch_id", branchID), nil, nil, true)
	if v, _ := created.Get("success"); v != true {
		t.Fatalf("the task context could not be created, so no note can land: keys=%v", created.Keys())
	}

	// The entity's own reader, on the same session as the adapters.
	reader, err := infrarepos.NewTaskContextRepository(sm, &user)
	if err != nil {
		t.Fatalf("NewTaskContextRepository: %v", err)
	}
	notes := func() []any {
		t.Helper()
		tc, err := reader.Get(ctx, taskID)
		if err != nil {
			t.Fatalf("TaskContextRepository.Get: %v", err)
		}
		updates, _ := tc.ImplementationNotes["progress_updates"].([]any)
		return updates
	}
	holds := func(note string) bool {
		t.Helper()
		for _, e := range notes() {
			if strings.Contains(fmt.Sprint(e), note) {
				return true
			}
		}
		return false
	}
	call := func(args map[string]any) (string, bool) {
		t.Helper()
		res, isErr := app.dispatchMCPTool(ctx, req, "manage_context", args)
		if res == nil {
			t.Fatalf("dispatchMCPTool(%v) returned nil", args["action"])
		}
		return renderAny(res), isErr
	}

	// THE ACCEPTANCE: the advertised shape, through the tool, read back by the entity's reader.
	const note = "a progress note written through the manage_context tool"
	answer, isErr := call(map[string]any{
		"action": "add_progress", "level": "task", "context_id": taskID, "content": note,
	})
	if !holds(note) {
		t.Errorf("a note sent in the shape manage_context advertises ({action:add_progress, level:task, context_id:%s}) is not in %s after the call. "+
			"notes in the column=%v; tool answer=%s (dispatch reported error=%v)",
			taskID, "ImplementationNotes[progress_updates]", truncateForLog(fmt.Sprint(notes()), 300), truncateForLog(answer, 400), isErr)
	}

	// THE CONTRAST, measured not asserted: the same note in the shape the guidance examples print
	// (task_id, no level, no context_id). dispatchMCPTool resolves the id from context_id/id only
	// (mcp_routes.go), so this addresses nothing. Reported so the two shapes are on the record together.
	const legacyNote = "a progress note sent as task_id only"
	legacyAnswer, legacyIsErr := call(map[string]any{"action": "add_progress", "task_id": taskID, "content": legacyNote})
	t.Logf("OBSERVED through the tool path: advertised shape (level+context_id) landed=%v; task_id-only shape landed=%v; "+
		"the task_id-only answer was %s (dispatch reported error=%v)",
		holds(note), holds(legacyNote), truncateForLog(legacyAnswer, 300), legacyIsErr)
}

func truncateForLog(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}

// renderAny flattens a tool response - OrderedMaps, slices and scalars - into text, so a case reports what
// the tool actually answered instead of a shape it guessed.
func renderAny(v any) string {
	var b strings.Builder
	writeAny(&b, v)
	return b.String()
}

func writeAny(b *strings.Builder, v any) {
	switch t := v.(type) {
	case nil:
		b.WriteString("null")
	case *entities.OrderedMap[any]:
		b.WriteString("{")
		for i, k := range t.Keys() {
			if i > 0 {
				b.WriteString(", ")
			}
			b.WriteString(k)
			b.WriteString(": ")
			item, _ := t.Get(k)
			writeAny(b, item)
		}
		b.WriteString("}")
	case []any:
		b.WriteString("[")
		for i, item := range t {
			if i > 0 {
				b.WriteString(", ")
			}
			writeAny(b, item)
		}
		b.WriteString("]")
	case map[string]any:
		b.WriteString("{")
		first := true
		for k, item := range t {
			if !first {
				b.WriteString(", ")
			}
			first = false
			b.WriteString(k)
			b.WriteString(": ")
			writeAny(b, item)
		}
		b.WriteString("}")
	default:
		b.WriteString(fmt.Sprint(t))
	}
}
