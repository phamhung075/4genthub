"""
Dependency Management Tool Description

This module contains the comprehensive documentation for the manage_dependency MCP tool.
Separated from the controller logic for better maintainability and organization.
"""
MANAGE_DEPENDENCY_DESCRIPTION = """
🔗 DEPENDENCY MANAGEMENT SYSTEM - Task Dependency Operations

⭐ WHAT IT DOES: Manages task dependencies with add, remove, list, and clear operations.
📋 WHEN TO USE: Task dependency management and workflow sequencing.
🎯 CRITICAL FOR: Workflow management and task sequencing.

| Action              | Required Parameters                | Optional Parameters                | Description                                      |
|---------------------|-----------------------------------|------------------------------------|--------------------------------------------------|
| add_dependency      | task_id, dependency_data (with dependency_id) | project_id (optional), git_branch_name (default: 'main'), user_id | Add a dependency to a task                       |
| remove_dependency   | task_id, dependency_data (with dependency_id) | project_id, git_branch_name, user_id | Remove a dependency from a task                  |
| get_dependencies    | task_id                           | project_id, git_branch_name, user_id | List all dependencies for a task                 |
| clear_dependencies  | task_id                           | project_id, git_branch_name, user_id | Remove all dependencies from a task              |
| get_blocking_tasks  | task_id                           | project_id, git_branch_name, user_id | List tasks blocking the given task               |

💡 USAGE GUIDELINES:
• Provide all required identifiers for each action (see table above).
• For add/remove actions, dependency_data must include a valid dependency_id.
• Optional parameters can be omitted unless overriding defaults.
• The tool returns detailed error messages for missing or invalid parameters, unknown actions, and internal errors.
• All business logic is delegated to the application layer.

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed.
• Unknown actions return an error listing valid actions.
• Internal errors are logged and returned with a generic error message.
"""

MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION = {
    "action": "Dependency management action to perform. Valid actions: 'add_dependency', 'remove_dependency', 'get_dependencies', 'clear_dependencies', 'get_blocking_tasks'",
    "task_id": "[OPTIONAL] Unique identifier for the target task. Required for all actions",
    "project_id": "[OPTIONAL] Project identifier for context. Optional - derived from task if not provided", 
    "git_branch_name": "[OPTIONAL] Task tree identifier for hierarchical context. Default: 'main'",
    "user_id": "[OPTIONAL] User identifier for auditing and access control. Required for multi-tenancy",
    "dependency_data": "[OPTIONAL] JSON string containing dependency_id for add/remove actions. Example: '{\"dependency_id\": \"task-uuid\"}'. Required for add_dependency and remove_dependency actions"
}

MANAGE_DEPENDENCY_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Task identification parameters
        "task_id": {
            "type": "string", 
            "description": MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION["task_id"]
        },
        "project_id": {
            "type": "string",
            "description": MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION["project_id"]
        },
        "git_branch_name": {
            "type": "string",
            "description": MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION["git_branch_name"]
        },
        
        # User and data parameters  
        "user_id": {
            "type": "string",
            "description": MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION["user_id"]
        },
        "dependency_data": {
            "type": "string",
            "description": MANAGE_DEPENDENCY_PARAMETERS_DESCRIPTION["dependency_data"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
}

def get_manage_dependency_parameters():
    """Get manage dependency parameters for use in controller."""
    return MANAGE_DEPENDENCY_PARAMS["properties"]

def get_manage_dependency_description():
    """Get manage dependency description for use in controller."""
    return MANAGE_DEPENDENCY_DESCRIPTION

# Legacy parameter descriptions for backward compatibility
MANAGE_DEPENDENCY_PARAMETERS = {
    "action": "Dependency management action to perform. Valid actions: 'add_dependency', 'remove_dependency', 'get_dependencies', 'clear_dependencies', 'get_blocking_tasks'. Required. (string)",
    "task_id": "Unique identifier for the target task. Required for all actions. (string)",
    "project_id": "Project identifier for context. Optional - derived from task if not provided. (string)",
    "git_branch_name": "Task tree identifier for hierarchical context. Optional, default: 'main'. (string)", 
    "user_id": "User identifier for auditing and access control. Required for multi-tenancy. (string)",
    "dependency_data": "Dictionary containing dependency_id for add/remove actions. Optional for list/clear actions. Example: {'dependency_id': 'task-uuid'}. (string)"
} 