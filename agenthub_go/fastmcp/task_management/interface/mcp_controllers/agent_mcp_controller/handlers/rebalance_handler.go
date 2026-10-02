package handlers

// Agent Rebalance Handler (Python rebalance_handler.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

// AgentRebalanceHandler ports AgentRebalanceHandler.
type AgentRebalanceHandler struct {
	responseFormatter ResponseFormatter
}

// NewAgentRebalanceHandler ports __init__(response_formatter).
func NewAgentRebalanceHandler(responseFormatter ResponseFormatter) *AgentRebalanceHandler {
	return &AgentRebalanceHandler{responseFormatter: responseFormatter}
}

// RebalanceAgents ports rebalance_agents(facade, project_id).
func (h *AgentRebalanceHandler) RebalanceAgents(ctx context.Context, facade *facades.AgentApplicationFacade, projectID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"rebalance",
				fmt.Sprintf("Failed to rebalance agents: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID),
			)
		}
	}()

	data := facade.RebalanceAgents(ctx, projectID)

	// Extract rebalancing statistics if available
	rebalancedCount := 0
	if v, ok := data.Get("rebalanced_agents"); ok {
		if n, ok := v.(int); ok {
			rebalancedCount = n
		}
	}

	return h.responseFormatter.CreateSuccessResponse(
		"rebalance",
		data,
		metaMap(
			"project_id", projectID,
			"rebalanced_agents", rebalancedCount,
			"success_message", fmt.Sprintf("Agent rebalancing completed successfully (%d agents affected)", rebalancedCount),
		),
	)
}
