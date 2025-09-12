"""
Task Management Tool Description

This module contains the comprehensive documentation for the manage_task MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

TOOL_NAME = "manage_task"

TOOL_DESCRIPTION = "Comprehensive task management with CRUD operations and dependency support"

MANAGE_TASK_DESCRIPTION = """
📋 TASK MANAGEMENT SYSTEM - Complete task lifecycle operations with Vision System Integration

⭐ WHAT IT DOES: Handles all task operations including CRUD, search, dependencies, and workflow management. Automatically enriches tasks with vision insights, progress tracking, and intelligent context updates.
📋 WHEN TO USE: For any task-related operation from creation to completion, including search and dependency management.
🎯 CRITICAL FOR: Project organization, workflow management, team collaboration, and maintaining development context.

🤖 AI USAGE GUIDELINES:
• ALWAYS create a task before starting any significant work (more than a single file edit)
• USE 'next' action to get AI-recommended tasks based on project state
• UPDATE tasks regularly with progress (status changes, completion percentage)
• COMPLETE tasks with detailed summaries to maintain project context
• SEARCH for existing tasks before creating duplicates
• CREATE subtasks using manage_subtask for complex tasks requiring multiple steps

| Action              | Required Parameters                | Optional Parameters                | Description                                      |
|---------------------|-----------------------------------|------------------------------------|--------------------------------------------------|
| create              | git_branch_id, title, assignees  | description, status, priority, details, estimated_effort, labels, due_date, dependencies | Create new task (MUST have at least 1 agent)    |
| update              | task_id                           | title, description, status, priority, details, estimated_effort, assignees, labels, due_date, context_id | Update existing task           |
| get                 | task_id                           | include_context                    | Retrieve task details                            |
| delete              | task_id                           |                                    | Remove task                                      |
| complete            | task_id                           | completion_summary, testing_notes  | Mark task as completed with context              |
| list                | (none)                            | status, priority, assignees, labels, limit, git_branch_id | List tasks with filtering         |
| search              | query                             | limit, git_branch_id               | Full-text search                                 |
| next                | git_branch_id                     | include_context                    | Get next recommended task                        |
| add_dependency      | task_id, dependency_id         |                                | Add dependency to task                           |
| remove_dependency   | task_id, dependency_id         |                                | Remove dependency from task                      |

⚠️ PARAMETER VALIDATION PATTERN - TWO-STAGE VALIDATION:

📌 WHY ONLY 'action' IS REQUIRED IN JSON SCHEMA:
The tool uses a two-stage validation pattern:
1. **Schema Level**: Only 'action' is marked as required in JSON schema
2. **Business Logic Level**: Based on the action value, specific parameters become required

This design provides:
- ✅ Flexibility: Different actions need different parameters
- ✅ Better Error Messages: Context-specific validation errors
- ✅ MCP Compatibility: Works better with single required parameter
- ✅ User Experience: Clear feedback about what's missing for each action

📋 ACTUAL REQUIRED PARAMETERS BY ACTION (Validated in Business Logic):
| Action | Required Parameters | Optional But Recommended | Notes |
|--------|-------------------|--------------------------|-------|
| create | action, git_branch_id, title, assignees | description, priority | MUST have at least 1 agent assigned |
| update | action, task_id | any field to update | task_id identifies which task to update |
| get | action, task_id | include_context | task_id identifies which task to retrieve |
| delete | action, task_id | - | task_id identifies which task to delete |
| complete | action, task_id | completion_summary, testing_notes | completion_summary highly recommended |
| list | action | git_branch_id, status, priority | git_branch_id optional to filter by branch |
| search | action, query | limit | query contains search terms |
| next | action, git_branch_id | include_context | git_branch_id needed to find next task in branch |
| add_dependency | action, task_id, dependency_id | - | establishes task order |
| remove_dependency | action, task_id, dependency_id | - | removes task dependency |

