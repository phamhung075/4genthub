package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SubtaskRepository is the repository interface for subtasks.
type SubtaskRepository interface {
	Save(ctx context.Context, subtask *entities.Subtask) (bool, error)
	FindByID(ctx context.Context, id string) (*entities.Subtask, error)
	FindByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error)
	FindByAssignee(ctx context.Context, assignee string) ([]*entities.Subtask, error)
	FindByStatus(ctx context.Context, status string) ([]*entities.Subtask, error)
	FindCompleted(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error)
	FindPending(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error)
	Delete(ctx context.Context, id string) (bool, error)
	DeleteByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (bool, error)
	Exists(ctx context.Context, id string) (bool, error)
	CountByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (int, error)
	CountCompletedByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) (int, error)
	GetNextID(ctx context.Context, parentTaskID value_objects.TaskId) (value_objects.TaskId, error)
	GetSubtaskProgress(ctx context.Context, parentTaskID value_objects.TaskId) (map[string]any, error)
	BulkUpdateStatus(ctx context.Context, parentTaskID value_objects.TaskId, status string) (bool, error)
	BulkComplete(ctx context.Context, parentTaskID value_objects.TaskId) (bool, error)
	RemoveSubtask(ctx context.Context, parentTaskID, subtaskID string) (bool, error)
}
