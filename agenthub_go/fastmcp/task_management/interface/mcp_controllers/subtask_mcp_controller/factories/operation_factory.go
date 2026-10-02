package factories

// Operation Factory for Subtask MCP Controller (Python operation_factory.py).

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

func panicMessage(r any) string {
	if err, ok := r.(error); ok {
		return err.Error()
	}
	return fmt.Sprint(r)
}

// ResponseFormatter is the minimal view of the interface-layer
// StandardResponseFormatter used by this factory. That module has no Go port
// yet; the interface is declared here and reported as a dependency.
type ResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// SubtaskCRUDHandler is the minimal view of SubtaskCRUDHandler
// (../handlers/crud_handler.py). That module has no Go port yet; the interface
// accepts the filtered kwargs ordered map in place of Python's **kwargs.
type SubtaskCRUDHandler interface {
	CreateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	UpdateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	DeleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	ListSubtasks(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CompleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// ProgressHandler is the minimal view of ProgressHandler
// (../handlers/progress_handler.py), which has no Go port yet.
type ProgressHandler interface {
	GetProgressSummary(taskID string, subtasks any) any
	CalculateTaskProgress(taskID string, subtasks any) any
}

// SubtaskOperationFactory ports SubtaskOperationFactory.
type SubtaskOperationFactory struct {
	responseFormatter ResponseFormatter
	contextFacade     any
	taskFacade        any
	crudHandler       SubtaskCRUDHandler
	progressHandler   ProgressHandler
}

// NewSubtaskOperationFactory ports __init__(response_formatter, context_facade=None, task_facade=None).
func NewSubtaskOperationFactory(responseFormatter ResponseFormatter, crudHandler SubtaskCRUDHandler, progressHandler ProgressHandler, contextFacade, taskFacade any) *SubtaskOperationFactory {
	return &SubtaskOperationFactory{
		responseFormatter: responseFormatter,
		contextFacade:     contextFacade,
		taskFacade:        taskFacade,
		crudHandler:       crudHandler,
		progressHandler:   progressHandler,
	}
}

// GetCRUDHandler ports get_crud_handler().
func (f *SubtaskOperationFactory) GetCRUDHandler() SubtaskCRUDHandler { return f.crudHandler }

// GetProgressHandler ports get_progress_handler().
func (f *SubtaskOperationFactory) GetProgressHandler() ProgressHandler { return f.progressHandler }

// HandleOperation ports handle_operation(operation, facade, **kwargs).
func (f *SubtaskOperationFactory) HandleOperation(ctx context.Context, operation string, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(operation, "Operation failed: "+panicMessage(r), "OPERATION_FAILED", nil)
		}
	}()

	switch operation {
	case "create", "update", "delete", "get", "list", "complete":
		return f.handleCRUDOperation(ctx, operation, facade, kwargs)
	case "progress", "summary":
		return f.handleProgressOperation(ctx, operation, facade, kwargs)
	default:
		return f.responseFormatter.CreateErrorResponse(operation, "Unknown operation: "+operation, "UNKNOWN_OPERATION", nil)
	}
}

func copyFiltered(kwargs *entities.OrderedMap[any], allowed map[string]struct{}) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if kwargs == nil {
		return out
	}
	for _, k := range kwargs.Keys() {
		if _, ok := allowed[k]; ok {
			out.Set(k, kwargs.GetAny(k))
		}
	}
	return out
}

func copyExcluded(kwargs *entities.OrderedMap[any], excluded map[string]struct{}) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if kwargs == nil {
		return out
	}
	for _, k := range kwargs.Keys() {
		if _, ok := excluded[k]; !ok {
			out.Set(k, kwargs.GetAny(k))
		}
	}
	return out
}

func stringSet(items ...string) map[string]struct{} {
	s := make(map[string]struct{}, len(items))
	for _, it := range items {
		s[it] = struct{}{}
	}
	return s
}

