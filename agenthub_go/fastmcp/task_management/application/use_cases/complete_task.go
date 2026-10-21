// Port of task_management/application/use_cases/complete_task.py.
package use_cases

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// completeTaskContextFacade is the subset of the UnifiedContextFacade
// used by the completion flow. Data payloads are OrderedMaps because the Python
// dicts they mirror have observable insertion order.
type completeTaskContextFacade interface {
	CreateContext(level, contextID string, data *entities.OrderedMap[any]) map[string]any
	GetContext(level, contextID string) map[string]any
	UpdateContext(level, contextID string, data *entities.OrderedMap[any], propagateChanges bool)
}

// completeTaskContextFacadeFactory builds a context facade scoped to a
// branch/project; it stands in for the UnifiedContextFacadeFactory.
type completeTaskContextFacadeFactory interface {
	CreateFacade(gitBranchID *string, projectID *string) completeTaskContextFacade
}

// CompleteTaskHooks is the TaskContextSyncService part of the completion flow
// (the service imports this package, so it is injected).
//
// TaskEventHooks IS EMBEDDED because a completion must BROADCAST, and this interface did not declare
// the capability the object handed to it already has: task_wiring.go passes one object to CreateTask,
// UpdateTask and CompleteTask alike, and create_task.go/update_task.go call NotifyTaskEvent on it
// while the completion path could not - the compiler proved the call impossible here, which is why a
// completed task neither animated nor refreshed the client while a created or updated one did.
// MIGRATION.md records the hooks pattern as "Done: create_task" with complete_task among the TODOs.
type CompleteTaskHooks interface {
	TaskEventHooks
	SyncTaskMetadata(ctx context.Context, taskID string, task *entities.Task, userID string) error
}

// CompleteTaskUseCase ports CompleteTaskUseCase: it marks a task done, requiring
// a completion summary and all subtasks complete.
type CompleteTaskUseCase struct {
	taskRepository        repositories.TaskRepository
	subtaskRepository     repositories.SubtaskRepository
	taskContextRepository services.TaskContextRepositoryProtocol
	completionService     *services.TaskCompletionService
	contextFacadeFactory  completeTaskContextFacadeFactory
	hooks                 CompleteTaskHooks

	// ledger writes each status move and its status_changed entry in one transaction. Unset leaves
	// the save exactly as it was.
	ledger StatusLedger
}

// WithHooks sets the status/metadata sync hooks (nil disables them).
func (uc *CompleteTaskUseCase) WithHooks(h CompleteTaskHooks) *CompleteTaskUseCase {
	uc.hooks = h
	return uc
}

// WithLedger wires the status ledger (unset leaves the status writes as they were).
func (uc *CompleteTaskUseCase) WithLedger(l StatusLedger) *CompleteTaskUseCase {
	uc.ledger = l
	return uc
}

// NewCompleteTaskUseCase builds the use case. subtaskRepository and
// taskContextRepository may be nil (Python's optional arguments); the completion
// service is only built when subtaskRepository is provided. contextFacadeFactory
// may be nil, in which case context-facade interactions are skipped (see the
// dropped-dependency note in complete_task.go's migration report).
func NewCompleteTaskUseCase(
	taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository,
	taskContextRepository services.TaskContextRepositoryProtocol,
	contextFacadeFactory completeTaskContextFacadeFactory,
) *CompleteTaskUseCase {
	uc := &CompleteTaskUseCase{
		taskRepository:        taskRepository,
		subtaskRepository:     subtaskRepository,
		taskContextRepository: taskContextRepository,
		contextFacadeFactory:  contextFacadeFactory,
	}
	if subtaskRepository != nil {
		uc.completionService = services.NewTaskCompletionService(subtaskRepository, taskContextRepository)
	}
	return uc
}

// Execute completes the task. taskID mirrors Python's `str | int`; the optional
// strings mirror `str | None`; nextRecommendations is `str | list | None`.
func (uc *CompleteTaskUseCase) Execute(
	ctx context.Context,
	taskID any,
	completionSummary *string,
	testingNotes *string,
	nextRecommendations any,
) (*entities.OrderedMap[any], error) {
	return uc.ExecuteWithCorrection(ctx, taskID, completionSummary, testingNotes, nextRecommendations, false)
}

