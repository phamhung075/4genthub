// Package use_cases ports task_management/application/use_cases/update_task.py.
package use_cases

import (
	"context"
	"fmt"
	"strconv"

	task "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// UpdateTaskUseCase ports UpdateTaskUseCase.
//
// The task_updated domain event is not dispatched: Python calls the non-existent
// TaskUpdatedEvent.create, so its try/except only ever logged a warning. The context
// metadata sync and the WebSocket notification run through the injected hooks.
type UpdateTaskUseCase struct {
	taskRepository      repositories.TaskRepository
	gitBranchRepository task.GitBranchGetter
	hooks               TaskEventHooks
}

// WithHooks sets the side-effect hooks (nil disables them).
func (u *UpdateTaskUseCase) WithHooks(h TaskEventHooks) *UpdateTaskUseCase {
	u.hooks = h
	return u
}

// NewUpdateTaskUseCase builds the use case. gitBranchRepository may be nil.
func NewUpdateTaskUseCase(taskRepository repositories.TaskRepository, gitBranchRepository task.GitBranchGetter) *UpdateTaskUseCase {
	return &UpdateTaskUseCase{taskRepository: taskRepository, gitBranchRepository: gitBranchRepository}
}

// Execute mirrors execute(). It has no try/except in Python, so every error
// (including TaskNotFoundError) propagates to the caller.
func (u *UpdateTaskUseCase) Execute(ctx context.Context, request task.UpdateTaskRequest) (*task.UpdateTaskResponse, error) {
	domainTaskID, err := updateTaskConvertToTaskID(request.TaskID)
	if err != nil {
		return nil, err
	}

	taskEntity, err := u.taskRepository.FindByID(ctx, domainTaskID)
	if err != nil {
		return nil, err
	}
	if taskEntity == nil {
		return nil, exceptions.NewTaskNotFoundError(
			fmt.Sprintf("Task %s not found", updateTaskString(request.TaskID)))
	}

	if request.Title != nil {
		if err := taskEntity.UpdateTitle(*request.Title); err != nil {
			return nil, err
		}
	}

	if request.Description != nil {
		if err := taskEntity.UpdateDescription(*request.Description); err != nil {
			return nil, err
		}
	}

	if request.Status != nil {
		newStatus, err := value_objects.NewTaskStatus(*request.Status)
		if err != nil {
			return nil, err
		}
		// Only update status if it's actually changing.
		if taskEntity.Status.Value != newStatus.Value {
			if err := taskEntity.UpdateStatus(newStatus); err != nil {
				return nil, err
			}
		}
	}

	if request.Priority != nil {
		newPriority, err := value_objects.NewPriority(*request.Priority)
		if err != nil {
			return nil, err
		}
		// Only update priority if it's actually changing.
		if taskEntity.Priority.Value != newPriority.Value {
			if err := taskEntity.UpdatePriority(newPriority); err != nil {
				return nil, err
			}
		}
	}

	if request.Details != nil {
		if err := taskEntity.AppendProgress(*request.Details); err != nil {
			return nil, err
		}
	}

	if request.EstimatedEffort != nil {
		if err := taskEntity.UpdateEstimatedEffort(*request.EstimatedEffort); err != nil {
			return nil, err
		}
	}

	if request.Assignees != nil {
		if err := taskEntity.UpdateAssignees(request.Assignees); err != nil {
			return nil, err
		}
	}

	if request.Labels != nil {
		if err := taskEntity.UpdateLabels(request.Labels); err != nil {
			return nil, err
		}
	}

	if request.DueDate != nil {
		if err := taskEntity.UpdateDueDate(request.DueDate); err != nil {
			return nil, err
		}
	}

	if request.ProgressPercentage != nil {
		if err := taskEntity.SetProgressPercentage(*request.ProgressPercentage); err != nil {
			return nil, err
		}
	}

	// IMPORTANT: Set context_id LAST, after all other updates that might clear it.
	if request.ContextID != nil {
		if err := taskEntity.SetContextID(*request.ContextID); err != nil {
			return nil, err
		}
	}

	// Save the updated task; Python ignores the return value but not exceptions.
	if _, err := u.taskRepository.Save(ctx, taskEntity); err != nil {
		return nil, err
	}

	// Auto-sync task context after update (best effort; the update never fails on it).
	taskIDStr := ""
	if taskEntity.ID != nil {
		taskIDStr = taskEntity.ID.Value
	}
	if u.hooks != nil {
		_ = u.hooks.SyncTaskMetadata(ctx, taskIDStr, taskEntity, "")
	}

	taskResponse, err := task.TaskResponseFromDomain(ctx, taskEntity, u.gitBranchRepository, nil, nil, nil, nil)
	if err != nil {
		return nil, err
	}

	// WebSocket notification for frontend real-time updates.
	if u.hooks != nil {
		gitBranchID := ""
		if taskEntity.GitBranchID != nil {
			gitBranchID = *taskEntity.GitBranchID
		}
		u.hooks.NotifyTaskEvent(ctx, "updated", taskEntity, taskResponse, nil, gitBranchID)
	}

	// Handle domain events (Python consumes them here even though it does nothing).
	_ = taskEntity.GetEvents()

	return task.NewUpdateTaskResponseSuccess(taskResponse, nil), nil
}

// updateTaskConvertToTaskID mirrors _convert_to_task_id.
func updateTaskConvertToTaskID(taskID any) (value_objects.TaskId, error) {
	if id, ok := taskID.(value_objects.TaskId); ok {
		return id, nil
	}
	// Always convert to string and use the constructor (TaskId.from_string(str(task_id))).
	return value_objects.NewTaskId(updateTaskString(taskID))
}

// updateTaskString mirrors Python str(task_id) for the values that reach
// messages: TaskId, str and int.
func updateTaskString(v any) string {
	switch x := v.(type) {
	case value_objects.TaskId:
		return x.Value
	case string:
		return x
	case int:
		return strconv.Itoa(x)
	case int64:
		return strconv.FormatInt(x, 10)
	}
	return value_objects.PyStr(v)
}
