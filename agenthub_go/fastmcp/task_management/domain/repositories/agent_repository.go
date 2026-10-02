package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// AgentRepository is the repository interface for agents.
type AgentRepository interface {
	RegisterAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error)
	UnregisterAgent(ctx context.Context, projectID, agentID string) (map[string]any, error)
	AssignAgentToTree(ctx context.Context, projectID, agentID, gitBranchID string) (map[string]any, error)
	// UnassignAgentFromTree: gitBranchID nil means all trees.
	UnassignAgentFromTree(ctx context.Context, projectID, agentID string, gitBranchID *string) (map[string]any, error)
	GetAgent(ctx context.Context, projectID, agentID string) (map[string]any, error)
	ListAgents(ctx context.Context, projectID string) (map[string]any, error)
	UpdateAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error)
	RebalanceAgents(ctx context.Context, projectID string) (map[string]any, error)
}