// ExecuteWithCorrection is Execute with the one decision the already-done branch needs: whether the
// caller has said, explicitly, that it is REPLACING the result line another caller wrote.
func (uc *CompleteTaskUseCase) ExecuteWithCorrection(
	ctx context.Context,
	taskID any,
	completionSummary *string,
	testingNotes *string,
	nextRecommendations any,
	correction bool,
) (*entities.OrderedMap[any], error) {
	taskIDStr := value_objects.PyStr(taskID)

	domainTaskID, err := value_objects.NewTaskId(taskIDStr)
	if err != nil {
		return nil, err
	}

	task, err := uc.taskRepository.FindByID(ctx, domainTaskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", taskIDStr))
	}

	if task.Status.IsDone() {
		return uc.completeAlreadyDoneTask(ctx, task, taskIDStr, completionSummary, testingNotes, nextRecommendations, correction)
	}

	response, early, err := uc.executeCore(ctx, task, taskIDStr, completionSummary, testingNotes, nextRecommendations)
	if err != nil {
		return uc.handleCompletionError(task, taskIDStr, err)
	}
	if early {
		return response, nil
	}

	// Save the task, with its status_changed entry, in one transaction. The entry reports the
	// transition the row makes: executeCore may already have moved todo -> in_progress, and that
	// move was recorded by its own call.
	if err := uc.ledger.Save(ctx, func(ctx context.Context) error {
		_, err := uc.taskRepository.Save(ctx, task)
		return err
	}, taskIDStr, nil); err != nil {
		return nil, err
	}

	// Update dependent tasks
	if err := uc.updateDependentTasks(ctx, task); err != nil {
		return nil, err
	}

	// Handle domain events (only TaskUpdated events are inspected).
	for _, event := range task.GetEvents() {
		if _, ok := event.(events.TaskUpdatedEvent); ok {
			// TaskUpdated event processed (logging dropped).
		}
	}

	// Legacy subtask progress for the response.
	legacyProgress := completeTaskLegacyProgressOrdered(task.GetSubtaskProgress())

	var newSubtaskSummary *entities.OrderedMap[any]
	if uc.completionService != nil {
		newSubtaskSummary = completeTaskSubtaskSummaryOrdered(
			uc.completionService.GetSubtaskCompletionSummary(ctx, task))
	} else if uc.subtaskRepository != nil {
		// Fallback: build the subtask summary directly from the repository.
		if task.ID != nil {
			if subtasks, err := uc.subtaskRepository.FindByParentTaskID(ctx, *task.ID); err == nil {
				if len(subtasks) > 0 {
					total := len(subtasks)
					completed := 0
					for _, subtask := range subtasks {
						if subtask.IsCompleted() {
							completed++
						}
					}
					incomplete := total - completed
					var completionPercentage any = 0
					if total > 0 {
						completionPercentage = value_objects.PyRound(float64(completed)/float64(total)*100, 1)
					}
					summary := entities.NewOrderedMap[any]()
					summary.Set("total", total)
					summary.Set("completed", completed)
					summary.Set("incomplete", incomplete)
					summary.Set("completion_percentage", completionPercentage)
					summary.Set("can_complete_parent", incomplete == 0)
					newSubtaskSummary = summary
				} else {
					summary := entities.NewOrderedMap[any]()
					summary.Set("total", 0)
					summary.Set("completed", 0)
					summary.Set("incomplete", 0)
					summary.Set("completion_percentage", 100)
					summary.Set("can_complete_parent", true)
					newSubtaskSummary = summary
				}
			}
		}
	}

	response = entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("task_id", taskIDStr)
	response.Set("status", task.Status.String())
	response.Set("subtask_progress", legacyProgress)
	response.Set("message", fmt.Sprintf("task %s done, can next_task", taskIDStr))
	response.Set("was_already_completed", false)
	if newSubtaskSummary != nil {
		response.Set("subtask_summary", newSubtaskSummary)
	}
	return response, nil
}

