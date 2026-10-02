package factories

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeFormatter struct {
	lastOperation string
	lastError     string
	lastCode      string
}

func (f *fakeFormatter) CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.lastOperation = operation
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("operation", operation)
	m.Set("data", data)
	return m
}

func (f *fakeFormatter) CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.lastOperation = operation
	f.lastError = errorMessage
	f.lastCode = errorCode
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("operation", operation)
	m.Set("error", errorMessage)
	m.Set("error_code", errorCode)
	return m
}

type fakeCRUD struct{ lastKwargs *entities.OrderedMap[any] }

func (h *fakeCRUD) CreateSubtask(_ context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	h.lastKwargs = kwargs
	return successResult()
}
func (h *fakeCRUD) UpdateSubtask(_ context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	h.lastKwargs = kwargs
	return successResult()
}
func (h *fakeCRUD) DeleteSubtask(_ context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	h.lastKwargs = kwargs
	return successResult()
}
func (h *fakeCRUD) GetSubtask(_ context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	h.lastKwargs = kwargs
	return successResult()
}
func (h *fakeCRUD) ListSubtasks(_ context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	h.lastKwargs = kwargs
	return successResult()
}
func (h *fakeCRUD) CompleteSubtask(_ context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	h.lastKwargs = kwargs
	return successResult()
}

type fakeProgress struct{}

func (fakeProgress) GetProgressSummary(taskID string, subtasks any) any { return "summary" }
func (fakeProgress) CalculateTaskProgress(taskID string, subtasks any) any {
	return "progress"
}

func successResult() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	return m
}

func TestHandleOperationUnknown(t *testing.T) {
	fm := &fakeFormatter{}
	f := NewSubtaskOperationFactory(fm, &fakeCRUD{}, fakeProgress{}, nil, nil)
	res := f.HandleOperation(context.Background(), "bogus", nil, entities.NewOrderedMap[any]())
	if v, _ := res.Get("success"); v != false {
		t.Fatal("expected failure")
	}
	if fm.lastCode != "UNKNOWN_OPERATION" {
		t.Fatalf("code = %s", fm.lastCode)
	}
	if fm.lastError != "Unknown operation: bogus" {
		t.Fatalf("error = %s", fm.lastError)
	}
}

func TestHandleOperationProgressMissingTaskID(t *testing.T) {
	fm := &fakeFormatter{}
	f := NewSubtaskOperationFactory(fm, &fakeCRUD{}, fakeProgress{}, nil, nil)
	res := f.HandleOperation(context.Background(), "progress", nil, entities.NewOrderedMap[any]())
	if v, _ := res.Get("success"); v != false {
		t.Fatal("expected failure")
	}
	if fm.lastCode != "VALIDATION_ERROR" {
		t.Fatalf("code = %s", fm.lastCode)
	}
	if fm.lastError != "task_id is required for progress operations" {
		t.Fatalf("error = %s", fm.lastError)
	}
}

func TestHandleOperationCreateAssigneesConversionAndFiltering(t *testing.T) {
	fm := &fakeFormatter{}
	crud := &fakeCRUD{}
	f := NewSubtaskOperationFactory(fm, crud, fakeProgress{}, nil, nil)

	kwargs := entities.NewOrderedMap[any]()
	kwargs.Set("task_id", "t1")
	kwargs.Set("title", "hello")
	kwargs.Set("assignees", "alice, bob")
	kwargs.Set("user_id", "u1")
	kwargs.Set("project_id", "should-be-filtered")

	f.HandleOperation(context.Background(), "create", nil, kwargs)

	if crud.lastKwargs == nil {
		t.Fatal("handler not called")
	}
	if crud.lastKwargs.Has("project_id") {
		t.Fatal("project_id must be filtered out of create")
	}
	if !crud.lastKwargs.Has("task_id") || !crud.lastKwargs.Has("title") || !crud.lastKwargs.Has("user_id") {
		t.Fatalf("allowed params missing: %v", crud.lastKwargs.Keys())
	}
	got := crud.lastKwargs.GetAny("assignees").([]any)
	if len(got) != 2 || got[0] != "alice" || got[1] != "bob" {
		t.Fatalf("assignees = %v", got)
	}
}

func TestHandleOperationListDropsSubtaskID(t *testing.T) {
	fm := &fakeFormatter{}
	crud := &fakeCRUD{}
	f := NewSubtaskOperationFactory(fm, crud, fakeProgress{}, nil, nil)

	kwargs := entities.NewOrderedMap[any]()
	kwargs.Set("task_id", "t1")
	kwargs.Set("subtask_id", "s1")
	kwargs.Set("limit", 10)

	f.HandleOperation(context.Background(), "list", nil, kwargs)

	if crud.lastKwargs == nil {
		t.Fatal("handler not called")
	}
	if crud.lastKwargs.Has("subtask_id") {
		t.Fatal("subtask_id must be filtered from list")
	}
	if !crud.lastKwargs.Has("task_id") || !crud.lastKwargs.Has("limit") {
		t.Fatalf("allowed list params missing: %v", crud.lastKwargs.Keys())
	}
}
