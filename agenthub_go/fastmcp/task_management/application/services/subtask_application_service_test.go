package services

import (
	"context"
	"testing"

	subtaskdto "agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestSubtaskApplicationService_UnknownAction(t *testing.T) {
	svc := NewSubtaskApplicationService(nil, nil, nil)
	_, err := svc.ManageSubtasks(context.Background(), "t1", "bogus", entities.NewOrderedMap[any]())
	ve, ok := err.(*value_objects.ValueError)
	if !ok {
		t.Fatalf("want ValueError, got %T %v", err, err)
	}
	if ve.Msg != "Unknown subtask action: bogus" {
		t.Fatalf("msg=%q", ve.Msg)
	}
}

func TestSubtaskApplicationService_MissingID(t *testing.T) {
	svc := NewSubtaskApplicationService(nil, nil, nil)
	for action, want := range map[string]string{
		"complete": "id is required for completing a subtask",
		"remove":   "id is required for removing a subtask",
		"get":      "id is required for getting a subtask",
	} {
		_, err := svc.ManageSubtasks(context.Background(), "t1", action, entities.NewOrderedMap[any]())
		ve, ok := err.(*value_objects.ValueError)
		if !ok || ve.Msg != want {
			t.Fatalf("action %q: got %v want %q", action, err, want)
		}
	}
}

func TestSubtaskApplicationService_AddValidatesTitle(t *testing.T) {
	svc := NewSubtaskApplicationService(nil, nil, nil)
	data := entities.NewOrderedMap[any]()
	data.Set("title", "")
	_, err := svc.ManageSubtasks(context.Background(), "t1", "add", data)
	ve, ok := err.(*value_objects.ValueError)
	if !ok || ve.Msg != "Title cannot be empty" {
		t.Fatalf("got %v", err)
	}
}

func TestSubtaskApplicationService_ResponseDictOrder(t *testing.T) {
	resp := &subtaskdto.SubtaskResponse{TaskID: "t1"}
	m := zpSubtaskAppResponseDict(resp)
	want := []string{"task_id", "subtask", "progress", "agent_inheritance_applied", "inherited_assignees"}
	got := m.Keys()
	if len(got) != len(want) {
		t.Fatalf("keys=%v", got)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys=%v want %v", got, want)
		}
	}
}

func TestSubtaskApplicationService_WithUser(t *testing.T) {
	svc := NewSubtaskApplicationService(nil, nil, nil)
	scoped := svc.WithUser("u1")
	if scoped == nil || scoped.userID == nil || *scoped.userID != "u1" {
		t.Fatal("WithUser did not scope user")
	}
	if scoped.taskRepository != nil {
		t.Fatal("repository should be carried over")
	}
}
