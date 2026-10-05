package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AddDependencyRequest ports manage_dependencies.AddDependencyRequest.
// TaskID/DependencyID are `str | int` in the Python, hence `any`.
type AddDependencyRequest struct {
	TaskID       any
	DependencyID any
}

// DependencyResponse ports manage_dependencies.DependencyResponse. The Python
// dataclass has no to_dict; callers serialize it (e.g. dataclasses.asdict).
type DependencyResponse struct {
	TaskID       string
	Dependencies []string
	Success      bool
	Message      string
}

// ManageDependenciesUseCase ports manage_dependencies.ManageDependenciesUseCase.
type ManageDependenciesUseCase struct {
	taskRepository repositories.TaskRepository
}

// NewManageDependenciesUseCase mirrors __init__(task_repository).
func NewManageDependenciesUseCase(taskRepository repositories.TaskRepository) *ManageDependenciesUseCase {
	return &ManageDependenciesUseCase{taskRepository: taskRepository}
}

// AddDependency mirrors ManageDependenciesUseCase.add_dependency.
func (u *ManageDependenciesUseCase) AddDependency(ctx context.Context, request *AddDependencyRequest) (*DependencyResponse, error) {
	taskID, err := smallUCConvertTaskID(request.TaskID)
	if err != nil {
		return nil, err
	}
	dependencyID, err := smallUCConvertTaskID(request.DependencyID)
	if err != nil {
		return nil, err
	}

	task, err := u.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", value_objects.PyStr(request.TaskID)))
	}

	dependencyTask, err := u.taskRepository.FindByIDAllStates(ctx, dependencyID)
	if err != nil {
		return nil, err
	}
	if dependencyTask == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Dependency task %s not found", value_objects.PyStr(request.DependencyID)))
	}

	if task.HasDependency(dependencyID) {
		return &DependencyResponse{
			TaskID:       value_objects.PyStr(request.TaskID),
			Dependencies: task.GetDependencyIDs(),
			Success:      false,
			Message:      fmt.Sprintf("Dependency %s already exists", value_objects.PyStr(request.DependencyID)),
		}, nil
	}

	if task.HasCircularDependency(dependencyID) {
		return &DependencyResponse{
			TaskID:       value_objects.PyStr(request.TaskID),
			Dependencies: task.GetDependencyIDs(),
			Success:      false,
			Message:      "Cannot add dependency: would create circular reference",
		}, nil
	}

	if err := task.AddDependency(dependencyID); err != nil {
		return nil, err
	}
	if _, err := u.taskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	return &DependencyResponse{
		TaskID:       value_objects.PyStr(request.TaskID),
		Dependencies: task.GetDependencyIDs(),
		Success:      true,
		Message:      fmt.Sprintf("Dependency %s added successfully", value_objects.PyStr(request.DependencyID)),
	}, nil
}

// RemoveDependency mirrors ManageDependenciesUseCase.remove_dependency.
func (u *ManageDependenciesUseCase) RemoveDependency(ctx context.Context, taskID, dependencyID any) (*DependencyResponse, error) {
	taskIDObj, err := smallUCConvertTaskID(taskID)
	if err != nil {
		return nil, err
	}
	dependencyIDObj, err := smallUCConvertTaskID(dependencyID)
	if err != nil {
		return nil, err
	}

	task, err := u.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", value_objects.PyStr(taskID)))
	}

	if !task.HasDependency(dependencyIDObj) {
		return &DependencyResponse{
			TaskID:       value_objects.PyStr(taskID),
			Dependencies: task.GetDependencyIDs(),
			Success:      false,
			Message:      fmt.Sprintf("Dependency %s does not exist", value_objects.PyStr(dependencyID)),
		}, nil
	}

	if err := task.RemoveDependency(dependencyIDObj); err != nil {
		return nil, err
	}
	if _, err := u.taskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	return &DependencyResponse{
		TaskID:       value_objects.PyStr(taskID),
		Dependencies: task.GetDependencyIDs(),
		Success:      true,
		Message:      fmt.Sprintf("Dependency %s removed successfully", value_objects.PyStr(dependencyID)),
	}, nil
}

// GetDependencies mirrors ManageDependenciesUseCase.get_dependencies.
func (u *ManageDependenciesUseCase) GetDependencies(ctx context.Context, taskID any) (*entities.OrderedMap[any], error) {
	taskIDObj, err := smallUCConvertTaskID(taskID)
	if err != nil {
		return nil, err
	}
	task, err := u.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", value_objects.PyStr(taskID)))
	}

	dependencyDetails := []any{}
	for _, depID := range task.GetDependencyIDs() {
		depIDObj, err := smallUCConvertTaskID(depID)
		if err != nil {
			return nil, err
		}
		depTask, err := u.taskRepository.FindByIDAllStates(ctx, depIDObj)
		if err != nil {
			return nil, err
		}
		if depTask != nil {
			entry := entities.NewOrderedMap[any]()
			entry.Set("id", depID)
			entry.Set("title", depTask.Title)
			entry.Set("status", depTask.Status.String())
			entry.Set("priority", depTask.Priority.String())
			dependencyDetails = append(dependencyDetails, entry)
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("task_id", value_objects.PyStr(taskID))
	result.Set("dependency_ids", task.GetDependencyIDs())
	result.Set("dependencies", dependencyDetails)
	result.Set("can_start", task.CanBeStarted())
	return result, nil
}

// ClearDependencies mirrors ManageDependenciesUseCase.clear_dependencies.
func (u *ManageDependenciesUseCase) ClearDependencies(ctx context.Context, taskID any) (*DependencyResponse, error) {
	taskIDObj, err := smallUCConvertTaskID(taskID)
	if err != nil {
		return nil, err
	}
	task, err := u.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", value_objects.PyStr(taskID)))
	}

	dependencyCount := len(task.Dependencies)
	if err := task.ClearDependencies(); err != nil {
		return nil, err
	}
	if _, err := u.taskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	return &DependencyResponse{
		TaskID:       value_objects.PyStr(taskID),
		Dependencies: []string{},
		Success:      true,
		Message:      fmt.Sprintf("Cleared %d dependencies", dependencyCount),
	}, nil
}

// GetBlockingTasks mirrors ManageDependenciesUseCase.get_blocking_tasks.
func (u *ManageDependenciesUseCase) GetBlockingTasks(ctx context.Context, taskID any) (*entities.OrderedMap[any], error) {
	taskIDObj, err := smallUCConvertTaskID(taskID)
	if err != nil {
		return nil, err
	}
	task, err := u.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", value_objects.PyStr(taskID)))
	}

	allTasks, err := u.taskRepository.FindAll(ctx)
	if err != nil {
		return nil, err
	}
	blockingTasks := []any{}
	for _, otherTask := range allTasks {
		if otherTask.HasDependency(taskIDObj) {
			entry := entities.NewOrderedMap[any]()
			entry.Set("id", smallUCTaskIDStr(otherTask.ID))
			entry.Set("title", otherTask.Title)
			entry.Set("status", otherTask.Status.String())
			entry.Set("priority", otherTask.Priority.String())
			blockingTasks = append(blockingTasks, entry)
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("task_id", value_objects.PyStr(taskID))
	result.Set("blocking_tasks", blockingTasks)
	result.Set("blocking_count", len(blockingTasks))
	return result, nil
}
