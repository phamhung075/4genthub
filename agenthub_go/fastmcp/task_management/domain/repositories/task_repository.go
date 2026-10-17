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
	// Search searches tasks by query string (Python default limit 10), applying
	// the optional status/priority/assignees/labels filters. offset skips that many
	// matches before the page is taken, so consecutive pages do not overlap.
	Search(ctx context.Context, query string, filters map[string]any, limit, offset int) ([]*entities.Task, error)
	Delete(ctx context.Context, taskID value_objects.TaskId) (bool, error)
	Exists(ctx context.Context, taskID value_objects.TaskId) (bool, error)
	GetNextID(ctx context.Context) (value_objects.TaskId, error)
	Count(ctx context.Context) (int, error)
	GetStatistics(ctx context.Context) (map[string]any, error)
	// FindByCriteria finds tasks by multiple criteria; a nil query.Limit means no limit.
	FindByCriteria(ctx context.Context, filters map[string]any, query ListQuery) ([]*entities.Task, error)
	// CountByCriteria counts the tasks the same filters select, so a page's caller can report a
	// total that is the board's, not the page's.
	CountByCriteria(ctx context.Context, filters map[string]any) (int, error)
	// FindByIDAllStates finds a task across all states (active, completed, archived).
	FindByIDAllStates(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
}

// ListQuery is one page request: the caller's limit and offset and the ordering it asked for.
// A nil Limit means no limit, a nil Offset means the first page, and an empty SortBy means
// updated_at. A repository MUST reject an ordering it cannot serve rather than fall back to its
// default, because a caller that believes its sort was applied reads the rows as ordered.
type ListQuery struct {
	Limit     *int
	Offset    *int
	SortBy    string
	SortOrder string // "asc" or "desc"; empty means "desc"
}
