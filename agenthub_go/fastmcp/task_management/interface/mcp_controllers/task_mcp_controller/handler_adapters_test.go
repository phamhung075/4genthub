package task_mcp_controller

import (
	"context"
	"testing"

	task "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers"
)

// fakeFormatter satisfies both factories.ResponseFormatter and
// handlers.SearchResponseFormatter (identical method sets).
type fakeFormatter struct{}

func (fakeFormatter) CreateSuccessResponse(operation string, data any, workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("operation", operation)
	m.Set("data", data)
	return m
}

func (fakeFormatter) CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("operation", operation)
	m.Set("error", errorMessage)
	m.Set("error_code", errorCode)
	return m
}

func (fakeFormatter) GetTimestamp() string { return "2025-01-01T00:00:00Z" }

// fakeSearchFacade implements handlers.TaskSearchFacade and (through the
// embedded TaskFacade) handlers.TaskFacade, recording the converted arguments.
type fakeSearchFacade struct {
	handlers.TaskFacade

	listResult   *entities.OrderedMap[any]
	searchResult *entities.OrderedMap[any]
	getResult    *entities.OrderedMap[any]
	countResult  *entities.OrderedMap[any]

	lastListRequest    *task.ListTasksRequest
	lastSearchRequest  *task.SearchTasksRequest
	lastCountFilters   map[string]any
	lastIncludeContext bool
}

func (f *fakeSearchFacade) ListTasks(ctx context.Context, request *task.ListTasksRequest) *entities.OrderedMap[any] {
	f.lastListRequest = request
	return f.listResult
}

func (f *fakeSearchFacade) SearchTasks(ctx context.Context, request *task.SearchTasksRequest) *entities.OrderedMap[any] {
	f.lastSearchRequest = request
	return f.searchResult
}

func (f *fakeSearchFacade) CountTasks(ctx context.Context, filters map[string]any) *entities.OrderedMap[any] {
	f.lastCountFilters = filters
	return f.countResult
}

func (f *fakeSearchFacade) GetTask(ctx context.Context, taskID string, includeContext bool) (*entities.OrderedMap[any], error) {
	f.lastIncludeContext = includeContext
	return f.getResult, nil
}

func newFakeSearchFacade() *fakeSearchFacade {
	taskData := entities.NewOrderedMap[any]()
	taskData.Set("id", "task-1")
	taskData.Set("title", "First task")
	taskData.Set("status", "todo")
	taskData.Set("priority", "high")
	taskData.Set("git_branch_id", "branch-1")

	listResult := entities.NewOrderedMap[any]()
	listResult.Set("success", true)
	listResult.Set("tasks", []any{taskData})

	searchResult := entities.NewOrderedMap[any]()
	searchResult.Set("success", true)
	searchResult.Set("tasks", []any{taskData})

	getResult := entities.NewOrderedMap[any]()
	getResult.Set("success", true)
	getResult.Set("task", taskData)

	countResult := entities.NewOrderedMap[any]()
	countResult.Set("success", true)
	countResult.Set("count", 1)

	return &fakeSearchFacade{
		listResult:   listResult,
		searchResult: searchResult,
		getResult:    getResult,
		countResult:  countResult,
	}
}

func mustSuccess(t *testing.T, result *entities.OrderedMap[any], label string) {
	t.Helper()
	if result == nil {
		t.Fatalf("%s: nil result", label)
	}
	v, ok := result.Get("success")
	if !ok || !value_objects.PyTruthy(v) {
		t.Fatalf("%s: expected success, got %v", label, result)
	}
}

