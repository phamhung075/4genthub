package factories

// The resume action's dispatch: one case proving the action reaches the facade and answers with the
// brief it returned, and one proving an unknown action is still refused as UNKNOWN_OPERATION (so the
// new case did not widen the default). A fake facade is enough at this layer - the brief's contents
// are the application service's business and are pinned in
// application/services/task_resume_service_test.go.

import (
	"context"
	"testing"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

type operationFakeFormatter struct {
	lastOperation string
	lastError     string
	lastCode      string
	errors        int
}

func (f *operationFakeFormatter) CreateSuccessResponse(operation string, data any,
	workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.lastOperation = operation
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("data", data)
	return out
}

func (f *operationFakeFormatter) CreateErrorResponse(operation, errorMessage, errorCode string,
	metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.lastOperation = operation
	f.lastError = errorMessage
	f.lastCode = errorCode
	f.errors++
	out := entities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("operation", operation)
	out.Set("error", errorMessage)
	out.Set("error_code", errorCode)
	return out
}

func (f *operationFakeFormatter) GetTimestamp() string { return "2024-01-01T00:00:00+00:00" }

// operationFakeFacade is handlers.TaskFacade: the resume method records the id it was asked about,
// and every other method is a stub the resume path never reaches.
type operationFakeFacade struct {
	resumedTaskID string
	brief         *entities.OrderedMap[any]
	err           error
}

func (f *operationFakeFacade) CreateTask(context.Context, *dtostask.CreateTaskRequest) *entities.OrderedMap[any] {
	return nil
}

func (f *operationFakeFacade) UpdateTask(context.Context, *dtostask.UpdateTaskRequest) *entities.OrderedMap[any] {
	return nil
}

func (f *operationFakeFacade) GetTask(context.Context, string, bool) (*entities.OrderedMap[any], error) {
	return nil, nil
}

func (f *operationFakeFacade) ResumeBrief(_ context.Context, taskID string) (*entities.OrderedMap[any], error) {
	f.resumedTaskID = taskID
	return f.brief, f.err
}

func (f *operationFakeFacade) DeleteTask(context.Context, string, *string) *entities.OrderedMap[any] {
	return nil
}

func (f *operationFakeFacade) CompleteTask(context.Context, string, string, *string, *string) *entities.OrderedMap[any] {
	return nil
}

func (f *operationFakeFacade) AddDependency(context.Context, string, string) *entities.OrderedMap[any] {
	return nil
}

func (f *operationFakeFacade) RemoveDependency(context.Context, string, string) *entities.OrderedMap[any] {
	return nil
}

func (f *operationFakeFacade) TaskRepository() repositories.TaskRepository { return nil }

const operationResumeTaskID = "11111111-1111-1111-1111-111111111111"

func TestHandleOperationResumeReturnsTheBrief(t *testing.T) {
	ff := &operationFakeFormatter{}
	brief := entities.NewOrderedMap[any]()
	brief.Set("next_action", "fix: the acceptance criterion is unmet")
	brief.Set("budget", "reported")
	facade := &operationFakeFacade{brief: brief}

	kwargs := map[string]any{
		"task_id": operationResumeTaskID,
		"user_id": "user-1",
		"title":   "a write field the read must ignore",
	}
	res := NewOperationFactory(ff, nil).HandleOperation(context.Background(), "resume", facade, kwargs)

	if res == nil {
		t.Fatal("resume answered nothing")
	}
	if v, _ := res.Get("success"); v != true {
		t.Fatalf("success = %v, want true", v)
	}
	if facade.resumedTaskID != operationResumeTaskID {
		t.Fatalf("dispatch never reached the facade with the task id: %q", facade.resumedTaskID)
	}
	got, ok := res.Get("brief")
	gotBrief, isBrief := got.(*entities.OrderedMap[any])
	if !ok || !isBrief {
		t.Fatalf("brief = %v, want the brief the facade returned", got)
	}
	if next, _ := gotBrief.Get("next_action"); next != "fix: the acceptance criterion is unmet" {
		t.Fatalf("brief.next_action = %v", next)
	}
	if ff.errors != 0 {
		t.Fatalf("resume answered through the error formatter: %s", ff.lastError)
	}
}

func TestHandleOperationUnknownStillAnswersUnknownOperation(t *testing.T) {
	ff := &operationFakeFormatter{}
	res := NewOperationFactory(ff, nil).HandleOperation(context.Background(), "resume_brief",
		&operationFakeFacade{}, map[string]any{"task_id": operationResumeTaskID})

	if res == nil {
		t.Fatal("unknown operation answered nothing")
	}
	if v, _ := res.Get("success"); v != false {
		t.Fatalf("success = %v, want false", v)
	}
	if ff.lastCode != "UNKNOWN_OPERATION" {
		t.Fatalf("error code = %q, want UNKNOWN_OPERATION", ff.lastCode)
	}
	if ff.lastError != "Unknown operation: resume_brief" {
		t.Fatalf("error = %q", ff.lastError)
	}
}
