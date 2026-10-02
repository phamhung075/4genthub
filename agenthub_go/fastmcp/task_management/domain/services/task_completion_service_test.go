package services

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type fakeSubtasks struct {
	repositories.SubtaskRepository
	list []*entities.Subtask
}

func (f fakeSubtasks) FindByParentTaskID(context.Context, value_objects.TaskId) ([]*entities.Subtask, error) {
	return f.list, nil
}

func sub(title, status string, progress int) *entities.Subtask {
	id := value_objects.GenerateNewTaskId()
	return &entities.Subtask{Title: title, ID: &id, Status: &value_objects.TaskStatus{Value: status}, ProgressPercentage: progress}
}

func TestTaskCompletion(t *testing.T) {
	id := value_objects.GenerateNewTaskId()
	task := &entities.Task{ID: &id, Title: "T"}
	svc := NewTaskCompletionService(fakeSubtasks{list: []*entities.Subtask{
		sub("a", "todo", 0), sub("b", "todo", 0), sub("c", "todo", 0), sub("d", "todo", 0), sub("e", "done", 100)}}, nil)
	ok, msg := svc.CanCompleteTask(context.Background(), task)
	if ok || *msg != "Cannot complete task: 4 of 5 subtasks are not done" {
		t.Fatal(ok, msg)
	}
	err := svc.ValidateTaskCompletion(context.Background(), task)
	e, isErr := err.(*exceptions.TaskCompletionError)
	if !isErr || e.Context["total_count"] != 5 || e.Context["incomplete_count"] != 4 {
		t.Fatalf("%v", err)
	}
	b := svc.GetCompletionBlockers(context.Background(), task)
	want := "4 of 5 subtasks are incomplete (including: a, b, c, and 1 more). Complete all subtasks first."
	if len(b) != 1 || b[0] != want {
		t.Fatal(b)
	}
	sum := svc.GetSubtaskCompletionSummary(context.Background(), task)
	if sum["completion_percentage"] != 20.0 || sum["can_complete_parent"] != false {
		t.Fatal(sum)
	}
	empty := NewTaskCompletionService(fakeSubtasks{}, nil)
	if ok, _ := empty.CanCompleteTask(context.Background(), task); !ok {
		t.Fatal("no subtasks")
	}
	if empty.GetSubtaskCompletionSummary(context.Background(), task)["completion_percentage"] != 100 {
		t.Fatal("empty summary")
	}
}
