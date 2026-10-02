package use_cases

import (
	"context"

	task "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
)

// TaskEventHooks are the post-write side effects shared by the task use cases: the
// TaskContextSyncService metadata sync and the WebSocketNotificationService broadcast
// (payload built by WebSocketPayloadBuilder). They sit behind an interface because the
// services import this package. Both are best-effort: Python logs failures and continues.
type TaskEventHooks interface {
	// SyncTaskMetadata is TaskContextSyncService.sync_task_metadata.
	SyncTaskMetadata(ctx context.Context, taskID string, task *entities.Task, userID string) error
	// NotifyTaskEvent builds the complete payload and calls sync_broadcast_task_event
	// (user falls back to "system" when userID is nil or empty).
	NotifyTaskEvent(ctx context.Context, eventType string, task *entities.Task, response *task.TaskResponse, userID *string, gitBranchID string)
}