func TestTaskSearchHandlerAdapterKwargs(t *testing.T) {
	ctx := context.Background()
	facade := newFakeSearchFacade()
	adapter := factories.NewSearchHandler(fakeFormatter{})
	if adapter == nil {
		t.Fatal("factories.NewSearchHandler returned nil: initHandlerAdapters did not register")
	}

	t.Run("list", func(t *testing.T) {
		result := adapter.ListTasks(ctx, facade, map[string]any{
			"status": "in_progress", "limit": 10, "offset": 5,
		})
		mustSuccess(t, result, "list")
		if facade.lastListRequest == nil {
			t.Fatal("list: facade did not receive a request")
		}
		if facade.lastListRequest.Status == nil || *facade.lastListRequest.Status != "in_progress" {
			t.Fatalf("list: status = %v", facade.lastListRequest.Status)
		}
		if facade.lastListRequest.Limit == nil || *facade.lastListRequest.Limit != 10 {
			t.Fatalf("list: limit = %v", facade.lastListRequest.Limit)
		}
		paginationAny, _ := result.Get("pagination")
		pagination, _ := paginationAny.(*entities.OrderedMap[any])
		if pagination == nil {
			t.Fatal("list: missing pagination")
		}
		if offset, _ := pagination.Get("offset"); offset != 5 {
			t.Fatalf("list: pagination offset = %v", offset)
		}
	})

	t.Run("search", func(t *testing.T) {
		result := adapter.SearchTasks(ctx, facade, map[string]any{
			"query": "jwt", "priority": "high", "limit": 7,
		})
		mustSuccess(t, result, "search")
		if facade.lastSearchRequest == nil {
			t.Fatal("search: facade did not receive a request")
		}
		if facade.lastSearchRequest.Query != "jwt" {
			t.Fatalf("search: query = %q", facade.lastSearchRequest.Query)
		}
		if facade.lastSearchRequest.Limit != 7 {
			t.Fatalf("search: limit = %d", facade.lastSearchRequest.Limit)
		}
	})

	t.Run("next include_context default true", func(t *testing.T) {
		result := adapter.GetNextTask(ctx, facade, map[string]any{"git_branch_id": "branch-1"})
		mustSuccess(t, result, "next")
		if !facade.lastIncludeContext {
			t.Fatal("next: include_context default should be true")
		}
	})

	t.Run("next include_context false", func(t *testing.T) {
		result := adapter.GetNextTask(ctx, facade, map[string]any{
			"git_branch_id": "branch-1", "include_context": false,
		})
		mustSuccess(t, result, "next false")
		if facade.lastIncludeContext {
			t.Fatal("next: include_context should be false")
		}
	})

	t.Run("count", func(t *testing.T) {
		result := adapter.CountTasks(ctx, facade, map[string]any{
			"status": "done", "priority": "low", "git_branch_id": "branch-1", "user_id": "u-1",
		})
		mustSuccess(t, result, "count")
		if facade.lastCountFilters["status"] != "done" {
			t.Fatalf("count: status = %v", facade.lastCountFilters["status"])
		}
		if facade.lastCountFilters["priority"] != "low" {
			t.Fatalf("count: priority = %v", facade.lastCountFilters["priority"])
		}
		if facade.lastCountFilters["git_branch_id"] != "branch-1" {
			t.Fatalf("count: git_branch_id = %v", facade.lastCountFilters["git_branch_id"])
		}
		if _, ok := facade.lastCountFilters["user_id"]; ok {
			t.Fatal("count: user_id must not reach SearchHandler.count_tasks")
		}
	})
}

// fakeContextFacade implements handlers.ContextFacade.
type fakeContextFacade struct {
	gotBranchID string
}

func (f *fakeContextFacade) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error) {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("level", level)
	m.Set("context_id", contextID)
	return m, nil
}

// fakeContextFacadeFactory implements handlers.ContextFacadeFactory.
type fakeContextFacadeFactory struct {
	facade *fakeContextFacade
}

func (f fakeContextFacadeFactory) CreateFacade(ctx context.Context, gitBranchID string) (handlers.ContextFacade, error) {
	if f.facade != nil {
		f.facade.gotBranchID = gitBranchID
	}
	return f.facade, nil
}

func TestTaskWorkflowHandlerAdapterContextFactory(t *testing.T) {
	ctx := context.Background()
	taskData := entities.NewOrderedMap[any]()
	taskData.Set("title", "First task")

	t.Run("nil factory", func(t *testing.T) {
		adapter := factories.NewWorkflowHandler(fakeFormatter{}, nil)
		if adapter == nil {
			t.Fatal("factories.NewWorkflowHandler returned nil")
		}
		result := adapter.CreateTaskContext(ctx, "task-1", taskData, nil)
		if result == nil {
			t.Fatal("nil factory: nil result")
		}
		if success, _ := result.Get("success"); value_objects.PyTruthy(success) {
			t.Fatalf("nil factory: expected failure, got %v", result)
		}
		if errVal, _ := result.Get("error"); errVal != "Context creation not available" {
			t.Fatalf("nil factory: error = %v", errVal)
		}
	})

	t.Run("non-implementing factory", func(t *testing.T) {
		adapter := factories.NewWorkflowHandler(fakeFormatter{}, struct{}{})
		result := adapter.CreateTaskContext(ctx, "task-1", taskData, nil)
		if errVal, _ := result.Get("error"); errVal != "Context creation not available" {
			t.Fatalf("non-implementing factory: error = %v", errVal)
		}
	})

	t.Run("implementing factory", func(t *testing.T) {
		contextFacade := &fakeContextFacade{}
		adapter := factories.NewWorkflowHandler(fakeFormatter{}, fakeContextFacadeFactory{facade: contextFacade})
		branchID := "branch-1"
		result := adapter.CreateTaskContext(ctx, "task-1", taskData, &branchID)
		mustSuccess(t, result, "implementing factory")
		if contextFacade.gotBranchID != branchID {
			t.Fatalf("implementing factory: git_branch_id = %q", contextFacade.gotBranchID)
		}
	})

	t.Run("enrich with map task data", func(t *testing.T) {
		adapter := factories.NewWorkflowHandler(fakeFormatter{}, nil)
		response := entities.NewOrderedMap[any]()
		response.Set("success", true)
		response.Set("task", entities.NewOrderedMap[any]())
		enriched := adapter.EnrichTaskResponse(response, "get", map[string]any{"status": "in_progress", "priority": "high"})
		if enriched == nil {
			t.Fatal("enrich: nil result")
		}
		if _, ok := enriched.Get("workflow_guidance"); !ok {
			t.Fatal("enrich: workflow_guidance missing")
		}
	})
}
