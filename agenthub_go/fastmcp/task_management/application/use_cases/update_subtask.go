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

	// ledger is where a note this update carries is RECORDED. A subtask note belongs to the PARENT
	// TASK's ledger - task_events.task_id has an FK to tasks.id - and subtask_id is the only thing
	// that says which subtask wrote it, which is also how the carry step writes the notes it moves out
	// of the dropped columns. Unset leaves the update as it was for every caller that passes no note,
	// and makes a note fail loudly rather than be dropped (StatusLedger.SaveProgress's contract).
	ledger StatusLedger
}

// NewUpdateSubtaskUseCase builds the use case.
func NewUpdateSubtaskUseCase(taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository) *UpdateSubtaskUseCase {
	return &UpdateSubtaskUseCase{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// WithLedger attaches the task-event ledger seam, wired by the composition root.
func (uc *UpdateSubtaskUseCase) WithLedger(l StatusLedger) *UpdateSubtaskUseCase {
	uc.ledger = l
	return uc
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
		if request.AcceptanceCriteria != nil {
			subtask.AcceptanceCriteria = append([]string{}, request.AcceptanceCriteria...)
		}
		if request.Scope != nil {
			subtask.Scope = append([]string{}, request.Scope...)
		}

		// The note this update carries is MANDATORY on the manage_subtask update path (the handler
		// refuses an update without one), and its home moved to the ledger with O1c: a subtask has no
		// progress column left to hold it. The note belongs to the PARENT task's ledger with subtask_id
		// naming the writer, and its number is the task's sequence - shared with the task's own notes,
		// because the carry step's collision check is per (task, progress_number). The ledger assigns
		// that number while it writes, inside this save's transaction.
		var progressNotes []LedgerProgress
		if text := progressNoteText(request.ProgressNotes); text != "" {
			if err := subtask.Touch("progress_update"); err != nil {
				return nil, err
			}
			timestamp := ""
			if subtask.UpdatedAt != nil {
				timestamp = value_objects.IsoFormat(*subtask.UpdatedAt)
			}
			progressNotes = append(progressNotes, LedgerProgress{
				SubtaskID: value_objects.PyStr(request.ID),
				Content:   text,
				Timestamp: timestamp,
			})
		}

		// The subtask and its note commit together or not at all: task_events.task_id has an FK to the
		// parent task, and an entry written outside this transaction could commit beside a save that
		// rolled back. With a note present and no ledger wired this FAILS rather than saving the
		// subtask and dropping the note - the silent drop is the defect this replaces.
		save := func(ctx context.Context) error {
			_, err := uc.subtaskRepository.Save(ctx, subtask)
			return err
		}
		var saveErr error
		if len(progressNotes) > 0 {
			saveErr = uc.ledger.SaveProgress(ctx, save, value_objects.PyStr(request.TaskID), progressNotes)
		} else {
			saveErr = save(ctx)
		}
		if saveErr != nil {
			return nil, saveErr
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
// Python method lazily imports task_context_sync_service (ported in
// application/services/task_context_sync_service.go) and requires
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

// progressNoteText is the note a request carries, trimmed. Empty means it brought none, and a
// whitespace-only note is nothing to record rather than a note the ledger should hold.
func progressNoteText(in *string) string {
	if in == nil {
		return ""
	}
	return value_objects.PyStrip(*in)
}
