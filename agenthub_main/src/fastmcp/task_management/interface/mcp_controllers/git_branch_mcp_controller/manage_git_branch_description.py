"""
Git Branch Management Tool Description

This module provides comprehensive descriptions for git branch management operations
following the established pattern of other tool descriptions in the system.
"""

# Main description for the manage_git_branch tool
MANAGE_GIT_BRANCH_DESCRIPTION = """
🌿 GIT BRANCH MANAGEMENT - Branch Operations and Task Tree Organization

Manages git branches (task trees) with CRUD operations, agent assignments, and lifecycle management. Automatically enriches branches with workflow guidance, progress tracking, and intelligent context updates.

**AI Usage Rules**:
• Create branch BEFORE tasks (tasks belong to branches)
• List existing branches before creating to avoid duplicates
• Assign agents for specialized work (e.g., coding-agent for feature branches)
• Check statistics to monitor progress
• Archive completed branches

| Action           | Required Parameters                | Optional Parameters                | Description                                      |
|------------------|-----------------------------------|------------------------------------|--------------------------------------------------|
| create           | project_id, git_branch_name        | git_branch_description             | Create a new git branch (task tree)              |
| get              | project_id, git_branch_id          |                                    | Retrieve git branch details by ID                |
| list             | project_id                         |                                    | List all git branches for a project              |
| update           | project_id, git_branch_id          | git_branch_name, git_branch_description | Update git branch properties                 |
| delete           | project_id, git_branch_id          |                                    | Remove git branch from project                   |
| assign_agent     | project_id, agent_id, (git_branch_name OR git_branch_id) |                    | Assign agent to git branch                       |
| unassign_agent   | project_id, agent_id, (git_branch_name OR git_branch_id) |                    | Remove agent from git branch                     |
| get_statistics   | project_id, git_branch_id          |                                    | Get branch statistics and metrics                |
| archive          | project_id, git_branch_id          |                                    | Archive git branch (soft delete)                 |
| restore          | project_id, git_branch_id          |                                    | Restore archived git branch                      |

**Example Pattern**: action="create", project_id="proj-uuid", git_branch_name="feature/user-auth", git_branch_description="Implement JWT"
**Agent Assignment**: Use git_branch_name OR git_branch_id for identification
**Statistics**: Returns total_tasks, completed_tasks, progress_percentage

**Decision Trees**:
Branch Creation: IF new_feature → IF similar_exists → use existing ELSE create + assign agent
Agent Assignment: feature→coding-agent | security→security-auditor-agent | test→test-orchestrator-agent | ai_docs→documentation-agent

**Error Handling**: Missing params/duplicate names/invalid UUIDs return clear error messages with existing entity info and resolution options
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
