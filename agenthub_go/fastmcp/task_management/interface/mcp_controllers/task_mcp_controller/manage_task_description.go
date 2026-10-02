package task_mcp_controller

// Task Management Tool Description
// (Python manage_task_description.py).
//
// Pure data module: no framework-specific code.

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// ToolName is TOOL_NAME.
const ToolName = "manage_task"

// ToolDescription is TOOL_DESCRIPTION.
const ToolDescription = "Comprehensive task management with CRUD operations and dependency support"

// ManageTaskDescription is MANAGE_TASK_DESCRIPTION.
const ManageTaskDescription = `
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
` + "```python" + `
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
` + "```" + `

DEPENDENCIES: Sequential (A→B→C) | Parallel | Blocking | Cross-feature | Add IF task needs output OR sequence part

ERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic | Vision→don't block
`

// ManageTaskParametersDescription is MANAGE_TASK_PARAMETERS_DESCRIPTION. Key order
// is not observable (only indexed), so a plain map is used.
var ManageTaskParametersDescription = map[string]string{
	"action":                  "Task management action. Valid: 'create', 'update', 'get', 'delete', 'complete', 'list', 'search', 'next', 'add_dependency', 'remove_dependency', 'ai_plan', 'ai_create', 'ai_enhance', 'ai_analyze', 'ai_suggest_agents'. Use 'create' to start new work, 'next' to find work, 'complete' when done. AI actions provide intelligent task planning and enhancement.",
	"git_branch_id":           "Git branch UUID identifier - contains all context (project_id, git_branch_name, user_id). Required for 'create' and 'next' actions. Get from git branch creation or list.",
	"task_id":                 "Task identifier (UUID). Required for: update, get, delete, complete, add/remove_dependency. Get from create response or list/search results.",
	"title":                   "Task title - be specific and action-oriented. Required for: create. Example: 'Implement JWT authentication with refresh tokens' not just 'Auth'",
	"description":             "Detailed task description with acceptance criteria. Optional but recommended for: create. Include technical approach, dependencies, and success criteria.",
	"status":                  "Task status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled'. Optional. Changes automatically: create→todo, update→in_progress, complete→done",
	"priority":                "Task priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: 'medium'. Higher priority tasks returned first by 'next' action.",
	"details":                 "[REQUIRED when updating status or progress_percentage] Progress notes describing what changed (minimum 10 characters). This field is MANDATORY when updating status or progress to ensure all changes are documented. Optional for: create",
	"estimated_effort":        "Time estimate like '2 hours', '3 days', '1 week'. Helps with planning. Optional for: create, update",
	"progress_percentage":     "Task completion percentage (0-100). Optional for 'update'. Automatically maps to status transitions and progress tracking when supplied.",
	"assignees":               "User identifiers - accepts string (single user) or comma-separated string (multiple users). Optional. Examples: 'user1' or 'user1,user2'. Default: current user",
	"labels":                  "Categories/tags - accepts string (single label) or comma-separated string (multiple labels). Optional. Examples: 'frontend' or 'frontend,auth,bug'. Useful for filtering.",
	"dependencies":            "Task IDs this task depends on (for create action) - accepts string (single dependency) or comma-separated string (multiple dependencies). Optional. Examples: 'task-uuid' or 'task-uuid-1,task-uuid-2'. Tasks must be completed before this task can start.",
	"due_date":                "Target completion date in ISO 8601 format (YYYY-MM-DD or full datetime). Optional. Example: '2024-12-31' or '2024-12-31T23:59:59Z'",
	"context_id":              "Context identifier for task. Optional for 'update' action. Usually same as task_id. Used for context synchronization and validation. Auto-created during task creation.",
	"completion_summary":      "DETAILED summary of what was accomplished. Highly recommended for 'complete' action. Example: 'Implemented JWT auth with 2FA support, added password reset flow, integrated with existing user service'",
	"testing_notes":           "Description of testing performed. Optional for 'complete' action. Example: 'Added unit tests for auth service, manual testing of login/logout flows, verified token expiry'",
	"include_context":         "Include vision insights and recommendations (true/false). Optional for 'get' and 'next' actions. Default: false. Set true for AI guidance.",
	"limit":                   "Maximum number of results. Optional for 'list' and 'search'. Default: 50. Range: 1-100",
	"query":                   "Search terms for finding tasks. Required for 'search' action. Searches in title, description, and labels. Example: 'authentication jwt'. Note: DEPRECATED for dependency operations - use 'dependency_id' instead.",
	"dependency_id":           "UUID of task that must be completed first. Required for: add_dependency, remove_dependency. Use to establish task order.",
	"force_full_generation":   "Force vision system regeneration. Optional. Default: false. Use if insights seem stale.",
	"offset":                  "Result offset for pagination. Optional. Default: 0. Used with 'limit' for paginated results.",
	"sort_by":                 "Field to sort results by. Optional. Examples: 'created_at', 'updated_at', 'priority', 'status', 'title'.",
	"sort_order":              "Sort order for results. Optional. Valid values: 'asc', 'desc'. Default: 'desc'.",
	"assignee":                "Filter tasks by specific assignee. Optional for 'list' action. Example: 'user123'.",
	"tag":                     "Filter tasks by specific tag/label. Optional for 'list' action. Example: 'frontend'.",
	"user_id":                 "User ID performing the operation. Optional - automatically populated from authentication context.",
	"requirements":            "Requirements description or JSON for AI planning. Required for: ai_plan, ai_analyze, ai_suggest_agents. Can be comma-separated text or structured JSON format.",
	"context":                 "Planning context for AI operations. Optional. Values: 'new_feature', 'bug_fix', 'enhancement', 'refactor'. Default: 'new_feature'.",
	"auto_create_tasks":       "Whether to automatically create MCP tasks from AI plan. Optional for 'ai_plan'. Default: true.",
	"enable_ai_breakdown":     "Enable AI-powered task breakdown into subtasks. Optional for 'ai_create'. Default: false.",
	"enable_smart_assignment": "Enable AI-powered agent assignment suggestions. Optional for 'ai_create'. Default: false.",
	"enable_auto_subtasks":    "Enable automatic subtask creation from AI analysis. Optional for 'ai_create'. Default: false.",
	"ai_requirements":         "Additional AI requirements for enhanced task creation. Optional for 'ai_create'. Provides context for AI planning.",
	"planning_context":        "Context for AI planning operations. Optional for 'ai_create'. Values: 'new_feature', 'bug_fix', 'enhancement'. Default: 'new_feature'.",
	"analyze_complexity":      "Analyze task complexity using AI. Optional for 'ai_enhance'. Default: true.",
	"suggest_optimizations":   "Generate AI-powered optimization suggestions. Optional for 'ai_enhance'. Default: true.",
	"identify_risks":          "Identify potential risks using AI analysis. Optional for 'ai_enhance'. Default: true.",
	"available_agents":        "Comma-separated list of available agents for assignment suggestions. Optional for 'ai_suggest_agents'.",
}

