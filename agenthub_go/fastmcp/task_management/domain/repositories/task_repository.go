package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskRepository is the repository interface for the Task aggregate.
type TaskRepository interface {
	// Save saves a task; it returns the saved task, or nil on failure.
	Save(ctx context.Context, task *entities.Task) (*entities.Task, error)
	FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
	FindAll(ctx context.Context) ([]*entities.Task, error)
	FindByStatus(ctx context.Context, status value_objects.TaskStatus) ([]*entities.Task, error)
	FindByPriority(ctx context.Context, priority value_objects.Priority) ([]*entities.Task, error)
	FindByAssignee(ctx context.Context, assignee string) ([]*entities.Task, error)
	// FindByLabels finds tasks containing any of the labels.
	FindByLabels(ctx context.Context, labels []string) ([]*entities.Task, error)
	// Search searches tasks by query string (Python default limit 10).
	Search(ctx context.Context, query string, limit int) ([]*entities.Task, error)
	Delete(ctx context.Context, taskID value_objects.TaskId) (bool, error)
	Exists(ctx context.Context, taskID value_objects.TaskId) (bool, error)
	GetNextID(ctx context.Context) (value_objects.TaskId, error)
	Count(ctx context.Context) (int, error)
	GetStatistics(ctx context.Context) (map[string]any, error)
	// FindByCriteria finds tasks by multiple criteria; limit nil means no limit.
	FindByCriteria(ctx context.Context, filters map[string]any, limit *int) ([]*entities.Task, error)
	// FindByIDAllStates finds a task across all states (active, completed, archived).
	FindByIDAllStates(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
}
