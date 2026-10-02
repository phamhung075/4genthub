// call_agent.go ports task_management/application/use_cases/call_agent.py.
package use_cases

import (
	"context"

	"agenthub/fastmcp/agent_management/interface/mcp_controllers"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
)

// CallAgentUseCase is Python's CallAgentUseCase: a lightweight wrapper around the
// agent_management module's call_agent MCP tool. Python's parameterless __init__ becomes
// the collaborators the Go MCP tool needs.
type CallAgentUseCase struct {
	Auth   mcp_controllers.AuthenticationService
	Facade mcp_controllers.AgentConfigProvider
}

// NewCallAgentUseCase mirrors CallAgentUseCase.__init__ (which only stores nothing);
// the Go tool requires its ambient services to be injected.
func NewCallAgentUseCase(auth mcp_controllers.AuthenticationService, facade mcp_controllers.AgentConfigProvider) *CallAgentUseCase {
	return &CallAgentUseCase{Auth: auth, Facade: facade}
}

// Execute mirrors CallAgentUseCase.execute; user_id is Optional -> *string.
func (u *CallAgentUseCase) Execute(ctx context.Context, nameAgent string, userID *string) *tmentities.OrderedMap[any] {
	return mcp_controllers.CallAgentMCPTool(ctx, nameAgent, userID, u.Auth, u.Facade)
}
