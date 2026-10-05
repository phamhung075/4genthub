package handlers

// Agent Assignment Handler (Python assignment_handler.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

// AgentAssignmentHandler ports AgentAssignmentHandler.
type AgentAssignmentHandler struct {
	responseFormatter ResponseFormatter
}

// NewAgentAssignmentHandler ports __init__(response_formatter).
func NewAgentAssignmentHandler(responseFormatter ResponseFormatter) *AgentAssignmentHandler {
	return &AgentAssignmentHandler{responseFormatter: responseFormatter}
}

// AssignAgent ports assign_agent(facade, project_id, agent_id, git_branch_id).
func (h *AgentAssignmentHandler) AssignAgent(ctx context.Context, facade *facades.AgentApplicationFacade, projectID, agentID, gitBranchID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"assign",
				fmt.Sprintf("Failed to assign agent: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID, "agent_id", agentID, "git_branch_id", gitBranchID),
			)
		}
	}()

	data := facade.AssignAgent(ctx, projectID, agentID, gitBranchID)
	return h.responseFormatter.CreateSuccessResponse(
		"assign",
		data,
		metaMap(
			"project_id", projectID,
			"agent_id", agentID,
			"git_branch_id", gitBranchID,
			"success_message", "Agent assigned successfully",
		),
	)
}

// UnassignAgent ports unassign_agent(facade, project_id, agent_id, git_branch_id).
func (h *AgentAssignmentHandler) UnassignAgent(ctx context.Context, facade *facades.AgentApplicationFacade, projectID, agentID, gitBranchID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"unassign",
				fmt.Sprintf("Failed to unassign agent: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID, "agent_id", agentID, "git_branch_id", gitBranchID),
			)
		}
	}()

	data := facade.UnassignAgent(ctx, projectID, agentID, &gitBranchID)
	return h.responseFormatter.CreateSuccessResponse(
		"unassign",
		data,
		metaMap(
			"project_id", projectID,
			"agent_id", agentID,
			"git_branch_id", gitBranchID,
			"success_message", "Agent unassigned successfully",
		),
	)
}