// completeAlreadyDoneTask is the `task.status.is_done()` branch.
//
// IT DOES NOT QUIETLY REWRITE THE RESULT LINE (board task ca541a97). The completion summary IS the
// ledger's result line - a task with no recorded result is not done - so a second `complete` that
// replaced it let any caller holding an id overwrite another seat's evidence, with no record of who
// wrote it or when. The write itself is defensible (correcting a bad line is reasonable); the
// SILENCE was the defect. Three rules now hold:
//
//   - Nothing new is a NO-OP: a complete that carries no summary, or the summary the row already
//     holds, writes nothing - the old code saved and moved updated_at anyway, which told every
//     reader the task had changed.
//   - A REPLACEMENT is allowed only for the caller the line is attributed to, or with the explicit
//     correction flag. Anyone else is refused, and the refusal names the author.
//   - A replacement KEEPS the old line: it is written as a `progress` ledger entry, attributed to
//     the seat that made the replacement, carrying the previous text, its author and its time.
func (uc *CompleteTaskUseCase) completeAlreadyDoneTask(
	ctx context.Context,
	task *entities.Task,
	taskIDStr string,
	completionSummary *string,
	testingNotes *string,
	nextRecommendations any,
	correction bool,
) (*entities.OrderedMap[any], error) {
	stored := ""
	if task.CompletionSummary != nil {
		stored = *task.CompletionSummary
	}
	requested := ""
	if completionSummary != nil {
		requested = *completionSummary
	}

	// Nothing to say, or the same thing again: no write at all.
	if strings.TrimSpace(requested) == "" || requested == stored {
		return completeTaskAlreadyDoneResponse(task, taskIDStr, "Task already completed"), nil
	}

	actorKind, actorID, hasActor := uc.actorOf(ctx)
	if !hasActor {
		return nil, errors.New("completion: no actor to attribute the result line to - the request named no seat and the ledger has no user")
	}
	_ = actorKind

	owner := ""
	if task.CompletedBy != nil {
		owner = *task.CompletedBy
	}
	if owner == "" {
		// A row completed before attribution was recorded. No caller can prove it wrote the line,
		// so replacing it needs the explicit flag rather than a guess.
		if !correction {
			return nil, value_objects.ValueErrorf(
				"Task %s is already done and its result line has no recorded author (it predates completion attribution); pass correction=true to replace it - the previous line is kept as a superseded ledger entry",
				taskIDStr)
		}
	} else if owner != actorID && !correction {
		return nil, value_objects.ValueErrorf(
			"Task %s is already done and its result line is attributed to %s; pass correction=true to replace it - the previous line is kept as a superseded ledger entry",
			taskIDStr, owner)
	}

	previousBy := ""
	if task.CompletedBy != nil {
		previousBy = *task.CompletedBy
	}
	previousAt := ""
	if task.CompletedAt != nil {
		previousAt = value_objects.IsoFormat(*task.CompletedAt)
	}

	if fac := uc.newFacade(task.GitBranchID, nil); fac != nil {
		completionTime := time.Now().UTC()
		lastUpdate := value_objects.IsoFormat(completionTime)
		fac.UpdateContext("task", taskIDStr,
			completeTaskCompletionContextUpdate(requested, nextRecommendations, testingNotes, &lastUpdate),
			true)
	}

	task.CompletionSummary = completionSummary
	task.CompletedBy = &actorID
	completedAt := time.Now().UTC().Truncate(time.Microsecond)
	task.CompletedAt = &completedAt

	// The superseded line, attributed and timed, rides the same transaction as the row it stopped
	// describing: a note recorded separately could outlive, or precede, a save that rolled back.
	note := completeTaskSupersededNote(previousBy, previousAt, stored, actorID)
	save := func(ctx context.Context) error {
		_, err := uc.taskRepository.Save(ctx, task)
		return err
	}
	if uc.ledger.Enabled() {
		if err := uc.ledger.Save(ctx, save, taskIDStr, []LedgerProgress{
			{Content: note, Timestamp: value_objects.IsoFormat(completedAt)},
		}); err != nil {
			return nil, err
		}
	} else {
		return nil, ErrLedgerNotWired
	}

	return completeTaskAlreadyDoneResponse(task, taskIDStr, "Task already completed, summary updated"), nil
}

// completeTaskSupersededNote is the ledger entry a replaced result line leaves behind. The actor and
// the entry's own timestamp say WHO replaced it and WHEN; the text says what it replaced, whose it
// was, and when that line was written - so the previous line is legible after it is gone from the
// column.
func completeTaskSupersededNote(previousBy, previousAt, previousSummary, replacedBy string) string {
	author := previousBy
	if author == "" {
		author = "an unrecorded caller"
	}
	when := previousAt
	if when == "" {
		when = "an unrecorded time"
	}
	return fmt.Sprintf("completion summary superseded by %s: previous line (%s, %s): %s",
		replacedBy, author, when, previousSummary)
}

