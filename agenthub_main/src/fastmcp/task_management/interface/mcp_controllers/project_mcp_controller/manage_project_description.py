"""
Project Management Tool Description

This module contains the comprehensive documentation for the manage_project MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_PROJECT_DESCRIPTION = """
📁 PROJECT MANAGEMENT SYSTEM - Complete Project Lifecycle and Multi-Project Orchestration

⭐ WHAT IT DOES: Manages projects throughout their lifecycle with comprehensive CRUD operations, health monitoring, resource management, and cross-project coordination. Provides intelligent maintenance, agent assignment optimization, and multi-project prioritization.
📋 WHEN TO USE: Project creation, management, monitoring, maintenance, multi-project coordination, resource optimization, and organizational structure management.
🎯 CRITICAL FOR: Project lifecycle management, organizational hierarchy, resource allocation, cross-project learning, and enterprise-scale development coordination.

🤖 AI USAGE GUIDELINES:
• ALWAYS list projects on startup to understand organizational context
• USE health checks before critical operations to ensure system integrity
• COORDINATE across projects using priority scores and context switching
• OPTIMIZE agent assignments based on project workload and specialization
• SHARE reusable patterns between projects through global context delegation

| Action                | Required Parameters  | Optional Parameters      | Description                                      |
|-----------------------|---------------------|-------------------------|--------------------------------------------------|
| create                | name                | description, user_id     | Create new project with automatic context initialization |
| get                   | project_id OR name  |                         | Retrieve project details by ID or name           |
| list                  | (none)              |                         | List all projects with status and health info    |
| update                | project_id          | name, description       | Update project metadata and trigger sync         |
| delete                | project_id          | force                   | Remove project from system                       |
| project_health_check  | project_id          |                         | Comprehensive health analysis with metrics       |
| cleanup_obsolete      | project_id          | force                   | Remove obsolete tasks, files, and resources      |
| validate_integrity    | project_id          | force                   | Validate structure, dependencies, and consistency |
| rebalance_agents      | project_id          | force                   | Optimize agent assignments across task trees     |

💡 USAGE GUIDELINES:
• Use either project_id OR name for 'get' action (not both)
• The 'force' parameter bypasses safety checks for maintenance operations
• All operations return detailed success/error status with actionable messages
• Business logic is delegated to the project application facade

🔍 AI DECISION TREES:

PROJECT CREATION WORKFLOW:
1. List existing projects
2. Check for similar projects
3. IF no_similar_project: Create new project → Initialize context → Assign agents
4. ELSE: Use existing project → Create new git branch

PROJECT HEALTH MONITORING:
1. Run project_health_check
2. IF health_issues_found: Address issues → Run cleanup_obsolete if needed
3. ELSE: Proceed with planned work

🛑 ERROR HANDLING:
• Missing required parameters return specific field validation errors
• Duplicate project names are rejected with existing project information
• Invalid UUIDs and non-existent projects return clear error messages
• Maintenance operations provide safety warnings and require confirmation
• All business logic errors are handled by the application layer facade
"""

MANAGE_PROJECT_PARAMETERS_DESCRIPTION = {
    "action": "Project management action to perform. Valid values: create, get, list, update, delete, project_health_check, cleanup_obsolete, validate_integrity, rebalance_agents",
    "project_id": "[OPTIONAL] Project identifier (UUID). Required for most actions except create/list",
    "name": "[OPTIONAL] Project name. Required for create, can be used instead of project_id for get action",
    "description": "[OPTIONAL] Project description. Optional for create/update operations",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails",
    "force": "[OPTIONAL] Force parameter to bypass safety checks for maintenance and delete operations",
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
            "type": "string",
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
    "required": [
        "action"
    ],
    "additionalProperties": False,
    "_validation_note": "Only action required at schema level - business logic validates per action",
}


def get_manage_project_parameters():
    """Get manage project parameters for use in controller."""
    return MANAGE_PROJECT_PARAMS["properties"]


def get_manage_project_description():
    """Get manage project description for use in controller."""
    return MANAGE_PROJECT_DESCRIPTION
