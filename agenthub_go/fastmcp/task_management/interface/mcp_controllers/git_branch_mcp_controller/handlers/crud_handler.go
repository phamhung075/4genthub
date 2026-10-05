package handlers

// Git Branch CRUD Handler (Python crud_handler.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GitBranchCRUDHandler ports GitBranchCRUDHandler.
type GitBranchCRUDHandler struct {
	responseFormatter ResponseFormatter
}

// NewGitBranchCRUDHandler ports __init__(response_formatter).
func NewGitBranchCRUDHandler(responseFormatter ResponseFormatter) *GitBranchCRUDHandler {
	return &GitBranchCRUDHandler{responseFormatter: responseFormatter}
}

// CreateGitBranch ports create_git_branch(facade, project_id, git_branch_name,
// git_branch_description=None).
func (h *GitBranchCRUDHandler) CreateGitBranch(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID, gitBranchName string, gitBranchDescription *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("create", fmt.Sprintf("Failed to create git branch: %v", r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "git_branch_name", gitBranchName))
		}
	}()

	description := ""
	if gitBranchDescription != nil {
		description = *gitBranchDescription
	}
	data := facade.CreateGitBranch(ctx, projectID, gitBranchName, description)

	return h.responseFormatter.CreateSuccessResponse("create", data, metaMap(
		"project_id", projectID,
		"git_branch_name", gitBranchName,
		"message", fmt.Sprintf("Git branch '%s' created successfully", gitBranchName),
	))
}

// UpdateGitBranch ports update_git_branch(facade, git_branch_id, project_id,
// git_branch_name=None, git_branch_description=None).
func (h *GitBranchCRUDHandler) UpdateGitBranch(ctx context.Context, facade *facades.GitBranchApplicationFacade, gitBranchID string, projectID string, gitBranchName, gitBranchDescription *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("update", fmt.Sprintf("Failed to update git branch: %v", r), ErrorCodeOperationFailed, metaMap("git_branch_id", gitBranchID, "project_id", projectID))
		}
	}()

	data := facade.UpdateGitBranch(ctx, gitBranchID, gitBranchName, gitBranchDescription, &projectID)

	return h.responseFormatter.CreateSuccessResponse("update", data, metaMap(
		"git_branch_id", gitBranchID,
		"project_id", projectID,
		"message", "Git branch updated successfully",
	))
}

// GetGitBranch ports get_git_branch(facade, project_id, git_branch_id).
func (h *GitBranchCRUDHandler) GetGitBranch(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID, gitBranchID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("get", fmt.Sprintf("Failed to retrieve git branch: %v", r), ErrorCodeOperationFailed, metaMap("git_branch_id", gitBranchID, "project_id", projectID))
		}
	}()

	data := facade.GetGitBranch(ctx, projectID, gitBranchID)

	return h.responseFormatter.CreateSuccessResponse("get", data, metaMap(
		"git_branch_id", gitBranchID,
		"project_id", projectID,
		"message", "Git branch retrieved successfully",
	))
}

// DeleteGitBranch ports delete_git_branch(facade, project_id, git_branch_id).
func (h *GitBranchCRUDHandler) DeleteGitBranch(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID, gitBranchID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("delete", fmt.Sprintf("Failed to delete git branch: %v", r), ErrorCodeOperationFailed, metaMap("git_branch_id", gitBranchID, "project_id", projectID))
		}
	}()

	data := facade.DeleteGitBranch(ctx, gitBranchID, &projectID)

	// Check if the deletion was successful
	if data != nil {
		if success, ok := data.Get("success"); ok && !value_objects.PyTruthy(success) {
			errorMsg := "Failed to delete git branch"
			if v, ok := data.Get("error"); ok && v != nil {
				errorMsg = value_objects.PyStr(v)
			}
			errorCode := any(ErrorCodeOperationFailed)
			if v, ok := data.Get("error_code"); ok && v != nil {
				errorCode = v
			}
			return h.responseFormatter.CreateErrorResponse("delete", errorMsg, value_objects.PyStr(errorCode), metaMap("git_branch_id", gitBranchID, "project_id", projectID))
		}
	}

	deleted := entities.NewOrderedMap[any]()
	deleted.Set("deleted", true)
	return h.responseFormatter.CreateSuccessResponse("delete", deleted, metaMap(
		"git_branch_id", gitBranchID,
		"project_id", projectID,
		"message", "Git branch deleted successfully",
	))
}

// ListGitBranches ports list_git_branches(facade, project_id).
func (h *GitBranchCRUDHandler) ListGitBranches(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("list", fmt.Sprintf("Failed to list git branches: %v", r), ErrorCodeOperationFailed, metaMap("project_id", projectID))
		}
	}()

	data := facade.ListGitBranchs(ctx, projectID)

	var branches any
	if data != nil {
		branches, _ = data.Get("git_branches")
	}
	count := listLen(branches)

	return h.responseFormatter.CreateSuccessResponse("list", data, metaMap(
		"project_id", projectID,
		"message", fmt.Sprintf("Retrieved %d git branches", count),
	))
}
