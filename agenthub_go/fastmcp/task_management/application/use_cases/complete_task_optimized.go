package use_cases

import (
	"context"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// optimizedContextManager is the context-manager surface used by
// OptimizedCompleteTaskUseCase (Python's self._context_manager). The unified
// context facade is ported in application/facades/unified_context_facade.go, so the
// minimal consumer-side interface is declared here.
type optimizedContextManager interface {
	GetContext(ctx context.Context, taskID string) (map[string]any, error)
	UpdateContext(ctx context.Context, taskID string, data map[string]any, mergeMode bool) error
}

// optimizedProgressService is the progress-service surface used by
// OptimizedCompleteTaskUseCase (Python's self._progress_service).
type optimizedProgressService interface {
	CalculateParentProgress(ctx context.Context, taskID string) (any, error)
}

// optimizedParentTaskIDProvider mirrors the dynamic task.parent_task_id attribute
// the Python probes with hasattr. entities.Task does not expose it, so the check
// is false for every current task.
type optimizedParentTaskIDProvider interface {
	ParentTaskID() *string
}

// OptimizedCompleteTaskRequest is the Go stand-in for the unported
// CompleteTaskRequest DTO (complete_task_request.py is absent from the Python tree).
type OptimizedCompleteTaskRequest struct {
	TaskID              string
	CompletionSummary   *string
	TestingNotes        *string
	NextRecommendations *string
}

// OptimizedCompleteTaskUseCase ports
// complete_task_optimized.OptimizedCompleteTaskUseCase. It is standalone because
// complete_task.py's CompleteTaskUseCase methods are not used by the ported body.
type OptimizedCompleteTaskUseCase struct {
	taskRepository    repositories.TaskRepository
	completionService *services.TaskCompletionService
	contextManager    optimizedContextManager
	progressService   optimizedProgressService
}

// NewOptimizedCompleteTaskUseCase builds the use case. The service pointers may
// be nil (Python's falsy optionals).
func NewOptimizedCompleteTaskUseCase(taskRepository repositories.TaskRepository, completionService *services.TaskCompletionService, contextManager optimizedContextManager, progressService optimizedProgressService) *OptimizedCompleteTaskUseCase {
	return &OptimizedCompleteTaskUseCase{
		taskRepository:    taskRepository,
		completionService: completionService,
		contextManager:    contextManager,
		progressService:   progressService,
	}
}

// Execute ports _execute_async (execute() only wrapped it in asyncio.run).
// Every exception becomes a CONTEXT_REQUIRED or OPERATION_FAILED response; the
// method never returns a non-nil error.
func (u *OptimizedCompleteTaskUseCase) Execute(ctx context.Context, request *OptimizedCompleteTaskRequest) (*entities.OrderedMap[any], error) {
	response, err := u.optimizedExecute(ctx, request)
	if err != nil {
		if strings.Contains(err.Error(), "must be updated before completing") {
			return optimizedContextRequiredResponse(err), nil
		}
		return optimizedOperationFailedResponse(err), nil
	}
	return response, nil
}

// optimizedExecute is the body of _execute_async.
func (u *OptimizedCompleteTaskUseCase) optimizedExecute(ctx context.Context, request *OptimizedCompleteTaskRequest) (*entities.OrderedMap[any], error) {
	if request.TaskID == "" {
		response := entities.NewOrderedMap[any]()
		response.Set("success", false)
		response.Set("error", "task_id is required")
		response.Set("error_code", "MISSING_FIELD")
		response.Set("field", "task_id")
		response.Set("expected", "A valid task_id")
		response.Set("hint", "Provide the ID of the task to complete")
		return response, nil
	}

	taskID, err := value_objects.NewTaskId(request.TaskID)
	if err != nil {
		return nil, err
	}

	task, err := u.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		response := entities.NewOrderedMap[any]()
		response.Set("success", false)
		response.Set("error", "Task not found: "+request.TaskID)
		response.Set("error_code", "NOT_FOUND")
		response.Set("field", "task_id")
		response.Set("hint", "Check that the task ID is correct")
		return response, nil
	}

	if u.completionService != nil {
		if err := u.completionService.ValidateTaskCompletion(ctx, task); err != nil {
			return nil, err
		}
	}

	// Get context ONCE and reuse it.
	var contextData map[string]any
	var contextUpdatedAt *time.Time

	if u.contextManager != nil {
		contextResult, err := u.contextManager.GetContext(ctx, request.TaskID)
		if err != nil {
			return nil, err
		}
		if value_objects.PyTruthy(contextResult["success"]) {
			contextData = contextResult

			if templateContext, ok := optimizedMapGet(contextResult, "template_context"); ok {
				if fullContext, ok := optimizedMapGet(templateContext, "full_context"); ok {
					if metadata, ok := optimizedMapGet(fullContext, "metadata"); ok {
						if updatedAt, ok := optimizedMapGet(metadata, "updated_at"); ok {
							parsed, err := optimizedParseUpdatedAt(updatedAt)
							if err != nil {
								return nil, err
							}
							contextUpdatedAt = parsed
						}
					}
				} else if taskMetadata, ok := optimizedMapGet(templateContext, "task_metadata"); ok {
					if updatedAt, ok := optimizedMapGet(taskMetadata, "updated_at"); ok {
						parsed, err := optimizedParseUpdatedAt(updatedAt)
						if err != nil {
							return nil, err
						}
						contextUpdatedAt = parsed
					}
				}
			}
		}
	}

	// Complete the task.
	completionSummary := ""
	if request.CompletionSummary != nil {
		completionSummary = *request.CompletionSummary
	}
	if err := task.CompleteTask(completionSummary, contextUpdatedAt); err != nil {
		return nil, err
	}

	// Python calls the absent task.add_metadata; the existing Task fields are the
	// closest storage. next_recommendations has no Go field and is dropped.
	if request.CompletionSummary != nil {
		task.CompletionSummary = request.CompletionSummary
	}
	if request.TestingNotes != nil {
		task.TestingNotes = request.TestingNotes
	}

	if _, err := u.taskRepository.Save(ctx, task); err != nil {
		return nil, err
	}

	// Update context with completion information (reusing the existing context data).
	if u.contextManager != nil && request.CompletionSummary != nil && *request.CompletionSummary != "" && contextData != nil {
		contextUpdate := map[string]any{"progress": map[string]any{
			"completion_summary":    request.CompletionSummary,
			"testing_notes":         request.TestingNotes,
			"next_recommendations":  request.NextRecommendations,
			"completion_percentage": 100.0,
		}}
		if err := u.contextManager.UpdateContext(ctx, request.TaskID, contextUpdate, true); err != nil {
			// Python logs and continues.
			_ = err
		}
	}

	// Update parent task progress if this is a subtask (Python probes hasattr).
	var parentProgress any
	if provider, ok := any(task).(optimizedParentTaskIDProvider); ok {
		if parentID := provider.ParentTaskID(); parentID != nil && *parentID != "" && u.progressService != nil {
			progress, err := u.progressService.CalculateParentProgress(ctx, *parentID)
			if err == nil {
				parentProgress = progress
			}
		}
	}

	taskMap := entities.NewOrderedMap[any]()
	taskMap.Set("id", optimizedTaskIDString(task))
	taskMap.Set("title", task.Title)
	taskMap.Set("status", optimizedTaskStatusString(task))
	taskMap.Set("completed_at", nil)
	taskMap.Set("completion_summary", optimizedOptionalString(request.CompletionSummary))
	taskMap.Set("testing_notes", optimizedOptionalString(request.TestingNotes))
	taskMap.Set("next_recommendations", optimizedOptionalString(request.NextRecommendations))

	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("task", taskMap)
	response.Set("message", fmt.Sprintf("Task '%s' completed successfully", task.Title))

	if value_objects.PyTruthy(parentProgress) {
		response.Set("parent_progress", parentProgress)
	}
	return response, nil
}

