package facades

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func newEmptyFacade() *SubtaskApplicationFacade {
	return NewSubtaskApplicationFacade(nil, nil, nil, nil, nil)
}

func TestHandleManageSubtaskRequiresTaskID(t *testing.T) {
	f := newEmptyFacade()
	_, err := f.HandleManageSubtask(context.Background(), "create", "", nil, nil, false, nil, nil, nil)
	if err == nil || err.Error() != "Task ID is required" {
		t.Fatalf("got %v", err)
	}
	if _, ok := err.(*value_objects.ValueError); !ok {
		t.Fatalf("expected *ValueError, got %T", err)
	}
}

func TestHandleManageSubtaskUnsupportedAction(t *testing.T) {
	f := newEmptyFacade()
	_, err := f.HandleManageSubtask(context.Background(), "frobnicate", "task-1", nil, nil, false, nil, nil, nil)
	if err == nil || err.Error() != "Unsupported subtask action: frobnicate" {
		t.Fatalf("got %v", err)
	}
}

func TestHandleManageSubtaskAddAliasNormalisesToCreate(t *testing.T) {
	f := newEmptyFacade()
	data := entities.NewOrderedMap[any]()
	// Missing title -> create validation error, proving "add" routed to create.
	_, err := f.HandleManageSubtask(context.Background(), "ADD", "task-1", data, nil, false, nil, nil, nil)
	if err == nil || err.Error() != "subtask_data with title is required" {
		t.Fatalf("got %v", err)
	}
}

func TestCreateSubtaskMissingArguments(t *testing.T) {
	f := newEmptyFacade()
	_, err := f.CreateSubtask(context.Background(), CreateSubtaskParams{})
	if err == nil || !strings.Contains(err.Error(), "missing required argument: 'task_id'") {
		t.Fatalf("got %v", err)
	}
	tid := "task-1"
	_, err = f.CreateSubtask(context.Background(), CreateSubtaskParams{TaskID: &tid})
	if err == nil || !strings.Contains(err.Error(), "missing required argument: 'title'") {
		t.Fatalf("got %v", err)
	}
}

func TestDeleteSubtaskRequiresIDs(t *testing.T) {
	f := newEmptyFacade()
	if _, err := f.DeleteSubtask(context.Background(), "", "s1", nil); err == nil ||
		err.Error() != "task_id and subtask_id are required" {
		t.Fatalf("got %v", err)
	}
	if _, err := f.CompleteSubtask(context.Background(), "t1", "", nil, nil); err == nil ||
		err.Error() != "task_id and subtask_id are required" {
		t.Fatalf("got %v", err)
	}
}
