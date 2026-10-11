package handlers

// The create_task assignee rule is entities.NormalizeAssignees, the same one
// subtask creation uses: '@<seat_key>' is kept as given and is the only valid
// assignee identity, every bare name is rejected.

import (
	"context"
	"strings"
	"testing"

	task "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
)

// createCapture records the request CreateTask hands to the facade.
type createCapture struct {
	TaskFacade
	request *task.CreateTaskRequest
}

func (f *createCapture) CreateTask(_ context.Context, request *task.CreateTaskRequest) *entities.OrderedMap[any] {
	f.request = request
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	return m
}

func createWithAssignees(assignees ...any) (*createCapture, *draftFormatter) {
	facade := &createCapture{}
	formatter := &draftFormatter{}
	NewCRUDHandler(formatter).CreateTask(context.Background(), facade, map[string]any{
		"title":         "t",
		"git_branch_id": "11111111-1111-1111-1111-111111111111",
		"assignees":     assignees,
	})
	return facade, formatter
}

func TestCreateTaskAcceptsSeatKeyWithAtPrefix(t *testing.T) {
	facade, formatter := createWithAssignees("@go-dev", "@lead")

	if facade.request == nil {
		t.Fatalf("seat keys were rejected: %q", formatter.lastMessage)
	}
	if got := strings.Join(facade.request.Assignees, ","); got != "@go-dev,@lead" {
		t.Fatalf("assignees = %q, want the seat keys kept as given", got)
	}
}

func TestCreateTaskRejectsABareName(t *testing.T) {
	facade, formatter := createWithAssignees("go-dev", "@lead")

	if facade.request != nil {
		t.Fatalf("create reached the facade with %v", facade.request.Assignees)
	}
	hint, _ := formatter.lastMetadata.Get("hint")
	if !strings.Contains(hint.(string), "Invalid assignees: ['go-dev']") {
		t.Fatalf("hint does not name the bare assignee: %v", hint)
	}
}

func TestCreateTaskStripsWhitespaceAroundASeatKey(t *testing.T) {
	facade, _ := createWithAssignees("  @lead ")

	if facade.request == nil || facade.request.Assignees[0] != "@lead" {
		t.Fatalf("request = %+v, want the stripped @lead", facade.request)
	}
}

func TestCreateTaskRejectsOnlyBlankAssignees(t *testing.T) {
	facade, formatter := createWithAssignees("  ", "")

	if facade.request != nil {
		t.Fatalf("blank assignees reached the facade")
	}
	if formatter.lastOperation != "create_task" {
		t.Fatalf("operation = %q, want a create_task validation error", formatter.lastOperation)
	}
}
