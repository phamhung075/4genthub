package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/application/dtos/dependency"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// addDependencyAcrossContextsFinder is the optional repository surface
// add_dependency probes for find_by_id_across_contexts (Python uses hasattr). The
// domain repositories.TaskRepository does not declare it; the same consumer-side
// interface pattern is used by domain/services/dependency_validation_service.go.
type addDependencyAcrossContextsFinder interface {
	FindByIDAcrossContexts(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
}

// AddDependencyUseCase ports add_dependency.AddDependencyUseCase.
type AddDependencyUseCase struct {
	taskRepository repositories.TaskRepository
}

// NewAddDependencyUseCase builds the use case.
func NewAddDependencyUseCase(taskRepository repositories.TaskRepository) *AddDependencyUseCase {
	return &AddDependencyUseCase{taskRepository: taskRepository}
}

// findDependencyTask mirrors _find_dependency_task: all states, then the plain
// lookup, then the optional across-contexts lookup. A repository error propagates
// exactly like the Python exception would.
func (uc *AddDependencyUseCase) findDependencyTask(ctx context.Context, dependencyID value_objects.TaskId) (*entities.Task, error) {
	dependencyTask, err := uc.taskRepository.FindByIDAllStates(ctx, dependencyID)
	if err != nil {
		return nil, err
	}
	if dependencyTask != nil {
		return dependencyTask, nil
	}

	dependencyTask, err = uc.taskRepository.FindByID(ctx, dependencyID)
	if err != nil {
		return nil, err
	}
	if dependencyTask != nil {
		return dependencyTask, nil
	}

	if finder, ok := uc.taskRepository.(addDependencyAcrossContextsFinder); ok {
		dependencyTask, err := finder.FindByIDAcrossContexts(ctx, dependencyID)
		if err != nil {
			return nil, err
		}
		if dependencyTask != nil {
			return dependencyTask, nil
		}
	}
	return nil, nil
}

// Execute ports execute().
func (uc *AddDependencyUseCase) Execute(ctx context.Context, request *dependency.AddDependencyRequest) (*dependency.DependencyResponse, error) {
	taskID, err := convertToTaskID(request.TaskID)
	if err != nil {
		return nil, err
	}
	dependencyID, err := convertToTaskID(request.DependsOnTaskID)
	if err != nil {
		return nil, err
	}

	task, err := uc.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError("Task " + value_objects.PyStr(request.TaskID) + " not found")
	}

	dependencyTask, err := uc.findDependencyTask(ctx, dependencyID)
	if err != nil {
		return nil, err
	}
	if dependencyTask == nil {
		return nil, exceptions.NewTaskNotFoundError(
			"Dependency task " + value_objects.PyStr(request.DependsOnTaskID) + " not found in active, completed, or archived tasks")
	}

	taskIDStr := value_objects.PyStr(request.TaskID)
	dependsOnStr := value_objects.PyStr(request.DependsOnTaskID)

	if task.HasDependency(dependencyID) {
		message := "Dependency " + dependsOnStr + " already exists"
		return &dependency.DependencyResponse{Success: false, Message: &message, TaskID: taskIDStr, DependsOnTaskID: dependsOnStr}, nil
	}
	if task.HasCircularDependency(dependencyID) {
		message := "Cannot add dependency: would create circular reference"
		return &dependency.DependencyResponse{Success: false, Message: &message, TaskID: taskIDStr, DependsOnTaskID: dependsOnStr}, nil
	}

	if err := task.AddDependency(dependencyID); err != nil {
		return nil, err
	}
	if _, err := uc.taskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	dependencyStatus := "None"
	if dependencyTask.Status != nil {
		dependencyStatus = dependencyTask.Status.Value
	}
	statusInfo := ""
	switch {
	case dependencyTask.Status != nil && dependencyTask.Status.IsDone():
		statusInfo = " (dependency is completed - task can proceed immediately)"
	case dependencyStatus == "todo" || dependencyStatus == "in_progress":
		statusInfo = " (dependency is " + dependencyStatus + " - task will wait for completion)"
	case dependencyStatus == "blocked":
		statusInfo = " (warning: dependency is currently blocked)"
	case dependencyStatus == "cancelled":
		statusInfo = " (warning: dependency was cancelled - please review)"
	}

	message := "Dependency " + dependsOnStr + " added successfully" + statusInfo
	dependencyType := request.DependencyType
	return &dependency.DependencyResponse{
		Success:         true,
		Message:         &message,
		TaskID:          taskIDStr,
		DependsOnTaskID: dependsOnStr,
		DependencyType:  &dependencyType,
	}, nil
}
