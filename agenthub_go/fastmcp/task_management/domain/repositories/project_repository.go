package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// ProjectRepository is the repository interface for projects.
type ProjectRepository interface {
	Save(ctx context.Context, project *entities.Project) error
	FindByID(ctx context.Context, projectID string) (*entities.Project, error)
	FindAll(ctx context.Context) ([]*entities.Project, error)
	Delete(ctx context.Context, projectID string) (bool, error)
	Exists(ctx context.Context, projectID string) (bool, error)
	Update(ctx context.Context, project *entities.Project) error
	FindByName(ctx context.Context, name string) (*entities.Project, error)
	Count(ctx context.Context) (int, error)
	FindProjectsWithAgent(ctx context.Context, agentID string) ([]*entities.Project, error)
	FindProjectsByStatus(ctx context.Context, status string) ([]*entities.Project, error)
	GetProjectHealthSummary(ctx context.Context) (map[string]any, error)
	UnassignAgentFromTree(ctx context.Context, projectID, agentID, gitBranchID string) (map[string]any, error)
}
