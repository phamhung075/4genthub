package handlers

// Focused tests for the drafting port of search_handler.py and
// workflow_handler.py. Expectations are read from the Python source.

import (
	"context"
	"testing"

	task "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
)

type draftFormatter struct {
	lastOperation string
	lastMessage   string
	lastCode      string
	lastMetadata  *entities.OrderedMap[any]
}

func (f *draftFormatter) CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.lastOperation = operation
	f.lastMessage = errorMessage
	f.lastCode = errorCode
	f.lastMetadata = metadata
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("operation", operation)
	m.Set("error", errorMessage)
	m.Set("error_code", errorCode)
	if metadata != nil {
		m.Set("metadata", metadata)
	}
	return m
}

func (f *draftFormatter) CreateSuccessResponse(operation string, data any, workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("operation", operation)
	m.Set("data", data)
	return m
}

func (f *draftFormatter) GetTimestamp() string { return "TS" }

type draftSearchFacade struct {
	tasks      []any
	count      int
	timestamp  any
	lastList   *task.ListTasksRequest
	lastSearch *task.SearchTasksRequest
}

func (f *draftSearchFacade) ListTasks(ctx context.Context, request *task.ListTasksRequest) *entities.OrderedMap[any] {
	f.lastList = request
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("tasks", f.tasks)
	return m
}

func (f *draftSearchFacade) SearchTasks(ctx context.Context, request *task.SearchTasksRequest) *entities.OrderedMap[any] {
	f.lastSearch = request
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("tasks", f.tasks)
	return m
}

func (f *draftSearchFacade) CountTasks(ctx context.Context, filters map[string]any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("count", f.count)
	m.Set("timestamp", f.timestamp)
	return m
}

func TestListTasksMinimalFieldsAndPagination(t *testing.T) {
	taskNode := entities.NewOrderedMap[any]()
	taskNode.Set("id", "t1")
	taskNode.Set("title", "Title")
	taskNode.Set("status", "todo")
	taskNode.Set("priority", "high")
	taskNode.Set("git_branch_id", "b1")
	taskNode.Set("dependencies", []any{"d1"})
	taskNode.Set("has_dependencies", true)
	taskNode.Set("dependency_count", 1)
	// Fields dropped by the minimal projection.
	taskNode.Set("description", "secret")

	facade := &draftSearchFacade{tasks: []any{taskNode}}
	handler := NewSearchHandler(&draftFormatter{})

	status := "todo"
	result := handler.ListTasks(context.Background(), facade, &status, nil, nil, nil, nil, nil, nil, nil, nil)

	tasksVal, _ := result.Get("tasks")
	tasks, _ := tasksVal.([]any)
	minimal, _ := tasks[0].(*entities.OrderedMap[any])
	wantKeys := []string{"id", "title", "status", "priority", "git_branch_id", "dependencies", "has_dependencies", "dependency_count"}
	if len(minimal.Keys()) != len(wantKeys) {
		t.Fatalf("keys = %v", minimal.Keys())
	}
	for i, key := range wantKeys {
		if minimal.Keys()[i] != key {
			t.Fatalf("key[%d] = %q, want %q", i, minimal.Keys()[i], key)
		}
	}

	pageVal, _ := result.Get("pagination")
	page, _ := pageVal.(*entities.OrderedMap[any])
	if v, _ := page.Get("total"); v != 1 {
		t.Fatalf("total = %v", v)
	}
	if v, _ := page.Get("limit"); v != 50 {
		t.Fatalf("limit = %v", v)
	}
	if v, _ := page.Get("has_more"); v != false {
		t.Fatalf("has_more = %v", v)
	}
	if v, _ := page.Get("tip"); v != "Use manage_task(action='get', task_id='...') for full details" {
		t.Fatalf("tip = %v", v)
	}
}

func TestSearchTasksMissingQuery(t *testing.T) {
	f := &draftFormatter{}
	handler := NewSearchHandler(f)
	result := handler.SearchTasks(context.Background(), &draftSearchFacade{}, nil, nil, nil, nil, nil, nil, nil, nil)

	if v, _ := result.Get("error"); v != "Missing required field: query. Expected: A search query string" {
		t.Fatalf("error = %v", v)
	}
	if f.lastCode != "VALIDATION_ERROR" {
		t.Fatalf("code = %q", f.lastCode)
	}
	field, _ := f.lastMetadata.Get("field")
	if field != "query" {
		t.Fatalf("field = %v", field)
	}
	hint, _ := f.lastMetadata.Get("hint")
	if hint != "Include 'query' in your request" {
		t.Fatalf("hint = %v", hint)
	}
}

