package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ContextRepository is the repository interface for task contexts.
type ContextRepository interface {
	CreateContext(ctx context.Context, c *entities.TaskContext) (map[string]any, error)
	GetContext(ctx context.Context, taskID string) (*entities.TaskContext, error)
	UpdateContext(ctx context.Context, c *entities.TaskContext) (map[string]any, error)
	DeleteContext(ctx context.Context, taskID string) (map[string]any, error)
	ListContexts(ctx context.Context) ([]*entities.TaskContext, error)
	GetProperty(ctx context.Context, taskID, propertyPath string) (any, error)
	UpdateProperty(ctx context.Context, taskID, propertyPath string, value any) (map[string]any, error)
	MergeContextData(ctx context.Context, taskID string, data map[string]any) (map[string]any, error)
	AddInsight(ctx context.Context, taskID string, insight entities.ContextInsight) (map[string]any, error)
	AddProgress(ctx context.Context, taskID string, progress entities.ContextProgressAction) (map[string]any, error)
	UpdateNextSteps(ctx context.Context, taskID string, nextSteps []string) (map[string]any, error)
	ContextExists(ctx context.Context, taskID string) (bool, error)
	GetContextMetadata(ctx context.Context, taskID string) (map[string]any, error)
	// SearchContexts searches contexts (Python default limit 10).
	SearchContexts(ctx context.Context, query string, limit int) ([]*entities.TaskContext, error)
}
