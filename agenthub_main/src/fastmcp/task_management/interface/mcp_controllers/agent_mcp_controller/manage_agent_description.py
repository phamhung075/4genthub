"""
Agent Management Tool Description

This module contains the comprehensive documentation for the manage_agent MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_AGENT_DESCRIPTION = """
AGENT MANAGEMENT - Registration & assignment: 33 specialized agents (coding, testing, architecture, DevOps, security, ML, etc.)

ACTIONS: register | assign | get | list | update | unassign | unregister | rebalance

KEY PARAMS: project_id (REQUIRED for all) | name (REQUIRED for register) | agent_id (REQUIRED for most except register/list/rebalance) | git_branch_id (REQUIRED for assign/unassign)

REGISTRATION: agent_id auto-generated if not provided

ERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic
"""

MANAGE_AGENT_PARAMETERS_DESCRIPTION = {
    "action": "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance",
    "project_id": "[REQUIRED] Project identifier for agent management. No default value - must be provided",
    "agent_id": "Agent identifier. Required for most actions except register/list/rebalance",
    "name": "Agent name. Required for register, optional for update",
    "call_agent": "Call agent string or configuration. Optional, for register/update actions",
    "git_branch_id": "Task tree identifier. Required for assign/unassign actions",
    "user_id": "User identifier for authentication and audit trails",
}

MANAGE_AGENT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["action"],
        },
        # Agent identification parameters
        "project_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["project_id"],
        },
        "agent_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["agent_id"],
        },
        # Agent configuration parameters
        "name": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["name"],
        },
        "call_agent": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["call_agent"],
        },
        # Context parameters
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["git_branch_id"],
        },
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["user_id"],
        },
    },
    "required": [
        "action"
    ],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False,
}


def get_manage_agent_parameters():
    """Get manage agent parameters for use in controller."""
    return MANAGE_AGENT_PARAMS["properties"]


def get_manage_agent_description():
    """Get manage agent description for use in controller."""
    return MANAGE_AGENT_DESCRIPTION


# Legacy support for existing imports
MANAGE_AGENT_PARAMETERS = {
    "action": "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance. (string)",
    "project_id": "Project identifier for agent management. Required for all actions. Must be provided. (string)",
    "agent_id": "Agent identifier. Required for most actions except register/list/rebalance. (string)",
    "name": "Agent name. Required for register, optional for update. (string)",
    "call_agent": "Call agent string or configuration. Optional, for register/update actions. (string)",
    "git_branch_id": "Task tree identifier. Required for assign/unassign actions. (string)",
}
