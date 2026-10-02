package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// gbWrapGitBranchService is the consumer-side surface of GitBranchService
// (application/services/git_branch_service.py), which has no Go port yet. The
// Python wrapper runs the async coroutine through _run_async; Go service methods
// are synchronous, so the wrapper delegates directly and passes ctx.
type gbWrapGitBranchService interface {
	CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) (*entities.OrderedMap[any], error)
	GetGitBranchByID(ctx context.Context, gitBranchID string) (*entities.OrderedMap[any], error)
	ListGitBranchs(ctx context.Context, projectID string) (*entities.OrderedMap[any], error)
	UpdateGitBranch(ctx context.Context, gitBranchID string, gitBranchName, gitBranchDescription *string) (*entities.OrderedMap[any], error)
	DeleteGitBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error)
	AssignAgentToBranch(ctx context.Context, projectID, agentID, gitBranchName string) (*entities.OrderedMap[any], error)
	UnassignAgentFromBranch(ctx context.Context, projectID, agentID, gitBranchName string) (*entities.OrderedMap[any], error)
	GetBranchStatistics(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error)
	ArchiveBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error)
	RestoreBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error)
}

// GitBranchServiceWrapper is the synchronous wrapper for GitBranchService
// (Python application/services/git_branch_service_wrapper.py).
type GitBranchServiceWrapper struct {
	gbWrapGitBranchService gbWrapGitBranchService
}

// NewGitBranchServiceWrapper mirrors __init__(git_branch_service=None). Python falls
// back to GitBranchService(), which requires repositories and raises
// ValueError("Project repository is required"); since the Go GitBranchService default
// constructor is not available here, a nil service raises the same ValueError.
func NewGitBranchServiceWrapper(gitBranchService gbWrapGitBranchService) (*GitBranchServiceWrapper, error) {
	if gitBranchService == nil {
		return nil, &value_objects.ValueError{Msg: "Project repository is required"}
	}
	return &GitBranchServiceWrapper{gbWrapGitBranchService: gitBranchService}, nil
}

// CreateGitBranch creates a new git branch within a project.
// Python default: git_branch_description="".
func (w *GitBranchServiceWrapper) CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.CreateGitBranch(ctx, projectID, gitBranchName, gitBranchDescription)
}

// GetGitBranchByID gets git branch information by git_branch_id.
func (w *GitBranchServiceWrapper) GetGitBranchByID(ctx context.Context, gitBranchID string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.GetGitBranchByID(ctx, gitBranchID)
}

// ListGitBranchs lists all git branches for a project.
func (w *GitBranchServiceWrapper) ListGitBranchs(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.ListGitBranchs(ctx, projectID)
}

// UpdateGitBranch updates an existing git branch.
func (w *GitBranchServiceWrapper) UpdateGitBranch(ctx context.Context, gitBranchID string, gitBranchName, gitBranchDescription *string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.UpdateGitBranch(ctx, gitBranchID, gitBranchName, gitBranchDescription)
}

// DeleteGitBranch deletes a git branch.
func (w *GitBranchServiceWrapper) DeleteGitBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.DeleteGitBranch(ctx, projectID, gitBranchID)
}

// AssignAgentToBranch assigns an agent to a git branch.
func (w *GitBranchServiceWrapper) AssignAgentToBranch(ctx context.Context, projectID, agentID, gitBranchName string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.AssignAgentToBranch(ctx, projectID, agentID, gitBranchName)
}

// UnassignAgentFromBranch unassigns an agent from a git branch.
func (w *GitBranchServiceWrapper) UnassignAgentFromBranch(ctx context.Context, projectID, agentID, gitBranchName string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.UnassignAgentFromBranch(ctx, projectID, agentID, gitBranchName)
}

// GetBranchStatistics gets statistics for a specific git branch.
func (w *GitBranchServiceWrapper) GetBranchStatistics(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.GetBranchStatistics(ctx, projectID, gitBranchID)
}

// ArchiveBranch archives a git branch.
func (w *GitBranchServiceWrapper) ArchiveBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.ArchiveBranch(ctx, projectID, gitBranchID)
}

// RestoreBranch restores an archived git branch.
func (w *GitBranchServiceWrapper) RestoreBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	return w.gbWrapGitBranchService.RestoreBranch(ctx, projectID, gitBranchID)
}
