package use_cases

import (
	"context"
	"math"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// completeSubtaskAtomicIncrementer is the optional TaskRepository surface used by
// CompleteSubtaskUseCase. The Python TaskRepository declares
// atomic_increment_completed_subtasks(task_id); repositories.TaskRepository does
// not, so the concrete repository is type-asserted here. A repository that does
// not implement it reproduces the Python AttributeError path (non-retryable).
type completeSubtaskAtomicIncrementer interface {
	AtomicIncrementCompletedSubtasks(ctx context.Context, taskID string) (bool, error)
}

// CompleteSubtaskUseCase ports complete_subtask.CompleteSubtaskUseCase.
type CompleteSubtaskUseCase struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository // nil mirrors the Python default None

	// ledger is where the note a completion carries is RECORDED, in the same transaction as the
	// subtask's save. A note this path accepts and never writes is a silent drop - the same defect the
	// update half of the tool had - and a subtask's note belongs to the PARENT TASK's ledger
	// (task_events.task_id has an FK to tasks.id) with subtask_id naming the writer. Unset leaves a
	// completion that carries no note exactly as it was, and makes one that does carry a note fail
	// loudly rather than be dropped (StatusLedger.SaveProgress's contract).
	ledger StatusLedger
}

// NewCompleteSubtaskUseCase mirrors __init__(task_repository, subtask_repository=None).
func NewCompleteSubtaskUseCase(taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository) *CompleteSubtaskUseCase {
	return &CompleteSubtaskUseCase{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// WithLedger attaches the task-event ledger seam, wired by the composition root.
func (uc *CompleteSubtaskUseCase) WithLedger(l StatusLedger) *CompleteSubtaskUseCase {
	uc.ledger = l
	return uc
}

// Execute ports execute(). userID is accepted but unused by the Python body. progressNotes is the
// note the completion carries, and it is REQUIRED on the tool path that reaches here.
func (uc *CompleteSubtaskUseCase) Execute(ctx context.Context, taskID any, id any, userID *string, completionSummary *string, insightsFound []any, testingNotes *string, progressNotes *string) (*entities.OrderedMap[any], error) {
	taskIDObj, err := completeSubtaskConvertToTaskID(taskID)
	if err != nil {
		return nil, err
	}

	// Retry task lookup on concurrent access conflicts.
	const maxRetries = 3
	const retryDelay = 0.01
	var task *entities.Task
	for attempt := 0; attempt < maxRetries; attempt++ {
		task, err = uc.taskRepository.FindByID(ctx, taskIDObj)
		if err == nil && task != nil {
			break
		}
		if err == nil {
			err = exceptions.NewTaskNotFoundError("Task " + value_objects.PyStr(taskID) + " not found")
		}
		errorStr := value_objects.PyLower(err.Error())
		isRetryable := strings.Contains(errorStr, "interfaceerror") ||
			strings.Contains(errorStr, "bad parameter") ||
			strings.Contains(errorStr, "database is locked") ||
			strings.Contains(errorStr, "api misuse")
		if isRetryable && attempt < maxRetries-1 {
			delay := retryDelay * math.Pow(2, float64(attempt))
			time.Sleep(time.Duration(delay * float64(time.Second)))
			continue
		}
		return nil, err
	}

	var success bool
	if uc.subtaskRepository != nil {
		subtask, err := uc.subtaskRepository.FindByID(ctx, value_objects.PyStr(id))
		if err != nil {
			return nil, err
		}
		if subtask == nil {
			return nil, value_objects.ValueErrorf("Subtask %s not found in task %s", value_objects.PyStr(id), value_objects.PyStr(taskID))
		}

		if err := subtask.Complete(); err != nil {
			return nil, err
		}

		// The note this completion carries is MANDATORY on the tool path (the handler refuses a
		// complete without one) and its home is the ledger: O1c dropped the progress columns, so there
		// is no column left to hold it. It belongs to the PARENT task's ledger with subtask_id naming
		// the writer, and its number is the task's sequence, assigned by the ledger while it writes,
		// inside this save's transaction.
		var noteEntries []LedgerProgress
		if text := progressNoteText(progressNotes); text != "" {
			timestamp := ""
			if subtask.UpdatedAt != nil {
				timestamp = value_objects.IsoFormat(*subtask.UpdatedAt)
			}
			noteEntries = append(noteEntries, LedgerProgress{
				SubtaskID: value_objects.PyStr(id),
				Content:   text,
				Timestamp: timestamp,
			})
		}

		// The completion and its note commit together or not at all: task_events.task_id has an FK to
		// the parent task, and an entry written outside this transaction could commit beside a save
		// that rolled back. With a note present and no ledger wired this FAILS rather than completing
		// the subtask and dropping the note - the silent drop is the defect this replaces.
		save := func(ctx context.Context) error {
			_, err := uc.subtaskRepository.Save(ctx, subtask)
			return err
		}
		var saveErr error
		if len(noteEntries) > 0 {
			saveErr = uc.ledger.SaveProgress(ctx, save, value_objects.PyStr(taskID), noteEntries)
		} else {
			saveErr = save(ctx)
		}
		if saveErr != nil {
			return nil, saveErr
		}
		success = true

		if err := uc.completeSubtaskIncrementCompletedSubtasks(ctx, taskID); err != nil {
			return nil, err
		}

		// task_status_changed dispatch: TaskStatusChangedEvent.create does not exist in
		// Python, so the AttributeError is swallowed and no event is ever dispatched.
	} else {
		// Fallback to the existing task entity method (a no-op in the Go domain).
		success = task.CompleteSubtask(value_objects.PyStr(id))
		if success {
			if _, err := uc.taskRepository.Save(ctx, task); err != nil {
				return nil, err
			}
		}
	}

	// Reload task to get the updated completed_subtasks count and calculate progress.
	task, err = uc.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError("Task " + value_objects.PyStr(taskID) + " not found after atomic increment")
	}

	totalSubtasks := len(task.Subtasks)
	completedSubtasks := task.CompletedSubtasks

	// Empty total is the Python int 0; otherwise float division.
	var progressPercentage any = 0
	if totalSubtasks > 0 {
		progressPercentage = float64(completedSubtasks) / float64(totalSubtasks) * 100
	}

	parentProgress := entities.NewOrderedMap[any]()
	parentProgress.Set("total", totalSubtasks)
	parentProgress.Set("completed", completedSubtasks)
	parentProgress.Set("percentage", progressPercentage)

	// Trigger parent task progress update (Python swallows every failure).
	uc.completeSubtaskUpdateParentTaskProgress(ctx, task, parentProgress)

	// Add insights and completion details to the parent task context if provided.
	uc.completeSubtaskUpdateParentTaskContext(task, completionSummary, insightsFound, testingNotes)

	result := entities.NewOrderedMap[any]()
	result.Set("success", success)
	result.Set("task_id", value_objects.PyStr(taskID))
	result.Set("subtask_id", value_objects.PyStr(id))
	result.Set("progress", parentProgress)
	result.Set("parent_progress", parentProgress)
	return result, nil
}

// completeSubtaskIncrementCompletedSubtasks ports the 5-attempt atomic increment
// retry loop (20ms base delay). The incrementer surface is asserted once; a
// repository without it fails immediately (non-retryable), like the Python
// AttributeError.
func (uc *CompleteSubtaskUseCase) completeSubtaskIncrementCompletedSubtasks(ctx context.Context, taskID any) error {
	incrementer, ok := uc.taskRepository.(completeSubtaskAtomicIncrementer)
	if !ok {
		return &value_objects.ValueError{Msg: "task repository does not implement atomic_increment_completed_subtasks"}
	}

	const maxSaveRetries = 5
	const saveRetryDelay = 0.02
	for saveAttempt := 0; saveAttempt < maxSaveRetries; saveAttempt++ {
		incrementSuccess, err := incrementer.AtomicIncrementCompletedSubtasks(ctx, value_objects.PyStr(taskID))
		if err == nil && !incrementSuccess {
			err = exceptions.NewTaskNotFoundError("Task " + value_objects.PyStr(taskID) + " not found for counter increment")
		}
		if err == nil {
			return nil
		}

		errorStr := value_objects.PyLower(err.Error())
		isConcurrentConflict := strings.Contains(errorStr, "database is locked") ||
			strings.Contains(errorStr, "concurrent") ||
			strings.Contains(errorStr, "locked")
		if isConcurrentConflict && saveAttempt < maxSaveRetries-1 {
			delay := saveRetryDelay * math.Pow(2, float64(saveAttempt))
			time.Sleep(time.Duration(delay * float64(time.Second)))
			continue
		}
		return err
	}
	return nil
}

// completeSubtaskUpdateParentTaskProgress ports _update_parent_task_progress.
// Every failure is swallowed (Python logs it).
func (uc *CompleteSubtaskUseCase) completeSubtaskUpdateParentTaskProgress(ctx context.Context, task *entities.Task, progress any) {
	progressValue := progress
	switch p := progress.(type) {
	case *entities.OrderedMap[any]:
		progressValue, _ = p.Get("percentage")
	case value_objects.OrderedAny:
		progressValue = p.GetAny("percentage")
	case map[string]any:
		progressValue = p["percentage"]
	}

	if len(task.Subtasks) > 0 {
		progressInt := completeSubtaskIntValue(progressValue)
		if err := task.SetProgressPercentage(progressInt); err != nil {
			return
		}
		_, _ = uc.taskRepository.Save(ctx, task)
	}
}

// completeSubtaskUpdateParentTaskContext ports _update_parent_task_context.
//
// Python mutates the dynamic task.context_data attribute. The Go *entities.Task
// has no context_data or Metadata field and this worker may only add files, so
// the mutation target does not exist; the guard is kept and the update is a
// no-op (see the worker report).
func (uc *CompleteSubtaskUseCase) completeSubtaskUpdateParentTaskContext(task *entities.Task, completionSummary *string, insightsFound []any, testingNotes *string) {
	hasSummary := completionSummary != nil && *completionSummary != ""
	hasInsights := len(insightsFound) > 0
	hasNotes := testingNotes != nil && *testingNotes != ""
	if !hasSummary && !hasInsights && !hasNotes {
		return
	}
}

// completeSubtaskIntValue is Python int(progress_value) for number-like values.
func completeSubtaskIntValue(v any) int {
	if f, ok := value_objects.PyFloat(v); ok {
		return int(f)
	}
	return 0
}

// completeSubtaskConvertToTaskID mirrors _convert_to_task_id.
func completeSubtaskConvertToTaskID(taskID any) (value_objects.TaskId, error) {
	switch x := taskID.(type) {
	case value_objects.TaskId:
		return x, nil
	case int:
		return value_objects.TaskIdFromInt(x)
	case int64:
		return value_objects.TaskIdFromInt(int(x))
	default:
		return value_objects.NewTaskId(value_objects.PyStr(taskID))
	}
}
