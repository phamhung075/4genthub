package factories

// Response Factory for Agent MCP Controller (Python response_factory.py).

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers"
)

// AgentResponseFactory ports AgentResponseFactory.
type AgentResponseFactory struct {
	responseFormatter handlers.ResponseFormatter
}

// NewAgentResponseFactory ports __init__(response_formatter).
func NewAgentResponseFactory(responseFormatter handlers.ResponseFormatter) *AgentResponseFactory {
	return &AgentResponseFactory{responseFormatter: responseFormatter}
}

// CreateMissingFieldError ports create_missing_field_error(field, action).
func (f *AgentResponseFactory) CreateMissingFieldError(field, action string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", "Missing required field: "+field)
	m.Set("error_code", handlers.ErrorCodeMissingField)
	m.Set("field", field)
	m.Set("action", action)
	m.Set("expected", "A valid "+field+" value")
	m.Set("hint", "Include '"+field+"' in your request for action '"+action+"'")
	return m
}

// CreateInvalidActionError ports create_invalid_action_error(invalid_action, valid_actions).
func (f *AgentResponseFactory) CreateInvalidActionError(invalidAction string, validActions []string) *entities.OrderedMap[any] {
	if validActions == nil {
		validActions = []string{
			"register",
			"assign",
			"get",
			"list",
			"update",
			"unassign",
			"unregister",
			"rebalance",
		}
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", "Invalid action")
	m.Set("error_code", handlers.ErrorCodeInvalidAction)
	m.Set("field", "action")
	m.Set("expected", "One of: "+strings.Join(validActions, ", "))
	m.Set("hint", "Invalid action: "+invalidAction+". Use one of the supported actions.")
	return m
}
