package use_cases

import (
	"context"
	"errors"
	"sort"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RemoveSubtaskUseCase ports remove_subtask.RemoveSubtaskUseCase.
type RemoveSubtaskUseCase struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository
	// ProgressUpdater is optional (nil skips the parent progress update).
	ProgressUpdater ParentTaskProgressUpdater
}

// NewRemoveSubtaskUseCase builds the use case.
func NewRemoveSubtaskUseCase(taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository) *RemoveSubtaskUseCase {
	return &RemoveSubtaskUseCase{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// Execute removes a subtask and updates the parent task counters.
func (uc *RemoveSubtaskUseCase) Execute(ctx context.Context, taskID any, subtaskID any,
	userID *string) (*entities.OrderedMap[any], error) {

	idStr := value_objects.PyStr(subtaskID)
	subtask, err := uc.subtaskRepository.FindByID(ctx, idStr)
	if err != nil {
		return nil, err
	}
	if subtask == nil {
		return nil, value_objects.ValueErrorf("Subtask %s not found in task %s", idStr, value_objects.PyStr(taskID))
	}

	taskIDObj, err := useCaseTaskID(taskID)
	if err != nil {
		return nil, err
	}
	parentTaskObj, err := uc.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}

	isSubtaskCompleted := subtask.IsCompleted()
	subtaskTitle := subtask.Title

	success, err := uc.subtaskRepository.RemoveSubtask(ctx, value_objects.PyStr(taskID), idStr)
	if err != nil {
		return nil, err
	}

	if success {
		if parentTaskObj == nil {
			return nil, errors.New("'NoneType' object has no attribute 'remove_subtask'")
		}
		if _, err := parentTaskObj.RemoveSubtask(idStr); err != nil {
			return nil, err
		}
		if isSubtaskCompleted {
			if err := parentTaskObj.DecrementCompletedSubtasks(); err != nil {
				return nil, err
			}
		}
		if _, err := uc.taskRepository.Save(ctx, parentTaskObj); err != nil {
			return nil, err
		}
		updateParentTaskProgressFromSubtasks(ctx, uc.ProgressUpdater, value_objects.PyStr(taskID))
	}

	progress := entities.NewOrderedMap[any]()
	if success {
		p, err := uc.subtaskRepository.GetSubtaskProgress(ctx, taskIDObj)
		if err != nil {
			progress.Set("total_subtasks", 0)
			progress.Set("completed_subtasks", 0)
			progress.Set("completion_percentage", 0)
		} else {
			progress = useCaseOrderedFromMap(p, []string{
				"total_subtasks", "completed_subtasks", "in_progress_subtasks", "blocked_subtasks",
				"pending_subtasks", "completion_percentage", "average_progress", "has_blockers",
			})
		}
	}

	subtaskMap := entities.NewOrderedMap[any]()
	subtaskMap.Set("id", idStr)
	subtaskMap.Set("title", subtaskTitle)

	out := entities.NewOrderedMap[any]()
	out.Set("success", success)
	out.Set("subtask", subtaskMap)
	out.Set("progress", progress)
	return out, nil
}

// useCaseOrderedFromMap converts a map to an OrderedMap preferring the given key
// order (Python dict insertion order) and then appending any remaining keys sorted.
func useCaseOrderedFromMap(m map[string]any, preferred []string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	seen := map[string]bool{}
	for _, k := range preferred {
		if v, ok := m[k]; ok {
			out.Set(k, v)
			seen[k] = true
		}
	}
	for _, k := range useCaseSortedKeys(m) {
		if !seen[k] {
			out.Set(k, m[k])
		}
	}
	return out
}

// useCaseSortedKeys returns the sorted keys of a map (matches Go's map
// serialization fallback for Python dicts whose order is unknown).
func useCaseSortedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
