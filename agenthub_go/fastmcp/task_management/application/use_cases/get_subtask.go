package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GetSubtaskUseCase ports get_subtask.GetSubtaskUseCase.
type GetSubtaskUseCase struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository
}

// NewGetSubtaskUseCase builds the use case.
func NewGetSubtaskUseCase(taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository) *GetSubtaskUseCase {
	return &GetSubtaskUseCase{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// Execute ports execute(): returns the same task_id/subtask/progress dict shape.
func (uc *GetSubtaskUseCase) Execute(ctx context.Context, taskID any, id any) (*entities.OrderedMap[any], error) {
	taskIDObj, err := smallUCConvertTaskID(taskID)
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

	var subtaskValue any
	if uc.subtaskRepository != nil {
		subtask, err := uc.subtaskRepository.FindByID(ctx, value_objects.PyStr(id))
		if err != nil {
			return nil, err
		}
		if subtask == nil {
			return nil, &value_objects.ValueError{Msg: "Subtask " + value_objects.PyStr(id) + " not found in task " + value_objects.PyStr(taskID)}
		}
		dict, err := subtask.ToDict(true)
		if err != nil {
			return nil, err
		}
		subtaskValue = orderedSubtaskFromDict(dict, true)
	} else {
		// Fallback keeps the Python entity method's plain string result.
		found := task.GetSubtask(value_objects.PyStr(id))
		if found == nil {
			return nil, &value_objects.ValueError{Msg: "Subtask " + value_objects.PyStr(id) + " not found in task " + value_objects.PyStr(taskID)}
		}
		subtaskValue = *found
	}

	result := entities.NewOrderedMap[any]()
	result.Set("task_id", value_objects.PyStr(taskID))
	result.Set("subtask", subtaskValue)
	result.Set("progress", orderedProgressMap(task.GetSubtaskProgress()))
	return result, nil
}
