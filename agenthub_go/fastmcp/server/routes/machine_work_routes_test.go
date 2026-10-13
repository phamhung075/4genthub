package routes

import (
	"context"
	"testing"

	taskdomain "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type fakeMachineWorkFinder struct {
	tasks []*taskdomain.Task
}

func (f *fakeMachineWorkFinder) FindAll(ctx context.Context) ([]*taskdomain.Task, error) {
	return f.tasks, nil
}

func TestGetMachineWorkFiltersCorrectly(t *testing.T) {
	todo, _ := value_objects.NewTaskStatus("todo")
	done, _ := value_objects.NewTaskStatus("done")
	review, _ := value_objects.NewTaskStatus("review")
	id1, _ := value_objects.NewTaskId("11111111-1111-1111-1111-111111111111")
	id2, _ := value_objects.NewTaskId("22222222-2222-2222-2222-222222222222")
	id3, _ := value_objects.NewTaskId("33333333-3333-3333-3333-333333333333")

	tasks := []*taskdomain.Task{
		{
			ID:                 &id1,
			Title:              "Task 1",
			Status:             &todo,
			Assignees:          []string{"4genthub-min/lead"},
			AcceptanceCriteria: []string{"Criteria A"},
		},
		{
			ID:        &id2,
			Title:     "Task 2 (Done)",
			Status:    &done,
			Assignees: []string{"4genthub-min/fe-dev"},
		},
		{
			ID:        &id3,
			Title:     "Task 3 (Different Machine)",
			Status:    &review,
			Assignees: []string{"other-room/backend"},
		},
	}

	finder := &fakeMachineWorkFinder{tasks: tasks}
	work, err := GetMachineWork(context.Background(), "4genthub-min", finder)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if len(work) != 1 {
		t.Fatalf("expected 1 work item, got %d", len(work))
	}
	item := work[0]
	if item.ID != id1.Value || item.Assignee != "4genthub-min/lead" || len(item.AcceptanceCriteria) != 1 {
		t.Errorf("unexpected work item: %+v", item)
	}
}
