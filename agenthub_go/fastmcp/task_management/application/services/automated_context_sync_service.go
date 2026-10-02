package services

import (
	"context"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpAutoSyncContextSyncer is the minimal port of the not-yet-ported
// TaskContextSyncService dependency. The Python constructor builds
// TaskContextSyncService(task_repo) internally; the Go constructor receives this
// interface instead (nil allowed).
type zpAutoSyncContextSyncer interface {
	// SyncContextAndGetTask mirrors
	// sync_context_and_get_task(task_id=..., user_id=..., project_id=..., git_branch_name=...).
	// Its return value's truthiness decides success; an error mirrors a Python exception.
	SyncContextAndGetTask(ctx context.Context, taskID, userID, projectID, gitBranchName string) (any, error)
}

// AutomatedContextSyncService is the centralized service for automated context
// synchronization (Python application/services/automated_context_sync_service.py).
type AutomatedContextSyncService struct {
	TaskRepository     repositories.TaskRepository
	SubtaskRepository  repositories.SubtaskRepository
	UserID             *string
	ContextSyncService zpAutoSyncContextSyncer
}

// NewAutomatedContextSyncService mirrors
// __init__(task_repository, subtask_repository=None, user_id=None). The Python builds
// the context sync service from the (user-scoped) task repository; Go takes the
// already-constructed syncer.
func NewAutomatedContextSyncService(
	taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository,
	userID *string,
	contextSyncService zpAutoSyncContextSyncer,
) *AutomatedContextSyncService {
	return &AutomatedContextSyncService{
		TaskRepository:     taskRepository,
		SubtaskRepository:  subtaskRepository,
		UserID:             userID,
		ContextSyncService: contextSyncService,
	}
}

// getUserScopedRepository mirrors _get_user_scoped_repository. The Go repository
// interfaces expose no with_user/user_id/session attributes, and the Python
// reconstruction branch has no Go equivalent, so the repository is returned unchanged.
func (s *AutomatedContextSyncService) getUserScopedRepository(repository any) any {
	return repository
}

// WithUser creates a new service instance scoped to a specific user.
func (s *AutomatedContextSyncService) WithUser(userID string) *AutomatedContextSyncService {
	return NewAutomatedContextSyncService(s.TaskRepository, s.SubtaskRepository, &userID, s.ContextSyncService)
}

// SyncTaskContextAfterUpdate synchronizes task context after any task operation. It
// returns true if sync was successful, false otherwise.
func (s *AutomatedContextSyncService) SyncTaskContextAfterUpdate(ctx context.Context, task *entities.Task, operationType string) bool {
	if s.ContextSyncService == nil {
		return false
	}
	taskIDStr := zpAutoSyncTaskIDString(task)
	projectID := zpAutoSyncTaskProjectID(task)
	if projectID == nil || *projectID == "" {
		// Python raises ValueError("project_id is required for automated context sync"),
		// which the surrounding except converts into False.
		return false
	}
	result, err := s.ContextSyncService.SyncContextAndGetTask(ctx, taskIDStr, "system_"+operationType, *projectID, "main")
	if err != nil {
		return false
	}
	return value_objects.PyTruthy(result)
}

// SyncTaskContextAfterUpdateSync is the synchronous wrapper for task context sync. The
// Python async/sync event-loop bridge has no Go analog, so it calls the sync method
// directly.
func (s *AutomatedContextSyncService) SyncTaskContextAfterUpdateSync(ctx context.Context, task *entities.Task, operationType string) bool {
	return s.SyncTaskContextAfterUpdate(ctx, task, operationType)
}

// SyncParentContextAfterSubtaskUpdate synchronizes parent task context after subtask
// changes.
func (s *AutomatedContextSyncService) SyncParentContextAfterSubtaskUpdate(ctx context.Context, parentTask *entities.Task, subtask *entities.Subtask, operationType string) bool {
	if s.SubtaskRepository != nil && parentTask != nil {
		_ = s.CalculateSubtaskProgress(ctx, parentTask)
	}
	return s.SyncTaskContextAfterUpdate(ctx, parentTask, "parent_"+operationType)
}

// SyncParentContextAfterSubtaskUpdateSync is the synchronous wrapper for parent context
// sync after a subtask update. The Python async/sync event-loop bridge has no Go analog,
// so it calls the sync method directly.
func (s *AutomatedContextSyncService) SyncParentContextAfterSubtaskUpdateSync(ctx context.Context, parentTask *entities.Task, subtask *entities.Subtask, operationType string) bool {
	return s.SyncParentContextAfterSubtaskUpdate(ctx, parentTask, subtask, operationType)
}

// CalculateSubtaskProgress calculates a subtask progress summary for the parent task.
func (s *AutomatedContextSyncService) CalculateSubtaskProgress(ctx context.Context, parentTask *entities.Task) *entities.OrderedMap[any] {
	if s.SubtaskRepository == nil {
		return nil
	}
	if parentTask == nil || parentTask.ID == nil {
		return nil
	}
	subtasks, err := s.SubtaskRepository.FindByParentTaskID(ctx, *parentTask.ID)
	if err != nil {
		return nil
	}
	if len(subtasks) == 0 {
		out := entities.NewOrderedMap[any]()
		out.Set("total_subtasks", 0)
		out.Set("completed_subtasks", 0)
		out.Set("progress_percentage", 100) // No subtasks = 100% complete
		out.Set("can_complete_parent", true)
		return out
	}

	total := len(subtasks)
	completed := 0
	for _, subtask := range subtasks {
		if subtask != nil && subtask.IsCompleted() {
			completed++
		}
	}
	progressPercentage := value_objects.PyRound(float64(completed)/float64(total)*100, 1)

	out := entities.NewOrderedMap[any]()
	out.Set("total_subtasks", total)
	out.Set("completed_subtasks", completed)
	out.Set("incomplete_subtasks", total-completed)
	out.Set("progress_percentage", progressPercentage)
	out.Set("can_complete_parent", completed == total)
	out.Set("last_updated", value_objects.IsoFormat(time.Now().UTC()))
	return out
}

// SyncMultipleTasks synchronizes context for multiple tasks in batch. The result maps
// task_id to sync success status, in input order.
func (s *AutomatedContextSyncService) SyncMultipleTasks(ctx context.Context, taskIDs []string) *entities.OrderedMap[bool] {
	results := entities.NewOrderedMap[bool]()

	for _, taskID := range taskIDs {
		domainTaskID, err := value_objects.NewTaskId(taskID)
		if err != nil {
			results.Set(taskID, false)
			continue
		}
		if s.TaskRepository == nil {
			results.Set(taskID, false)
			continue
		}
		task, err := s.TaskRepository.FindByID(ctx, domainTaskID)
		if err != nil || task == nil {
			results.Set(taskID, false)
			continue
		}
		results.Set(taskID, s.SyncTaskContextAfterUpdate(ctx, task, "batch_sync"))
	}

	return results
}

// GetSyncStatistics returns statistics about context synchronization operations.
func (s *AutomatedContextSyncService) GetSyncStatistics() *entities.OrderedMap[any] {
	features := entities.NewOrderedMap[any]()
	features.Set("task_context_sync", true)
	features.Set("subtask_parent_sync", s.SubtaskRepository != nil)
	features.Set("batch_operations", true)
	features.Set("progress_calculation", s.SubtaskRepository != nil)

	out := entities.NewOrderedMap[any]()
	out.Set("service_status", "active")
	out.Set("sync_service_available", s.ContextSyncService != nil)
	out.Set("subtask_repository_available", s.SubtaskRepository != nil)
	out.Set("last_health_check", value_objects.IsoFormat(time.Now().UTC()))
	out.Set("features", features)
	return out
}

// ValidateSyncConfiguration validates that the sync service is properly configured.
func (s *AutomatedContextSyncService) ValidateSyncConfiguration() *entities.OrderedMap[any] {
	issues := []any{}

	if s.TaskRepository == nil {
		issues = append(issues, "Task repository not configured")
	}
	if s.ContextSyncService == nil {
		issues = append(issues, "Context sync service not available")
	}

	// The Python probes asyncio.get_event_loop(); Go always supports concurrency, so
	// async support is always reported as available.
	asyncAvailable := true

	recommendations := []any{}
	if len(issues) > 0 {
		recommendations = append(recommendations,
			"Ensure all repositories are properly injected",
			"Verify async/await support in runtime environment",
			"Test context sync service connectivity")
	}

	out := entities.NewOrderedMap[any]()
	out.Set("is_valid", len(issues) == 0)
	out.Set("issues", issues)
	out.Set("recommendations", recommendations)
	out.Set("async_support", asyncAvailable)
	out.Set("validation_timestamp", value_objects.IsoFormat(time.Now().UTC()))
	return out
}

// zpAutoSyncTaskProjectID mirrors getattr(task, "project_id", None). The ported
// entities.Task (like Python's Task) has no project_id attribute, so the default lookup
// always yields nil; it is a variable so tests can exercise the sync path.
var zpAutoSyncTaskProjectID = func(task *entities.Task) *string { return nil }

// zpAutoSyncTaskIDString mirrors str(task.id.value if hasattr(task.id, "value") else task.id).
func zpAutoSyncTaskIDString(task *entities.Task) string {
	if task == nil || task.ID == nil {
		return "None"
	}
	return task.ID.Value
}
