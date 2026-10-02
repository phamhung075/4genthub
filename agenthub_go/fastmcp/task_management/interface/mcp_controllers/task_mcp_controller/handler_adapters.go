package task_mcp_controller

// Go-only composition glue for the task MCP controller (no Python module).
//
// factories.NewSearchHandler / factories.NewWorkflowHandler are nil-returning
// constructor hooks because the Python search_handler.py / workflow_handler.py
// ports live in the sibling handlers package with typed signatures, while the
// factory interfaces pass the Python **kwargs mapping. These adapters convert
// kwargs exactly as operation_factory.py does and bridge the two views.
//
// The Python operation_factory filters the kwargs before calling a handler:
//   list   -> status, priority, assignee, tag, git_branch_id, limit, offset,
//             sort_by, sort_order
//   search -> query, status, priority, assignee, tag, git_branch_id, limit, offset
//   next   -> git_branch_id, include_context (default True)
//   count  -> everything except user_id, task_id, title, description
//
// The adapters therefore read only those keys and leave the missing ones nil,
// matching dict.get(key) semantics.

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/handlers"
)

// initHandlerAdapters registers the real handlers on the operation factory's
// constructor hooks. It must run before the first OperationFactory is built.
// Go runs every init function in a package, so init below invokes it and the
// existing init in task_mcp_controller.go coexists without conflict.
func initHandlerAdapters() {
	factories.NewSearchHandler = func(responseFormatter factories.ResponseFormatter) factories.TaskSearchHandler {
		return taskSearchHandlerAdapter{
			searchHandler:     handlers.NewSearchHandler(responseFormatter),
			responseFormatter: responseFormatter,
		}
	}
	factories.NewWorkflowHandler = func(responseFormatter factories.ResponseFormatter, contextFacadeFactory any) factories.TaskWorkflowHandler {
		return taskWorkflowHandlerAdapter{
			workflowHandler: handlers.NewWorkflowHandler(responseFormatter, adaptContextFacadeFactory(contextFacadeFactory)),
		}
	}
}

func init() { initHandlerAdapters() }

// taskSearchHandlerAdapter adapts handlers.SearchHandler (typed parameters) to
// factories.TaskSearchHandler (the Python **kwargs mapping).
type taskSearchHandlerAdapter struct {
	searchHandler     *handlers.SearchHandler
	responseFormatter handlers.SearchResponseFormatter
}

// ListTasks ports SearchHandler.list_tasks(facade, status, priority, assignee,
// tag, git_branch_id, limit, offset, sort_by, sort_order).
func (a taskSearchHandlerAdapter) ListTasks(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any] {
	searchFacade, ok := facade.(handlers.TaskSearchFacade)
	if !ok {
		return a.facadeMismatch("list_tasks", facade)
	}
	return a.searchHandler.ListTasks(ctx, searchFacade,
		adapterKwString(params, "status"),
		adapterKwString(params, "priority"),
		adapterKwString(params, "assignee"),
		adapterKwString(params, "tag"),
		adapterKwString(params, "git_branch_id"),
		adapterKwInt(params, "limit"),
		adapterKwInt(params, "offset"),
		adapterKwString(params, "sort_by"),
		adapterKwString(params, "sort_order"),
	)
}

// SearchTasks ports SearchHandler.search_tasks(facade, query, status, priority,
// assignee, tag, git_branch_id, limit, offset).
func (a taskSearchHandlerAdapter) SearchTasks(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any] {
	searchFacade, ok := facade.(handlers.TaskSearchFacade)
	if !ok {
		return a.facadeMismatch("search_tasks", facade)
	}
	return a.searchHandler.SearchTasks(ctx, searchFacade,
		adapterKwString(params, "query"),
		adapterKwString(params, "status"),
		adapterKwString(params, "priority"),
		adapterKwString(params, "assignee"),
		adapterKwString(params, "tag"),
		adapterKwString(params, "git_branch_id"),
		adapterKwInt(params, "limit"),
		adapterKwInt(params, "offset"),
	)
}