// handleCRUDOperation ports _handle_crud_operation(operation, facade, **kwargs).
func (f *SubtaskOperationFactory) handleCRUDOperation(ctx context.Context, operation string, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	handler := f.crudHandler

	// Handle string-to-list conversion for assignees parameter.
	if kwargs != nil && kwargs.Has("assignees") && kwargs.GetAny("assignees") != nil {
		if assignees, ok := kwargs.GetAny("assignees").(string); ok {
			if strings.Contains(assignees, ",") {
				parts := []any{}
				for _, a := range strings.Split(assignees, ",") {
					if t := strings.TrimSpace(a); t != "" {
						parts = append(parts, t)
					}
				}
				kwargs.Set("assignees", parts)
			} else {
				t := strings.TrimSpace(assignees)
				if t != "" {
					kwargs.Set("assignees", []any{t})
				} else {
					kwargs.Set("assignees", []any{})
				}
			}
		}
	}

	var filtered *entities.OrderedMap[any]
	switch operation {
	case "create":
		filtered = copyFiltered(kwargs, stringSet("task_id", "title", "description", "priority", "assignees", "progress_notes", "user_id"))
	case "list":
		filtered = copyFiltered(kwargs, stringSet("task_id", "status", "priority", "limit", "offset"))
	case "get":
		filtered = copyFiltered(kwargs, stringSet("task_id", "subtask_id"))
	case "update":
		filtered = copyFiltered(kwargs, stringSet("task_id", "subtask_id", "title", "description", "status", "priority", "assignees", "progress_percentage", "progress_notes"))
	case "delete":
		filtered = copyFiltered(kwargs, stringSet("task_id", "subtask_id", "progress_notes"))
	case "complete":
		filtered = copyExcluded(kwargs, stringSet("user_id"))
	default:
		filtered = copyExcluded(kwargs, stringSet("user_id"))
	}

	var result *entities.OrderedMap[any]
	switch operation {
	case "create":
		result = handler.CreateSubtask(ctx, facade, filtered)
	case "update":
		result = handler.UpdateSubtask(ctx, facade, filtered)
	case "delete":
		result = handler.DeleteSubtask(ctx, facade, filtered)
	case "get":
		result = handler.GetSubtask(ctx, facade, filtered)
	case "list":
		if filtered.Has("subtask_id") {
			filtered.Delete("subtask_id")
		}
		result = handler.ListSubtasks(ctx, facade, filtered)
	case "complete":
		result = handler.CompleteSubtask(ctx, facade, filtered)
	default:
		panic("Unknown CRUD operation: " + operation)
	}

	// Enhance result with progress information if successful.
	if successTrue(result) && (operation == "create" || operation == "update" || operation == "delete" || operation == "complete") {
		if kwargs != nil {
			taskID := getString(kwargs, "task_id")
			if taskID != "" && result.Has("subtasks") {
				progressSummary := f.progressHandler.GetProgressSummary(taskID, result.GetAny("subtasks"))
				result.Set("progress_summary", progressSummary)
			}
		}
	}

	return result
}

// handleProgressOperation ports _handle_progress_operation(operation, facade, **kwargs).
func (f *SubtaskOperationFactory) handleProgressOperation(ctx context.Context, operation string, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) (result *entities.OrderedMap[any]) {
	handler := f.progressHandler
	taskID := getString(kwargs, "task_id")

	if taskID == "" {
		return f.responseFormatter.CreateErrorResponse(operation, "task_id is required for progress operations", "VALIDATION_ERROR", nil)
	}

	defer func() {
		if r := recover(); r != nil {
			result = f.responseFormatter.CreateErrorResponse(operation, "Progress operation failed: "+panicMessage(r), "OPERATION_FAILED", nil)
		}
	}()

	subtasksResult, err := facade.HandleManageSubtask(ctx, "list", taskID, nil, nil, false, nil, nil, nil)
	if err != nil {
		return f.responseFormatter.CreateErrorResponse(operation, "Progress operation failed: "+err.Error(), "OPERATION_FAILED", nil)
	}
	if !successTrue(subtasksResult) {
		return subtasksResult
	}
	subtasks := subtasksResult.GetAny("subtasks")

	switch operation {
	case "progress":
		progress := handler.CalculateTaskProgress(taskID, subtasks)
		data := entities.NewOrderedMap[any]()
		data.Set("progress", progress)
		return f.responseFormatter.CreateSuccessResponse("get_progress", data, nil)
	case "summary":
		summary := handler.GetProgressSummary(taskID, subtasks)
		data := entities.NewOrderedMap[any]()
		data.Set("summary", summary)
		return f.responseFormatter.CreateSuccessResponse("get_progress_summary", data, nil)
	default:
		panic("Unknown progress operation: " + operation)
	}
}

func successTrue(result *entities.OrderedMap[any]) bool {
	if result == nil {
		return false
	}
	v, ok := result.Get("success")
	return ok && v == true
}

func getString(m *entities.OrderedMap[any], key string) string {
	if m == nil {
		return ""
	}
	if s, ok := m.GetAny(key).(string); ok {
		return s
	}
	return ""
}
