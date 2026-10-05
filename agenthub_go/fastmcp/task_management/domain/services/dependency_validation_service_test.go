package services

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type depRepo struct{ tasks []*entities.Task }

func (r depRepo) FindByID(_ context.Context, id value_objects.TaskId) (*entities.Task, error) {
	for _, t := range r.tasks {
		if t.ID.Value == id.Value {
			return t, nil
		}
	}
	return nil, nil
}
func (r depRepo) FindAll(context.Context) ([]*entities.Task, error) { return r.tasks, nil }

func uid(n int) string { return fmt.Sprintf("00000000-0000-4000-8000-%012d", n) }

func depTask(n int, title, status string, deps ...any) *entities.Task {
	id, _ := value_objects.NewTaskId(uid(n))
	prio := value_objects.PriorityHigh()
	t := &entities.Task{ID: &id, Title: title, Status: &value_objects.TaskStatus{Value: status}, Priority: &prio}
	for _, d := range deps {
		switch x := d.(type) {
		case int:
			did, _ := value_objects.NewTaskId(uid(x))
			t.Dependencies = append(t.Dependencies, did)
		case string:
			t.Dependencies = append(t.Dependencies, value_objects.TaskId{EntityId: value_objects.EntityId{Value: x}})
		}
	}
	return t
}

func normalizeJSON(t *testing.T, v any) any {
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	var out any
	_ = json.Unmarshal(b, &out)
	return out
}

// Expected values come from running the Python DependencyValidationService on the same
// graph. Notable: A -> (B, C) -> D is a diamond, which Python's DFS mishandles (ValueError
// swallowed), so no cycle is ever reported for it.
func TestDependencyValidationAgainstPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/dependency_validation_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var want map[string]map[string]any
	if err := json.Unmarshal(raw, &want); err != nil {
		t.Fatal(err)
	}
	repo := depRepo{[]*entities.Task{
		depTask(1, "A", "todo", 2, 3), depTask(2, "B", "in_progress", 4), depTask(3, "C", "blocked", 4), depTask(4, "D", "done"),
		depTask(5, "E", "todo", 6), depTask(6, "F", "todo", 5), depTask(7, "G", "todo", 1, 99, 7, "bad"),
		depTask(8, "H", "todo", 9, 10), depTask(9, "I", "cancelled"), depTask(10, "J", "done"), depTask(11, "K", "todo"),
	}}
	svc := NewDependencyValidationService(repo, nil)
	ctx := context.Background()
	id := func(n int) value_objects.TaskId { v, _ := value_objects.NewTaskId(uid(n)); return v }
	strip := func(m map[string]any) map[string]any {
		delete(m, "validation_timestamp")
		delete(m, "analysis_timestamp")
		return m
	}
	for _, n := range []int{1, 5, 7, 8, 11, 50} {
		got := normalizeJSON(t, strip(svc.ValidateDependencyChain(ctx, id(n))))
		if !reflect.DeepEqual(got, any(want[fmt.Sprintf("v%d", n)])) {
			t.Errorf("v%d\n got  %v\n want %v", n, got, want[fmt.Sprintf("v%d", n)])
		}
	}
	for _, n := range []int{1, 7, 50} {
		got := normalizeJSON(t, strip(svc.GetDependencyChainStatus(ctx, id(n))))
		if !reflect.DeepEqual(got, any(want[fmt.Sprintf("s%d", n)])) {
			t.Errorf("s%d\n got  %v\n want %v", n, got, want[fmt.Sprintf("s%d", n)])
		}
	}
}
