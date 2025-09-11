"""
Git Branch Management Tool Description

This module provides comprehensive descriptions for git branch management operations
following the established pattern of other tool descriptions in the system.
"""

# Main description for the manage_git_branch tool
MANAGE_GIT_BRANCH_DESCRIPTION = """
🌿 GIT BRANCH MANAGEMENT SYSTEM - Branch Operations and Task Tree Organization

⭐ WHAT IT DOES: Manages git branches (task trees) with CRUD operations, agent assignments, and branch lifecycle management. Automatically enriches branches with workflow guidance, progress tracking, and intelligent context updates.
📋 WHEN TO USE: Git branch operations, task tree management, and branch-specific workflows.
🎯 CRITICAL FOR: Task organization, branch lifecycle, and hierarchical project structure.

🤖 AI USAGE GUIDELINES:
• ALWAYS create a branch before creating tasks (tasks belong to branches)
• USE 'list' action to discover existing branches before creating duplicates
• ASSIGN agents to branches for specialized work (e.g., coding-agent for feature branches)
• CHECK statistics to monitor branch progress and task completion
• ARCHIVE completed branches to maintain a clean workspace

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

💡 PRACTICAL EXAMPLES FOR AI:
1. Creating a feature branch:
   - action: "create", project_id: "proj-uuid", git_branch_name: "feature/user-auth", git_branch_description: "Implement JWT authentication"

2. Assigning specialist agent:
   - action: "assign_agent", project_id: "proj-uuid", git_branch_name: "feature/user-auth", agent_id: "security-auditor-agent"
   - Note: Can use either git_branch_name OR git_branch_id for identification

3. Monitoring progress:
   - action: "get_statistics", project_id: "proj-uuid", git_branch_id: "branch-uuid"
   - Returns: total_tasks, completed_tasks, progress_percentage

4. Listing active branches:
   - action: "list", project_id: "proj-uuid"
   - Use this before creating to avoid duplicates

🔍 DECISION TREES:

BRANCH CREATION DECISION:
IF new_feature_requested:
    IF similar_branch_exists:
        USE existing branch
    ELSE:
        CREATE new branch with descriptive name
        ASSIGN appropriate specialist agent

AGENT ASSIGNMENT DECISION:
IF branch_type == "feature":
    ASSIGN coding-agent OR @ui_designer_agent
ELIF branch_type == "security":
    ASSIGN security-auditor-agent
ELIF branch_type == "test":
    ASSIGN test-orchestrator-agent
ELIF branch_type == "ai_docs":
    ASSIGN documentation-agent

🛑 ERROR HANDLING:
• Missing required parameters return clear error messages
• Duplicate branch names are rejected with existing branch information
• Invalid UUIDs and non-existent entities return specific error codes
• Agent assignment conflicts are resolved with reassignment options
"""

MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION = {
    "action": "Git branch management action to perform. Valid values: create, get, list, update, delete, assign_agent, unassign_agent, get_statistics, archive, restore",
    "project_id": "[OPTIONAL] Project identifier for the git branch operation",
    "git_branch_id": "[OPTIONAL] Git branch identifier (UUID). Required for most actions except create/list",
    "git_branch_name": "[OPTIONAL] Git branch name. Required for create, optional for update. Can be used instead of git_branch_id for agent assignment",
    "git_branch_description": "[OPTIONAL] Description of the git branch. Optional for create/update operations",
    "agent_id": "[OPTIONAL] Agent identifier for assignment operations. Required for assign_agent/unassign_agent actions",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails"
}

MANAGE_GIT_BRANCH_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Project identification parameters
        "project_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["project_id"]
        },
        
        # Branch identification parameters
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["git_branch_id"]
        },
        "git_branch_name": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["git_branch_name"]
        },
        
        # Branch configuration parameters
        "git_branch_description": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["git_branch_description"]
        },
        
        # Agent assignment parameters
        "agent_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["agent_id"]
        },
        
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_GIT_BRANCH_PARAMETERS_DESCRIPTION["user_id"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
}

def get_manage_git_branch_parameters():
    """Get manage git branch parameters for use in controller."""
    return MANAGE_GIT_BRANCH_PARAMS["properties"]

def get_manage_git_branch_description():
    """Get manage git branch description for use in controller."""
    return MANAGE_GIT_BRANCH_DESCRIPTION