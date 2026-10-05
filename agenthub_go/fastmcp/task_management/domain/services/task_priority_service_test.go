package services

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type prioRepo struct{ tasks []*entities.Task }

func (r prioRepo) FindAll(context.Context) ([]*entities.Task, error) { return r.tasks, nil }
func (r prioRepo) FindByGitBranchID(context.Context, string) ([]*entities.Task, error) {
	return r.tasks, nil
}

func prioTask(n int, status, prio string, ageDays float64, deps ...int) *entities.Task {
	id, _ := value_objects.NewTaskId(uid(n))
	p, _ := value_objects.NewPriority(prio)
	created := time.Now().UTC().Add(-time.Duration(ageDays*24*float64(time.Hour)) - time.Hour)
	t := &entities.Task{ID: &id, Title: fmt.Sprintf("t%d", n), Status: &value_objects.TaskStatus{Value: status}, Priority: &p}
	t.CreatedAt = &created
	for _, d := range deps {
		did, _ := value_objects.NewTaskId(uid(d))
		t.Dependencies = append(t.Dependencies, did)
	}
	return t
}

func roundTrip(t *testing.T, v any) any {
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	var out any
	_ = json.Unmarshal(b, &out)
	return out
}

func without(m map[string]any, keys ...string) map[string]any {
	out := map[string]any{}
	for k, v := range m {
		out[k] = v
	}
	for _, k := range keys {
		delete(out, k)
	}
	return out
}

// Expected values come from running the Python TaskPriorityService.
func TestTaskPriorityAgainstPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/task_priority_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var want map[string]any
	if err := json.Unmarshal(raw, &want); err != nil {
		t.Fatal(err)
	}
	tasks := []*entities.Task{
		prioTask(1, "todo", "medium", 0.5), prioTask(2, "in_progress", "high", 10), prioTask(3, "review", "critical", 100),
		prioTask(4, "blocked", "low", 5), prioTask(5, "done", "urgent", 40), prioTask(6, "testing", "medium", 2, 2, 5),
		prioTask(7, "todo", "high", 50, 1),
	}
	svc := NewTaskPriorityService(prioRepo{tasks})
	scores, ctxScores, adjust := map[string]any{}, map[string]any{}, map[string]any{}
	for _, task := range tasks {
		id := task.ID.Value
		scores[id] = svc.CalculatePriorityScore(task, nil)
		ctxScores[id] = svc.CalculatePriorityScore(task, map[string]any{"dependent_task_count": 4})
		adjust[id] = svc.AdjustPriorityForDependencies(task, tasks)
	}
	check := func(name string, got any) {
		if g := roundTrip(t, got); !reflect.DeepEqual(g, want[name]) {
			t.Errorf("%s\n got  %v\n want %v", name, g, want[name])
		}
	}
	check("scores", scores)
	check("ctx", ctxScores)
	check("adjust", adjust)
	check("bad_ctx", svc.CalculatePriorityScore(tasks[0], map[string]any{"dependent_task_count": "x"}))
	check("adjust_none", svc.AdjustPriorityForDependencies(tasks[0], nil))

	var order []any
	for _, o := range svc.OrderTasksByPriority(tasks, nil) {
		f := o["priority_factors"].(map[string]any)
		factors := map[string]any{}
		for k, v := range f {
			if k == "age_factor" {
				v = v.(map[string]any)["score"]
			}
			factors[k] = v
		}
		order = append(order, []any{o["task_id"], o["priority_score"], o["base_priority"], o["status"], factors})
	}
	check("order", order)
	ctx := context.Background()
	check("rec", without(svc.GetNextTaskRecommendation(ctx, "b", nil), "task"))
	if r := svc.GetNextTaskRecommendation(ctx, "b", []string{"DONE", "cancelled", "in_progress"}); r == nil {
		t.Fatal("rec_excl nil")
	} else {
		check("rec_excl", without(r, "task"))
	}
}

// Python defect: a due date (a str) makes _get_priority_factors raise, so ordering falls
// back to error entries and the recommendation is None.
func TestTaskPriorityDueDateDefect(t *testing.T) {
	due := "2030-01-01T00:00:00+00:00"
	a, b := prioTask(1, "todo", "medium", 0.5), prioTask(2, "todo", "medium", 0.5)
	b.DueDate = &due
	svc := NewTaskPriorityService(prioRepo{[]*entities.Task{a, b}})
	if u := calculateUrgencyScore(b); u != 30.0 {
		t.Fatal(u)
	}
	got := svc.OrderTasksByPriority([]*entities.Task{a, b}, nil)
	if len(got) != 2 || got[0]["priority_score"] != 0.0 || got[0]["error"] != "'str' object has no attribute 'isoformat'" {
		t.Fatalf("%v", got)
	}
	if r := svc.GetNextTaskRecommendation(context.Background(), "b", nil); r != nil {
		t.Fatalf("%v", r)
	}
}
