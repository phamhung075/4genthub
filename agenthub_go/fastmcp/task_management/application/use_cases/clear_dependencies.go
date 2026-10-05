package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/application/dtos/dependency"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ClearDependenciesUseCase ports clear_dependencies.ClearDependenciesUseCase.
type ClearDependenciesUseCase struct {
	taskRepository repositories.TaskRepository
}

// NewClearDependenciesUseCase builds the use case.
func NewClearDependenciesUseCase(taskRepository repositories.TaskRepository) *ClearDependenciesUseCase {
	return &ClearDependenciesUseCase{taskRepository: taskRepository}
}

// Execute ports execute(). Python builds DependencyResponse(..., dependencies=[]),
// but dtos.dependency.DependencyResponse has no `dependencies` field, so after the
// dependencies are cleared and saved the call raises TypeError. Reproduced faithfully.
func (uc *ClearDependenciesUseCase) Execute(ctx context.Context, taskID any) (*dependency.DependencyResponse, error) {
	taskIDObj, err := convertToTaskID(taskID)
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

	if err := task.ClearDependencies(); err != nil {
		return nil, err
	}
	if _, err := uc.taskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	return nil, value_objects.TypeErrorf(
		"DependencyResponse.__init__() got an unexpected keyword argument 'dependencies'")
}
