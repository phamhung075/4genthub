package services

import (
	"context"
	"encoding/json"
	"fmt"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type progressSubs []*entities.Subtask

func (p progressSubs) FindByParentTaskID(context.Context, value_objects.TaskId) ([]*entities.Subtask, error) {
	return p, nil
}

func progressSub(title string, n int, done bool) *entities.Subtask {
	id, _ := value_objects.NewTaskId(fmt.Sprintf("00000000-0000-4000-8000-00000000000%d", n))
	status, progress := "todo", 10
	if done {
		status, progress = "done", 100
	}
	return &entities.Subtask{ID: &id, Title: title, Status: &value_objects.TaskStatus{Value: status}, ProgressPercentage: progress}
}

// normalize round-trips through JSON so int/float and slice types compare like Python's json.dumps output.
func normalize(t *testing.T, v any) any {
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	var out any
	_ = json.Unmarshal(b, &out)
	return out
}

func decode(t *testing.T, s string) any {
	var out any
	if err := json.Unmarshal([]byte(s), &out); err != nil {
		t.Fatal(err)
	}
	return out
}

// Expected JSON was produced by the Python TaskProgressService.
func TestTaskProgressAgainstPython(t *testing.T) {
	tid, _ := value_objects.NewTaskId("00000000-0000-4000-8000-000000000009")
	task := &entities.Task{ID: &tid, Status: &value_objects.TaskStatus{Value: "in_progress"}}
	subs := progressSubs{progressSub("a", 1, true)}
	for i, c := range "bcdefg" {
		subs = append(subs, progressSub(string(c), i+2, false))
	}
	ctx := context.Background()
	svc := NewTaskProgressService(subs)
	want := `{"base_progress": {"is_blocked": false, "is_completed": false, "is_in_progress": true, "progress_percentage": 50.0, "status": "in_progress"}, "blocking_factors": ["6 of 7 subtasks incomplete"], "can_complete": false, "overall_progress": {"base_contribution": 50.0, "calculation_method": "weighted_combination", "percentage": 35.72, "subtask_contribution": 14.3, "weighted_percentage": 35.72}, "subtask_progress": {"can_complete_parent": false, "completed": 1, "completed_titles": ["a"], "completion_percentage": 14.3, "details": [{"id": "00000000-0000-4000-8000-000000000001", "progress_percentage": 100, "status": "completed", "title": "a"}, {"id": "00000000-0000-4000-8000-000000000002", "progress_percentage": 10, "status": "incomplete", "title": "b"}, {"id": "00000000-0000-4000-8000-000000000003", "progress_percentage": 10, "status": "incomplete", "title": "c"}, {"id": "00000000-0000-4000-8000-000000000004", "progress_percentage": 10, "status": "incomplete", "title": "d"}, {"id": "00000000-0000-4000-8000-000000000005", "progress_percentage": 10, "status": "incomplete", "title": "e"}, {"id": "00000000-0000-4000-8000-000000000006", "progress_percentage": 10, "status": "incomplete", "title": "f"}, {"id": "00000000-0000-4000-8000-000000000007", "progress_percentage": 10, "status": "incomplete", "title": "g"}], "incomplete": 6, "incomplete_titles": ["b", "c", "d", "e", "f"], "total": 7}, "task_id": "00000000-0000-4000-8000-000000000009"}`
	if got := normalize(t, svc.CalculateTaskProgress(ctx, task)); !reflect.DeepEqual(got, decode(t, want)) {
		t.Fatalf("got %v", got)
	}
	if s := svc.CalculateProgressScore(ctx, task); s != 0.3572 {
		t.Fatal(s)
	}
	if p := NewTaskProgressService(subs[:3]).CalculateSubtaskCompletionPercentage(ctx, task); p != 33.3 {
		t.Fatal(p)
	}
	wantNone := `{"base_progress": {"is_blocked": false, "is_completed": false, "is_in_progress": true, "progress_percentage": 50.0, "status": "in_progress"}, "blocking_factors": [], "can_complete": true, "overall_progress": {"calculation_method": "task_status_only", "percentage": 50.0, "weighted_percentage": 50.0}, "subtask_progress": null, "task_id": "00000000-0000-4000-8000-000000000009"}`
	if got := normalize(t, NewTaskProgressService(nil).CalculateTaskProgress(ctx, task)); !reflect.DeepEqual(got, decode(t, wantNone)) {
		t.Fatalf("got %v", got)
	}
	// ROUND_HALF_UP: 1/16*100 = 6.25 -> 6.3 (banker's rounding would give 6.2)
	if percentOneDecimal(1, 16) != 6.3 {
		t.Fatal(percentOneDecimal(1, 16))
	}
}
