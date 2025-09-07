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
• ASSIGN agents to branches for specialized work (e.g., @coding_agent for feature branches)
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
   - action: "assign_agent", project_id: "proj-uuid", git_branch_name: "feature/user-auth", agent_id: "@security_auditor_agent"
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
    IF security_related:
        ASSIGN "@security_auditor_agent"
    ELIF ui_related:
        ASSIGN "@ui_designer_agent"
    ELSE:
        ASSIGN "@coding_agent"
ELIF branch_type == "bugfix":
    ASSIGN "@debugger_agent"
ELIF branch_type == "test":
    ASSIGN "@test_orchestrator_agent"

BRANCH LIFECYCLE DECISION:
IF all_tasks_completed AND tests_passing:
    IF merged_to_main:
        ARCHIVE branch
    ELSE:
        KEEP active for merge
ELIF abandoned_for_30_days:
    ARCHIVE branch
ELIF needs_reactivation:
    RESTORE branch

📊 WORKFLOW PATTERNS:

1. Feature Development Flow:
   a) CREATE branch with descriptive name (feature/xyz)
   b) ASSIGN specialist agent based on feature type
   c) CREATE tasks within the branch
   d) Monitor with GET_STATISTICS
   e) ARCHIVE after merge

2. Multi-Agent Collaboration:
   a) CREATE branch for complex feature
   b) ASSIGN primary agent (e.g., @coding_agent)
   c) Work progresses...
   d) UNASSIGN current agent
   e) ASSIGN review agent (e.g., @code_reviewer_agent)

3. Branch Progress Monitoring:
   a) LIST all branches to get overview
   b) GET_STATISTICS for active branches
   c) Identify blocked/stalled branches
   d) Reassign agents or escalate as needed

🔗 BRANCH-TASK RELATIONSHIPS:
• Branches are containers for related tasks (1-to-many relationship)
• All tasks MUST belong to a branch (no orphan tasks)
• Branch progress = aggregate of task completion
• Deleting a branch deletes all associated tasks
• Agent assigned to branch has access to all branch tasks
• Branch context inherits to all contained tasks

💡 ENHANCED PARAMETERS:
• project_id: UUID of the project (get from project list or creation)
• git_branch_name: Descriptive name following git conventions (e.g., "feature/auth", "bugfix/login-error")
• git_branch_id: UUID returned from create or list actions
• git_branch_description: Detailed purpose and scope of the branch
• agent_id: Agent name with @ prefix (e.g., "@coding_agent") or UUID

📈 RESPONSE ENHANCEMENTS:
• workflow_guidance: AI-generated hints for next actions
• statistics: Progress metrics and task counts
• assigned_agents: Current agent assignments
• branch_health: Status indicators and blockers

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed.
• Unknown actions return an error listing valid actions.
• Internal errors are logged and returned with a generic error message.
• Branch name conflicts are detected and alternatives suggested.

⚠️ IMPORTANT NOTES:
• Always create branches before creating tasks
• Use git naming conventions (feature/, bugfix/, test/, etc.)
• Archive completed branches to maintain organization
• Agent assignments persist until explicitly changed
• Statistics are calculated in real-time from task data
"""

# Parameter descriptions for the manage_git_branch tool
MANAGE_GIT_BRANCH_PARAMETERS = {
    "action": "Git branch management action to perform. Valid actions: 'create', 'get', 'list', 'update', 'delete', 'assign_agent', 'unassign_agent', 'get_statistics', 'archive', 'restore' (string)",
    "project_id": "Project identifier. Required for all actions. (string)",
    "git_branch_name": "Git branch name identifier (can be used for assignment operations)",
    "git_branch_id": "Git branch UUID for lookup (can be used for assignment operations)",
    "git_branch_description": "Git branch description",
    "agent_id": "Agent identifier. Required for assign_agent and unassign_agent actions. (string)"
}

# Complete tool description combining description and parameters
manage_git_branch_description = {
    "description": MANAGE_GIT_BRANCH_DESCRIPTION,
    "parameters": MANAGE_GIT_BRANCH_PARAMETERS
}