⚡ VALIDATION FLOW:
1. MCP receives request → Checks if 'action' exists (schema validation)
2. Controller receives request → Checks action-specific requirements (business validation)
3. Returns specific error if required parameter is missing for that action

📝 PRACTICAL EXAMPLES FOR AI:
1. Starting a new feature:
   - action: "create", git_branch_id: "550e8400-e29b-41d4-a716-446655440001", title: "Implement user authentication", description: "Add JWT-based authentication with login, logout, and session management", assignees: "coding-agent,@security-auditor-agent", priority: "high", estimated_effort: "3 days"

2. Getting recommended work:
   - action: "next", git_branch_id: "550e8400-e29b-41d4-a716-446655440000", include_context: true
   - This returns the most appropriate task based on priorities, dependencies, and project state

3. Updating progress:
   - action: "update", task_id: "550e8400-e29b-41d4-a716-446655440005", status: "in_progress", details: "Completed login UI, working on JWT integration"

4. Completing with context:
   - action: "complete", task_id: "550e8400-e29b-41d4-a716-446655440006", completion_summary: "Implemented full authentication flow with JWT tokens, refresh mechanism, and secure cookie storage", testing_notes: "Added unit tests for auth service, integration tests for login flow"

5. Finding related tasks:
   - action: "search", query: "authentication login", limit: 10

6. Creating task with dependencies:
   - action: "create", git_branch_id: "550e8400-e29b-41d4-a716-446655440002", title: "Add login tests", description: "Unit and integration tests for login", assignees: "@test-orchestrator-agent", dependencies: ["550e8400-e29b-41d4-a716-446655440003", "550e8400-e29b-41d4-a716-446655440004"]

7. Managing dependencies:
   - action: "add_dependency", task_id: "550e8400-e29b-41d4-a716-446655440007", dependency_id: "550e8400-e29b-41d4-a716-446655440008"
   - action: "remove_dependency", task_id: "550e8400-e29b-41d4-a716-446655440007", dependency_id: "550e8400-e29b-41d4-a716-446655440009"

🔄 DEPENDENCY WORKFLOW PATTERNS:
• Sequential Tasks: Create tasks with dependencies to enforce completion order
• Parallel Work: Tasks without dependencies can be worked on simultaneously
• Blocking Dependencies: Task status automatically becomes 'blocked' if dependencies aren't complete
• Dependency Chain: A → B → C ensures proper workflow sequence
• Cross-Feature Dependencies: Link tasks across different features when needed

🤖 AI DECISION RULES FOR DEPENDENCIES:
IF task requires another task's output:
    ADD as dependency
ELIF task is independent:
    NO dependencies needed
ELIF task is part of sequence:
    ADD previous step as dependency
ELIF testing/verification task:
    ADD implementation tasks as dependencies

🔄 VISION SYSTEM FEATURES (Automatic):
• Task enrichment with project context and best practices
• Intelligent priority and effort estimation
• Workflow hints and next action suggestions
• Progress tracking with milestone detection
• Blocker identification and resolution suggestions
• Impact analysis on related tasks
• Automatic context updates for team awareness

💡 ENHANCED PARAMETERS:
• title: Be specific and action-oriented (e.g., "Implement user login with email validation" not just "Login")
• description: Include acceptance criteria and technical approach when known
• priority: 'low', 'medium', 'high', 'urgent', 'critical' - affects task ordering in 'next' action
• status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled'
• estimated_effort: Use realistic estimates (e.g., "2 hours", "3 days", "1 week")
• assignees: **REQUIRED for task creation** - Must have at least one agent. Use format: "@agent-name" (e.g., "coding-agent", "@test-orchestrator-agent"). Can be comma-separated for multiple agents: "coding-agent,debugger-agent"
• labels: Can be a single string "frontend" or list ["frontend", "auth"] or comma-separated "frontend,auth,security"
• dependencies: Task IDs that must be completed first (for create action) - can be list ["task-id-1", "task-id-2"], single string "task-id", or comma-separated "task-id-1,task-id-2"
• completion_summary: Detailed summary of what was accomplished (for complete action)
• testing_notes: Description of testing performed (for complete action)
• include_context: Set to true to get vision insights and recommendations

