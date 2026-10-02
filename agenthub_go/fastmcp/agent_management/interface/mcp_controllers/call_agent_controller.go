// Package mcp_controllers ports agent_management/interface/mcp_controllers.
package mcp_controllers

import (
	"context"

	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// FastMCPServer is the minimal FastMCP server interface for tool registration.
type FastMCPServer interface {
	Tool(name string, description string, fn any)
}

// CallAgentMCPController wraps CallAgentMCPTool following the MCP controller pattern.
type CallAgentMCPController struct {
	auth   AuthenticationService
	facade AgentConfigProvider
}

// NewCallAgentMCPController creates a new CallAgentMCPController.
func NewCallAgentMCPController(auth AuthenticationService, facade AgentConfigProvider) *CallAgentMCPController {
	return &CallAgentMCPController{
		auth:   auth,
		facade: facade,
	}
}

// CallAgent loads and invokes a specialized agent.
func (c *CallAgentMCPController) CallAgent(ctx context.Context, nameAgent string, userID *string) *tmentities.OrderedMap[any] {
	return CallAgentMCPTool(ctx, nameAgent, userID, c.auth, c.facade)
}

// RegisterTools registers the call_agent tool with an MCP server instance.
func (c *CallAgentMCPController) RegisterTools(server FastMCPServer) {
	if server == nil {
		return
	}
	server.Tool(
		"call_agent",
		"Load and invoke a specialized agent by name using the database-backed "+
			"user agent instance system. Returns agent configuration including "+
			"system_prompt, tools, and capabilities.",
		func(ctx context.Context, nameAgent string, userID *string) *tmentities.OrderedMap[any] {
			return c.CallAgent(ctx, nameAgent, userID)
		},
	)
}