// completeTaskAlreadyDoneResponse is the answer both the no-op and the replacement give.
func completeTaskAlreadyDoneResponse(task *entities.Task, taskIDStr, message string) *entities.OrderedMap[any] {
	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("task_id", taskIDStr)
	response.Set("message", message)
	response.Set("status", task.Status.String())
	response.Set("was_already_completed", true)
	return response
}

// actorOf names who this request is attributed to, from the ledger recorder that settles attribution
// for every other write in this flow. Without a wired ledger there is no authority to name anyone,
// and the completion gate refuses rather than guessing.
func (uc *CompleteTaskUseCase) actorOf(ctx context.Context) (entities.TaskEventActorKind, string, bool) {
	if !uc.ledger.Enabled() || uc.ledger.Ledger == nil {
		return "", "", false
	}
	return uc.ledger.Ledger.ActorOf(ctx)
}

// executeCore is the body of Python's outer try block; `early` reports a direct
// return (the fallback subtask validation).
func (uc *CompleteTaskUseCase) executeCore(
	ctx context.Context,
	task *entities.Task,
	taskIDStr string,
	completionSummary *string,
	testingNotes *string,
	nextRecommendations any,
) (*entities.OrderedMap[any], bool, error) {
	contextExists := false

	// Check for context existence using the legacy context repository.
	if uc.taskContextRepository != nil {
		legacyContext, err := uc.taskContextRepository.Get(taskIDStr)
		if err != nil {
			return nil, false, err
		}
		if legacyContext != nil {
			contextExists = true
			if task.ContextID == nil {
				id := taskIDStr
				task.ContextID = &id
				if _, err := uc.taskRepository.Save(ctx, task); err != nil {
					return nil, false, err
				}
			}
		}
	}

	// Check the unified context system (failures swallowed).
	if !contextExists {
		if fac := uc.newFacade(task.GitBranchID, nil); fac != nil {
			result := fac.GetContext("task", taskIDStr)
			if completeTaskGetTruthy(result, "success") {
				if _, hasContext := result["context"]; hasContext {
					contextExists = true
					if task.ContextID == nil {
						id := taskIDStr
						task.ContextID = &id
						if _, err := uc.taskRepository.Save(ctx, task); err != nil {
							return nil, false, err
						}
					}
				}
			}
		}
	}

	// Auto-create context if it does not exist (failures swallowed).
	if !contextExists {
		_ = uc.autoCreateContext(ctx, task, taskIDStr)
	}

	// Validate task completion using the domain service.
	if uc.completionService != nil {
		if err := uc.completionService.ValidateTaskCompletion(ctx, task); err != nil {
			return nil, false, err
		}
	} else if uc.subtaskRepository != nil {
		// Fallback validation: check subtasks directly.
		if task.ID != nil {
			subtasks, err := uc.subtaskRepository.FindByParentTaskID(ctx, *task.ID)
			if err != nil {
				return nil, false, err
			}
			if len(subtasks) > 0 {
				incompleteSubtasks := []*entities.Subtask{}
				for _, subtask := range subtasks {
					if !subtask.IsCompleted() {
						incompleteSubtasks = append(incompleteSubtasks, subtask)
					}
				}
				if len(incompleteSubtasks) > 0 {
					incompleteCount := len(incompleteSubtasks)
					totalCount := len(subtasks)
					details := []*entities.OrderedMap[any]{}
					for _, subtask := range incompleteSubtasks {
						id := ""
						if subtask.ID != nil {
							id = subtask.ID.Value
						}
						detail := entities.NewOrderedMap[any]()
						detail.Set("id", id)
						detail.Set("title", subtask.Title)
						detail.Set("status", subtask.Status.Value)
						details = append(details, detail)
					}
					errorMsg := fmt.Sprintf("Cannot complete task: %d of %d subtasks are not done", incompleteCount, totalCount)
					response := entities.NewOrderedMap[any]()
					response.Set("success", false)
					response.Set("task_id", taskIDStr)
					response.Set("message", errorMsg)
					response.Set("status", task.Status.String())
					errorObj := entities.NewOrderedMap[any]()
					errorObj.Set("message", errorMsg)
					errorObj.Set("code", "SUBTASKS_NOT_COMPLETE")
					detailObj := entities.NewOrderedMap[any]()
					detailObj.Set("incomplete_subtasks", details)
					detailObj.Set("incomplete_count", incompleteCount)
					detailObj.Set("total_count", totalCount)
					errorObj.Set("details", detailObj)
					response.Set("error", errorObj)
					return response, true, nil
				}
			}
		}
	}

	// Get context timestamp to validate context is newer than the task.
	var contextUpdatedAt *time.Time
	if task.ContextID != nil {
		if fac := uc.newFacade(task.GitBranchID, nil); fac != nil {
			result := fac.GetContext("task", taskIDStr)
			if completeTaskGetTruthy(result, "success") {
				if ctxAny, ok := result["context"]; ok {
					if ctxMap, ok := ctxAny.(map[string]any); ok {
						if updatedAny, ok := ctxMap["updated_at"]; ok {
							if updatedStr, ok := updatedAny.(string); ok {
								if parsed, perr := time.Parse("2006-01-02 15:04:05", updatedStr); perr == nil {
									contextUpdatedAt = &parsed
								}
							}
						}
					}
				}
			}
		}
	}

	// Handle state transition from todo -> in_progress -> done. The move to in_progress is a status
	// write of its own, so it carries its own entry, in its own transaction.
	if strings.ToLower(task.Status.String()) == "todo" {
		inProgress, _ := value_objects.NewTaskStatus("in_progress")
		task.Status = &inProgress
		if err := uc.ledger.Save(ctx, func(ctx context.Context) error {
			_, err := uc.taskRepository.Save(ctx, task)
			return err
		}, taskIDStr, nil); err != nil {
			return nil, false, err
		}
	}

	// Complete the task (will complete all subtasks and set status to done).
	summary := ""
	if completionSummary != nil {
		summary = *completionSummary
	}
	var ctxUpdated *time.Time
	if task.ContextID != nil {
		ctxUpdated = contextUpdatedAt
	}
	if err := task.CompleteTask(summary, ctxUpdated); err != nil {
		message := err.Error()
		if strings.Contains(message, "Context must be updated") ||
			strings.Contains(strings.ToLower(message), "context must be updated") {
			// Context validation failed - bypass it and complete anyway.
			done, _ := value_objects.NewTaskStatus("done")
			task.Status = &done
			task.CompletionSummary = completionSummary
			if err := task.Touch("task_completed_manually"); err != nil {
				return nil, false, err
			}
			// Python appends TaskUpdated(field_name=..., ...) here, but the alias
			// resolves to TaskUpdatedEvent, whose generated __init__ rejects those
			// keyword arguments with this TypeError. Reproduced faithfully.
			return nil, false, value_objects.TypeErrorf(
				"TaskUpdatedEvent.__init__() got an unexpected keyword argument 'field_name'")
		}
		return nil, false, err
	}

	// WHO wrote the result line and WHEN. Recorded here, on the transition into done, so a later
	// complete of the same task has an author to compare the caller against - the row had the
	// completed_at column all along and nothing wrote it (board task ca541a97).
	if _, actorID, ok := uc.actorOf(ctx); ok {
		task.CompletedBy = &actorID
	}
	completedAt := time.Now().UTC().Truncate(time.Microsecond)
	task.CompletedAt = &completedAt

	// Update context with completion information.
	if completeTaskNonEmpty(completionSummary) {
		if fac := uc.newFacade(task.GitBranchID, nil); fac != nil {
			fac.UpdateContext("task", taskIDStr,
				completeTaskCompletionContextUpdate(*completionSummary, nextRecommendations, testingNotes, nil),
				true)
			// Synchronize the task's context-owned fields after completion. The completion itself does
			// not fail on it, but it is logged: a silent sync is how a done task kept resolving as
			// todo. The STATUS the completion sets lives on the task row, which a context read serves
			// from that row; writing it into the context's metadata stored nothing and recorded
			// `add metadata.status` on every completion (reviewer row 87b7d8fb).
			if uc.hooks != nil {
				if err := uc.hooks.SyncTaskMetadata(ctx, taskIDStr, task, ""); err != nil {
					log.Printf("[complete_task] the metadata did not land in the context of %s: %v", taskIDStr, err)
				}
			}
		}
		// THE BROADCAST IS NOT GATED ON THE CONTEXT FACADE, and my first attempt had it inside that
		// guard - which the test caught: a completion this process cannot touch the facade for still
		// HAPPENED, and a completed task nobody is told about is exactly the defect being repaired.
		// The sync above stays where it is because it synchronises the CONTEXT the update above follows.
		//
		// create_task.go:172 and update_task.go:160 both call this on the same object the wiring hands
		// to this use case; CompleteTaskHooks simply did not declare it, so the compiler made the call
		// impossible at this site. THE VOCABULARY IS THE CLIENT'S: a completion emits "completed" (its
		// own distinct animation) and every other status move emits "updated", matching update_task.go's
		// literal - a distinct animation per transition would be a vocabulary addition and the owner's
		// decision, not something to discover from a copy-paste.
		if uc.hooks != nil {
			branchID := ""
			if task.GitBranchID != nil {
				branchID = *task.GitBranchID
			}
			uc.hooks.NotifyTaskEvent(ctx, "completed", task, nil, nil, branchID, []string{"status"})
		}
	}

	return nil, false, nil
}