📊 RESPONSE ENHANCEMENTS:
• vision_insights: AI-generated insights about the task
• workflow_hints: Contextual guidance for next steps
• related_tasks: Other tasks that might be affected
• progress_indicators: Milestone tracking information
• blocker_analysis: Identification of potential impediments
• impact_assessment: How this task affects project goals

💡 BEST PRACTICES FOR AI:
• Create tasks BEFORE starting work to maintain project visibility
• Use descriptive titles that clearly state the goal
• Include technical details in description field
• Update task status when starting work (todo → in_progress)
• Use 'next' action when unsure what to work on
• Complete tasks with detailed summaries for knowledge retention
• Search before creating to avoid duplicates
• Add dependencies for tasks that must be done in sequence
• Use labels for better organization and filtering
• Define dependencies upfront during task creation for better workflow planning
• Review dependency chains before starting work to understand task order
• Update dependent tasks when completing prerequisites

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed
• Unknown actions return an error listing valid actions
• Internal errors are logged and returned with a generic error message
• Vision system failures don't block core operations
"""

# Parameter descriptions for the manage_task tool
MANAGE_TASK_PARAMETERS_DESCRIPTION = {
    "action": "Task management action. Valid: 'create', 'update', 'get', 'delete', 'complete', 'list', 'search', 'next', 'add_dependency', 'remove_dependency'. Use 'create' to start new work, 'next' to find work, 'complete' when done.",
    "git_branch_id": "Git branch UUID identifier - contains all context (project_id, git_branch_name, user_id). Required for 'create' and 'next' actions. Get from git branch creation or list.",
    "task_id": "Task identifier (UUID). Required for: update, get, delete, complete, add/remove_dependency. Get from create response or list/search results.",
    "title": "Task title - be specific and action-oriented. Required for: create. Example: 'Implement JWT authentication with refresh tokens' not just 'Auth'",
    "description": "Detailed task description with acceptance criteria. Optional but recommended for: create. Include technical approach, dependencies, and success criteria.",
    "status": "Task status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled'. Optional. Changes automatically: create→todo, update→in_progress, complete→done",
    "priority": "Task priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: 'medium'. Higher priority tasks returned first by 'next' action.",
    "details": "Additional implementation notes, technical details, or context. Updated during work. Optional for: create, update",
    "estimated_effort": "Time estimate like '2 hours', '3 days', '1 week'. Helps with planning. Optional for: create, update",
    "assignees": "User identifiers - accepts string (single user) or comma-separated string (multiple users). Optional. Examples: 'user1' or 'user1,user2'. Default: current user",
    "labels": "Categories/tags - accepts string (single label) or comma-separated string (multiple labels). Optional. Examples: 'frontend' or 'frontend,auth,bug'. Useful for filtering.",
    "dependencies": "Task IDs this task depends on (for create action) - accepts string (single dependency) or comma-separated string (multiple dependencies). Optional. Examples: 'task-uuid' or 'task-uuid-1,task-uuid-2'. Tasks must be completed before this task can start.",
    "due_date": "Target completion date in ISO 8601 format (YYYY-MM-DD or full datetime). Optional. Example: '2024-12-31' or '2024-12-31T23:59:59Z'",
    "context_id": "Context identifier for task. Optional for 'update' action. Usually same as task_id. Used for context synchronization and validation. Auto-created during task creation.",
    "completion_summary": "DETAILED summary of what was accomplished. Highly recommended for 'complete' action. Example: 'Implemented JWT auth with 2FA support, added password reset flow, integrated with existing user service'",
    "testing_notes": "Description of testing performed. Optional for 'complete' action. Example: 'Added unit tests for auth service, manual testing of login/logout flows, verified token expiry'",
    "include_context": "Include vision insights and recommendations (true/false). Optional for 'get' and 'next' actions. Default: false. Set true for AI guidance.",
    "limit": "Maximum number of results. Optional for 'list' and 'search'. Default: 50. Range: 1-100",
    "query": "Search terms for finding tasks. Required for 'search' action. Searches in title, description, and labels. Example: 'authentication jwt'. Note: DEPRECATED for dependency operations - use 'dependency_id' instead.",
    "dependency_id": "UUID of task that must be completed first. Required for: add_dependency, remove_dependency. Use to establish task order.",
    "force_full_generation": "Force vision system regeneration. Optional. Default: false. Use if insights seem stale.",
    "offset": "Result offset for pagination. Optional. Default: 0. Used with 'limit' for paginated results.",
    "sort_by": "Field to sort results by. Optional. Examples: 'created_at', 'updated_at', 'priority', 'status', 'title'.",
    "sort_order": "Sort order for results. Optional. Valid values: 'asc', 'desc'. Default: 'desc'.",
    "assignee": "Filter tasks by specific assignee. Optional for 'list' action. Example: 'user123'.",
    "tag": "Filter tasks by specific tag/label. Optional for 'list' action. Example: 'frontend'.",
    "user_id": "User ID performing the operation. Optional - automatically populated from authentication context."
}


# JSON Schema for manage_task parameters
#
# TWO-STAGE VALIDATION DESIGN:
# - Schema Level: Only 'action' is marked as required here
# - Business Logic: Action-specific parameters are validated in the controller
#
# This allows one entry point with flexible validation based on the action.
# The controller's ValidationFactory checks required parameters per action:
# - create: requires title, git_branch_id
# - update/get/delete/complete: requires task_id
# - search: requires query
# - next: requires git_branch_id
# - add/remove_dependency: requires task_id, dependency_id
#
# This pattern provides better error messages and MCP compatibility.
MANAGE_TASK_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Task identification parameters
        "task_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["task_id"]
        },
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["git_branch_id"]
        },
        
        # Task creation/update parameters
        "title": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["title"]
        },
        "description": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["description"]
        },
        "status": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["status"]
        },
        "priority": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["priority"]
        },
        "details": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["details"]
        },
        "estimated_effort": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["estimated_effort"]
        },
        
        # Multi-value parameters (accept comma-separated strings)
        "assignees": {
            "type": "string",
            "description": "**REQUIRED for create action** - Agent identifiers (minimum 1 required). Use @agent-name format (e.g., 'coding-agent'). For multiple agents use comma-separated: 'coding-agent,@test-orchestrator-agent'. Available agents: coding-agent, test-orchestrator-agent, debugger-agent, security-auditor-agent, code-reviewer-agent, and 37+ more specialized agents (42 total available)."
        },
        "labels": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["labels"]
        },
        
        # Date and dependency parameters
        "due_date": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["due_date"]
        },
        "dependencies": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["dependencies"]
        },
        "dependency_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["dependency_id"]
        },
        
        # Context and completion parameters
        "context_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["context_id"]
        },
        "completion_summary": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["completion_summary"]
        },
        "testing_notes": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["testing_notes"]
        },
        
        # Search and filter parameters
        "query": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["query"]
        },
        "limit": {
            "type": "integer",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["limit"]
        },
        "offset": {
            "type": "integer",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["offset"]
        },
        "sort_by": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["sort_by"]
        },
        "sort_order": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["sort_order"]
        },
        
        # Boolean control parameters
        "include_context": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["include_context"]
        },
        "force_full_generation": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["force_full_generation"]
        },
        
        # Additional filter parameters
        "assignee": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["assignee"]
        },
        "tag": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["tag"]
        },
        
        # Authentication parameter
        "user_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["user_id"]
        }
    },
    "required": ["action"],
    "additionalProperties": False
}


def get_manage_task_description():
    """Get the complete task management tool description."""
    return MANAGE_TASK_DESCRIPTION


def get_manage_task_parameters():
    """Get the task management tool parameters schema."""
    return MANAGE_TASK_PARAMS



