package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GetSubtasksUseCase ports get_subtasks.GetSubtasksUseCase.
type GetSubtasksUseCase struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository // may be nil (Python default None)
}

// NewGetSubtasksUseCase builds the use case; subtaskRepository may be nil.
func NewGetSubtasksUseCase(taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository) *GetSubtasksUseCase {
	return &GetSubtasksUseCase{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// Execute returns the subtasks and progress for a task.
func (uc *GetSubtasksUseCase) Execute(ctx context.Context, taskID any) (*entities.OrderedMap[any], error) {
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

	var subtasksData []any
	var progress any

	if uc.subtaskRepository != nil {
		subtasks, err := uc.subtaskRepository.FindByParentTaskID(ctx, taskIDObj)
		if err != nil {
			return nil, err
		}
		subtasksData = []any{}
		completed := 0
		for _, subtask := range subtasks {
			dict, err := subtask.ToDict(true)
			if err != nil {
				return nil, err
			}
			subtasksData = append(subtasksData, dict)
			if subtask.IsCompleted() {
				completed++
			}
		}
		total := len(subtasks)
		var percentage any = 0
		if total > 0 {
			percentage = float64(completed) / float64(total) * 100
		}
		p := entities.NewOrderedMap[any]()
		p.Set("total", total)
		p.Set("completed", completed)
		p.Set("percentage", percentage)
		progress = p
	} else {
		// Fallback: task.subtasks holds IDs (list[str]); the Python isinstance(subtask,
		// dict) check is always false for that shape, so the list stays empty.
		task.CleanSubtaskAssignees()
		subtasksData = []any{}
		progress = task.GetSubtaskProgress()
	}

	out := entities.NewOrderedMap[any]()
	out.Set("task_id", value_objects.PyStr(taskID))
	out.Set("subtasks", subtasksData)
	out.Set("progress", progress)
	return out, nil
}