// handleCompletionError maps the Python except clauses.
func (uc *CompleteTaskUseCase) handleCompletionError(
	task *entities.Task,
	taskIDStr string,
	err error,
) (*entities.OrderedMap[any], error) {
	var missing *exceptions.MissingCompletionSummaryError
	if errors.As(err, &missing) {
		response := entities.NewOrderedMap[any]()
		response.Set("success", false)
		response.Set("task_id", taskIDStr)
		response.Set("message", missing.Error())
		response.Set("status", task.Status.String())
		response.Set("hint", "Use the 'complete_task_with_context' action or provide 'completion_summary' parameter")
		return response, nil
	}

	var completionErr *exceptions.TaskCompletionError
	if errors.As(err, &completionErr) {
		response := entities.NewOrderedMap[any]()
		response.Set("success", false)
		response.Set("task_id", taskIDStr)
		response.Set("message", completionErr.Error())
		response.Set("status", task.Status.String())

		if len(completionErr.IncompleteSubtasks) > 0 {
			code := completionErr.ErrorCode
			if code == "" {
				code = "SUBTASKS_NOT_COMPLETE"
			}
			totalCount := len(completionErr.IncompleteSubtasks)
			if v, ok := completionErr.Context["total_count"]; ok {
				totalCount = completeTaskIntValue(v, totalCount)
			}
			errorObj := entities.NewOrderedMap[any]()
			errorObj.Set("message", completionErr.Error())
			errorObj.Set("code", code)
			detailObj := entities.NewOrderedMap[any]()
			detailObj.Set("incomplete_subtasks", completeTaskIncompleteSubtasksOrdered(completionErr.IncompleteSubtasks))
			detailObj.Set("incomplete_count", len(completionErr.IncompleteSubtasks))
			detailObj.Set("total_count", totalCount)
			errorObj.Set("details", detailObj)
			response.Set("error", errorObj)
		}
		return response, nil
	}

	var valueErr *value_objects.ValueError
	if errors.As(err, &valueErr) {
		// Re-raise to be caught by the facade.
		return nil, err
	}
	return nil, err
}

