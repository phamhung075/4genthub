package facades

import (
	"context"
	"testing"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
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

// capturingMinimalLister records the assignee the facade hands the performance path. That
// path used to receive a literal nil on EVERY list call - IsPerformanceMode() is
// unconditionally true - so a filtered list answered with rows the caller had excluded.
type capturingMinimalLister struct {
	assigneeID *string
	offset     int
	total      int
	calls      int
	countCalls int
}

func (c *capturingMinimalLister) ListTasksMinimal(_ context.Context, _, _, assigneeID, _ *string, _, offset *int) ([]*entities.OrderedMap[any], error) {
	c.calls++
	c.assigneeID = assigneeID
	if offset != nil {
		c.offset = *offset
	}
	return nil, nil
}

func (c *capturingMinimalLister) CountTasksMinimal(_ context.Context, _, _, _, _ *string) (int, error) {
	c.countCalls++
	return c.total, nil
}

func TestListTasksForwardsTheAssigneeToThePerformancePath(t *testing.T) {
	assignee := "@go-dev"
	lister := &capturingMinimalLister{}
	f := &TaskApplicationFacade{deps: TaskFacadeDeps{
		NewMinimalLister: func(_, _ *string) (TaskMinimalLister, error) { return lister, nil },
	}}

	f.ListTasks(context.Background(), dtostask.ListTasksRequest{
		Assignees: []string{assignee},
		Limit:     new(int),
	}, false, true, false)

	if lister.calls != 1 {
		t.Fatalf("performance path should have run once, ran %d", lister.calls)
	}
	if lister.assigneeID == nil || *lister.assigneeID != assignee {
		t.Fatalf("assignee filter was not forwarded: %v", lister.assigneeID)
	}

	// An unfiltered list must still take the performance path, with no assignee invented.
	unfiltered := &capturingMinimalLister{}
	f.deps.NewMinimalLister = func(_, _ *string) (TaskMinimalLister, error) { return unfiltered, nil }
	f.ListTasks(context.Background(), dtostask.ListTasksRequest{Limit: new(int)}, false, true, false)
	if unfiltered.calls != 1 || unfiltered.assigneeID != nil {
		t.Fatalf("unfiltered list: calls=%d assignee=%v", unfiltered.calls, unfiltered.assigneeID)
	}
}

// TestListTasksPerformancePathForwardsOffsetAndTotal is the live path's half of the enumeration
// defect: IsPerformanceMode() is unconditionally true, so the MCP list runs here - and this branch
// used to hardcode offset 0 and report the page length as the total, which made page 2 the same as
// page 1 while the pagination block claimed otherwise.
func TestListTasksPerformancePathForwardsOffsetAndTotal(t *testing.T) {
	lister := &capturingMinimalLister{total: 137}
	f := &TaskApplicationFacade{deps: TaskFacadeDeps{
		NewMinimalLister: func(_, _ *string) (TaskMinimalLister, error) { return lister, nil },
	}}

	limit, offset := 20, 40
	out := f.ListTasks(context.Background(), dtostask.ListTasksRequest{
		Limit:  &limit,
		Offset: &offset,
	}, false, true, false)

	if lister.offset != 40 {
		t.Fatalf("performance path offset = %d, want the requested 40", lister.offset)
	}
	if lister.countCalls != 1 {
		t.Fatalf("count calls = %d, want 1: a total must come from a count, not the page", lister.countCalls)
	}
	if total, _ := out.Get("total"); total != 137 {
		t.Fatalf("facade total = %v, want 137", total)
	}

	// An explicit ordering the minimal lister cannot serve falls through instead of being ignored:
	// the ORM lister sorts by updated_at and the superset lister by created_at, so any named ordering
	// has to go to the full path, which honours it.
	sortBy, sortOrder := "title", "asc"
	if minimalListerServesOrder(&sortBy, nil) || minimalListerServesOrder(nil, &sortOrder) {
		t.Fatal("minimalListerServesOrder accepted an explicit ordering the lister cannot serve")
	}
	if !minimalListerServesOrder(nil, nil) || !minimalListerServesOrder(new(string), new(string)) {
		t.Fatal("minimalListerServesOrder rejected the default ordering")
	}
}
