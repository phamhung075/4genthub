package factories

// Operation Factory for Task MCP Controller (Python operation_factory.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers"
)

// TaskSearchHandler is the SearchHandler surface used by the factory. The
// Python handlers/search_handler.py has no Go port yet; the interface is
// declared here and reported as a dependency. Method parameters are passed as
// the Python **kwargs mapping to keep the filtering semantics.
type TaskSearchHandler interface {
	ListTasks(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any]
	SearchTasks(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any]
	GetNextTask(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any]
	CountTasks(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any]
}

// TaskWorkflowHandler is the WorkflowHandler surface used by the factory.
// Python handlers/workflow_handler.py has no Go port yet.
type TaskWorkflowHandler interface {
	CreateTaskContext(ctx context.Context, taskID string, taskData *entities.OrderedMap[any],
		gitBranchID *string) *entities.OrderedMap[any]
	EnrichTaskResponse(response *entities.OrderedMap[any], action string, taskData any) *entities.OrderedMap[any]
}

// Constructor hooks for the search/workflow handlers.
var (
	NewSearchHandler   = func(responseFormatter ResponseFormatter) TaskSearchHandler { return nil }
	// NewWorkflowHandler's default returns nil, and task_mcp_controller/handler_adapters.go
	// ASSIGNS the real handler at initialisation (:44), so a running server never holds the
	// nil. Read that assignment before treating this hook as unfilled.
	NewWorkflowHandler = func(responseFormatter ResponseFormatter, contextFacadeFactory any) TaskWorkflowHandler {
		return nil
	}
)

// OperationFactory ports OperationFactory.
type OperationFactory struct {
	responseFormatter    ResponseFormatter
	contextFacadeFactory any

	crudHandler     *handlers.CRUDHandler
	searchHandler   TaskSearchHandler
	workflowHandler TaskWorkflowHandler
	aiHandler       *handlers.AIHandler
}

// NewOperationFactory ports __init__(response_formatter, context_facade_factory=None).
func NewOperationFactory(responseFormatter ResponseFormatter, contextFacadeFactory any) *OperationFactory {
	return &OperationFactory{
		responseFormatter:    responseFormatter,
		contextFacadeFactory: contextFacadeFactory,
		crudHandler:          handlers.NewCRUDHandler(responseFormatter),
		searchHandler:        NewSearchHandler(responseFormatter),
		workflowHandler:      NewWorkflowHandler(responseFormatter, contextFacadeFactory),
		aiHandler:            handlers.NewAIHandler(responseFormatter),
	}
}

// GetCrudHandler ports get_crud_handler.
func (f *OperationFactory) GetCrudHandler() *handlers.CRUDHandler { return f.crudHandler }

// GetSearchHandler ports get_search_handler.
func (f *OperationFactory) GetSearchHandler() TaskSearchHandler { return f.searchHandler }

// GetWorkflowHandler ports get_workflow_handler.
func (f *OperationFactory) GetWorkflowHandler() TaskWorkflowHandler { return f.workflowHandler }

// GetAiHandler ports get_ai_handler.
func (f *OperationFactory) GetAiHandler() *handlers.AIHandler { return f.aiHandler }

// HandleOperation ports handle_operation. The defer mirrors `except Exception`.
func (f *OperationFactory) HandleOperation(ctx context.Context, operation string,
	facade handlers.TaskFacade, kwargs map[string]any) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(operation,
				"Operation failed: "+panicMessage(r), ErrorCodeOperationFailed, nil)
		}
	}()

	switch operation {
	case "create", "update", "delete", "get", "complete":
		return f.handleCRUDOperation(ctx, operation, facade, kwargs)
	case "list", "search", "next", "count":
		return f.handleSearchOperation(ctx, operation, facade, kwargs)
	case "enrich", "context", "workflow":
		return f.handleWorkflowOperation(ctx, operation, facade, kwargs)
	case "add_dependency", "remove_dependency":
		return f.handleDependencyOperation(ctx, operation, facade, kwargs)
	case "ai_plan", "ai_create", "ai_enhance", "ai_analyze", "ai_suggest_agents":
		return f.handleAIOperation(ctx, operation, facade, kwargs)
	default:
		return f.responseFormatter.CreateErrorResponse(operation,
			"Unknown operation: "+operation, "UNKNOWN_OPERATION", nil)
	}
}