// optimizedOperationFailedResponse is the OPERATION_FAILED branch.
func optimizedOperationFailedResponse(err error) *entities.OrderedMap[any] {
	response := entities.NewOrderedMap[any]()
	response.Set("success", false)
	response.Set("error", "Failed to complete task: "+err.Error())
	response.Set("error_code", "OPERATION_FAILED")
	return response
}

// optimizedContextRequiredResponse is the CONTEXT_REQUIRED branch.
func optimizedContextRequiredResponse(err error) *entities.OrderedMap[any] {
	example := entities.NewOrderedMap[any]()
	example.Set("step1", "manage_context(action='update', level='task', context_id='...', data={'status': 'done'})")
	example.Set("step2", "manage_task(action='complete', task_id='...', completion_summary='...')")

	response := entities.NewOrderedMap[any]()
	response.Set("success", false)
	response.Set("error", err.Error())
	response.Set("error_code", "CONTEXT_REQUIRED")
	response.Set("hint", "Update the task context before completing")
	response.Set("example", example)
	return response
}

// optimizedParseUpdatedAt is datetime.fromisoformat for the context timestamp.
func optimizedParseUpdatedAt(v any) (*time.Time, error) {
	s, ok := v.(string)
	if !ok {
		return nil, value_objects.TypeErrorf("fromisoformat: argument must be str")
	}
	ts, err := value_objects.ParseISO(s)
	if err != nil {
		return nil, err
	}
	return &ts, nil
}

// optimizedMapGet is Python `key in container` / container[key] for the plain-map
// and OrderedMap shapes that can appear in the context result.
func optimizedMapGet(v any, key string) (any, bool) {
	switch m := v.(type) {
	case map[string]any:
		value, ok := m[key]
		return value, ok
	case value_objects.OrderedAny:
		for _, k := range m.KeysAny() {
			if k == key {
				return m.GetAny(key), true
			}
		}
	}
	return nil, false
}

// optimizedTaskIDString is str(task.id).
func optimizedTaskIDString(task *entities.Task) string {
	if task.ID == nil {
		return "None"
	}
	return task.ID.Value
}

// optimizedTaskStatusString is str(task.status).
func optimizedTaskStatusString(task *entities.Task) string {
	if task.Status == nil {
		return "None"
	}
	return task.Status.String()
}

// optimizedOptionalString renders an optional request field as str or None.
func optimizedOptionalString(v *string) any {
	if v == nil {
		return nil
	}
	return *v
}
