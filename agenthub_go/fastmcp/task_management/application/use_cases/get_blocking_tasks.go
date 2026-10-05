package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// smallUCConvertTaskID mirrors the use cases' _convert_to_task_id: an int is
// converted with TaskId.from_int, anything else with TaskId.from_string(str(x)).
func smallUCConvertTaskID(taskID any) (value_objects.TaskId, error) {
	switch v := taskID.(type) {
	case int:
		return value_objects.TaskIdFromInt(v)
	case int8:
		return value_objects.TaskIdFromInt(int(v))
	case int16:
		return value_objects.TaskIdFromInt(int(v))
	case int32:
		return value_objects.TaskIdFromInt(int(v))
	case int64:
		return value_objects.TaskIdFromInt(int(v))
	default:
		return value_objects.NewTaskId(value_objects.PyStr(taskID))
	}
}

// smallUCTaskIDStr mirrors str(other_task.id) for a possibly nil TaskId.
func smallUCTaskIDStr(id *value_objects.TaskId) string {
	if id == nil {
		return "None"
	}
	return id.String()
}

// GetBlockingTasksUseCase ports get_blocking_tasks.GetBlockingTasksUseCase.
type GetBlockingTasksUseCase struct {
	taskRepository repositories.TaskRepository
}

// NewGetBlockingTasksUseCase mirrors __init__(task_repository).
func NewGetBlockingTasksUseCase(taskRepository repositories.TaskRepository) *GetBlockingTasksUseCase {
	return &GetBlockingTasksUseCase{taskRepository: taskRepository}
}

// Execute mirrors GetBlockingTasksUseCase.execute. It returns TaskNotFoundError
// when the task is missing, like the Python.
func (u *GetBlockingTasksUseCase) Execute(ctx context.Context, taskID any) (*entities.OrderedMap[any], error) {
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