func TestCountTasksFiltersAndDataOrder(t *testing.T) {
	facade := &draftSearchFacade{count: 3, timestamp: "2024-01-01T00:00:00Z"}
	handler := NewSearchHandler(&draftFormatter{})
	status := "todo"
	priority := "high"
	branch := "b1"
	result := handler.CountTasks(context.Background(), facade, &status, &priority, &branch)

	dataVal, _ := result.Get("data")
	data, _ := dataVal.(*entities.OrderedMap[any])
	if keys := data.Keys(); len(keys) != 3 || keys[0] != "count" || keys[1] != "filters" || keys[2] != "timestamp" {
		t.Fatalf("data keys = %v", data.Keys())
	}
	filtersVal, _ := data.Get("filters")
	filters, _ := filtersVal.(*entities.OrderedMap[any])
	if keys := filters.Keys(); len(keys) != 3 || keys[0] != "status" || keys[1] != "priority" || keys[2] != "git_branch_id" {
		t.Fatalf("filters keys = %v", filters.Keys())
	}
}

func TestWorkflowGuidance(t *testing.T) {
	handler := NewWorkflowHandler(&draftFormatter{}, nil)

	// create + pending -> the three create guidance actions.
	data := entities.NewOrderedMap[any]()
	data.Set("status", "pending")
	data.Set("priority", "high")
	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	out := handler.EnrichTaskResponse(response, "create", data)

	guidanceVal, ok := out.Get("workflow_guidance")
	if !ok {
		t.Fatal("workflow_guidance missing")
	}
	guidance, _ := guidanceVal.(*entities.OrderedMap[any])
	statusGuidance, _ := guidance.Get("status_guidance")
	if statusGuidance == nil || *statusGuidance.(*string) != "Task is ready to be worked on. Consider updating to 'in_progress' when starting work." {
		t.Fatalf("status_guidance = %v", statusGuidance)
	}
	priorityGuidance, _ := guidance.Get("priority_guidance")
	if priorityGuidance == nil || *priorityGuidance.(*string) != "High priority task - consider working on this soon." {
		t.Fatalf("priority_guidance = %v", priorityGuidance)
	}
	nextVal, _ := guidance.Get("next_actions")
	next, _ := nextVal.([]string)
	if len(next) != 3 || next[0] != "Update task status to 'in_progress' when starting work" {
		t.Fatalf("next_actions = %v", next)
	}

	// Priority lookup is case-insensitive; status is used lower-cased for lookup
	// but the create/pending branch compares the raw status.
	unknown := entities.NewOrderedMap[any]()
	unknown.Set("status", "pending")
	unknown.Set("priority", "unknown")
	resp2 := entities.NewOrderedMap[any]()
	resp2.Set("success", true)
	out2 := handler.EnrichTaskResponse(resp2, "update", unknown)
	g2Val, _ := out2.Get("workflow_guidance")
	g2, _ := g2Val.(*entities.OrderedMap[any])
	if v, _ := g2.Get("priority_guidance"); v != nil {
		t.Fatalf("priority_guidance = %v", v)
	}

	// No guidance at all -> key absent.
	empty := entities.NewOrderedMap[any]()
	empty.Set("status", "weird")
	empty.Set("priority", "weird")
	resp3 := entities.NewOrderedMap[any]()
	resp3.Set("success", true)
	out3 := handler.EnrichTaskResponse(resp3, "update", empty)
	if _, present := out3.Get("workflow_guidance"); present {
		t.Fatal("workflow_guidance should be absent")
	}
}

func TestWorkflowCreateTaskContextUnavailable(t *testing.T) {
	handler := NewWorkflowHandler(&draftFormatter{}, nil)
	result := handler.CreateTaskContext(context.Background(), "t1", entities.NewOrderedMap[any](), "b1")
	if v, _ := result.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	if v, _ := result.Get("error"); v != "Context creation not available" {
		t.Fatalf("error = %v", v)
	}
}
