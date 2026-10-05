// Package facades ports task_management/application/facades.
package facades

import (
	"context"
	"errors"
	"strings"

	dependencydto "agenthub/fastmcp/task_management/application/dtos/dependency"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DependencyApplicationFacade ports dependency_application_facade.DependencyApplicationFacade.
type DependencyApplicationFacade struct {
	taskRepository       repositories.TaskRepository
	dependencyAppService *services.DependencieApplicationService
}

// NewDependencyApplicationFacade mirrors __init__(task_repository).
func NewDependencyApplicationFacade(taskRepository repositories.TaskRepository) *DependencyApplicationFacade {
	return &DependencyApplicationFacade{
		taskRepository:       taskRepository,
		dependencyAppService: services.NewDependencieApplicationService(taskRepository, nil),
	}
}

// ManageDependencies ports manage_dependencies. The Python returns a plain dict
// whose key order is observable by the HTTP layer, so this returns an OrderedMap.
func (f *DependencyApplicationFacade) ManageDependencies(ctx context.Context, action, taskID string, dependencyData map[string]any) *entities.OrderedMap[any] {
	if strings.TrimSpace(taskID) == "" {
		return dependencyFacadeError(&value_objects.ValueError{Msg: "Task ID is required for dependency operations"})
	}

	switch action {
	case "add_dependency":
		dependencyID, ok := dependencyFacadeDependencyID(dependencyData)
		if !ok {
			return dependencyFacadeError(&value_objects.ValueError{Msg: "dependency_data with dependency_id is required"})
		}
		request := dependencydto.NewAddDependencyRequest(taskID, dependencyID, nil)
		// Python's use case returns dtos.dependency.DependencyResponse, which has
		// no `dependencies` attribute; the facade then reads response.dependencies
		// and the AttributeError is caught by the generic handler. Executing the
		// use case first keeps its side effects, then we reproduce that error.
		if _, err := f.dependencyAppService.AddDependency(ctx, request); err != nil {
			return dependencyFacadeUseCaseError(err)
		}
		return dependencyFacadeGenericError("Dependency operation failed: 'DependencyResponse' object has no attribute 'dependencies'")

	case "remove_dependency":
		dependencyID, ok := dependencyFacadeDependencyID(dependencyData)
		if !ok {
			return dependencyFacadeError(&value_objects.ValueError{Msg: "dependency_data with dependency_id is required"})
		}
		// Python's remove use case builds dtos.dependency.DependencyResponse with a
		// `dependencies` kwarg the dataclass does not declare, so it raises
		// TypeError after saving (or right away when the dependency is absent).
		// Execute first (the task is saved when the dependency exists), then
		// reproduce the observed error.
		if _, err := f.dependencyAppService.RemoveDependency(ctx, taskID, value_objects.PyStr(dependencyID)); err != nil {
			return dependencyFacadeUseCaseError(err)
		}
		return dependencyFacadeGenericError("Dependency operation failed: DependencyResponse.__init__() got an unexpected keyword argument 'dependencies'")

	case "get_dependencies":
		response, err := f.dependencyAppService.GetDependencies(ctx, taskID)
		if err != nil {
			return dependencyFacadeUseCaseError(err)
		}
		return dependencyFacadeMerge("get_dependencies", response)

	case "clear_dependencies":
		// Python's clear use case builds dtos.dependency.DependencyResponse with a
		// `dependencies` kwarg the dataclass does not declare, so it raises
		// TypeError before returning. Execute first (the task is saved), then
		// reproduce the observed error.
		if _, err := f.dependencyAppService.ClearDependencies(ctx, taskID); err != nil {
			return dependencyFacadeUseCaseError(err)
		}
		return dependencyFacadeGenericError("Dependency operation failed: DependencyResponse.__init__() got an unexpected keyword argument 'dependencies'")

	case "get_blocking_tasks":
		response, err := f.dependencyAppService.GetBlockingTasks(ctx, taskID)
		if err != nil {
			return dependencyFacadeUseCaseError(err)
		}
		return dependencyFacadeMerge("get_blocking_tasks", response)

	default:
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", "Unknown dependency action: "+action)
		return m
	}
}

// dependencyFacadeDependencyID mirrors `if not dependency_data or "dependency_id" not in dependency_data`.
func dependencyFacadeDependencyID(dependencyData map[string]any) (any, bool) {
	if dependencyData == nil {
		return nil, false
	}
	v, ok := dependencyData["dependency_id"]
	return v, ok
}

// dependencyFacadeError mirrors `{"success": False, "error": str(e)}`.
func dependencyFacadeError(err error) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", err.Error())
	return m
}

// dependencyFacadeUseCaseError reproduces the two dedicated except clauses
// (TaskNotFoundError, ValueError) versus the generic Exception handler.
func dependencyFacadeUseCaseError(err error) *entities.OrderedMap[any] {
	var notFound *exceptions.TaskNotFoundError
	var valueErr *value_objects.ValueError
	if errors.As(err, &notFound) || errors.As(err, &valueErr) {
		return dependencyFacadeError(err)
	}
	return dependencyFacadeGenericError("Dependency operation failed: " + err.Error())
}

func dependencyFacadeGenericError(message string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", message)
	return m
}

// dependencyFacadeMerge builds {"success": True, "action": action, **response}.
func dependencyFacadeMerge(action string, response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", action)
	if response != nil {
		for _, k := range response.Keys() {
			v, _ := response.Get(k)
			m.Set(k, v)
		}
	}
	return m
}