// GetNextTask ports SearchHandler.get_next_task(facade, git_branch_id,
// include_context=True).
func (a taskSearchHandlerAdapter) GetNextTask(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any] {
	searchFacade, ok := facade.(handlers.TaskSearchFacade)
	if !ok {
		return a.facadeMismatch("next_task", facade)
	}
	includeContext := true
	if v, present := params["include_context"]; present {
		includeContext = value_objects.PyTruthy(v)
	}
	return a.searchHandler.GetNextTask(ctx, searchFacade, adapterKwString(params, "git_branch_id"), includeContext)
}

// CountTasks ports SearchHandler.count_tasks(facade, status, priority,
// git_branch_id).
func (a taskSearchHandlerAdapter) CountTasks(ctx context.Context, facade handlers.TaskFacade, params map[string]any) *entities.OrderedMap[any] {
	searchFacade, ok := facade.(handlers.TaskSearchFacade)
	if !ok {
		return a.facadeMismatch("count_tasks", facade)
	}
	return a.searchHandler.CountTasks(ctx, searchFacade,
		adapterKwString(params, "status"),
		adapterKwString(params, "priority"),
		adapterKwString(params, "git_branch_id"),
	)
}

// facadeMismatch is the Go analogue of the Python AttributeError that
// SearchHandler catches: the facade does not expose the search surface.
func (a taskSearchHandlerAdapter) facadeMismatch(operation string, facade handlers.TaskFacade) *entities.OrderedMap[any] {
	return a.responseFormatter.CreateErrorResponse(operation,
		fmt.Sprintf("Task facade %T does not implement handlers.TaskSearchFacade", facade),
		handlers.ErrorCodeOperationFailed, nil)
}

// taskWorkflowHandlerAdapter adapts handlers.WorkflowHandler (typed parameters)
// to factories.TaskWorkflowHandler (the Python **kwargs mapping).
type taskWorkflowHandlerAdapter struct {
	workflowHandler *handlers.WorkflowHandler
}

// CreateTaskContext ports WorkflowHandler.create_task_context(task_id,
// task_data, git_branch_id).
func (a taskWorkflowHandlerAdapter) CreateTaskContext(ctx context.Context, taskID string,
	taskData *entities.OrderedMap[any], gitBranchID *string) *entities.OrderedMap[any] {
	branchID := ""
	if gitBranchID != nil {
		branchID = *gitBranchID
	}
	return a.workflowHandler.CreateTaskContext(ctx, taskID, taskData, branchID)
}

// EnrichTaskResponse ports WorkflowHandler.enrich_task_response(response,
// action, task_data=None).
func (a taskWorkflowHandlerAdapter) EnrichTaskResponse(response *entities.OrderedMap[any],
	action string, taskData any) *entities.OrderedMap[any] {
	return a.workflowHandler.EnrichTaskResponse(response, action, adapterOrderedMap(taskData))
}

// adaptContextFacadeFactory exposes the factory's `any` context facade factory
// as handlers.ContextFacadeFactory when it implements it, else nil (Python
// `context_facade_factory=None`).
func adaptContextFacadeFactory(factory any) handlers.ContextFacadeFactory {
	if f, ok := factory.(handlers.ContextFacadeFactory); ok {
		return f
	}
	return nil
}

// adapterKwString mirrors dict.get(key) for a string value.
func adapterKwString(params map[string]any, key string) *string {
	v, ok := params[key]
	if !ok || v == nil {
		return nil
	}
	if s, isStr := v.(string); isStr {
		return &s
	}
	return nil
}

// adapterKwInt mirrors int(dict.get(key)) for the limit/offset keywords.
func adapterKwInt(params map[string]any, key string) *int {
	v, ok := params[key]
	if !ok || v == nil {
		return nil
	}
	switch n := v.(type) {
	case int:
		return &n
	case int64:
		i := int(n)
		return &i
	case float64:
		i := int(n)
		return &i
	case string:
		if i, err := strconv.Atoi(strings.TrimSpace(n)); err == nil {
			return &i
		}
	}
	return nil
}

// adapterOrderedMap normalizes a task_data value into the handlers' OrderedMap
// view; a JSON object arrives as map[string]any.
func adapterOrderedMap(v any) *entities.OrderedMap[any] {
	switch m := v.(type) {
	case nil:
		return nil
	case *entities.OrderedMap[any]:
		return m
	case map[string]any:
		out := entities.NewOrderedMap[any]()
		for k, val := range m {
			out.Set(k, val)
		}
		return out
	}
	return nil
}
