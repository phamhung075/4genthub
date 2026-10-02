package services

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func minRespOrderedKeys(t *testing.T, m *entities.OrderedMap[any]) string {
	t.Helper()
	return strings.Join(m.Keys(), ",")
}

func TestMinimalResponseSerializerTaskCreateKeyOrder(t *testing.T) {
	full := entities.NewOrderedMap[any]()
	full.Set("id", "t1")
	full.Set("created_at", "2025-01-01T00:00:00+00:00")
	full.Set("updated_at", "2025-01-02T00:00:00+00:00")
	full.Set("context_id", "c1")
	full.Set("overall_progress", 42)
	full.Set("progress_percentage", 42)
	full.Set("progress_count", 3)
	full.Set("subtask_count", 2)
	full.Set("completed_subtasks", 1)
	full.Set("dependency_count", 4)
	full.Set("git_branch_id", "b1")
	full.Set("status", "in_progress")
	full.Set("priority", "high")
	full.Set("title", "ignored")

	out, err := MinimalResponseSerializer{}.SerializeTaskMinimal(full, "create")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	// Python insertion order.
	want := "id,created_at,updated_at,context_id,overall_progress,progress_percentage,progress_count,subtask_count,completed_subtasks,dependency_count,git_branch_id,status,priority"
	if got := minRespOrderedKeys(t, out); got != want {
		t.Fatalf("key order = %q, want %q", got, want)
	}
	if v, _ := out.Get("id"); v != "t1" {
		t.Errorf("id = %v, want t1", v)
	}
	if v, _ := out.Get("context_id"); v != "c1" {
		t.Errorf("context_id = %v, want c1", v)
	}
	if v, _ := out.Get("priority"); v != "high" {
		t.Errorf("priority = %v, want high", v)
	}
}

func TestMinimalResponseSerializerTaskUpdateDropsCreateOnlyFields(t *testing.T) {
	full := entities.NewOrderedMap[any]()
	full.Set("id", "t1")
	full.Set("created_at", "a")
	full.Set("updated_at", "b")
	full.Set("git_branch_id", "b1")
	full.Set("status", "done")
	full.Set("priority", "low")

	out, err := MinimalResponseSerializer{}.SerializeTaskMinimal(full, "update")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := "id,created_at,updated_at"
	if got := minRespOrderedKeys(t, out); got != want {
		t.Fatalf("key order = %q, want %q", got, want)
	}
}

func TestMinimalResponseSerializerSubtaskCreateKeyOrder(t *testing.T) {
	full := entities.NewOrderedMap[any]()
	full.Set("id", "s1")
	full.Set("title", "sub")
	full.Set("description", "desc")
	full.Set("status", "todo")
	full.Set("parent_task_id", "t1")
	full.Set("created_at", "a")
	full.Set("updated_at", "b")
	full.Set("progress_percentage", 10)
	full.Set("progress_count", 1)
	full.Set("priority", "medium")

	out, err := MinimalResponseSerializer{}.SerializeSubtaskMinimal(full, "create")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := "id,title,description,status,task_id,parent_task_id,created_at,updated_at,progress_percentage,progress_count,priority"
	if got := minRespOrderedKeys(t, out); got != want {
		t.Fatalf("key order = %q, want %q", got, want)
	}
	if v, _ := out.Get("task_id"); v != "t1" {
		t.Errorf("task_id = %v, want t1", v)
	}
	if v, _ := out.Get("parent_task_id"); v != "t1" {
		t.Errorf("parent_task_id = %v, want t1", v)
	}
}

func TestMinimalResponseSerializerSubtaskUpdateDropsPriority(t *testing.T) {
	full := entities.NewOrderedMap[any]()
	full.Set("id", "s1")
	full.Set("title", "sub")
	full.Set("status", "todo")
	full.Set("priority", "medium")

	out, err := MinimalResponseSerializer{}.SerializeSubtaskMinimal(full, "update")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out.Has("priority") {
		t.Errorf("priority should be dropped for update")
	}
}

