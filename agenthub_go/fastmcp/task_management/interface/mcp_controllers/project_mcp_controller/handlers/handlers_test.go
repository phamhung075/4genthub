package handlers

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestSuccessFalse(t *testing.T) {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	if !successFalse(m) {
		t.Fatal("expected successFalse for success=false")
	}
	m2 := entities.NewOrderedMap[any]()
	m2.Set("success", true)
	if successFalse(m2) {
		t.Fatal("expected not successFalse for success=true")
	}
	if successFalse(nil) {
		t.Fatal("nil result is not a false-success dict")
	}
}

func TestIncludeProjectContext(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	project := entities.NewOrderedMap[any]()
	project.Set("id", "p1")
	result.Set("project", project)

	out := includeProjectContext(result)
	ctxAny, ok := out.Get("project_context")
	if !ok {
		t.Fatal("project_context not added")
	}
	ctx := ctxAny.(*entities.OrderedMap[any])
	if v, _ := ctx.Get("management_available"); v != true {
		t.Fatalf("management_available = %v", v)
	}
	if v, _ := ctx.Get("health_check_available"); v != true {
		t.Fatalf("health_check_available = %v", v)
	}
	ops := ctx.GetAny("maintenance_operations").([]any)
	want := []string{"project_health_check", "cleanup_obsolete", "validate_integrity", "rebalance_agents"}
	if len(ops) != len(want) {
		t.Fatalf("maintenance_operations len = %d", len(ops))
	}
	for i, w := range want {
		if ops[i] != w {
			t.Fatalf("maintenance_operations[%d] = %v, want %s", i, ops[i], w)
		}
	}
	// key order: project then project_context
	if keys := out.Keys(); len(keys) != 2 || keys[0] != "project" || keys[1] != "project_context" {
		t.Fatalf("keys = %v", keys)
	}
}

func TestIncludeProjectContextNoProject(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("data", 1)
	out := includeProjectContext(result)
	if out.Has("project_context") {
		t.Fatal("project_context must not be added when project key absent")
	}
}

func TestPyLen(t *testing.T) {
	if pyLen([]any{1, 2, 3}) != 3 {
		t.Fatal("list len")
	}
	if pyLen(map[string]any{"a": 1}) != 1 {
		t.Fatal("map len")
	}
	if pyLen(nil) != 0 {
		t.Fatal("nil len")
	}
}
