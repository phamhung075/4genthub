// Package hooks wires the side effects Python's use cases perform inline (task-context
// creation, metadata sync, WebSocket notifications) to the Go services. It sits above
// use_cases, factories and services, which import each other and so cannot reference the
// concrete services directly.
package hooks

import (
	"agenthub/fastmcp/task_management/application/use_cases"
	"context"

	"agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskHooks implements use_cases.CreateTaskHooks (and TaskEventHooks).
type TaskHooks struct {
	ContextFactory *factories.UnifiedContextFacadeFactory
	Notifier       *services.WebSocketNotificationService
	TaskRepository repositories.TaskRepository
}

func taskIDString(t *entities.Task) string {
	if t.ID == nil {
		return "None"
	}
	return t.ID.Value
}

// CreateTaskContext is the context_facade.create_context(level="task") call of create_task.
func (h *TaskHooks) CreateTaskContext(ctx context.Context, t *entities.Task, userID string, projectID *string, gitBranchID string) (bool, error) {
	if h.ContextFactory == nil {
		return false, nil
	}
	facade, err := h.ContextFactory.CreateFacade(ctx, &userID, projectID, &gitBranchID)
	if err != nil {
		return false, err
	}
	taskData := entities.NewOrderedMap[any]()
	taskData.Set("title", t.Title)
	taskData.Set("status", t.Status.String())
	taskData.Set("description", t.Description)
	taskData.Set("priority", t.Priority.String())
	data := entities.NewOrderedMap[any]()
	data.Set("branch_id", gitBranchID)
	if projectID != nil {
		data.Set("project_id", *projectID)
	} else {
		data.Set("project_id", nil)
	}
	data.Set("task_data", taskData)

	resp, err := facade.CreateContext(ctx, "task", taskIDString(t), data, &userID)
	if err != nil {
		return false, err
	}
	success, _ := resp.Get("success")
	return value_objects.PyTruthy(success), nil
}

// SyncTaskMetadata is TaskContextSyncService(repo, user_id=user).sync_task_metadata.
func (h *TaskHooks) SyncTaskMetadata(ctx context.Context, taskID string, t *entities.Task, userID string) error {
	if h.ContextFactory == nil {
		return nil
	}
	facade, err := h.ContextFactory.CreateFacade(ctx, &userID, nil, nil)
	if err != nil {
		return err
	}
	svc, err := services.NewTaskContextSyncService(h.TaskRepository, nil, &userID, facade)
	if err != nil {
		return err
	}
	return svc.SyncTaskMetadata(ctx, taskID, t)
}

// SyncTaskStatus is TaskContextSyncService(repo).sync_task_status.
func (h *TaskHooks) SyncTaskStatus(ctx context.Context, taskID string, newStatus string) error {
	if h.ContextFactory == nil {
		return nil
	}
	facade, err := h.ContextFactory.CreateFacade(ctx, nil, nil, nil)
	if err != nil {
		return err
	}
	svc, err := services.NewTaskContextSyncService(h.TaskRepository, nil, nil, facade)
	if err != nil {
		return err
	}
	return svc.SyncTaskStatus(ctx, taskID, newStatus)
}

// NotifyTaskEvent builds the complete payload and broadcasts the task event.
func (h *TaskHooks) NotifyTaskEvent(ctx context.Context, eventType string, t *entities.Task, resp *task.TaskResponse, userID *string, gitBranchID string) {
	if h.Notifier == nil {
		return
	}
	payload := services.WebSocketPayloadBuilder{}.BuildTaskPayload(t, resp, true)
	uid := "system"
	if userID != nil && *userID != "" {
		uid = *userID
	}
	branch := gitBranchID
	_ = h.Notifier.SyncBroadcastTask(ctx, services.SyncTaskEventParams{
		EventType: eventType, TaskID: taskIDString(t), UserID: uid, TaskData: payload, GitBranchID: &branch,
	})
}

var _ use_cases.ParentTaskProgressUpdater = (*services.TaskProgressService)(nil)
