"""
Project Management Tool Description

This module contains the comprehensive documentation for the manage_project MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

from __future__ import annotations

MANAGE_PROJECT_DESCRIPTION = """
PROJECT MANAGEMENT - Complete lifecycle: CRUD | health monitoring | resource management | multi-project coordination

ACTIONS: create | get | list | update | delete | project_health_check | cleanup_obsolete | validate_integrity | rebalance_agents

KEY PARAMS: name (REQUIRED for create) | project_id (REQUIRED for most except create/list) | force (bypass safety for maintenance/delete)

FEATURES: Health monitoring | Resource allocation | Cross-project learning | Agent optimization

ERRORS: Missing fields→specific error | Duplicate names→rejected | Invalid UUIDs→clear error | Maintenance→safety warnings
"""

MANAGE_PROJECT_PARAMETERS_DESCRIPTION = {
    "action": "Project management action to perform. Valid values: create, get, list, update, delete, project_health_check, cleanup_obsolete, validate_integrity, rebalance_agents",
    "project_id": "Project identifier (UUID). Required for most actions except create/list",
    "name": "Project name. Required for create, can be used instead of project_id for get action",
    "description": "Project description. Optional for create/update operations",
    "user_id": "User identifier for authentication and audit trails",
    "force": "Force parameter to bypass safety checks for maintenance and delete operations",
}

MANAGE_PROJECT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_PROJECT_PARAMETERS_DESCRIPTION["action"],
        },
        # Project identification parameters
        "project_id": {
            "type": "UUID",
            "description": MANAGE_PROJECT_PARAMETERS_DESCRIPTION["project_id"],
        },
        "name": {
            "type": "string",
            "description": MANAGE_PROJECT_PARAMETERS_DESCRIPTION["name"],
        },
        # Project configuration parameters
        "description": {
            "type": "string",
            "description": MANAGE_PROJECT_PARAMETERS_DESCRIPTION["description"],
        },
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_PROJECT_PARAMETERS_DESCRIPTION["user_id"],
        },
        # Maintenance parameters
        "force": {
            "type": "string",
            "description": MANAGE_PROJECT_PARAMETERS_DESCRIPTION["force"],
        },
    },
    "required": ["action"],
    "additionalProperties": False,
    "_validation_note": "Only action required at schema level - business logic validates per action",
}


def get_manage_project_parameters():
    """Get manage project parameters for use in controller."""
    return MANAGE_PROJECT_PARAMS["properties"]


def get_manage_project_description():
    """Get manage project description for use in controller."""
    return MANAGE_PROJECT_DESCRIPTION