// GetManageTaskDescription ports get_manage_task_description.
func GetManageTaskDescription() string { return ManageTaskDescription }

// GetManageTaskParameters ports get_manage_task_parameters.
func GetManageTaskParameters() *entities.OrderedMap[any] {
	properties := entities.NewOrderedMap[any]()

	stringProp := func(name string) *entities.OrderedMap[any] {
		return paramProp("string", ManageTaskParametersDescription[name])
	}
	intProp := func(name string) *entities.OrderedMap[any] {
		return paramProp("integer", ManageTaskParametersDescription[name])
	}
	boolProp := func(name string) *entities.OrderedMap[any] {
		return paramProp("boolean", ManageTaskParametersDescription[name])
	}

	properties.Set("action", stringProp("action"))
	properties.Set("task_id", stringProp("task_id"))
	properties.Set("git_branch_id", stringProp("git_branch_id"))
	properties.Set("title", stringProp("title"))
	properties.Set("description", stringProp("description"))
	properties.Set("status", stringProp("status"))
	properties.Set("priority", stringProp("priority"))
	properties.Set("details", stringProp("details"))
	properties.Set("estimated_effort", stringProp("estimated_effort"))
	properties.Set("progress_percentage", intProp("progress_percentage"))
	properties.Set("assignees", paramProp("string",
		"**REQUIRED for create action** - Agent identifiers (minimum 1 required). Use @agent-name format (e.g., 'coding-agent'). For multiple agents use comma-separated: 'coding-agent,@test-orchestrator-agent'. Available agents: coding-agent, test-orchestrator-agent, debugger-agent, security-auditor-agent, code-reviewer-agent, and 37+ more specialized agents (42 total available)."))
	properties.Set("labels", stringProp("labels"))
	properties.Set("due_date", stringProp("due_date"))
	properties.Set("dependencies", stringProp("dependencies"))
	properties.Set("dependency_id", stringProp("dependency_id"))
	properties.Set("context_id", stringProp("context_id"))
	properties.Set("completion_summary", stringProp("completion_summary"))
	properties.Set("testing_notes", stringProp("testing_notes"))
	properties.Set("query", stringProp("query"))
	properties.Set("limit", intProp("limit"))
	properties.Set("offset", intProp("offset"))
	properties.Set("sort_by", stringProp("sort_by"))
	properties.Set("sort_order", stringProp("sort_order"))
	properties.Set("include_context", boolProp("include_context"))
	properties.Set("force_full_generation", boolProp("force_full_generation"))
	properties.Set("assignee", stringProp("assignee"))
	properties.Set("tag", stringProp("tag"))
	properties.Set("user_id", stringProp("user_id"))
	properties.Set("requirements", stringProp("requirements"))
	properties.Set("context", stringProp("context"))
	properties.Set("auto_create_tasks", boolProp("auto_create_tasks"))
	properties.Set("enable_ai_breakdown", boolProp("enable_ai_breakdown"))
	properties.Set("enable_smart_assignment", boolProp("enable_smart_assignment"))
	properties.Set("enable_auto_subtasks", boolProp("enable_auto_subtasks"))
	properties.Set("ai_requirements", stringProp("ai_requirements"))
	properties.Set("planning_context", stringProp("planning_context"))
	properties.Set("analyze_complexity", boolProp("analyze_complexity"))
	properties.Set("suggest_optimizations", boolProp("suggest_optimizations"))
	properties.Set("identify_risks", boolProp("identify_risks"))
	properties.Set("available_agents", stringProp("available_agents"))

	params := entities.NewOrderedMap[any]()
	params.Set("type", "object")
	params.Set("properties", properties)
	params.Set("required", []any{"action"})
	params.Set("additionalProperties", false)
	return params
}

func paramProp(typeName, description string) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("type", typeName)
	p.Set("description", description)
	return p
}
