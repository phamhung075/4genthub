package handlers

// Search Handler for Task MCP Controller
// (Python handlers/search_handler.py).
//
// The interface-layer StandardResponseFormatter has no Go port yet, so it is
// declared here (ResponseFormatter). The facade's list/search methods and the
// CRUD handler are declared as minimal interfaces/hooks; they are unported and
// reported as dependencies.

import (
	"context"
	"fmt"

	task "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SearchResponseFormatter extends the handlers ResponseFormatter (declared in
// crud_handler.go) with the success/timestamp surface used by the search
// handler. The interface-layer StandardResponseFormatter has no Go port yet.
type SearchResponseFormatter interface {
	ResponseFormatter
	CreateSuccessResponse(operation string, data any, workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetTimestamp() string
}

// TaskSearchFacade is the subset of TaskApplicationFacade used by the search
// handler. ListTasks/SearchTasks are not ported yet; CountTasks exists.
type TaskSearchFacade interface {
	ListTasks(ctx context.Context, request *task.ListTasksRequest) *entities.OrderedMap[any]
	SearchTasks(ctx context.Context, request *task.SearchTasksRequest) *entities.OrderedMap[any]
	CountTasks(ctx context.Context, filters map[string]any) *entities.OrderedMap[any]
}

// SearchHandler ports SearchHandler.
type SearchHandler struct {
	responseFormatter SearchResponseFormatter
}

// NewSearchHandler ports __init__(response_formatter).
func NewSearchHandler(responseFormatter SearchResponseFormatter) *SearchHandler {
	return &SearchHandler{responseFormatter: responseFormatter}
}

// ListTasks ports list_tasks.
func (h *SearchHandler) ListTasks(ctx context.Context, facade TaskSearchFacade, status, priority, assignee, tag, gitBranchID *string,
	limit, offset *int, sortBy, sortOrder *string) (result *entities.OrderedMap[any]) {
	_ = sortBy
	_ = sortOrder

	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("list_tasks",
				"Failed to list tasks: "+fmt.Sprint(r), ErrorCodeOperationFailed, nil)
		}
	}()

	var assignees []string
	if assignee != nil {
		assignees = []string{*assignee}
	}
	var labels []string
	if tag != nil {
		labels = []string{*tag}
	}
	effectiveLimit := 50
	if limit != nil {
		effectiveLimit = *limit
	}

	request := &task.ListTasksRequest{
		GitBranchID: gitBranchID,
		Status:      status,
		Priority:    priority,
		Assignees:   assignees,
		Labels:      labels,
		Limit:       &effectiveLimit,
	}

	result = facade.ListTasks(ctx, request)

	successVal, _ := result.Get("success")
	if !value_objects.PyTruthy(successVal) {
		return result
	}
	tasksVal, hasTasks := result.Get("tasks")
	if !hasTasks {
		return result
	}

	minimalTasks := make([]any, 0)
	for _, taskItem := range omList(tasksVal) {
		tm, _ := taskItem.(*entities.OrderedMap[any])
		minimal := entities.NewOrderedMap[any]()
		minimal.Set("id", omGetOr(tm, "id", nil))
		minimal.Set("title", omGetOr(tm, "title", nil))
		minimal.Set("status", omGetOr(tm, "status", nil))
		minimal.Set("priority", omGetOr(tm, "priority", nil))
		minimal.Set("git_branch_id", omGetOr(tm, "git_branch_id", nil))
		minimal.Set("dependencies", omGetOr(tm, "dependencies", []any{}))
		minimal.Set("has_dependencies", omGetOr(tm, "has_dependencies", false))
		minimal.Set("dependency_count", omGetOr(tm, "dependency_count", 0))
		minimalTasks = append(minimalTasks, minimal)
	}
	result.Set("tasks", minimalTasks)

	pagination := entities.NewOrderedMap[any]()
	pagination.Set("total", len(minimalTasks))
	pagination.Set("limit", effectiveLimit)
	offsetValue := 0
	if offset != nil {
		offsetValue = *offset
	}
	pagination.Set("offset", offsetValue)
	pagination.Set("has_more", len(minimalTasks) == effectiveLimit)
	pagination.Set("tip", "Use manage_task(action='get', task_id='...') for full details")
	result.Set("pagination", pagination)

	return result
}

