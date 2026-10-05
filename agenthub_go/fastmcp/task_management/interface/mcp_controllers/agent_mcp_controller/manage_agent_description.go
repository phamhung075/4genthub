package agent_mcp_controller

// Agent Management Tool Description (Python manage_agent_description.py).

import "agenthub/fastmcp/task_management/domain/entities"

// ManageAgentDescription ports MANAGE_AGENT_DESCRIPTION.
const ManageAgentDescription = `
AGENT MANAGEMENT - Registration & assignment: 33 specialized agents (coding, testing, architecture, DevOps, security, ML, etc.)

ACTIONS: register | assign | get | list | update | unassign | unregister | rebalance

KEY PARAMS: project_id (REQUIRED for all) | name (REQUIRED for register) | agent_id (REQUIRED for most except register/list/rebalance) | git_branch_id (REQUIRED for assign/unassign)

REGISTRATION: agent_id auto-generated if not provided

ERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic
`

// ManageAgentParametersDescription ports MANAGE_AGENT_PARAMETERS_DESCRIPTION.
var ManageAgentParametersDescription = map[string]string{
	"action":        "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance",
	"project_id":    "[REQUIRED] Project identifier for agent management. No default value - must be provided",
	"agent_id":      "Agent identifier. Required for most actions except register/list/rebalance",
	"name":          "Agent name. Required for register, optional for update",
	"call_agent":    "Call agent string or configuration. Optional, for register/update actions",
	"git_branch_id": "Task tree identifier. Required for assign/unassign actions",
	"user_id":       "User identifier for authentication and audit trails",
}

// LegacyManageAgentParameters ports the legacy MANAGE_AGENT_PARAMETERS map.
// (Named with a prefix to avoid colliding with a concurrently-added
// unified_agent_description.go that also declares ManageAgentParameters.)
var LegacyManageAgentParameters = map[string]string{
	"action":        "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance. (string)",
	"project_id":    "Project identifier for agent management. Required for all actions. Must be provided. (string)",
	"agent_id":      "Agent identifier. Required for most actions except register/list/rebalance. (string)",
	"name":          "Agent name. Required for register, optional for update. (string)",
	"call_agent":    "Call agent string or configuration. Optional, for register/update actions. (string)",
	"git_branch_id": "Task tree identifier. Required for assign/unassign actions. (string)",
}

// manageAgentParams ports MANAGE_AGENT_PARAMS (schema wrapper).
func manageAgentParams() *entities.OrderedMap[any] {
	properties := entities.NewOrderedMap[any]()
	for _, field := range []string{"action", "project_id", "agent_id", "name", "call_agent", "git_branch_id", "user_id"} {
		fieldSchema := entities.NewOrderedMap[any]()
		fieldSchema.Set("type", "string")
		fieldSchema.Set("description", ManageAgentParametersDescription[field])
		properties.Set(field, fieldSchema)
	}

	params := entities.NewOrderedMap[any]()
	params.Set("type", "object")
	params.Set("properties", properties)
	params.Set("required", []string{"action"})
	params.Set("additionalProperties", false)
	return params
}

// GetManageAgentParameters ports get_manage_agent_parameters().
func GetManageAgentParameters() any {
	properties, _ := manageAgentParams().Get("properties")
	return properties
}

// GetManageAgentDescription ports get_manage_agent_description().
func GetManageAgentDescription() string {
	return ManageAgentDescription
}
