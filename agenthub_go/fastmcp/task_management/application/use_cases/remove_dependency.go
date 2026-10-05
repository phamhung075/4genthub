package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RemoveDependencyUseCase ports remove_dependency.RemoveDependencyUseCase. The
// Python module imports the dtos.dependency.DependencyResponse (no `dependencies`
// field) but builds manage_dependencies.DependencyResponse; the port reuses that
// shape (see report).
type RemoveDependencyUseCase struct {
	taskRepository repositories.TaskRepository
}

// NewRemoveDependencyUseCase builds the use case.
func NewRemoveDependencyUseCase(taskRepository repositories.TaskRepository) *RemoveDependencyUseCase {
	return &RemoveDependencyUseCase{taskRepository: taskRepository}
}

// Execute ports execute().
func (uc *RemoveDependencyUseCase) Execute(ctx context.Context, taskID, dependencyID any) (*DependencyResponse, error) {
	taskIDObj, err := smallUCConvertTaskID(taskID)
	if err != nil {
		return nil, err
	}
	dependencyIDObj, err := smallUCConvertTaskID(dependencyID)
	if err != nil {
		return nil, err
	}
	task, err := uc.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError("Task " + value_objects.PyStr(taskID) + " not found")
	}
	if !task.HasDependency(dependencyIDObj) {
		return &DependencyResponse{
			TaskID:       value_objects.PyStr(taskID),
			Dependencies: task.GetDependencyIDs(),
			Success:      false,
			Message:      "Dependency " + value_objects.PyStr(dependencyID) + " does not exist",
		}, nil
	}
	if err := task.RemoveDependency(dependencyIDObj); err != nil {
		return nil, err
	}
	if _, err := uc.taskRepository.Save(ctx, task); err != nil {
		return nil, err
	}
	return &DependencyResponse{
		TaskID:       value_objects.PyStr(taskID),
		Dependencies: task.GetDependencyIDs(),
		Success:      true,
		Message:      "Dependency " + value_objects.PyStr(dependencyID) + " removed successfully",
	}, nil
}