// autoCreateContext mirrors the "not context_exists" auto-creation block. The
// whole block is wrapped in try/except in Python, so the returned error is
// swallowed by the caller.
func (uc *CompleteTaskUseCase) autoCreateContext(ctx context.Context, task *entities.Task, taskIDStr string) error {
	gitBranchID := task.GitBranchID
	// Python's Task has no `project_id` attribute, so getattr(..., None) is None.
	var projectID *string

	if projectID == nil && gitBranchID != nil {
		return value_objects.ValueErrorf(
			"project_id is required for context completion (no fallback allowed for DDD compliance)")
	}

	fac := uc.newFacade(gitBranchID, projectID)
	if fac == nil {
		return nil
	}

	createdAny := false

	if projectID != nil {
		data := entities.NewOrderedMap[any]()
		data.Set("project_id", *projectID)
		data.Set("auto_created", true)
		data.Set("created_during", "task_completion")
		if completeTaskGetTruthy(fac.CreateContext("project", *projectID, data), "success") {
			createdAny = true
		}
	}

	if gitBranchID != nil {
		data := entities.NewOrderedMap[any]()
		data.Set("project_id", completeTaskAny(projectID))
		data.Set("git_branch_id", *gitBranchID)
		data.Set("auto_created", true)
		data.Set("created_during", "task_completion")
		if completeTaskGetTruthy(fac.CreateContext("branch", *gitBranchID, data), "success") {
			createdAny = true
		}
	}

	taskData := entities.NewOrderedMap[any]()
	taskData.Set("title", task.Title)
	taskData.Set("status", task.Status.String())
	taskData.Set("description", task.Description)

	contextData := entities.NewOrderedMap[any]()
	contextData.Set("branch_id", completeTaskAny(gitBranchID))
	contextData.Set("project_id", completeTaskAny(projectID))
	contextData.Set("task_data", taskData)
	contextData.Set("auto_created", true)
	contextData.Set("created_during", "task_completion")

	createResult := fac.CreateContext("task", taskIDStr, contextData)
	if completeTaskGetTruthy(createResult, "success") {
		createdAny = true
		id := taskIDStr
		task.ContextID = &id
		if _, err := uc.taskRepository.Save(ctx, task); err != nil {
			return err
		}
	}

	_ = createdAny
	return nil
}

