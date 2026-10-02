package use_cases

import (
	"context"

	subtaskdto "agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// UpdateSubtaskUseCase ports update_subtask.UpdateSubtaskUseCase.
type UpdateSubtaskUseCase struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository

	// ProgressUpdater is optional (nil skips the parent progress update).
	ProgressUpdater ParentTaskProgressUpdater
}

// NewUpdateSubtaskUseCase builds the use case.
func NewUpdateSubtaskUseCase(taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository) *UpdateSubtaskUseCase {
	return &UpdateSubtaskUseCase{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// Execute ports execute(). Domain errors are returned as error values.
func (uc *UpdateSubtaskUseCase) Execute(ctx context.Context, request *subtaskdto.UpdateSubtaskRequest) (*subtaskdto.SubtaskResponse, error) {
	taskID, err := smallUCConvertTaskID(request.TaskID)
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

	var updatedSubtask *entities.OrderedMap[any]
	if uc.subtaskRepository != nil {
		subtask, err := uc.subtaskRepository.FindByID(ctx, value_objects.PyStr(request.ID))
		if err != nil {
			return nil, err
		}
		if subtask == nil {
			return nil, &value_objects.ValueError{Msg: "Subtask " + value_objects.PyStr(request.ID) + " not found in task " + value_objects.PyStr(request.TaskID)}
		}

		if request.Title != nil {
			if err := subtask.UpdateTitle(*request.Title); err != nil {
				return nil, err
			}
		}
		if request.Description != nil {
			if err := subtask.UpdateDescription(*request.Description); err != nil {
				return nil, err
			}
		}
		if request.Status != nil {
			switch *request.Status {
			case "done":
				if err := subtask.Complete(); err != nil {
					return nil, err
				}
			case "todo":
				if err := subtask.Reopen(); err != nil {
					return nil, err
				}
			default:
				statusObj, err := value_objects.TaskStatusFromString(*request.Status)
				if err != nil {
					return nil, err
				}
				if err := subtask.UpdateStatus(statusObj); err != nil {
					return nil, err
				}
			}
		}
		if request.Priority != nil {
			priorityObj, err := value_objects.PriorityFromString(*request.Priority)
			if err != nil {
				return nil, err
			}
			if err := subtask.UpdatePriority(priorityObj); err != nil {
				return nil, err
			}
		}
		if request.Assignees != nil {
			if err := subtask.UpdateAssignees(anySliceToStrings(request.Assignees)); err != nil {
				return nil, err
			}
		}
		if request.ProgressPercentage != nil {
			if err := subtask.UpdateProgressPercentage(*request.ProgressPercentage); err != nil {
				return nil, err
			}
		}
		if request.ProgressNotes != nil {
			if err := subtask.AppendProgress(*request.ProgressNotes); err != nil {
				return nil, err
			}
		}

		if _, err := uc.subtaskRepository.Save(ctx, subtask); err != nil {
			return nil, err
		}
		dict, err := subtask.ToDict(true)
		if err != nil {
			return nil, err
		}
		updatedSubtask = orderedSubtaskFromDict(dict, true)

		updateParentTaskProgressFromSubtasks(ctx, uc.ProgressUpdater, value_objects.PyStr(request.TaskID))
		uc.syncParentTaskContext(task)
	} else {
		// Fallback: Task.update_subtask is a stub that always returns False, so the
		// Python path always raises ValueError.
		return nil, &value_objects.ValueError{Msg: "Subtask " + value_objects.PyStr(request.ID) + " not found in task " + value_objects.PyStr(request.TaskID)}
	}

	return &subtaskdto.SubtaskResponse{
		TaskID:   value_objects.PyStr(request.TaskID),
		Subtask:  updatedSubtask,
		Progress: orderedProgressMap(task.GetSubtaskProgress()),
	}, nil
}

// syncParentTaskContext ports _sync_parent_task_context_after_subtask_update. The
// Python method lazily imports task_context_sync_service (not ported) and requires
// a project_id, but the Task entity has no project_id attribute, so it always
// raises and is swallowed by the surrounding try/except. The port is a no-op.
func (uc *UpdateSubtaskUseCase) syncParentTaskContext(parentTask *entities.Task) {
	_ = parentTask
}

func anySliceToStrings(in []any) []string {
	out := make([]string, 0, len(in))
	for _, v := range in {
		out = append(out, value_objects.PyStr(v))
	}
	return out
}