// SearchTasks ports search_tasks.
func (h *SearchHandler) SearchTasks(ctx context.Context, facade TaskSearchFacade, query, status, priority, assignee, tag, gitBranchID *string,
	limit, offset *int) (result *entities.OrderedMap[any]) {
	_ = status
	_ = priority
	_ = assignee
	_ = tag
	_ = offset

	if query == nil || !value_objects.PyTruthy(*query) {
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("field", "query")
		metadata.Set("hint", "Include 'query' in your request")
		return h.responseFormatter.CreateErrorResponse("search_tasks",
			"Missing required field: query. Expected: A search query string",
			ErrorCodeValidationError, metadata)
	}

	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("search_tasks",
				"Search failed: "+fmt.Sprint(r), ErrorCodeOperationFailed, nil)
		}
	}()

	request := task.NewSearchTasksRequest(*query, gitBranchID, limit)
	result = facade.SearchTasks(ctx, request)

	successVal, _ := result.Get("success")
	if !value_objects.PyTruthy(successVal) {
		return result
	}
	tasksVal, hasTasks := result.Get("tasks")
	if !hasTasks {
		return result
	}

	minimalTasks := make([]any, 0)
	for _, taskItem := range omList(tasksVal) {
		tm, _ := taskItem.(*entities.OrderedMap[any])
		minimal := entities.NewOrderedMap[any]()
		minimal.Set("id", omGetOr(tm, "id", nil))
		minimal.Set("title", omGetOr(tm, "title", nil))
		minimal.Set("status", omGetOr(tm, "status", nil))
		minimal.Set("priority", omGetOr(tm, "priority", nil))
		minimalTasks = append(minimalTasks, minimal)
	}
	result.Set("tasks", minimalTasks)

	searchMetadata := entities.NewOrderedMap[any]()
	searchMetadata.Set("query", *query)
	searchMetadata.Set("git_branch_id", gitBranchID)
	searchMetadata.Set("total_results", len(minimalTasks))
	searchMetadata.Set("tip", "Use manage_task(action='get', task_id='...') for full details")
	result.Set("search_metadata", searchMetadata)

	return result
}

// GetNextTask ports get_next_task(git_branch_id, include_context=True).
func (h *SearchHandler) GetNextTask(ctx context.Context, facade TaskSearchFacade, gitBranchID *string, includeContext bool) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("next_task",
				"Failed to get next task: "+fmt.Sprint(r), ErrorCodeOperationFailed, nil)
		}
	}()

	one := 1
	todo := "todo"
	request := &task.ListTasksRequest{
		GitBranchID: gitBranchID,
		Status:      &todo,
		Limit:       &one,
	}
	listResult := facade.ListTasks(ctx, request)

	successVal, _ := listResult.Get("success")
	tasksVal, _ := listResult.Get("tasks")
	tasks := omList(tasksVal)
	if value_objects.PyTruthy(successVal) && len(tasks) > 0 {
		nextTaskMinimal, _ := tasks[0].(*entities.OrderedMap[any])
		taskIDAny, _ := nextTaskMinimal.Get("id")
		taskID, _ := taskIDAny.(string)

		crudFacade, ok := facade.(TaskFacade)
		if !ok {
			return h.responseFormatter.CreateErrorResponse("next_task",
				"Failed to fetch full details for task "+taskID, ErrorCodeOperationFailed, nil)
		}
		crudHandler := NewCRUDHandler(h.responseFormatter)
		fullTaskResult := crudHandler.GetTask(ctx, crudFacade, taskID, includeContext)

		fullSuccess, _ := fullTaskResult.Get("success")
		taskNodeAny, hasTask := fullTaskResult.Get("task")
		taskData, _ := taskNodeAny.(*entities.OrderedMap[any])
		if value_objects.PyTruthy(fullSuccess) && hasTask && taskData != nil {
			if includeContext {
				if parentContext := h.resolveParentContextHierarchy(ctx, taskData, gitBranchID); parentContext != nil {
					if _, ok := taskData.Get("inherited_context"); !ok {
						taskData.Set("inherited_context", entities.NewOrderedMap[any]())
					}
					taskData.Set("parent_contexts", parentContext)
					taskData.Set("parent_context_available", true)
				} else {
					taskData.Set("parent_context_available", false)
				}
			}

			next := entities.NewOrderedMap[any]()
			next.Set("success", true)
			next.Set("action", "next")
			next.Set("task", taskData)
			next.Set("message", "Next task found with parent context")
			next.Set("include_context", includeContext)
			return next
		}
		return h.responseFormatter.CreateErrorResponse("next_task",
			"Failed to fetch full details for task "+taskID, ErrorCodeOperationFailed, nil)
	}

	noTasks := entities.NewOrderedMap[any]()
	noTasks.Set("success", false)
	noTasks.Set("action", "next")
	noTasks.Set("message", "No tasks found. Create a task to get started!")
	noTasks.Set("error", "No actionable tasks found.")
	return noTasks
}