// newFacade builds the context facade, or nil when the factory is absent.
func (uc *CompleteTaskUseCase) newFacade(gitBranchID, projectID *string) completeTaskContextFacade {
	if uc.contextFacadeFactory == nil {
		return nil
	}
	return uc.contextFacadeFactory.CreateFacade(gitBranchID, projectID)
}

// updateDependentTasks mirrors _update_dependent_tasks, with one deliberate difference: no discarded error on
// this path may read as success. A failed scan of the dependent tasks is returned, and so is a dependent task's
// failed status write - Python logged both and continued, which is how a pass that never ran and a write that
// never happened both reached the caller as a completed task.
func (uc *CompleteTaskUseCase) updateDependentTasks(ctx context.Context, completedTask *entities.Task) error {
	allTasks, err := uc.taskRepository.FindAll(ctx)
	if err != nil {
		return err
	}

	completedID := ""
	if completedTask.ID != nil {
		completedID = completedTask.ID.Value
	}

	dependentTasks := []*entities.Task{}
	for _, t := range allTasks {
		matched := false
		if len(t.Dependencies) > 0 {
			for _, dependency := range t.Dependencies {
				if dependency.Value == completedID {
					matched = true
					break
				}
			}
		} else if ids := t.GetDependencyIDs(); len(ids) > 0 {
			for _, id := range ids {
				if id == completedID {
					matched = true
					break
				}
			}
		}
		if matched {
			dependentTasks = append(dependentTasks, t)
		}
	}

	for _, dependentTask := range dependentTasks {
		if err := uc.updateSingleDependentTask(ctx, dependentTask, allTasks); err != nil {
			return err
		}
	}
	return nil
}

// updateSingleDependentTask mirrors _update_single_dependent_task.
func (uc *CompleteTaskUseCase) updateSingleDependentTask(ctx context.Context, dependentTask *entities.Task, allTasks []*entities.Task) error {
	allDependenciesComplete := completeTaskAllDependenciesComplete(dependentTask, allTasks)
	if allDependenciesComplete && dependentTask.Status != nil {
		switch dependentTask.Status.Value {
		case "blocked":
			todo, _ := value_objects.NewTaskStatus("todo")
			dependentTask.Status = &todo
			// The unblock is this OTHER task's status write, so it carries its own entry, in its own
			// transaction. Python logs a failure here and continues; that discard is exactly what made a
			// failed write read as success to this use case's caller, so the error is returned instead.
			if err := uc.ledger.Save(ctx, func(ctx context.Context) error {
				_, err := uc.taskRepository.Save(ctx, dependentTask)
				return err
			}, ledgerTaskID(dependentTask), nil); err != nil {
				return err
			}
		case "todo":
			// Ready to start: all dependencies completed.
		default:
			// No change needed.
		}
	}
	return nil
}

