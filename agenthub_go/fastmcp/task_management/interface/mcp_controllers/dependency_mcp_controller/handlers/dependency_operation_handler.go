// Package handlers ports
// task_management/interface/mcp_controllers/dependency_mcp_controller/handlers.
package handlers

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DependencyTaskFacade is the minimal TaskApplicationFacade surface the Python
// handler calls. AddDependency/RemoveDependency are not on the Go
// TaskApplicationFacade yet (it only exposes GetDependencies/ClearDependencies/
// GetBlockingTasks), so they are declared here.
type DependencyTaskFacade interface {
	AddDependency(ctx context.Context, taskID string, dependencyID string) *entities.OrderedMap[any]
	RemoveDependency(ctx context.Context, taskID string, dependencyID string) *entities.OrderedMap[any]
	GetDependencies(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any]
	ClearDependencies(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any]
	GetBlockingTasks(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any]
}

// DependencyOperationHandler handles all dependency operations.
type DependencyOperationHandler struct {
	taskFacade DependencyTaskFacade
}

// NewDependencyOperationHandler mirrors DependencyOperationHandler(task_facade).
func NewDependencyOperationHandler(taskFacade DependencyTaskFacade) *DependencyOperationHandler {
	return &DependencyOperationHandler{taskFacade: taskFacade}
}

// HandleOperation mirrors handle_operation. The Python try/except Exception is
// mirrored with recover so any facade panic becomes the INTERNAL_ERROR response.
func (h *DependencyOperationHandler) HandleOperation(ctx context.Context, action string, taskID string, projectID *string, gitBranchName string, userID *string, dependencyData map[string]any) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = dependencyInternalError(value_objects.PyStr(r))
		}
	}()

	if taskID == "" {
		return missingFieldError("task_id", "A valid task_id string")
	}

	switch action {
	case "add_dependency":
		return h.handleAddDependency(ctx, taskID, dependencyData)
	case "remove_dependency":
		return h.handleRemoveDependency(ctx, taskID, dependencyData)
	case "get_dependencies":
		return h.taskFacade.GetDependencies(ctx, taskID, nil)
	case "clear_dependencies":
		return h.taskFacade.ClearDependencies(ctx, taskID, nil)
	case "get_blocking_tasks":
		return h.taskFacade.GetBlockingTasks(ctx, taskID, nil)
	default:
		return unknownActionError(action)
	}
}

func (h *DependencyOperationHandler) handleAddDependency(ctx context.Context, taskID string, dependencyData map[string]any) *entities.OrderedMap[any] {
	if dependencyID, ok := dependencyIDFrom(dependencyData); ok {
		return h.taskFacade.AddDependency(ctx, taskID, dependencyID)
	}
	return missingDependencyIDError()
}

func (h *DependencyOperationHandler) handleRemoveDependency(ctx context.Context, taskID string, dependencyData map[string]any) *entities.OrderedMap[any] {
	if dependencyID, ok := dependencyIDFrom(dependencyData); ok {
		return h.taskFacade.RemoveDependency(ctx, taskID, dependencyID)
	}
	return missingDependencyIDError()
}

func dependencyIDFrom(dependencyData map[string]any) (string, bool) {
	if len(dependencyData) == 0 {
		return "", false
	}
	value, ok := dependencyData["dependency_id"]
	if !ok {
		return "", false
	}
	return value_objects.PyStr(value), true
}

func missingFieldError(field string, expected string) *entities.OrderedMap[any] {
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", false)
	resp.Set("error", "Missing required field: "+field)
	resp.Set("error_code", "MISSING_FIELD")
	resp.Set("field", field)
	resp.Set("expected", expected)
	resp.Set("hint", "Include '"+field+"' in your request body")
	return resp
}

func missingDependencyIDError() *entities.OrderedMap[any] {
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", false)
	resp.Set("error", "Missing required field: dependency_id in dependency_data")
	resp.Set("error_code", "MISSING_FIELD")
	resp.Set("field", "dependency_data.dependency_id")
	resp.Set("expected", "A valid dependency_id string inside dependency_data")
	resp.Set("hint", "Include 'dependency_data': {'dependency_id': ...} in your request body")
	return resp
}

func unknownActionError(action string) *entities.OrderedMap[any] {
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", false)
	resp.Set("error", "Unknown dependency action: "+action)
	resp.Set("error_code", "UNKNOWN_ACTION")
	resp.Set("field", "action")
	resp.Set("expected", "One of: add_dependency, remove_dependency, get_dependencies, clear_dependencies, get_blocking_tasks")
	resp.Set("hint", "Check the 'action' parameter for typos")
	return resp
}

func dependencyInternalError(message string) *entities.OrderedMap[any] {
	resp := entities.NewOrderedMap[any]()
	resp.Set("success", false)
	resp.Set("error", "Dependency operation failed: "+message)
	resp.Set("error_code", "INTERNAL_ERROR")
	resp.Set("details", message)
	return resp
}
