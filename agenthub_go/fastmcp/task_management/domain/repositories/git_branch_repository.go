package repositories

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// GitBranchRepository is the repository interface for git branch operations.
type GitBranchRepository interface {
	// FindByID finds a git branch by ID, optionally filtered by project (nil = any).
	FindByID(ctx context.Context, branchID string, projectID *string) (*entities.GitBranch, error)
	// CreateGitBranch creates a git branch (description default "").
	CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) (map[string]any, error)
	GetGitBranchByID(ctx context.Context, gitBranchID string) (map[string]any, error)
	GetGitBranchByName(ctx context.Context, projectID, gitBranchName string) (map[string]any, error)
	ListGitBranchs(ctx context.Context, projectID string) (map[string]any, error)
	UpdateGitBranch(ctx context.Context, gitBranchID string, gitBranchName, gitBranchDescription *string) (map[string]any, error)
	DeleteGitBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error)
	AssignAgentToBranch(ctx context.Context, projectID, agentID, gitBranchName string) (map[string]any, error)
	UnassignAgentFromBranch(ctx context.Context, projectID, agentID, gitBranchName string) (map[string]any, error)
	GetBranchStatistics(ctx context.Context, projectID, gitBranchID string) (map[string]any, error)
	ArchiveBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error)
	RestoreBranch(ctx context.Context, projectID, gitBranchID string) (map[string]any, error)
}