// completeTaskAllDependenciesComplete mirrors _check_all_dependencies_complete.
func completeTaskAllDependenciesComplete(task *entities.Task, allTasks []*entities.Task) bool {
	dependencyIDs := []string{}
	if len(task.Dependencies) > 0 {
		for _, dep := range task.Dependencies {
			dependencyIDs = append(dependencyIDs, dep.Value)
		}
	} else if ids := task.GetDependencyIDs(); len(ids) > 0 {
		dependencyIDs = ids
	}

	if len(dependencyIDs) == 0 {
		return true
	}

	for _, depID := range dependencyIDs {
		var depTask *entities.Task
		for _, t := range allTasks {
			if t.ID != nil && t.ID.Value == depID {
				depTask = t
				break
			}
		}
		if depTask == nil {
			return false
		}
		if depTask.Status != nil && !depTask.Status.IsDone() {
			return false
		}
	}
	return true
}

// completeTaskCompletionContextUpdate builds the OrderedMap update_context payload.
// lastSummaryUpdate is only set in the already-completed branch.
func completeTaskCompletionContextUpdate(
	completionSummary string,
	nextRecommendations any,
	testingNotes *string,
	lastSummaryUpdate *string,
) *entities.OrderedMap[any] {
	nextSteps := completeTaskNextSteps(nextRecommendations)
	if completeTaskNonEmpty(testingNotes) {
		nextSteps = append(nextSteps, "Testing completed: "+*testingNotes)
	}

	progress := entities.NewOrderedMap[any]()
	progress.Set("current_session_summary", completionSummary)
	progress.Set("completion_percentage", 100.0)
	progress.Set("next_steps", nextSteps)
	progress.Set("completed_actions", []any{})

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("status", "done")
	if lastSummaryUpdate != nil {
		metadata.Set("last_summary_update", *lastSummaryUpdate)
	}

	update := entities.NewOrderedMap[any]()
	update.Set("progress", progress)
	update.Set("metadata", metadata)
	return update
}

// completeTaskNextSteps mirrors the list-normalization of next_recommendations.
func completeTaskNextSteps(v any) []any {
	if !value_objects.PyTruthy(v) {
		return []any{}
	}
	switch list := v.(type) {
	case []string:
		out := make([]any, len(list))
		for i, s := range list {
			out[i] = s
		}
		return out
	case []any:
		return append([]any{}, list...)
	default:
		return []any{v}
	}
}

// completeTaskLegacyProgressOrdered rebuilds get_subtask_progress in Python order.
func completeTaskLegacyProgressOrdered(m map[string]any) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	for _, k := range []string{"total", "completed", "percentage"} {
		if v, ok := m[k]; ok {
			out.Set(k, v)
		}
	}
	return out
}

// completeTaskSubtaskSummaryOrdered rebuilds get_subtask_completion_summary in
// Python key order.
func completeTaskSubtaskSummaryOrdered(m map[string]any) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	out := entities.NewOrderedMap[any]()
	for _, k := range []string{"total", "completed", "incomplete", "completion_percentage", "can_complete_parent", "error"} {
		if v, ok := m[k]; ok {
			out.Set(k, v)
		}
	}
	return out
}

// completeTaskIncompleteSubtasksOrdered rebuilds the TaskCompletionError detail
// dicts in Python key order (id, title, status); the domain service stores them
// as plain maps whose JSON key order would otherwise be sorted.
func completeTaskIncompleteSubtasksOrdered(details []map[string]any) []*entities.OrderedMap[any] {
	out := make([]*entities.OrderedMap[any], 0, len(details))
	for _, detail := range details {
		om := entities.NewOrderedMap[any]()
		for _, k := range []string{"id", "title", "status"} {
			if v, ok := detail[k]; ok {
				om.Set(k, v)
			}
		}
		out = append(out, om)
	}
	return out
}

// completeTaskNonEmpty is Python truthiness for an optional string.
func completeTaskNonEmpty(s *string) bool { return s != nil && *s != "" }

// completeTaskGetTruthy is `m.get(key)` truthiness for a facade result.
func completeTaskGetTruthy(m map[string]any, key string) bool {
	v, ok := m[key]
	return ok && value_objects.PyTruthy(v)
}

// completeTaskAny converts an optional string to a Python-like None/str value.
func completeTaskAny(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// completeTaskIntValue reads an int-ish value from an exception context.
func completeTaskIntValue(v any, fallback int) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return fallback
}

// Exported names for the context facade ports, for the composition root.
type (
	CompleteTaskContextFacade        = completeTaskContextFacade
	CompleteTaskContextFacadeFactory = completeTaskContextFacadeFactory
)
