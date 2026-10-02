package services

import (
	"context"
	"testing"

	taskdtos "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
)

type zpTaskAppTestCreate struct{ got taskdtos.CreateTaskRequest }

func (f *zpTaskAppTestCreate) Execute(request taskdtos.CreateTaskRequest) (*taskdtos.CreateTaskResponse, error) {
	f.got = request
	return taskdtos.NewCreateTaskResponseSuccess(&taskdtos.TaskResponse{ID: "t1", Title: "T", Description: "D", Status: "pending", Priority: "medium"}, nil), nil
}

type zpTaskAppTestGet struct{ notFound bool }

func (f *zpTaskAppTestGet) Execute(ctx context.Context, taskID string, generateRules, forceFullGeneration, includeContext bool) (*taskdtos.TaskResponse, error) {
	if f.notFound {
		return nil, exceptions.NewTaskNotFoundError(taskID)
	}
	return &taskdtos.TaskResponse{ID: taskID}, nil
}

type zpTaskAppTestUpdate struct{}

func (f *zpTaskAppTestUpdate) Execute(request taskdtos.UpdateTaskRequest) (*taskdtos.UpdateTaskResponse, error) {
	return taskdtos.NewUpdateTaskResponseSuccess(&taskdtos.TaskResponse{ID: "t1"}, nil), nil
}

type zpTaskAppTestList struct{ got taskdtos.ListTasksRequest }

func (f *zpTaskAppTestList) Execute(ctx context.Context, request taskdtos.ListTasksRequest) (*taskdtos.TaskListResponse, error) {
	f.got = request
	return &taskdtos.TaskListResponse{Count: 0}, nil
}

type zpTaskAppTestSearch struct{}

func (f *zpTaskAppTestSearch) Execute(ctx context.Context, request taskdtos.SearchTasksRequest) (*taskdtos.TaskListResponse, error) {
	return &taskdtos.TaskListResponse{Count: 0}, nil
}

type zpTaskAppTestDelete struct{ result bool }

func (f *zpTaskAppTestDelete) Execute(ctx context.Context, taskID string) (bool, error) {
	return f.result, nil
}

type zpTaskAppTestComplete struct {
	taskID string
	args   [3]*string
}

func (f *zpTaskAppTestComplete) Execute(ctx context.Context, taskID string, completionSummary, testingNotes, nextRecommendations *string) (*entities.OrderedMap[any], error) {
	f.taskID = taskID
	f.args = [3]*string{completionSummary, testingNotes, nextRecommendations}
	return entities.NewOrderedMap[any](), nil
}

type zpTaskAppTestContext struct {
	createdLevel, createdID string
	createdData             *entities.OrderedMap[any]
	deletedID               string
}

func (f *zpTaskAppTestContext) CreateContext(level, contextID string, data *entities.OrderedMap[any]) error {
	f.createdLevel, f.createdID, f.createdData = level, contextID, data
	return nil
}
func (f *zpTaskAppTestContext) UpdateContext(level, contextID string, data *entities.OrderedMap[any]) error {
	return nil
}
func (f *zpTaskAppTestContext) DeleteContext(level, contextID string) (bool, error) {
	f.deletedID = contextID
	return true, nil
}

func zpTaskAppTestService(t *testing.T) (*TaskApplicationService, *zpTaskAppTestCreate, *zpTaskAppTestGet, *zpTaskAppTestList, *zpTaskAppTestDelete, *zpTaskAppTestComplete, *zpTaskAppTestContext) {
	t.Helper()
	create := &zpTaskAppTestCreate{}
	get := &zpTaskAppTestGet{}
	list := &zpTaskAppTestList{}
	del := &zpTaskAppTestDelete{result: true}
	complete := &zpTaskAppTestComplete{}
	ctxSvc := &zpTaskAppTestContext{}
	deps := zpTaskAppDeps{CreateTask: create, GetTask: get, UpdateTask: &zpTaskAppTestUpdate{}, ListTasks: list, SearchTasks: &zpTaskAppTestSearch{}, DeleteTask: del, CompleteTask: complete}
	return NewTaskApplicationService(nil, nil, nil, ctxSvc, deps), create, get, list, del, complete, ctxSvc
}

func TestTaskApplicationService_CreateTaskBuildsContextData(t *testing.T) {
	svc, _, _, _, _, _, ctxSvc := zpTaskAppTestService(t)
	if _, err := svc.CreateTask(context.Background(), taskdtos.CreateTaskRequest{Title: "T"}); err != nil {
		t.Fatal(err)
	}
	if ctxSvc.createdLevel != "task" || ctxSvc.createdID != "t1" {
		t.Fatalf("context = %q %q", ctxSvc.createdLevel, ctxSvc.createdID)
	}
	taskData := zpRespGetMap(ctxSvc.createdData, "task_data")
	want := []string{"title", "description", "status", "priority", "assignees", "labels", "estimated_effort", "due_date"}
	if taskData.Len() != len(want) {
		t.Fatalf("task_data keys = %v", taskData.Keys())
	}
	for i, k := range want {
		if taskData.Keys()[i] != k {
			t.Fatalf("task_data keys = %v, want %v", taskData.Keys(), want)
		}
	}
	if v, _ := taskData.Get("due_date"); v != nil {
		t.Fatalf("due_date = %v, want nil", v)
	}
}

func TestTaskApplicationService_GetTaskNotFoundReturnsNil(t *testing.T) {
	svc, _, get, _, _, _, _ := zpTaskAppTestService(t)
	get.notFound = true
	resp, err := svc.GetTask(context.Background(), "missing", true, false, false, nil, "", "main")
	if err != nil {
		t.Fatal(err)
	}
	if resp != nil {
		t.Fatalf("expected nil, got %v", resp)
	}
}

func TestTaskApplicationService_DeleteTaskDeletesContext(t *testing.T) {
	svc, _, _, _, _, _, ctxSvc := zpTaskAppTestService(t)
	ok, err := svc.DeleteTask(context.Background(), "t9", "u1", "", "main")
	if err != nil || !ok {
		t.Fatalf("ok=%v err=%v", ok, err)
	}
	if ctxSvc.deletedID != "t9" {
		t.Fatalf("deletedID = %q", ctxSvc.deletedID)
	}
}

func TestTaskApplicationService_ListFilters(t *testing.T) {
	svc, _, _, list, _, _, _ := zpTaskAppTestService(t)
	if _, err := svc.GetTasksByStatus(context.Background(), "in_progress"); err != nil {
		t.Fatal(err)
	}
	if list.got.Status == nil || *list.got.Status != "in_progress" {
		t.Fatalf("status filter = %v", list.got.Status)
	}
	if _, err := svc.GetTasksByAssignee(context.Background(), "@dev"); err != nil {
		t.Fatal(err)
	}
	if len(list.got.Assignees) != 1 || list.got.Assignees[0] != "@dev" {
		t.Fatalf("assignees filter = %v", list.got.Assignees)
	}
}

func TestTaskApplicationService_CompleteTaskArgs(t *testing.T) {
	svc, _, _, _, _, complete, _ := zpTaskAppTestService(t)
	summary := "done"
	if _, err := svc.CompleteTask(context.Background(), "t1", &summary, nil, nil); err != nil {
		t.Fatal(err)
	}
	if complete.taskID != "t1" || complete.args[0] == nil || *complete.args[0] != "done" {
		t.Fatalf("complete args = %q %v", complete.taskID, complete.args)
	}
}
