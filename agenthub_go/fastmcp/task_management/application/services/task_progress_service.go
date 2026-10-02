package services

import (
	"context"
	"math"

	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskProgressStore abstracts the direct `get_session()` / ORM Task-model access the
// Python service performs at the end of update_task_progress_from_subtasks and in
// get_task_progress. The application layer must not import the database package, so
// the storage is injected as this minimal interface (implemented by infrastructure).
type TaskProgressStore interface {
	// GetProgress is session.get(TaskModel, task_id).progress_percentage. ok is false
	// when the model (or attribute) is missing.
	GetProgress(ctx context.Context, taskID string) (value float64, ok bool)
	// SetProgress assigns TaskModel.progress_percentage and commits.
	SetProgress(ctx context.Context, taskID string, value float64) error
}

// TaskProgressService manages task progress based on subtask completion
// (Python application/services/task_progress_service.py).
type TaskProgressService struct {
	TaskRepository    repositories.TaskRepository
	SubtaskRepository repositories.SubtaskRepository
	UserID            *string
	// Store is the ORM-session dependency described on TaskProgressStore.
	Store TaskProgressStore
}

// NewTaskProgressService mirrors __init__(task_repository, subtask_repository, user_id=None).
func NewTaskProgressService(taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository, userID *string, store TaskProgressStore) *TaskProgressService {
	return &TaskProgressService{TaskRepository: taskRepository, SubtaskRepository: subtaskRepository, UserID: userID, Store: store}
}

// WithUser creates a new service instance scoped to a specific user.
func (s *TaskProgressService) WithUser(userID string) *TaskProgressService {
	return &TaskProgressService{TaskRepository: s.TaskRepository, SubtaskRepository: s.SubtaskRepository, UserID: &userID, Store: s.Store}
}

// getUserScopedRepository mirrors the repeated _get_user_scoped_repository helper.
func (s *TaskProgressService) getUserScopedRepository(repository any) any {
	return serviceUserScopedRepository(repository, s.UserID)
}

// UpdateTaskProgressFromSubtasks calculates and updates task progress based on subtask
// completion. It returns the calculated percentage or nil if the task is not found. On
// any error the Python catches the exception and returns None, so this returns nil too.
func (s *TaskProgressService) UpdateTaskProgressFromSubtasks(ctx context.Context, taskID string) *float64 {
	domainTaskID, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil
	}
	taskRepo := s.TaskRepository
	if r, ok := s.getUserScopedRepository(s.TaskRepository).(repositories.TaskRepository); ok {
		taskRepo = r
	}
	task, err := taskRepo.FindByID(ctx, domainTaskID)
	if err != nil || task == nil {
		return nil
	}
	subtaskRepo := s.SubtaskRepository
	if r, ok := s.getUserScopedRepository(s.SubtaskRepository).(repositories.SubtaskRepository); ok {
		subtaskRepo = r
	}
	subtasks, err := subtaskRepo.FindByParentTaskID(ctx, domainTaskID)
	if err != nil {
		return nil
	}
	if len(subtasks) == 0 {
		// Python returns getattr(task, "progress_percentage", 0); the Task entity has no
		// such attribute, so the default 0 is always returned.
		zero := 0.0
		return &zero
	}
	totalSubtasks := len(subtasks)
	completedSubtasks := 0
	totalProgress := 0.0
	for _, subtask := range subtasks {
		if subtask == nil {
			continue
		}
		if subtask.IsCompleted() {
			completedSubtasks++
			totalProgress += 100
		} else {
			totalProgress += float64(subtask.ProgressPercentage)
		}
	}
	_ = completedSubtasks
	progressPercentage := math.RoundToEven(totalProgress / float64(totalSubtasks))

	if s.Store != nil {
		if err := s.Store.SetProgress(ctx, taskID, progressPercentage); err != nil {
			return nil
		}
	}
	return &progressPercentage
}

// GetTaskProgress returns the current progress percentage, 0 when the model is missing,
// or nil on error.
func (s *TaskProgressService) GetTaskProgress(ctx context.Context, taskID string) *float64 {
	if s.Store == nil {
		zero := 0.0
		return &zero
	}
	value, ok := s.Store.GetProgress(ctx, taskID)
	if !ok {
		zero := 0.0
		return &zero
	}
	return &value
}
