package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func zpAMockTestOrderedMap(t *testing.T, pairs ...any) *entities.OrderedMap[any] {
	t.Helper()
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

func zpAMockTestData(t *testing.T, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	t.Helper()
	dataAny, _ := context.Get("data")
	data, ok := dataAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("data = %v, want *OrderedMap", dataAny)
	}
	return data
}

func zpAMockTestExpectKeys(t *testing.T, m *entities.OrderedMap[any], want []string) {
	t.Helper()
	got := m.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
}

func TestMockUnifiedContextService_GetContext_Absent(t *testing.T) {
	svc := NewMockUnifiedContextService()
	if got := svc.GetContext("task", "missing", true, false); got != nil {
		t.Fatalf("GetContext = %v, want nil", got)
	}
}

func TestMockUnifiedContextService_CreateAndGetContext(t *testing.T) {
	svc := NewMockUnifiedContextService()
	data := zpAMockTestOrderedMap(t, "a", 1)
	parentID := "parent-1"

	created := svc.CreateContext("task", "ctx-1", data, &parentID)
	zpAMockTestExpectKeys(t, created, []string{"id", "level", "data", "parent_id", "created_at", "updated_at"})
	if v, _ := created.Get("id"); v != "ctx-1" {
		t.Fatalf("id = %v", v)
	}
	if v, _ := created.Get("level"); v != "task" {
		t.Fatalf("level = %v", v)
	}
	if v, _ := created.Get("parent_id"); v != "parent-1" {
		t.Fatalf("parent_id = %v", v)
	}
	if got := svc.GetContext("task", "ctx-1", true, false); got != created {
		t.Fatalf("GetContext did not return the stored context")
	}
	if v, _ := created.Get("created_at"); v == "" {
		t.Fatalf("created_at empty")
	}
}

func TestMockUnifiedContextService_CreateContext_NoParent(t *testing.T) {
	svc := NewMockUnifiedContextService()
	created := svc.CreateContext("project", "ctx-1", entities.NewOrderedMap[any](), nil)
	if v, ok := created.Get("parent_id"); !ok || v != nil {
		t.Fatalf("parent_id = %v (%v), want nil", v, ok)
	}
}

func TestMockUnifiedContextService_UpdateContext_Merge(t *testing.T) {
	svc := NewMockUnifiedContextService()
	svc.CreateContext("task", "ctx-1", zpAMockTestOrderedMap(t, "a", 1, "b", 2), nil)

	updated := svc.UpdateContext("task", "ctx-1", zpAMockTestOrderedMap(t, "b", 3, "c", 4), true, false)
	data := zpAMockTestData(t, updated)
	if len(data.Keys()) != 3 {
		t.Fatalf("keys = %v, want 3 entries", data.Keys())
	}
	if v, _ := data.Get("a"); v != 1 {
		t.Fatalf("a = %v", v)
	}
	if v, _ := data.Get("b"); v != 3 {
		t.Fatalf("b = %v", v)
	}
	if v, _ := data.Get("c"); v != 4 {
		t.Fatalf("c = %v", v)
	}
}

func TestMockUnifiedContextService_UpdateContext_Replace(t *testing.T) {
	svc := NewMockUnifiedContextService()
	svc.CreateContext("task", "ctx-1", zpAMockTestOrderedMap(t, "a", 1), nil)

	updated := svc.UpdateContext("task", "ctx-1", zpAMockTestOrderedMap(t, "b", 2), false, false)
	data := zpAMockTestData(t, updated)
	if len(data.Keys()) != 1 {
		t.Fatalf("keys = %v, want [b]", data.Keys())
	}
	if v, _ := data.Get("b"); v != 2 {
		t.Fatalf("b = %v", v)
	}
}

func TestMockUnifiedContextService_UpdateContext_AutoCreate(t *testing.T) {
	svc := NewMockUnifiedContextService()
	updated := svc.UpdateContext("task", "ctx-1", zpAMockTestOrderedMap(t, "a", 1), true, false)
	zpAMockTestExpectKeys(t, updated, []string{"id", "level", "data", "parent_id", "created_at", "updated_at"})
	if got := svc.GetContext("task", "ctx-1", true, false); got != updated {
		t.Fatalf("auto-created context not stored")
	}
}

func TestMockUnifiedContextService_DeleteContext(t *testing.T) {
	svc := NewMockUnifiedContextService()
	svc.CreateContext("task", "ctx-1", entities.NewOrderedMap[any](), nil)

	if !svc.DeleteContext("task", "ctx-1") {
		t.Fatalf("first DeleteContext = false, want true")
	}
	if svc.DeleteContext("task", "ctx-1") {
		t.Fatalf("second DeleteContext = true, want false")
	}
}

