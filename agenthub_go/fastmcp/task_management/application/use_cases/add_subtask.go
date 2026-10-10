package use_cases

import (
	"context"
	"strings"
	"time"

	subtaskdto "agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ParentTaskProgressUpdater is the task-progress service surface used by the
// subtask use cases (satisfied by *services.TaskProgressService, wired at server
// composition because services imports this package). Calls are best-effort.
type ParentTaskProgressUpdater interface {
	UpdateTaskProgressFromSubtasks(ctx context.Context, taskID string) *float64
}

// AddSubtaskUseCase ports add_subtask.AddSubtaskUseCase.
type AddSubtaskUseCase struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository

	// ProgressUpdater is optional (nil skips the parent progress update).
	ProgressUpdater ParentTaskProgressUpdater
}

// NewAddSubtaskUseCase builds the use case.
func NewAddSubtaskUseCase(taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository) *AddSubtaskUseCase {
	return &AddSubtaskUseCase{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// Execute ports execute(). Errors are returned like the Python exceptions.
func (uc *AddSubtaskUseCase) Execute(ctx context.Context, request *subtaskdto.AddSubtaskRequest) (*subtaskdto.SubtaskResponse, error) {
	taskID, err := smallUCConvertTaskID(request.TaskID)
	if err != nil {
		return nil, err
	}

	task, err := uc.findTaskWithRetries(ctx, taskID, request.TaskID)
	if err != nil {
		return nil, err
	}

	agentInheritanceApplied := false
	inheritedAssignees := []string{}

	var addedSubtask *entities.OrderedMap[any]

	if uc.subtaskRepository != nil {
		subtaskID, err := uc.subtaskRepository.GetNextID(ctx, taskID)
		if err != nil {
			return nil, err
		}

		var priority *value_objects.Priority
		if request.Priority != nil {
			p, err := value_objects.PriorityFromString(*request.Priority)
			if err != nil {
				return nil, err
			}
			priority = &p
		}

		var status *value_objects.TaskStatus
		if request.Status != nil {
			st, err := value_objects.TaskStatusFromString(*request.Status)
			if err != nil {
				return nil, err
			}
			status = &st
		}

		progressPercentage := 0
		if request.ProgressPercentage != nil {
			progressPercentage = *request.ProgressPercentage
		}

		if progressPercentage >= 100 && status == nil {
			done, _ := value_objects.TaskStatusFromString("done")
			status = &done
		} else if progressPercentage > 0 && status == nil {
			inProgress, _ := value_objects.TaskStatusFromString("in_progress")
			status = &inProgress
		}

		subtask, err := entities.CreateSubtask(subtaskID, request.Title, request.Description, taskID, status, priority,
			entities.SubtaskOptions{Assignees: request.Assignees, ProgressPercentage: progressPercentage,
				AcceptanceCriteria: request.AcceptanceCriteria, Scope: request.Scope})
		if err != nil {
			return nil, err
		}

		if subtask.ShouldInheritAssignees() {
			parentAssignees := task.GetInheritedAssigneesForSubtasks()
			if len(parentAssignees) > 0 {
				if err := subtask.InheritAssigneesFromParent(parentAssignees); err != nil {
					return nil, err
				}
				agentInheritanceApplied = true
				inheritedAssignees = append([]string{}, parentAssignees...)
			}
		}

		if _, err := uc.subtaskRepository.Save(ctx, subtask); err != nil {
			return nil, err
		}
		subtaskDict, err := subtask.ToDict(true)
		if err != nil {
			return nil, err
		}
		addedSubtask = orderedSubtaskFromDict(subtaskDict, true)

		if err := uc.addSubtaskToParentWithRetries(ctx, task, taskID, subtask, request.TaskID); err != nil {
			return nil, err
		}

		updateParentTaskProgressFromSubtasks(ctx, uc.ProgressUpdater, taskID.Value)

		// task_created dispatch: TaskCreatedEvent.create does not exist in Python, so the
		// AttributeError is swallowed and no event is ever dispatched.
	} else {
		// Fallback: Python builds a dict and calls task.add_subtask(subtask), which
		// raises ValueError because the argument is not a string.
		return nil, &value_objects.ValueError{Msg: "Subtask ID must be a non-empty string"}
	}

	progress := task.GetSubtaskProgress()
	response := &subtaskdto.SubtaskResponse{
		TaskID:   value_objects.PyStr(request.TaskID),
		Subtask:  addedSubtask,
		Progress: orderedProgressMap(progress),
	}
	if agentInheritanceApplied {
		response.AgentInheritanceApplied = true
		response.InheritedAssignees = inheritedAssignees
	}
	return response, nil
}

// findTaskWithRetries mirrors the lookup retry loop (3 attempts, 10ms base delay).
func (uc *AddSubtaskUseCase) findTaskWithRetries(ctx context.Context, taskID value_objects.TaskId, rawTaskID any) (*entities.Task, error) {
	const maxRetries = 3
	const retryDelay = 0.01
	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		task, err := uc.taskRepository.FindByID(ctx, taskID)
		if err == nil {
			if task == nil {
				return nil, exceptions.NewTaskNotFoundError("Task " + value_objects.PyStr(rawTaskID) + " not found")
			}
			return task, nil
		}
		lastErr = err
		errorStr := value_objects.PyLower(err.Error())
		isRetryable := strings.Contains(errorStr, "interfaceerror") ||
			strings.Contains(errorStr, "bad parameter") ||
			strings.Contains(errorStr, "database is locked") ||
			strings.Contains(errorStr, "api misuse")
		if isRetryable && attempt < maxRetries-1 {
			time.Sleep(time.Duration(retryDelay * float64(int(1)<<attempt) * float64(time.Second)))
			continue
		}
		return nil, err
	}
	return nil, lastErr
}

// addSubtaskToParentWithRetries ports the parent save retry loop (5 attempts, 20ms base delay).
func (uc *AddSubtaskUseCase) addSubtaskToParentWithRetries(ctx context.Context, task *entities.Task, taskID value_objects.TaskId, subtask *entities.Subtask, rawTaskID any) error {
	const maxSaveRetries = 5
	const saveRetryDelay = 0.02
	for saveAttempt := 0; saveAttempt < maxSaveRetries; saveAttempt++ {
		_, addErr := task.AddSubtask(subtask.ID.String())
		if addErr == nil {
			_, addErr = uc.taskRepository.Save(ctx, task)
		}
		if addErr == nil {
			return nil
		}

		errorStr := value_objects.PyLower(addErr.Error())
		isConcurrentConflict := strings.Contains(errorStr, "expected to update") ||
			strings.Contains(errorStr, "stale") ||
			strings.Contains(errorStr, "concurrent") ||
			strings.Contains(errorStr, "could not refresh") ||
			strings.Contains(errorStr, "detached")
		if isConcurrentConflict && saveAttempt < maxSaveRetries-1 {
			time.Sleep(time.Duration(saveRetryDelay * float64(int(1)<<saveAttempt) * float64(time.Second)))
			fresh, err := uc.taskRepository.FindByID(ctx, taskID)
			if err != nil {
				return err
			}
			if fresh == nil {
				return exceptions.NewTaskNotFoundError("Task " + value_objects.PyStr(rawTaskID) + " not found during retry")
			}
			// The subtask is already persisted; only the parent list is re-applied.
			task = fresh
			continue
		}
		return addErr
	}
	return nil
}

// updateParentTaskProgressFromSubtasks is the shared best-effort helper.
func updateParentTaskProgressFromSubtasks(ctx context.Context, updater ParentTaskProgressUpdater, taskID string) {
	if updater == nil {
		return
	}
	updater.UpdateTaskProgressFromSubtasks(ctx, taskID)
}
