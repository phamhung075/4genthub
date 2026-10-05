package handlers

// Git Branch Advanced Handler (Python advanced_handler.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

// GitBranchAdvancedHandler ports GitBranchAdvancedHandler.
type GitBranchAdvancedHandler struct {
	responseFormatter ResponseFormatter
}

// NewGitBranchAdvancedHandler ports __init__(response_formatter).
func NewGitBranchAdvancedHandler(responseFormatter ResponseFormatter) *GitBranchAdvancedHandler {
	return &GitBranchAdvancedHandler{responseFormatter: responseFormatter}
}

// GetStatistics ports get_statistics(facade, project_id, git_branch_id).
func (h *GitBranchAdvancedHandler) GetStatistics(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID, gitBranchID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("get_statistics", fmt.Sprintf("Failed to get statistics: %v", r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "git_branch_id", gitBranchID))
		}
	}()

	data := facade.GetStatistics(ctx, projectID, gitBranchID)

	return h.responseFormatter.CreateSuccessResponse("get_statistics", data, metaMap(
		"project_id", projectID,
		"git_branch_id", gitBranchID,
		"message", "Git branch statistics retrieved successfully",
	))
}

// ArchiveGitBranch ports archive_git_branch. The Python facade has no
// archive_git_branch attribute, so the call raises AttributeError which the
// handler catches and turns into this exact error response; the quirk is kept.
func (h *GitBranchAdvancedHandler) ArchiveGitBranch(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID, gitBranchID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("archive", fmt.Sprintf("Failed to archive git branch: %v", r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "git_branch_id", gitBranchID))
		}
	}()

	_ = facade
	_ = ctx
	return h.responseFormatter.CreateErrorResponse(
		"archive",
		"Failed to archive git branch: 'GitBranchApplicationFacade' object has no attribute 'archive_git_branch'",
		ErrorCodeOperationFailed,
		metaMap("project_id", projectID, "git_branch_id", gitBranchID),
	)
}

// RestoreGitBranch ports restore_git_branch. Like archive, the Python facade has
// no restore_git_branch attribute; the AttributeError-driven error response is kept.
func (h *GitBranchAdvancedHandler) RestoreGitBranch(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID, gitBranchID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("restore", fmt.Sprintf("Failed to restore git branch: %v", r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "git_branch_id", gitBranchID))
		}
	}()

	_ = facade
	_ = ctx
	return h.responseFormatter.CreateErrorResponse(
		"restore",
		"Failed to restore git branch: 'GitBranchApplicationFacade' object has no attribute 'restore_git_branch'",
		ErrorCodeOperationFailed,
		metaMap("project_id", projectID, "git_branch_id", gitBranchID),
	)
}