func (f *OperationFactory) handleCRUDOperation(ctx context.Context, operation string,
	facade handlers.TaskFacade, kwargs map[string]any) *entities.OrderedMap[any] {

	switch operation {
	case "create":
		allowed := stringSet("git_branch_id", "title", "description", "status", "priority", "details",
			"estimated_effort", "assignees", "labels", "due_date", "dependencies", "user_id")
		result := f.crudHandler.CreateTask(ctx, facade, filterKeys(kwargs, allowed))

		if result != nil {
			successVal, _ := result.Get("success")
			taskVal, hasTask := result.Get("task")
			taskData, taskIsMap := taskVal.(*entities.OrderedMap[any])
			if value_objects.PyTruthy(successVal) && hasTask && taskIsMap {
				taskIDVal, _ := taskData.Get("id")
				taskID, _ := taskIDVal.(string)
				gitBranchID := kwString(kwargs, "git_branch_id")
				if taskID != "" && gitBranchID != nil {
					contextResult := f.workflowHandler.CreateTaskContext(ctx, taskID, taskData, gitBranchID)
					if contextResult != nil {
						cs, _ := contextResult.Get("success")
						if value_objects.PyTruthy(cs) {
							result.Set("context_created", true)
							result.Set("context_id", taskID)
						}
					}
				}
			}
		}
		return result

	case "update":
		allowed := stringSet("task_id", "title", "description", "status", "priority", "details",
			"estimated_effort", "progress_percentage", "assignees", "labels", "due_date",
			"context_id", "completion_summary", "testing_notes")
		return f.crudHandler.UpdateTask(ctx, facade, filterKeys(kwargs, allowed))

	case "delete":
		allowed := stringSet("task_id", "user_id")
		filtered := filterKeys(kwargs, allowed)
		return f.crudHandler.DeleteTask(ctx, facade, kwStringValue(filtered, "task_id"), kwString(filtered, "user_id"))

	case "get":
		allowed := stringSet("task_id", "include_context")
		filtered := filterKeys(kwargs, allowed)
		if _, ok := filtered["include_context"]; !ok {
			filtered["include_context"] = true
		}
		result := f.crudHandler.GetTask(ctx, facade, kwStringValue(filtered, "task_id"),
			kwBoolDefault(filtered, "include_context", true))
		if result != nil {
			successVal, _ := result.Get("success")
			taskVal, hasTask := result.Get("task")
			if value_objects.PyTruthy(successVal) && hasTask {
				result = f.workflowHandler.EnrichTaskResponse(result, operation, taskVal)
			}
		}
		return result

	case "complete":
		allowed := stringSet("task_id", "completion_summary", "testing_notes")
		filtered := filterKeys(kwargs, allowed)
		return f.crudHandler.CompleteTask(ctx, facade, kwStringValue(filtered, "task_id"),
			kwString(filtered, "completion_summary"), kwString(filtered, "testing_notes"))
	}

	panic(&value_objects.ValueError{Msg: "Unknown CRUD operation: " + operation})
}

func (f *OperationFactory) handleSearchOperation(ctx context.Context, operation string,
	facade handlers.TaskFacade, kwargs map[string]any) *entities.OrderedMap[any] {

	switch operation {
	case "list":
		allowed := stringSet("status", "priority", "assignee", "tag", "git_branch_id",
			"limit", "offset", "sort_by", "sort_order")
		return f.searchHandler.ListTasks(ctx, facade, filterKeys(kwargs, allowed))
	case "search":
		allowed := stringSet("query", "status", "priority", "assignee", "tag", "git_branch_id",
			"limit", "offset")
		return f.searchHandler.SearchTasks(ctx, facade, filterKeys(kwargs, allowed))
	case "next":
		allowed := stringSet("git_branch_id", "include_context")
		return f.searchHandler.GetNextTask(ctx, facade, filterKeys(kwargs, allowed))
	case "count":
		excluded := stringSet("user_id", "task_id", "title", "description")
		return f.searchHandler.CountTasks(ctx, facade, excludeKeys(kwargs, excluded))
	}

	panic(&value_objects.ValueError{Msg: "Unknown search operation: " + operation})
}

func (f *OperationFactory) handleWorkflowOperation(ctx context.Context, operation string,
	facade handlers.TaskFacade, kwargs map[string]any) *entities.OrderedMap[any] {

	switch operation {
	case "enrich":
		response := orderedMapDefault(kwargs, "response")
		action := "unknown"
		if v := kwString(kwargs, "action"); v != nil {
			action = *v
		}
		return f.workflowHandler.EnrichTaskResponse(response, action, kwargs["task_data"])
	case "context":
		taskID := kwStringValue(kwargs, "task_id")
		taskData := orderedMapDefault(kwargs, "task_data")
		return f.workflowHandler.CreateTaskContext(ctx, taskID, taskData, kwString(kwargs, "git_branch_id"))
	}

	panic(&value_objects.ValueError{Msg: "Unknown workflow operation: " + operation})
}

