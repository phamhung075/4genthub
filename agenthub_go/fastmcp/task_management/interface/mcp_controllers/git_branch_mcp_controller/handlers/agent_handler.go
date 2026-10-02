package handlers

// Git Branch Agent Handler (Python agent_handler.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GitBranchAgentHandler ports GitBranchAgentHandler.
type GitBranchAgentHandler struct {
	responseFormatter ResponseFormatter
}

// NewGitBranchAgentHandler ports __init__(response_formatter).
func NewGitBranchAgentHandler(responseFormatter ResponseFormatter) *GitBranchAgentHandler {
	return &GitBranchAgentHandler{responseFormatter: responseFormatter}
}

// resolveBranchID ports the shared git_branch_name -> git_branch_id lookup.
// It returns the resolved id, or an error response when the name is unknown.
func (h *GitBranchAgentHandler) resolveBranchID(ctx context.Context, facade *facades.GitBranchApplicationFacade, operation, projectID string, gitBranchID, gitBranchName *string, agentID string) (string, *entities.OrderedMap[any]) {
	resolved := ""
	if gitBranchID != nil {
		resolved = *gitBranchID
	}

	if gitBranchName != nil && *gitBranchName != "" && resolved == "" {
		branchesResult := facade.ListGitBranchs(ctx, projectID)
		var branchesValue any
		if branchesResult != nil {
			branchesValue, _ = branchesResult.Get("git_branches")
		}
		gitBranches := branchListOf(branchesValue)

		var matchingBranch any
		for _, branch := range gitBranches {
			if v := branchName(branch); v != nil && value_objects.PyStr(v) == *gitBranchName {
				matchingBranch = branch
				break
			}
		}

		if matchingBranch == nil {
			available := make([]any, 0, len(gitBranches))
			for _, b := range gitBranches {
				available = append(available, branchName(b))
			}
			return "", h.responseFormatter.CreateErrorResponse(
				operation,
				fmt.Sprintf("Git branch with name '%s' not found in project '%s'", *gitBranchName, projectID),
				ErrorCodeResourceNotFound,
				metaMap("project_id", projectID, "git_branch_name", *gitBranchName, "agent_id", agentID, "available_branches", available),
			)
		}

		resolved = value_objects.PyStr(branchID(matchingBranch))
	}

	if resolved == "" {
		return "", h.responseFormatter.CreateErrorResponse(
			operation,
			"Either git_branch_id or git_branch_name must be provided",
			ErrorCodeValidation,
			metaMap("project_id", projectID, "agent_id", agentID),
		)
	}
	return resolved, nil
}

// AssignAgent ports assign_agent(facade, project_id, git_branch_id, git_branch_name, agent_id).
func (h *GitBranchAgentHandler) AssignAgent(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID string, gitBranchID, gitBranchName *string, agentID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("assign_agent", fmt.Sprintf("Failed to assign agent: %v", r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "git_branch_id", gitBranchID, "git_branch_name", gitBranchName, "agent_id", agentID))
		}
	}()

	resolvedID, errResp := h.resolveBranchID(ctx, facade, "assign_agent", projectID, gitBranchID, gitBranchName, agentID)
	if errResp != nil {
		return errResp
	}

	data := facade.AssignAgent(ctx, resolvedID, agentID, &projectID)

	return h.responseFormatter.CreateSuccessResponse("assign_agent", data, metaMap(
		"project_id", projectID,
		"git_branch_id", resolvedID,
		"git_branch_name", gitBranchName,
		"agent_id", agentID,
		"message", fmt.Sprintf("Agent '%s' assigned to git branch successfully", agentID),
	))
}

// UnassignAgent ports unassign_agent(facade, project_id, git_branch_id, git_branch_name, agent_id).
func (h *GitBranchAgentHandler) UnassignAgent(ctx context.Context, facade *facades.GitBranchApplicationFacade, projectID string, gitBranchID, gitBranchName *string, agentID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("unassign_agent", fmt.Sprintf("Failed to unassign agent: %v", r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "git_branch_id", gitBranchID, "git_branch_name", gitBranchName, "agent_id", agentID))
		}
	}()

	resolvedID, errResp := h.resolveBranchID(ctx, facade, "unassign_agent", projectID, gitBranchID, gitBranchName, agentID)
	if errResp != nil {
		return errResp
	}

	data := facade.UnassignAgent(ctx, resolvedID, agentID, &projectID)

	return h.responseFormatter.CreateSuccessResponse("unassign_agent", data, metaMap(
		"project_id", projectID,
		"git_branch_id", resolvedID,
		"git_branch_name", gitBranchName,
		"agent_id", agentID,
		"message", fmt.Sprintf("Agent '%s' unassigned from git branch successfully", agentID),
	))
}
