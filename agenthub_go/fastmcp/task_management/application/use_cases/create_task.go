// Package use_cases ports task_management/application/use_cases/create_task.py.
package use_cases

import (
	"context"
	"errors"

	task "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateTaskUseCase ports CreateTaskUseCase.
//
// The task_created domain event is not dispatched: Python calls the non-existent
// TaskCreatedEvent.create, so its try/except only ever logged a warning. The
// Python git_branch_exists check has no counterpart on repositories.TaskRepository
// and is dropped. The context auto-creation, metadata sync and WebSocket
// notification run through the injected CreateTaskHooks.
type CreateTaskUseCase struct {
	taskRepository      repositories.TaskRepository
	gitBranchRepository task.GitBranchGetter
	hooks               CreateTaskHooks
}

// CreateTaskHooks are the side effects create_task performs inline in Python through
// UnifiedContextFacadeFactory, TaskContextSyncService and WebSocketNotificationService /
// WebSocketPayloadBuilder. They live behind an interface because those services import
// this package. Every method is best-effort: Python logs and continues on failure.
type CreateTaskHooks interface {
	TaskEventHooks
	// CreateTaskContext creates the task-level context (context_facade.create_context) and
	// reports whether the response was successful.
	CreateTaskContext(ctx context.Context, task *entities.Task, userID string, projectID *string, gitBranchID string) (bool, error)
}

// WithHooks sets the side-effect hooks (nil disables them, as in a DB-less test).
func (u *CreateTaskUseCase) WithHooks(h CreateTaskHooks) *CreateTaskUseCase {
	u.hooks = h
	return u
}

// NewCreateTaskUseCase builds the use case. gitBranchRepository may be nil.
func NewCreateTaskUseCase(taskRepository repositories.TaskRepository, gitBranchRepository task.GitBranchGetter) *CreateTaskUseCase {
	return &CreateTaskUseCase{taskRepository: taskRepository, gitBranchRepository: gitBranchRepository}
}

// Execute mirrors execute(): it returns an error only for Python ValueError
// (re-raised); every other failure becomes a CreateTaskResponse.error_response.
func (u *CreateTaskUseCase) Execute(ctx context.Context, request task.CreateTaskRequest) (*task.CreateTaskResponse, error) {
	fail := func(e error) (*task.CreateTaskResponse, error) {
		var ve *value_objects.ValueError
		if errors.As(e, &ve) {
			// Python re-raises ValueError so the caller can handle validation errors.
			return nil, e
		}
		return task.NewCreateTaskResponseError("Failed to create task: "+e.Error(), nil), nil
	}

	taskID, err := u.taskRepository.GetNextID(ctx)
	if err != nil {
		return fail(err)
	}

	// TaskStatus(request.status or TaskStatusEnum.TODO.value)
	statusValue := string(value_objects.TaskStatusTodo)
	if request.Status != nil && *request.Status != "" {
		statusValue = *request.Status
	}
	status, err := value_objects.NewTaskStatus(statusValue)
	if err != nil {
		return fail(err)
	}

	// Priority(request.priority or PriorityLevel.MEDIUM.label)
	priorityValue := "medium"
	if request.Priority != nil && *request.Priority != "" {
		priorityValue = *request.Priority
	}
	priority, err := value_objects.NewPriority(priorityValue)
	if err != nil {
		return fail(err)
	}

	// The ENTITY owns the length limits: NewTask validates through ValidateEntity, which refuses a
	// title over 200 characters or a description over 2000 with the same message the update path
	// reports - so there is ONE definition of the limit rather than a validator and a slicer that
	// disagree. This path used to slice both silently: a create returned success with a truncated row
	// stored, nothing on it saying so, and no way for the caller to learn what had been cut. The
	// slicing was inherited from agenthub_main's create_task.py, an archived tree that is not a
	// parity target.
	title := request.Title

	description := ""
	if request.Description != nil {
		description = *request.Description
	}

	// Get user_id from request or repository. The repository user_id attribute is
	// not part of repositories.TaskRepository, so only the request value remains.
	var userID *string
	if request.UserID != nil && *request.UserID != "" {
		userID = request.UserID
	}

	gitBranchID := request.GitBranchID
	taskEntity, err := entities.CreateTask(entities.Task{
		ID:              &taskID,
		Title:           title,
		Description:     description,
		Status:          &status,
		Priority:        &priority,
		GitBranchID:     &gitBranchID,
		EstimatedEffort: request.EstimatedEffort,
		Assignees:       request.Assignees,
		Labels:          request.Labels,
		DueDate:         request.DueDate,
		UserID:          userID,
	})
	if err != nil {
		return fail(err)
	}

	// Add initial progress if details provided.
	if request.Details != "" {
		if err := taskEntity.AppendProgress(request.Details); err != nil {
			return fail(err)
		}
	}

	// Add dependencies if provided; invalid dependencies are skipped (Python logs
	// a warning and keeps creating the task).
	for _, depID := range request.Dependencies {
		if value_objects.PyStrip(depID) == "" {
			continue
		}
		parsed, err := value_objects.NewTaskId(depID)
		if err != nil {
			continue
		}
		_ = taskEntity.AddDependency(parsed)
	}

	saved, err := u.taskRepository.Save(ctx, taskEntity)
	if err != nil {
		return fail(err)
	}
	if saved == nil {
		return task.NewCreateTaskResponseError(
			"Failed to save task to database. This may be due to an invalid git_branch_id or database constraint violation.", nil), nil
	}

	// dispatch_domain_event("task_created", ...) not dispatched: TaskCreatedEvent.create does not exist in Python (AttributeError swallowed).

	// Handle domain events (Python consumes them here even though it does nothing).
	_ = taskEntity.GetEvents()

	// Auto-create task context for hierarchical context inheritance. Every failure is
	// logged and ignored, including the missing user (UserAuthenticationRequiredError).
	if u.hooks != nil && userID != nil {
		u.autoCreateTaskContext(ctx, taskEntity, *userID, gitBranchID)
	}

	taskResponse, err := task.TaskResponseFromDomain(ctx, taskEntity, u.gitBranchRepository, nil, nil, nil, nil)
	if err != nil {
		return fail(err)
	}

	// WebSocket notification for frontend real-time updates (after task_response creation).
	if u.hooks != nil {
		u.hooks.NotifyTaskEvent(ctx, "created", taskEntity, taskResponse, request.UserID, gitBranchID)
	}

	return task.NewCreateTaskResponseSuccess(taskResponse, nil), nil
}

// autoCreateTaskContext mirrors the "Auto-create task context" block of execute().
func (u *CreateTaskUseCase) autoCreateTaskContext(ctx context.Context, taskEntity *entities.Task, userID, gitBranchID string) {
	var projectID *string
	if u.gitBranchRepository != nil {
		if branch, err := u.gitBranchRepository.GetByID(ctx, gitBranchID); err == nil && branch != nil {
			p := branch.ProjectID
			projectID = &p
		}
	}
	taskIDStr := ""
	if taskEntity.ID != nil {
		taskIDStr = taskEntity.ID.Value
	}
	ok, err := u.hooks.CreateTaskContext(ctx, taskEntity, userID, projectID, gitBranchID)
	if err != nil || !ok {
		return
	}
	if err := taskEntity.SetContextID(taskIDStr); err != nil {
		return
	}
	if _, err := u.taskRepository.Save(ctx, taskEntity); err != nil {
		return
	}
	_ = u.hooks.SyncTaskMetadata(ctx, taskIDStr, taskEntity, userID)
}
