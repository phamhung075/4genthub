package facades

import (
	"context"
	"testing"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
)

// TestFacadeEmptyTaskIDResponses checks the application-boundary validation
// branches of get_dependencies / clear_dependencies / get_blocking_tasks: the
// Python returns a fixed dict before touching any use case, so the facade can be
// exercised with nil dependencies.
func TestFacadeEmptyTaskIDResponses(t *testing.T) {
	f := &TaskApplicationFacade{}
	ctx := context.Background()

	cases := []struct {
		name   string
		got    func() (bool, string, string)
		action string
	}{
		{
			name: "get_dependencies",
			got: func() (bool, string, string) {
				m := f.GetDependencies(ctx, "  ", nil)
				success, _ := m.Get("success")
				action, _ := m.Get("action")
				errMsg, _ := m.Get("error")
				return success.(bool), action.(string), errMsg.(string)
			},
			action: "get_dependencies",
		},
		{
			name: "clear_dependencies",
			got: func() (bool, string, string) {
				m := f.ClearDependencies(ctx, "", nil)
				success, _ := m.Get("success")
				action, _ := m.Get("action")
				errMsg, _ := m.Get("error")
				return success.(bool), action.(string), errMsg.(string)
			},
			action: "clear_dependencies",
		},
		{
			name: "get_blocking_tasks",
			got: func() (bool, string, string) {
				m := f.GetBlockingTasks(ctx, "", nil)
				success, _ := m.Get("success")
				action, _ := m.Get("action")
				errMsg, _ := m.Get("error")
				return success.(bool), action.(string), errMsg.(string)
			},
			action: "get_blocking_tasks",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			success, action, errMsg := tc.got()
			if success {
				t.Fatalf("expected success=false")
			}
			if action != tc.action {
				t.Fatalf("action = %q, want %q", action, tc.action)
			}
			if errMsg != "Task ID is required" {
				t.Fatalf("error = %q, want %q", errMsg, "Task ID is required")
			}
		})
	}
}

// TestFacadeFilterHelpers checks the dict.get-equivalent conversions used by
// count_tasks: missing keys become nil / empty slice, present keys are kept.
func TestFacadeFilterHelpers(t *testing.T) {
	filters := map[string]any{
		"status":    "todo",
		"assignees": []any{"alice", "bob"},
	}

	if got := facadeStringPtr(filters, "status"); got == nil || *got != "todo" {
		t.Fatalf("status = %v, want todo", got)
	}
	if got := facadeStringPtr(filters, "priority"); got != nil {
		t.Fatalf("missing priority = %v, want nil", got)
	}
	if got := facadeStringSlice(filters, "assignees"); len(got) != 2 || got[0] != "alice" || got[1] != "bob" {
		t.Fatalf("assignees = %v, want [alice bob]", got)
	}
	if got := facadeStringSlice(filters, "labels"); got == nil || len(got) != 0 {
		t.Fatalf("missing labels = %v, want empty slice", got)
	}
}

func TestFacadeBoundaryValidation(t *testing.T) {
	ctx := context.Background()
	f := &TaskApplicationFacade{}

	if r := f.SearchTasks(ctx, dtostask.SearchTasksRequest{Query: "  "}, false); r.Has("tasks") || facadeDictGet(r, "error") != "Search query is required" || facadeDictGet(r, "action") != "search" {
		t.Fatalf("search: %v", r)
	}
	if r := f.GetTask(ctx, " ", true, true); facadeDictGet(r, "error") != "Unexpected error: Task ID is required" {
		t.Fatalf("get: %v", r)
	}
	if r := f.DeleteTask(ctx, "", nil); facadeDictGet(r, "error") != "Task ID is required" {
		t.Fatalf("delete: %v", r)
	}
	if r := f.CompleteTask(ctx, "", nil, nil, nil); facadeDictGet(r, "error") != "Task ID is required" {
		t.Fatalf("complete: %v", r)
	}
	if r := f.AddDependency(ctx, "", "x"); facadeDictGet(r, "success") != true || facadeDictGet(r, "task") != nil {
		t.Fatalf("add noop: %v", r)
	}
	if r := f.RemoveDependency(ctx, "a", " "); facadeDictGet(r, "error") != "Dependency ID cannot be empty or whitespace" {
		t.Fatalf("remove: %v", r)
	}
	if r := f.ListSubtasksSummary(ctx, "a", true); facadeDictGet(r, "error") != "Subtask repository not configured" {
		t.Fatalf("subtasks: %v", r)
	}
}

func TestFacadeSliceBounds(t *testing.T) {
	two, neg := 2, -2
	cases := []struct {
		n     int
		start *int
		stop  int
		lo    int
		hi    int
	}{
		{5, nil, 3, 0, 3}, {5, nil, -2, 0, 3}, {5, nil, 99, 0, 5}, {5, &two, 5, 2, 5},
		{5, &two, 0, 2, 2}, {5, &neg, 5, 3, 5}, {0, nil, -1, 0, 0},
	}
	for _, c := range cases {
		lo, hi := facadeSliceBounds(c.n, c.start, c.stop)
		if lo != c.lo || hi != c.hi {
			t.Errorf("n=%d start=%v stop=%d: got [%d:%d] want [%d:%d]", c.n, c.start, c.stop, lo, hi, c.lo, c.hi)
		}
	}
}