func TestMinimalResponseSerializerListKeyOrder(t *testing.T) {
	task := entities.NewOrderedMap[any]()
	task.Set("id", "t1")
	task.Set("title", "x")
	task.Set("description", "should be excluded")
	out := MinimalResponseSerializer{}.SerializeTaskListMinimal([]any{task})
	if len(out) != 1 {
		t.Fatalf("len = %d, want 1", len(out))
	}
	want := "id,title,status,priority,progress_percentage,subtask_count,completed_subtasks,assignees,created_at,updated_at"
	if got := minRespOrderedKeys(t, out[0]); got != want {
		t.Fatalf("key order = %q, want %q", got, want)
	}

	sub := entities.NewOrderedMap[any]()
	sub.Set("id", "s1")
	sub.Set("description", "should be excluded")
	outSub := MinimalResponseSerializer{}.SerializeSubtaskListMinimal([]any{sub})
	wantSub := "id,title,status,priority,progress_percentage,assignees,created_at,updated_at"
	if got := minRespOrderedKeys(t, outSub[0]); got != wantSub {
		t.Fatalf("subtask key order = %q, want %q", got, wantSub)
	}
}

func TestMinimalResponseSerializerDecisions(t *testing.T) {
	s := MinimalResponseSerializer{}
	for _, op := range []string{"create", "update", "complete"} {
		if !s.ShouldUseMinimalSerialization(op) {
			t.Errorf("ShouldUseMinimalSerialization(%q) = false, want true", op)
		}
	}
	for _, op := range []string{"list", "search", "get", ""} {
		if s.ShouldUseMinimalSerialization(op) {
			t.Errorf("ShouldUseMinimalSerialization(%q) = true, want false", op)
		}
	}
	cases := map[string]string{
		"create":   "~70-75% reduction (600-800 tokens → 150-200 tokens)",
		"update":   "~70-75% reduction (600-800 tokens → 150-200 tokens)",
		"complete": "~70-75% reduction (600-800 tokens → 150-200 tokens)",
		"list":     "~40-50% reduction per item",
		"search":   "~40-50% reduction per item",
		"other":    "No optimization (full details needed)",
	}
	for op, want := range cases {
		if got := s.GetTokenSavingsEstimate(op); got != want {
			t.Errorf("GetTokenSavingsEstimate(%q) = %q, want %q", op, got, want)
		}
	}
}

func TestOrchestratorServiceWithUser(t *testing.T) {
	svc := NewOrchestratorService(nil)
	if svc.UserID != nil {
		t.Fatalf("UserID = %v, want nil", svc.UserID)
	}
	other := svc.WithUser("u1")
	if other.UserID == nil || *other.UserID != "u1" {
		t.Fatalf("WithUser UserID = %v, want u1", other.UserID)
	}
	if svc.UserID != nil {
		t.Fatalf("original UserID mutated")
	}
}

type minRespFakeProgressStore struct {
	value float64
	ok    bool
	set   *float64
}

func (f *minRespFakeProgressStore) GetProgress(_ context.Context, _ string) (float64, bool) {
	return f.value, f.ok
}
func (f *minRespFakeProgressStore) SetProgress(_ context.Context, _ string, v float64) error {
	f.set = &v
	return nil
}

func TestTaskProgressServiceGetTaskProgress(t *testing.T) {
	svc := NewTaskProgressService(nil, nil, nil, &minRespFakeProgressStore{value: 55, ok: true})
	if got := svc.GetTaskProgress(nil, "t1"); got == nil || *got != 55 {
		t.Fatalf("GetTaskProgress = %v, want 55", got)
	}
	svc2 := NewTaskProgressService(nil, nil, nil, &minRespFakeProgressStore{ok: false})
	if got := svc2.GetTaskProgress(nil, "t1"); got == nil || *got != 0 {
		t.Fatalf("GetTaskProgress missing = %v, want 0", got)
	}
}

func TestTaskProgressServiceWithUser(t *testing.T) {
	svc := NewTaskProgressService(nil, nil, nil, nil)
	other := svc.WithUser("u1")
	if other.UserID == nil || *other.UserID != "u1" {
		t.Fatalf("WithUser UserID = %v, want u1", other.UserID)
	}
}
