// Package mcp_controllers ports agent_management/interface/mcp_controllers.
package mcp_controllers

import (
	"context"
	"errors"

	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AuthenticationService is the minimal interface call_agent needs from the
// task_management authentication service (which has no Go port yet).
type AuthenticationService interface {
	GetAuthenticatedUserID(ctx context.Context, providedUserID *string, operationName string) (string, error)
}

// AgentConfigProvider is the minimal facade surface call_agent needs.
type AgentConfigProvider interface {
	GetAgentForCall(ctx context.Context, userID *amvo.UserId, agentSlug string) (*tmentities.OrderedMap[any], error)
}

// CallAgentMCPTool loads an agent configuration, mirroring the Python function that
// catches every error and always returns a response dict.
func CallAgentMCPTool(ctx context.Context, nameAgent string, userID *string, auth AuthenticationService, facade AgentConfigProvider) *tmentities.OrderedMap[any] {
	authenticatedUserID, err := auth.GetAuthenticatedUserID(ctx, userID, "call_agent")
	if err != nil {
		return callAgentFailure(err)
	}
	userIDVO, err := amvo.NewUserId(authenticatedUserID)
	if err != nil {
		return callAgentFailure(err)
	}
	agentConfig, err := facade.GetAgentForCall(ctx, &userIDVO, nameAgent)
	if err != nil {
		var valueErr *tmvo.ValueError
		if errors.As(err, &valueErr) {
			resp := tmentities.NewOrderedMap[any]()
			resp.Set("success", false)
			resp.Set("error", "Agent not found: "+nameAgent)
			resp.Set("message", valueErr.Msg)
			return resp
		}
		return callAgentFailure(err)
	}
	if agentConfig == nil {
		return callAgentFailure(errors.New("'NoneType' object is not subscriptable"))
	}
	resp := tmentities.NewOrderedMap[any]()
	resp.Set("success", true)
	resp.Set("agent", agentConfig)
	resp.Set("source", "agent-management-system")
	return resp
}

func callAgentFailure(err error) *tmentities.OrderedMap[any] {
	resp := tmentities.NewOrderedMap[any]()
	resp.Set("success", false)
	resp.Set("error", "Failed to load agent")
	resp.Set("message", err.Error())
	return resp
}