func TestMockUnifiedContextService_ResolveContext(t *testing.T) {
	svc := NewMockUnifiedContextService()
	stored := svc.CreateContext("task", "ctx-1", zpAMockTestOrderedMap(t, "a", 1), nil)
	if got := svc.ResolveContext("task", "ctx-1", true, false); got != stored {
		t.Fatalf("ResolveContext did not return the stored context")
	}

	defaultContext := svc.ResolveContext("task", "absent", true, false)
	zpAMockTestExpectKeys(t, defaultContext, []string{"id", "level", "data", "resolved", "created_at"})
	if v, _ := defaultContext.Get("resolved"); v != true {
		t.Fatalf("resolved = %v", v)
	}
	if data := zpAMockTestData(t, defaultContext); data.Len() != 0 {
		t.Fatalf("default data = %v, want empty", data.Keys())
	}
}

func TestMockUnifiedContextService_DelegateContext(t *testing.T) {
	svc := NewMockUnifiedContextService()
	result := svc.DelegateContext("task", "ctx-1", "project", entities.NewOrderedMap[any](), nil)
	zpAMockTestExpectKeys(t, result, []string{"success", "delegated_to", "delegation_reason"})
	if v, _ := result.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	if v, _ := result.Get("delegated_to"); v != "project" {
		t.Fatalf("delegated_to = %v", v)
	}
	if v, _ := result.Get("delegation_reason"); v != nil {
		t.Fatalf("delegation_reason = %v, want nil", v)
	}

	reason := "why"
	result = svc.DelegateContext("task", "ctx-1", "project", entities.NewOrderedMap[any](), &reason)
	if v, _ := result.Get("delegation_reason"); v != "why" {
		t.Fatalf("delegation_reason = %v", v)
	}
}

func TestMockUnifiedContextService_ListContexts(t *testing.T) {
	svc := NewMockUnifiedContextService()
	c1 := svc.CreateContext("task", "1", entities.NewOrderedMap[any](), nil)
	c2 := svc.CreateContext("task", "2", entities.NewOrderedMap[any](), nil)
	c3 := svc.CreateContext("project", "1", entities.NewOrderedMap[any](), nil)

	all := svc.ListContexts(nil, nil)
	if len(all) != 3 || all[0] != c1 || all[1] != c2 || all[2] != c3 {
		t.Fatalf("all = %v, want [c1 c2 c3]", all)
	}

	level := "task"
	tasks := svc.ListContexts(&level, nil)
	if len(tasks) != 2 || tasks[0] != c1 || tasks[1] != c2 {
		t.Fatalf("tasks = %v, want [c1 c2]", tasks)
	}

	emptyLevel := ""
	if got := svc.ListContexts(&emptyLevel, nil); len(got) != 3 {
		t.Fatalf("empty-level filter = %d, want 3", len(got))
	}
}

func TestMockUnifiedContextService_AddInsight(t *testing.T) {
	svc := NewMockUnifiedContextService()
	insight := zpAMockTestOrderedMap(t, "note", "n1")

	context := svc.AddInsight("task", "ctx-1", insight)
	zpAMockTestExpectKeys(t, context, []string{"id", "level", "data", "parent_id", "created_at", "updated_at"})
	data := zpAMockTestData(t, context)
	insights, _ := data.Get("insights")
	list, ok := insights.([]any)
	if !ok || len(list) != 1 || list[0] != insight {
		t.Fatalf("insights = %v, want [insight]", insights)
	}

	context = svc.AddInsight("task", "ctx-1", insight)
	data = zpAMockTestData(t, context)
	insights, _ = data.Get("insights")
	list, _ = insights.([]any)
	if len(list) != 2 {
		t.Fatalf("insights length = %d, want 2", len(list))
	}
}

func TestMockUnifiedContextService_AddProgress(t *testing.T) {
	svc := NewMockUnifiedContextService()
	progress := zpAMockTestOrderedMap(t, "percent", 50)

	context := svc.AddProgress("task", "ctx-1", progress)
	zpAMockTestExpectKeys(t, context, []string{"id", "level", "data", "parent_id", "created_at", "updated_at"})
	data := zpAMockTestData(t, context)
	progressUpdates, _ := data.Get("progress")
	list, ok := progressUpdates.([]any)
	if !ok || len(list) != 1 || list[0] != progress {
		t.Fatalf("progress = %v, want [progress]", progressUpdates)
	}
}

func TestMockUnifiedContextService_ValidateHierarchy(t *testing.T) {
	svc := NewMockUnifiedContextService()
	result := svc.ValidateHierarchy("task-1", nil, nil)
	zpAMockTestExpectKeys(t, result, []string{"valid", "message"})
	if v, _ := result.Get("valid"); v != true {
		t.Fatalf("valid = %v", v)
	}
	if v, _ := result.Get("message"); v != "Mock hierarchy validation - always valid" {
		t.Fatalf("message = %v", v)
	}
}

func TestMockUnifiedContextService_GetHierarchyChain(t *testing.T) {
	svc := NewMockUnifiedContextService()
	if got := svc.GetHierarchyChain("task", "absent"); len(got) != 0 {
		t.Fatalf("chain = %v, want empty", got)
	}
	context := svc.CreateContext("task", "ctx-1", entities.NewOrderedMap[any](), nil)
	chain := svc.GetHierarchyChain("task", "ctx-1")
	if len(chain) != 1 || chain[0] != context {
		t.Fatalf("chain = %v, want [context]", chain)
	}
}
