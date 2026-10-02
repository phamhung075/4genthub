package handlers

// Agent Invocation Handler (Python agent_invocation_handler.py).

import (
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
)

// CallAgentUseCase is the application use case surface used by the invocation
// handler (Python call_agent_use_case.execute(name_agent)).
type CallAgentUseCase interface {
	Execute(nameAgent string) *entities.OrderedMap[any]
}

// AgentInvocationHandler ports AgentInvocationHandler.
type AgentInvocationHandler struct {
	callAgentUseCase CallAgentUseCase
}

// NewAgentInvocationHandler ports __init__(call_agent_use_case).
func NewAgentInvocationHandler(callAgentUseCase CallAgentUseCase) *AgentInvocationHandler {
	return &AgentInvocationHandler{callAgentUseCase: callAgentUseCase}
}

// InvokeAgent ports invoke_agent(name_agent, available_agents).
func (h *AgentInvocationHandler) InvokeAgent(nameAgent string, availableAgents []string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = metaMap(
				"success", false,
				"error", fmt.Sprintf("Call agent operation failed: %v", r),
				"error_code", "INTERNAL_ERROR",
				"details", fmt.Sprint(r),
				"available_agents", availableAgents,
			)
		}
	}()

	if nameAgent == "" {
		return metaMap(
			"success", false,
			"error", "Missing required field: name_agent",
			"error_code", "MISSING_FIELD",
			"field", "name_agent",
			"expected", "A valid agent name string",
			"hint", "Include 'name_agent' in your request body",
			"available_agents", availableAgents,
		)
	}

	return h.callAgentUseCase.Execute(nameAgent)
}
