"""
Git Branch Management Tool Description

This module provides comprehensive descriptions for git branch management operations
following the established pattern of other tool descriptions in the system.
"""

# Main description for the manage_git_branch tool
MANAGE_GIT_BRANCH_DESCRIPTION = """
GIT BRANCH MANAGEMENT - Branch operations: CRUD | agent assignment | lifecycle | statistics

ACTIONS: create | get | list | update | delete | assign_agent | unassign_agent | get_statistics | archive | restore

KEY PARAMS: project_id (REQUIRED for all) | git_branch_name (REQUIRED for create) | git_branch_id (REQUIRED for most except create/list) | agent_id (REQUIRED for assign/unassign)

AGENT ASSIGNMENT: Use git_branch_name OR git_branch_id for identification

STATISTICS: total_tasks | completed_tasks | progress_percentage

ERRORS: Missing fields→specific error | Duplicate names→rejected | Invalid UUIDs→clear error
"""

MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION = {
    "action": "Git branch management action to perform. Valid values: create, get, list, update, delete, assign_agent, unassign_agent, get_statistics, archive, restore",
    "project_id": "Project identifier for the git branch operation",
    "git_branch_id": "Git branch identifier (UUID). Required for most actions except create/list",
    "git_branch_name": "Git branch name. Required for create, optional for update. Can be used instead of git_branch_id for agent assignment",
    "git_branch_description": "Description of the git branch. Optional for create/update operations",
    "agent_id": "Agent identifier for assignment operations. Required for assign_agent/unassign_agent actions",
    "user_id": "User identifier for authentication and audit trails",
}

MANAGE_GIT_BRANCH_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["action"],
        },
        # Project identification parameters
        "project_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["project_id"],
        },
        # Branch identification parameters
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["git_branch_id"],
        },
        "git_branch_name": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["git_branch_name"],
        },
        # Branch configuration parameters
        "git_branch_description": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION[
                "git_branch_description"
            ],
        },
        # Agent assignment parameters
        "agent_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["agent_id"],
        },
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["user_id"],
        },
    },
    "required": [
        "action"
    ],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False,
}


def get_manage_git_branch_parameters():
    """Get manage git branch parameters for use in controller."""
    return MANAGE_GIT_BRANCH_PARAMS["properties"]


def get_manage_git_branch_description():
    """Get manage git branch description for use in controller."""
    return MANAGE_GIT_BRANCH_DESCRIPTION
