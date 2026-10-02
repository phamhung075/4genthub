// Package routes ports fastmcp/server/routes/agent_routes.py.
package routes

import (
	"context"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

// AgentRegisterRequest mirrors RegisterAgentRequest.
type AgentRegisterRequest struct {
	Name         string                    `json:"name"`
	Role         string                    `json:"role"`
	Description  *string                   `json:"description,omitempty"`
	Capabilities []string                  `json:"capabilities,omitempty"`
	Metadata     *entities.OrderedMap[any] `json:"metadata,omitempty"`
}

// AgentUpdateRequest mirrors UpdateAgentRequest.
type AgentUpdateRequest struct {
	Name         *string                   `json:"name,omitempty"`
	Role         *string                   `json:"role,omitempty"`
	Description  *string                   `json:"description,omitempty"`
	Capabilities []string                  `json:"capabilities,omitempty"`
	Metadata     *entities.OrderedMap[any] `json:"metadata,omitempty"`
}

// AgentAssignRequest mirrors AssignAgentRequest.
type AgentAssignRequest struct {
	TaskID *string `json:"task_id,omitempty"`
	Role   *string `json:"role,omitempty"`
}

// AgentUnassignRequest mirrors UnassignAgentRequest.
type AgentUnassignRequest struct {
	TaskID *string `json:"task_id,omitempty"`
}

// AgentController is the controller interface for user-scoped agent operations.
type AgentController interface {
	GetAllAgentsMetadata(ctx context.Context, userID string) (ControllerResult, error)
	GetSingleAgentMetadata(ctx context.Context, agentName, userID string) (ControllerResult, error)
	RegisterAgent(ctx context.Context, req AgentRegisterRequest, userID string) (ControllerResult, error)
	ListAgents(ctx context.Context, userID string) (ControllerResult, error)
	UpdateAgent(ctx context.Context, agentID string, req AgentUpdateRequest, userID string) (ControllerResult, error)
	DeleteAgent(ctx context.Context, agentID, userID string) (ControllerResult, error)
	AssignAgent(ctx context.Context, agentID string, req AgentAssignRequest, userID string) (ControllerResult, error)
	UnassignAgent(ctx context.Context, agentID string, req AgentUnassignRequest, userID string) (ControllerResult, error)
}

// GetAllAgentsMetadata gets metadata for all available agents.
func GetAllAgentsMetadata(ctx context.Context, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.GetAllAgentsMetadata(ctx, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to fetch agent metadata")
	}
	if !result.Success {
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to fetch agent metadata"))
	}
	return result.Body, nil
}

// GetSingleAgentMetadata gets metadata for a specific agent.
func GetSingleAgentMetadata(ctx context.Context, agentName string, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.GetSingleAgentMetadata(ctx, agentName, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to fetch agent metadata")
	}
	if !result.Success {
		if containsNotFound(result.Error) {
			return nil, httpErr(404, "Agent "+agentName+" not found")
		}
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to fetch agent metadata"))
	}
	return result.Body, nil
}

// RegisterAgent registers a new agent.
func RegisterAgent(ctx context.Context, req AgentRegisterRequest, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.RegisterAgent(ctx, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to register agent")
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Message, "Failed to register agent"))
	}
	return result.Body, nil
}

// ListAgents lists all agents for the user.
func ListAgents(ctx context.Context, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.ListAgents(ctx, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to fetch agents")
	}
	if !result.Success {
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to fetch agents"))
	}
	return result.Body, nil
}

// UpdateAgent updates an agent.
func UpdateAgent(ctx context.Context, agentID string, req AgentUpdateRequest, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.UpdateAgent(ctx, agentID, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to update agent")
	}
	if !result.Success {
		if containsNotFound(result.Error) {
			return nil, httpErr(404, "Agent "+agentID+" not found")
		}
		return nil, httpErr(400, pyOrStr(result.Message, "Failed to update agent"))
	}
	return result.Body, nil
}

// DeleteAgent deletes an agent.
func DeleteAgent(ctx context.Context, agentID string, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.DeleteAgent(ctx, agentID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to delete agent")
	}
	if !result.Success {
		if containsNotFound(result.Error) {
			return nil, httpErr(404, "Agent "+agentID+" not found")
		}
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to delete agent"))
	}
	return result.Body, nil
}

// AssignAgent assigns an agent to a task.
func AssignAgent(ctx context.Context, agentID string, req AgentAssignRequest, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.AssignAgent(ctx, agentID, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to assign agent")
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Message, "Failed to assign agent"))
	}
	return result.Body, nil
}

// UnassignAgent unassigns an agent from a task.
func UnassignAgent(ctx context.Context, agentID string, req AgentUnassignRequest, currentUser *authdomain.User, c AgentController) (*entities.OrderedMap[any], error) {
	result, err := c.UnassignAgent(ctx, agentID, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to unassign agent")
	}
	if !result.Success {
		return nil, httpErr(400, pyOrStr(result.Message, "Failed to unassign agent"))
	}
	return result.Body, nil
}
