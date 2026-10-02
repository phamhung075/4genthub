package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GetDependenciesUseCase ports get_dependencies.GetDependenciesUseCase.
type GetDependenciesUseCase struct {
	taskRepository repositories.TaskRepository
}

// NewGetDependenciesUseCase builds the use case.
func NewGetDependenciesUseCase(taskRepository repositories.TaskRepository) *GetDependenciesUseCase {
	return &GetDependenciesUseCase{taskRepository: taskRepository}
}

// Execute returns the dependency details for a task.
func (uc *GetDependenciesUseCase) Execute(ctx context.Context, taskID any) (*entities.OrderedMap[any], error) {
	taskIDObj, err := useCaseTaskID(taskID)
	if err != nil {
		return nil, err
	}
	task, err := uc.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", value_objects.PyStr(taskID)))
	}

	dependencyDetails := []any{}
	dependencyIDs := task.GetDependencyIDs()
	for _, depID := range dependencyIDs {
		depTaskID, err := useCaseTaskID(depID)
		if err != nil {
			return nil, err
		}
		depTask, err := uc.taskRepository.FindByID(ctx, depTaskID)
		if err != nil {
			return nil, err
		}
		if depTask == nil {
			continue
		}
		detail := entities.NewOrderedMap[any]()
		detail.Set("id", depID)
		detail.Set("title", depTask.Title)
		detail.Set("status", depTask.Status.String())
		detail.Set("priority", depTask.Priority.String())
		dependencyDetails = append(dependencyDetails, detail)
	}

	out := entities.NewOrderedMap[any]()
	out.Set("task_id", value_objects.PyStr(taskID))
	out.Set("dependency_ids", dependencyIDs)
	out.Set("dependencies", dependencyDetails)
	out.Set("can_start", task.CanBeStarted())
	return out, nil
}

// useCaseTaskID mirrors the Python _convert_to_task_id helper: an int becomes
// TaskId.from_int, everything else is str()'d and parsed.
func useCaseTaskID(taskID any) (value_objects.TaskId, error) {
	if i, ok := taskID.(int); ok {
		return value_objects.TaskIdFromInt(i)
	}
	return value_objects.NewTaskId(value_objects.PyStr(taskID))
}
