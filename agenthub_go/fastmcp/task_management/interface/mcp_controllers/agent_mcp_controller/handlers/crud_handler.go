package handlers

// Agent CRUD Handler (Python crud_handler.py).

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentCRUDHandler ports AgentCRUDHandler.
type AgentCRUDHandler struct {
	responseFormatter ResponseFormatter
}

// NewAgentCRUDHandler ports __init__(response_formatter).
func NewAgentCRUDHandler(responseFormatter ResponseFormatter) *AgentCRUDHandler {
	return &AgentCRUDHandler{responseFormatter: responseFormatter}
}

// RegisterAgent ports register_agent(facade, project_id, agent_id, name, call_agent, user_id).
func (h *AgentCRUDHandler) RegisterAgent(ctx context.Context, facade *facades.AgentApplicationFacade, projectID string, agentID *string, name string, callAgent, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"register",
				fmt.Sprintf("Failed to register agent: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID, "agent_name", name),
			)
		}
	}()

	// Auto-generate agent_id if not provided
	resolvedAgentID := ""
	if agentID == nil || *agentID == "" {
		resolvedAgentID = value_objects.NewUUIDv4()
	} else {
		resolvedAgentID = *agentID
	}

	namePtr := name
	data := facade.RegisterAgent(ctx, projectID, &resolvedAgentID, &namePtr, callAgent, userID)

	return h.responseFormatter.CreateSuccessResponse(
		"register",
		data,
		metaMap(
			"project_id", projectID,
			"agent_id", resolvedAgentID,
			"agent_name", name,
			"success_message", fmt.Sprintf("Agent '%s' registered successfully", name),
		),
	)
}

// GetAgent ports get_agent(facade, project_id, agent_id).
func (h *AgentCRUDHandler) GetAgent(ctx context.Context, facade *facades.AgentApplicationFacade, projectID, agentID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"get",
				fmt.Sprintf("Failed to retrieve agent: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID, "agent_id", agentID),
			)
		}
	}()

	data := facade.GetAgent(ctx, projectID, agentID)
	return h.responseFormatter.CreateSuccessResponse(
		"get",
		data,
		metaMap(
			"project_id", projectID,
			"agent_id", agentID,
			"success_message", "Agent retrieved successfully",
		),
	)
}

// ListAgents ports list_agents(facade, project_id).
func (h *AgentCRUDHandler) ListAgents(ctx context.Context, facade *facades.AgentApplicationFacade, projectID string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"list",
				fmt.Sprintf("Failed to list agents: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID),
			)
		}
	}()

	data := facade.ListAgents(ctx, projectID)
	agentCount := pyLen(data.GetAny("agents"))
	return h.responseFormatter.CreateSuccessResponse(
		"list",
		data,
		metaMap(
			"project_id", projectID,
			"agent_count", agentCount,
			"success_message", fmt.Sprintf("Retrieved %d agents", agentCount),
		),
	)
}

// UpdateAgent ports update_agent(facade, project_id, agent_id, name, call_agent, user_id).
func (h *AgentCRUDHandler) UpdateAgent(ctx context.Context, facade *facades.AgentApplicationFacade, projectID, agentID string, name, callAgent, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"update",
				fmt.Sprintf("Failed to update agent: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID, "agent_id", agentID),
			)
		}
	}()

	data := facade.UpdateAgent(ctx, projectID, agentID, name, callAgent, userID)
	return h.responseFormatter.CreateSuccessResponse(
		"update",
		data,
		metaMap(
			"project_id", projectID,
			"agent_id", agentID,
			"updated_name", pyAny(name),
			"success_message", "Agent updated successfully",
		),
	)
}

// UnregisterAgent ports unregister_agent(facade, project_id, agent_id, user_id).
func (h *AgentCRUDHandler) UnregisterAgent(ctx context.Context, facade *facades.AgentApplicationFacade, projectID, agentID string, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(
				"unregister",
				fmt.Sprintf("Failed to unregister agent: %v", r),
				ErrorCodeOperationFailed,
				metaMap("project_id", projectID, "agent_id", agentID),
			)
		}
	}()

	data := facade.UnregisterAgent(ctx, projectID, agentID, userID)
	return h.responseFormatter.CreateSuccessResponse(
		"unregister",
		data,
		metaMap(
			"project_id", projectID,
			"agent_id", agentID,
			"success_message", "Agent unregistered successfully",
		),
	)
}

// pyAny converts a *string to any, preserving Python None (nil).
func pyAny(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// pyLen mirrors Python len(value) for the list/dict shapes used here; a missing
// or non-sized value yields 0 (Python would raise, but .get default covers the
// missing-key case and the facade always returns a list).
func pyLen(v any) int {
	switch t := v.(type) {
	case []*entities.OrderedMap[any]:
		return len(t)
	case []any:
		return len(t)
	case *entities.OrderedMap[any]:
		if t == nil {
			return 0
		}
		return t.Len()
	default:
		return 0
	}
}