func (f *OperationFactory) handleDependencyOperation(ctx context.Context, operation string,
	facade handlers.TaskFacade, kwargs map[string]any) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(operation,
				"Dependency operation failed: "+panicMessage(r), ErrorCodeOperationFailed, nil)
		}
	}()

	taskID := kwStringValue(kwargs, "task_id")
	dependencyID := kwStringValue(kwargs, "dependency_id")

	if taskID == "" {
		return f.responseFormatter.CreateErrorResponse(operation,
			"task_id is required for dependency operations", ErrorCodeValidation, nil)
	}
	if dependencyID == "" {
		return f.responseFormatter.CreateErrorResponse(operation,
			"dependency_id is required for dependency operations", ErrorCodeValidation, nil)
	}

	switch operation {
	case "add_dependency":
		return facade.AddDependency(ctx, taskID, dependencyID)
	case "remove_dependency":
		return facade.RemoveDependency(ctx, taskID, dependencyID)
	}
	panic(&value_objects.ValueError{Msg: "Unknown dependency operation: " + operation})
}

func (f *OperationFactory) handleAIOperation(ctx context.Context, operation string,
	facade handlers.TaskFacade, kwargs map[string]any) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(operation,
				"AI operation failed: "+panicMessage(r), ErrorCodeOperationFailed, nil)
		}
	}()

	switch operation {
	case "ai_plan":
		allowed := stringSet("requirements", "title", "description", "git_branch_id", "context",
			"auto_create_tasks", "user_id")
		return f.aiHandler.AIPlan(ctx, facade, filterKeys(kwargs, allowed))
	case "ai_create":
		allowed := stringSet("title", "description", "git_branch_id", "priority", "assignees",
			"estimated_effort", "labels", "dependencies", "user_id", "enable_ai_breakdown",
			"enable_smart_assignment", "enable_auto_subtasks", "ai_requirements", "planning_context")
		return f.aiHandler.AICreate(ctx, facade, filterKeys(kwargs, allowed))
	case "ai_enhance":
		allowed := stringSet("task_id", "analyze_complexity", "suggest_optimizations", "identify_risks")
		return f.aiHandler.AIEnhance(ctx, facade, filterKeys(kwargs, allowed))
	case "ai_analyze":
		allowed := stringSet("requirements", "context")
		return f.aiHandler.AIAnalyze(ctx, facade, filterKeys(kwargs, allowed))
	case "ai_suggest_agents":
		allowed := stringSet("requirements", "available_agents")
		return f.aiHandler.AISuggestAgents(ctx, facade, filterKeys(kwargs, allowed))
	}
	panic(&value_objects.ValueError{Msg: "Unknown AI operation: " + operation})
}

// --- helpers ---

func stringSet(keys ...string) map[string]bool {
	set := make(map[string]bool, len(keys))
	for _, k := range keys {
		set[k] = true
	}
	return set
}

func filterKeys(source map[string]any, allowed map[string]bool) map[string]any {
	out := make(map[string]any, len(source))
	for k, v := range source {
		if allowed[k] {
			out[k] = v
		}
	}
	return out
}

func excludeKeys(source map[string]any, excluded map[string]bool) map[string]any {
	out := make(map[string]any, len(source))
	for k, v := range source {
		if !excluded[k] {
			out[k] = v
		}
	}
	return out
}

func orderedMapDefault(source map[string]any, key string) *entities.OrderedMap[any] {
	if v, ok := source[key]; ok && v != nil {
		if m, isMap := v.(*entities.OrderedMap[any]); isMap {
			return m
		}
	}
	return entities.NewOrderedMap[any]()
}

func panicMessage(r any) string {
	if err, ok := r.(error); ok {
		return err.Error()
	}
	return fmt.Sprint(r)
}

// kwString mirrors dict.get(key) for a string value.
func kwString(m map[string]any, key string) *string {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	if s, isStr := v.(string); isStr {
		return &s
	}
	return nil
}

// kwStringValue mirrors dict.get(key) or "".
func kwStringValue(m map[string]any, key string) string {
	if v := kwString(m, key); v != nil {
		return *v
	}
	return ""
}

// kwBoolDefault mirrors dict.get(key, default) for a bool value.
func kwBoolDefault(m map[string]any, key string, def bool) bool {
	v, ok := m[key]
	if !ok || v == nil {
		return def
	}
	if b, isBool := v.(bool); isBool {
		return b
	}
	return value_objects.PyTruthy(v)
}
