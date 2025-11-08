"""
Task Management Tool Description

This module contains the comprehensive documentation for the manage_task MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

TOOL_NAME = "manage_task"

TOOL_DESCRIPTION = (
    "Comprehensive task management with CRUD operations and dependency support"
)

MANAGE_TASK_DESCRIPTION = """
TASK MANAGEMENT - Complete lifecycle: CRUD | search | dependencies | workflow | vision insights | progress tracking

USE FOR: Task operations creation→completion | AI recommendations | Project organization | Team collaboration

AI RULES: Create before work (>1 file edit) | Use 'next' for recommendations | Update progress regularly | Complete with summaries | Search before creating | Use manage_subtask for complex work

| Action              | Required                          | Optional                           | Description                        |
|---------------------|-----------------------------------|------------------------------------|------------------------------------|
| create              | git_branch_id, title, assignees   | description, status, priority, details, estimated_effort, labels, due_date, dependencies | Create task (min 1 agent)         |
| update              | task_id                           | title, description, status, priority, details, estimated_effort, assignees, labels, due_date, context_id | Update task                        |
| get                 | task_id                           | include_context                    | Retrieve task                      |
| delete              | task_id                           |                                    | Remove task                        |
| complete            | task_id                           | completion_summary, testing_notes  | Complete task                      |
| list                | (none)                            | status, priority, assignees, labels, limit, git_branch_id | List with filters                  |
| search              | query                             | limit, git_branch_id               | Full-text search                   |
| next                | git_branch_id                     | include_context                    | Get recommended task               |
| add_dependency      | task_id, dependency_id            |                                    | Add dependency                     |
| remove_dependency   | task_id, dependency_id            |                                    | Remove dependency                  |
| ai_plan             | requirements, title, git_branch_id| description, context, auto_create_tasks | AI task plan                       |
| ai_create           | title, git_branch_id              | enable_ai_breakdown, enable_smart_assignment, ai_requirements | AI-enhanced task                   |
| ai_enhance          | task_id                           | analyze_complexity, suggest_optimizations, identify_risks | AI insights                        |
| ai_analyze          | requirements                      | context                            | Analyze requirements               |
| ai_suggest_agents   | requirements                      | available_agents                   | Suggest agents                     |

VALIDATION: Two-stage (schema: 'action' only → business logic: action-specific) | CRUD needs task_id | Create needs git_branch_id+title+assignees (min 1) | Search needs query | Dependencies need task_id+dependency_id

KEY PARAMS: assignees (@agent-name, comma-separated, REQUIRED for create) | priority (low|medium|high|urgent|critical, affects 'next') | status (todo|in_progress|blocked|review|testing|done|cancelled) | dependencies (task IDs, comma-separated) | include_context (true for vision)

VISION (Auto): Task enrichment | Priority estimation | Workflow hints | Progress tracking | Blocker detection | Impact analysis | Context updates

BEST PRACTICES: Create before work | Specific titles | Update status | Detailed summaries | Search first | Define deps upfront | Use labels

PROGRESS UPDATES: When updating 'status' or 'progress_percentage', you MUST include the 'details' parameter with at least 10 characters describing the progress made. This enforces documentation best practices and ensures all changes are tracked.

Examples:
```python
# ❌ WRONG - Will fail validation
manage_task(action="update", task_id="xxx", status="in_progress")

# ✅ CORRECT - Includes required details
manage_task(
    action="update",
    task_id="xxx",
    status="in_progress",
    details="Started implementation of authentication module"
)

# ✅ CORRECT - Progress percentage with details
manage_task(
    action="update",
    task_id="xxx",
    progress_percentage=50,
    details="Completed database schema design and API endpoint structure"
)
```

DEPENDENCIES: Sequential (A→B→C) | Parallel | Blocking | Cross-feature | Add IF task needs output OR sequence part

ERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic | Vision→don't block
"""

# Parameter descriptions for the manage_task tool
MANAGE_TASK_PARAMETERS_DESCRIPTION = {
    "action": "Task management action. Valid: 'create', 'update', 'get', 'delete', 'complete', 'list', 'search', 'next', 'add_dependency', 'remove_dependency', 'ai_plan', 'ai_create', 'ai_enhance', 'ai_analyze', 'ai_suggest_agents'. Use 'create' to start new work, 'next' to find work, 'complete' when done. AI actions provide intelligent task planning and enhancement.",
    "git_branch_id": "Git branch UUID identifier - contains all context (project_id, git_branch_name, user_id). Required for 'create' and 'next' actions. Get from git branch creation or list.",
    "task_id": "Task identifier (UUID). Required for: update, get, delete, complete, add/remove_dependency. Get from create response or list/search results.",
    "title": "Task title - be specific and action-oriented. Required for: create. Example: 'Implement JWT authentication with refresh tokens' not just 'Auth'",
    "description": "Detailed task description with acceptance criteria. Optional but recommended for: create. Include technical approach, dependencies, and success criteria.",
    "status": "Task status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled'. Optional. Changes automatically: create→todo, update→in_progress, complete→done",
    "priority": "Task priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: 'medium'. Higher priority tasks returned first by 'next' action.",
    "details": "[REQUIRED when updating status or progress_percentage] Progress notes describing what changed (minimum 10 characters). This field is MANDATORY when updating status or progress to ensure all changes are documented. Optional for: create",
    "estimated_effort": "Time estimate like '2 hours', '3 days', '1 week'. Helps with planning. Optional for: create, update",
    "progress_percentage": "Task completion percentage (0-100). Optional for 'update'. Automatically maps to status transitions and progress tracking when supplied.",
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
    "user_id": "User ID performing the operation. Optional - automatically populated from authentication context.",
    # AI-specific parameters
    "requirements": "Requirements description or JSON for AI planning. Required for: ai_plan, ai_analyze, ai_suggest_agents. Can be comma-separated text or structured JSON format.",
    "context": "Planning context for AI operations. Optional. Values: 'new_feature', 'bug_fix', 'enhancement', 'refactor'. Default: 'new_feature'.",
    "auto_create_tasks": "Whether to automatically create MCP tasks from AI plan. Optional for 'ai_plan'. Default: true.",
    "enable_ai_breakdown": "Enable AI-powered task breakdown into subtasks. Optional for 'ai_create'. Default: false.",
    "enable_smart_assignment": "Enable AI-powered agent assignment suggestions. Optional for 'ai_create'. Default: false.",
    "enable_auto_subtasks": "Enable automatic subtask creation from AI analysis. Optional for 'ai_create'. Default: false.",
    "ai_requirements": "Additional AI requirements for enhanced task creation. Optional for 'ai_create'. Provides context for AI planning.",
    "planning_context": "Context for AI planning operations. Optional for 'ai_create'. Values: 'new_feature', 'bug_fix', 'enhancement'. Default: 'new_feature'.",
    "analyze_complexity": "Analyze task complexity using AI. Optional for 'ai_enhance'. Default: true.",
    "suggest_optimizations": "Generate AI-powered optimization suggestions. Optional for 'ai_enhance'. Default: true.",
    "identify_risks": "Identify potential risks using AI analysis. Optional for 'ai_enhance'. Default: true.",
    "available_agents": "Comma-separated list of available agents for assignment suggestions. Optional for 'ai_suggest_agents'.",
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
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["action"],
        },
        # Task identification parameters
        "task_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["task_id"],
        },
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["git_branch_id"],
        },
        # Task creation/update parameters
        "title": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["title"],
        },
        "description": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["description"],
        },
        "status": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["status"],
        },
        "priority": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["priority"],
        },
        "details": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["details"],
        },
        "estimated_effort": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["estimated_effort"],
        },
        "progress_percentage": {
            "type": "integer",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["progress_percentage"],
        },
        # Multi-value parameters (accept comma-separated strings)
        "assignees": {
            "type": "string",
            "description": "**REQUIRED for create action** - Agent identifiers (minimum 1 required). Use @agent-name format (e.g., 'coding-agent'). For multiple agents use comma-separated: 'coding-agent,@test-orchestrator-agent'. Available agents: coding-agent, test-orchestrator-agent, debugger-agent, security-auditor-agent, code-reviewer-agent, and 37+ more specialized agents (42 total available).",
        },
        "labels": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["labels"],
        },
        # Date and dependency parameters
        "due_date": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["due_date"],
        },
        "dependencies": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["dependencies"],
        },
        "dependency_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["dependency_id"],
        },
        # Context and completion parameters
        "context_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["context_id"],
        },
        "completion_summary": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["completion_summary"],
        },
        "testing_notes": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["testing_notes"],
        },
        # Search and filter parameters
        "query": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["query"],
        },
        "limit": {
            "type": "integer",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["limit"],
        },
        "offset": {
            "type": "integer",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["offset"],
        },
        "sort_by": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["sort_by"],
        },
        "sort_order": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["sort_order"],
        },
        # Boolean control parameters
        "include_context": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["include_context"],
        },
        "force_full_generation": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["force_full_generation"],
        },
        # Additional filter parameters
        "assignee": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["assignee"],
        },
        "tag": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["tag"],
        },
        # Authentication parameter
        "user_id": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["user_id"],
        },
        # AI-specific parameters
        "requirements": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["requirements"],
        },
        "context": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["context"],
        },
        "auto_create_tasks": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["auto_create_tasks"],
        },
        "enable_ai_breakdown": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["enable_ai_breakdown"],
        },
        "enable_smart_assignment": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION[
                "enable_smart_assignment"
            ],
        },
        "enable_auto_subtasks": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["enable_auto_subtasks"],
        },
        "ai_requirements": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["ai_requirements"],
        },
        "planning_context": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["planning_context"],
        },
        "analyze_complexity": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["analyze_complexity"],
        },
        "suggest_optimizations": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["suggest_optimizations"],
        },
        "identify_risks": {
            "type": "boolean",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["identify_risks"],
        },
        "available_agents": {
            "type": "string",
            "description": MANAGE_TASK_PARAMETERS_DESCRIPTION["available_agents"],
        },
    },
    "required": ["action"],
    "additionalProperties": False,
}


def get_manage_task_description():
    """Get the complete task management tool description."""
    return MANAGE_TASK_DESCRIPTION


def get_manage_task_parameters():
    """Get the task management tool parameters schema."""
    return MANAGE_TASK_PARAMS
