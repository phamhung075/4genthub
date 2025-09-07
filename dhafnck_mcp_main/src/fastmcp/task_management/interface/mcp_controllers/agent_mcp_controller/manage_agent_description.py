"""
Agent Management Tool Description

This module contains the comprehensive documentation for the manage_agent MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_AGENT_DESCRIPTION = """
🤖 AGENT MANAGEMENT SYSTEM - Agent Registration and Assignment

⭐ WHAT IT DOES: Manages agent registration, assignment, and lifecycle within projects.
📋 WHEN TO USE: Agent registration, assignment, updates, and project agent management.
🎯 CRITICAL FOR: Multi-agent orchestration and dynamic agent assignment.

| Action      | Required Parameters                  | Optional Parameters                | Description                                      |
|-------------|-------------------------------------|------------------------------------|--------------------------------------------------|
| register    | project_id, name                    | agent_id (auto-generated if blank), call_agent | Register a new agent to a project                |
| assign      | project_id, agent_id, git_branch_id  |                                    | Assign an agent to a task tree (branch)          |
| get         | project_id, agent_id                |                                    | Retrieve agent details                           |
| list        | project_id                          |                                    | List all agents in a project                     |
| update      | project_id, agent_id                | name, call_agent                   | Update agent metadata                            |
| unassign    | project_id, agent_id, git_branch_id  |                                   | Remove agent from a task tree (branch)           |
| unregister  | project_id, agent_id                |                                    | Remove agent from a project                      |
| rebalance   | project_id                          |                                    | Rebalance agent assignments in a project         |

💡 USAGE GUIDELINES:
• Provide all required identifiers for each action (see above).
• Optional parameters can be omitted unless updating values.
• The tool returns detailed error messages for missing or invalid parameters, unknown actions, and internal errors.
• All business logic is delegated to the application layer (AgentApplicationFacade).

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed.
• Unknown actions return an error listing valid actions.
• Internal errors are logged and returned with a generic error message.
"""

MANAGE_AGENT_PARAMETERS_DESCRIPTION = {
    "action": "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance",
    "project_id": "[REQUIRED] Project identifier for agent management. No default value - must be provided",
    "agent_id": "[OPTIONAL] Agent identifier. Required for most actions except register/list/rebalance",
    "name": "[OPTIONAL] Agent name. Required for register, optional for update",
    "call_agent": "[OPTIONAL] Call agent string or configuration. Optional, for register/update actions",
    "git_branch_id": "[OPTIONAL] Task tree identifier. Required for assign/unassign actions",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails"
}

MANAGE_AGENT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Agent identification parameters
        "project_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["project_id"]
        },
        "agent_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["agent_id"]
        },
        
        # Agent configuration parameters
        "name": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["name"]
        },
        "call_agent": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["call_agent"]
        },
        
        # Context parameters
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["git_branch_id"]
        },
        
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["user_id"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
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
    "git_branch_id": "Task tree identifier. Required for assign/unassign actions. (string)"
}