// resolveParentContextHierarchy ports _resolve_parent_context_hierarchy.
func (h *SearchHandler) resolveParentContextHierarchy(ctx context.Context, taskData *entities.OrderedMap[any], gitBranchID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = nil
		}
	}()

	_ = taskData
	if GetUnifiedContextFacade == nil {
		return nil
	}
	contextFacade := GetUnifiedContextFacade()
	if contextFacade == nil {
		return nil
	}

	parentContexts := entities.NewOrderedMap[any]()

	if gitBranchID != nil {
		branchContextResult := contextFacade.ResolveContext(ctx, "branch", *gitBranchID, false)
		if branchContextResult != nil {
			successVal, _ := branchContextResult.Get("success")
			resolvedAny, hasResolved := branchContextResult.Get("resolved_context")
			if value_objects.PyTruthy(successVal) && hasResolved {
				parentContexts.Set("branch", resolvedAny)

				var projectID *string
				if branchData, isMap := resolvedAny.(*entities.OrderedMap[any]); isMap {
					if pidAny, ok := branchData.Get("project_id"); ok && pidAny != nil {
						if pid, isStr := pidAny.(string); isStr {
							projectID = &pid
						}
					}
				}

				if projectID != nil {
					projectContextResult := contextFacade.ResolveContext(ctx, "project", *projectID, false)
					if projectContextResult != nil {
						pSuccess, _ := projectContextResult.Get("success")
						pResolvedAny, pHasResolved := projectContextResult.Get("resolved_context")
						if value_objects.PyTruthy(pSuccess) && pHasResolved {
							parentContexts.Set("project", pResolvedAny)

							var userID *string
							if projectData, isMap := pResolvedAny.(*entities.OrderedMap[any]); isMap {
								if uidAny, ok := projectData.Get("user_id"); ok && uidAny != nil {
									if uid, isStr := uidAny.(string); isStr {
										userID = &uid
									}
								}
							}

							if userID != nil {
								globalContextResult := contextFacade.ResolveContext(ctx, "global", *userID, false)
								if globalContextResult != nil {
									gSuccess, _ := globalContextResult.Get("success")
									gResolvedAny, gHasResolved := globalContextResult.Get("resolved_context")
									if value_objects.PyTruthy(gSuccess) && gHasResolved {
										parentContexts.Set("global", gResolvedAny)
									}
								}
							}
						}
					}
				}
			}
		}
	}

	if parentContexts.Len() > 0 {
		result = entities.NewOrderedMap[any]()
		result.Set("hierarchy_levels", parentContexts.Keys())
		result.Set("contexts", parentContexts)
		result.Set("inheritance_chain", buildInheritanceChain(parentContexts))
		return result
	}
	return nil
}

// buildInheritanceChain ports _build_inheritance_chain.
func buildInheritanceChain(parentContexts *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	inheritanceChain := entities.NewOrderedMap[any]()
	hierarchyOrder := []string{"global", "project", "branch"}

	for _, level := range hierarchyOrder {
		contextDataAny, ok := parentContexts.Get(level)
		if !ok {
			continue
		}
		contextData, isMap := contextDataAny.(*entities.OrderedMap[any])
		if !isMap {
			continue
		}
		for _, key := range contextData.Keys() {
			value, _ := contextData.Get(key)
			if value != nil {
				if _, exists := inheritanceChain.Get(key); !exists {
					inheritanceChain.Set(key, value)
				}
			}
		}
	}
	return inheritanceChain
}

// CountTasks ports count_tasks.
func (h *SearchHandler) CountTasks(ctx context.Context, facade TaskSearchFacade, status, priority, gitBranchID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("count_tasks",
				"Failed to count tasks: "+fmt.Sprint(r), ErrorCodeOperationFailed, nil)
		}
	}()

	filters := map[string]any{}
	if status != nil && *status != "" {
		filters["status"] = *status
	}
	if priority != nil && *priority != "" {
		filters["priority"] = *priority
	}
	if gitBranchID != nil && *gitBranchID != "" {
		filters["git_branch_id"] = *gitBranchID
	}

	result = facade.CountTasks(ctx, filters)

	successVal, _ := result.Get("success")
	if value_objects.PyTruthy(successVal) {
		countAny, _ := result.Get("count")
		count := 0
		if c, isInt := countAny.(int); isInt {
			count = c
		}
		timestampAny, _ := result.Get("timestamp")

		filtersMap := entities.NewOrderedMap[any]()
		for _, key := range []string{"status", "priority", "git_branch_id"} {
			if v, ok := filters[key]; ok {
				filtersMap.Set(key, v)
			}
		}

		data := entities.NewOrderedMap[any]()
		data.Set("count", count)
		data.Set("filters", filtersMap)
		data.Set("timestamp", timestampAny)

		return h.responseFormatter.CreateSuccessResponse("count_tasks", data, nil)
	}

	return result
}

// omList converts an OrderedMap "tasks" value (list of dicts) into a slice.
func omList(v any) []any {
	switch t := v.(type) {
	case []any:
		return t
	case []*entities.OrderedMap[any]:
		out := make([]any, 0, len(t))
		for _, item := range t {
			out = append(out, item)
		}
		return out
	}
	return nil
}
