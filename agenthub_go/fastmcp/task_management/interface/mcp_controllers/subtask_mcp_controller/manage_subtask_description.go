package subtask_mcp_controller

// Subtask Management Tool Description (Python manage_subtask_description.py).
// Pure constants and accessors; kept for parity with the Python module.

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// GetSubtaskDescription ports get_subtask_description.
func GetSubtaskDescription() string { return MANAGE_SUBTASK_DESCRIPTION }

// MANAGE_SUBTASK_DESCRIPTION ports the module-level description string.
const MANAGE_SUBTASK_DESCRIPTION = `
SUBTASK MANAGEMENT - Hierarchical breakdown: CRUD | progress tracking | auto parent updates | context sync

USE FOR: Breaking down complex tasks | Granular progress | Multi-step workflows

AI RULES: Use for tasks with multiple steps | Update with progress_notes (MANDATORY for update/complete) | progress_percentage auto-maps status | Complete with detailed summaries | All actions auto-update parent

| Action   | Required                 | Optional                           | Description                  |
|----------|--------------------------|------------------------------------|-----------------------------|
| create   | task_id, title           | description, status, priority, assignees, progress_notes | Create subtask                  |
| update   | task_id, subtask_id, progress_notes | title, description, status, priority, assignees, progress_percentage, blockers, insights_found | Update with progress history    |
| delete   | task_id, subtask_id      |                                    | Remove subtask              |
| get      | task_id, subtask_id      |                                    | Retrieve subtask            |
| list     | task_id                  |                                    | List all subtasks           |
| complete | task_id, subtask_id, completion_summary, progress_notes | impact_on_parent, insights_found | Complete with context       |

VALIDATION: task_id always required | subtask_id for update/delete/get/complete | title for create | progress_notes MANDATORY for update/complete | completion_summary MANDATORY for complete

KEY PARAMS: progress_notes (MANDATORY update/complete, builds timestamped history) | completion_summary (MANDATORY complete, be specific) | progress_percentage (0-100, auto-maps: 0=todo, 1-99=in_progress, 100=done) | assignees (inherits from parent if not specified)

AUTO FEATURES: Progress history tracking | Agent inheritance | Parent progress recalc | Status mapping | Blocker escalation | Insight propagation | Workflow hints

BEST PRACTICES: Update with progress_notes every step | Complete with detailed summary | Use progress_percentage over status | Let assignees inherit

**Progress Documentation Requirements**: The 'progress_notes' parameter is MANDATORY for 'update' and 'complete' actions. This builds timestamped progress history and ensures visibility into work progress. Operations will fail without this field.

USAGE EXAMPLES:
` + "```python" + `
# ❌ WRONG - Will fail validation
manage_subtask(action="update", task_id="xxx", subtask_id="yyy", progress_percentage=50)

# ✅ CORRECT - Includes required progress_notes
manage_subtask(
    action="update",
    task_id="xxx",
    subtask_id="yyy",
    progress_percentage=50,
    progress_notes="Completed UI mockup, starting on API integration"
)

# ❌ WRONG - Complete without progress_notes
manage_subtask(action="complete", task_id="xxx", subtask_id="yyy", completion_summary="Done")

# ✅ CORRECT - Complete with both required fields
manage_subtask(
    action="complete",
    task_id="xxx",
    subtask_id="yyy",
    completion_summary="Completed JWT token structure with proper expiry times",
    progress_notes="Final review completed, structure documented"
)
` + "```" + `

ERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic | Context updates→don't block
`

// MANAGE_SUBTASK_PARAMETERS_DESCRIPTION ports the parameter description dict.
var MANAGE_SUBTASK_PARAMETERS_DESCRIPTION = func() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("action", "Subtask management action to perform. Valid values: create, update, delete, get, list, complete")
	m.Set("task_id", "Parent task identifier (UUID). Required for all actions")
	m.Set("subtask_id", "Subtask identifier (UUID). Required for update, delete, get, complete actions")
	m.Set("title", "Subtask title. Required for create, optional for update")
	m.Set("description", "Detailed subtask description explaining what needs to be done. Include acceptance criteria if relevant")
	m.Set("status", "Subtask status: 'todo', 'in_progress', 'done'. Note: use progress_percentage instead for automatic status mapping")
	m.Set("priority", "Subtask priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: inherits from parent")
	m.Set("assignees", "Agent identifiers - **Inherits from parent task if not specified**. Use @agent-name format. Comma-separated for multiple: 'coding-agent,@test-orchestrator-agent'. Leave empty to inherit parent's agents automatically.")
	m.Set("progress_percentage", "Integer 0-100 representing completion. Automatically maps to status (0=todo, 1-99=in_progress, 100=done). Use this instead of status field")
	m.Set("progress_notes", "[REQUIRED for 'update' and 'complete' actions] Brief description of current work status that builds progress history. MANDATORY for update and complete operations. Creates timestamped progress entries automatically. Minimum 10 characters. Example: 'Completed UI mockup, starting on API integration'")
	m.Set("completion_summary", "[REQUIRED for 'complete' action] Detailed summary of what was accomplished. BE SPECIFIC! MANDATORY for complete operations. Example: 'Implemented JWT authentication with refresh tokens, 2-hour expiry, and secure httpOnly cookies'")
	m.Set("testing_notes", "Notes about testing performed. Example: 'Tested login flow with valid/invalid credentials, verified token refresh'")
	m.Set("insights_found", "Important discoveries or learnings. Comma-separated string or JSON array. Example: 'Found existing utility function for validation,Discovered performance bottleneck in query'")
	m.Set("challenges_overcome", "Challenges faced and how they were resolved. Comma-separated string or JSON array")
	m.Set("skills_learned", "New skills or knowledge gained. Comma-separated string or JSON array")
	m.Set("next_recommendations", "Suggestions for future work. Comma-separated string or JSON array")
	m.Set("deliverables", "Artifacts or outputs created. Comma-separated string or JSON array")
	m.Set("completion_quality", "Quality assessment of work completed. Example: 'Production-ready', 'Requires review', 'Prototype only'")
	m.Set("blockers", "Issues preventing progress. Comma-separated string or JSON array. Example: 'Missing API documentation,Waiting for database schema approval'")
	m.Set("impact_on_parent", "How completing this subtask affects the parent task. Required for complete action")
	m.Set("user_id", "User identifier for authentication and audit trails")
	return m
}()

// MANAGE_SUBTASK_PARAMS ports the JSON-schema description dict.
var MANAGE_SUBTASK_PARAMS = func() *entities.OrderedMap[any] {
	properties := entities.NewOrderedMap[any]()
	properties.Set("action", schemaProp("string", "action"))
	properties.Set("task_id", schemaProp("string", "task_id"))
	properties.Set("subtask_id", schemaProp("string", "subtask_id"))
	properties.Set("title", schemaProp("string", "title"))
	properties.Set("description", schemaProp("string", "description"))
	properties.Set("status", schemaProp("string", "status"))
	properties.Set("priority", schemaProp("string", "priority"))
	properties.Set("assignees", schemaProp("string", "assignees"))
	properties.Set("progress_percentage", schemaProp("integer", "progress_percentage"))
	properties.Set("progress_notes", schemaProp("string", "progress_notes"))
	properties.Set("completion_summary", schemaProp("string", "completion_summary"))
	properties.Set("testing_notes", schemaProp("string", "testing_notes"))
	properties.Set("insights_found", schemaProp("string", "insights_found"))
	properties.Set("challenges_overcome", schemaProp("string", "challenges_overcome"))
	properties.Set("skills_learned", schemaProp("string", "skills_learned"))
	properties.Set("next_recommendations", schemaProp("string", "next_recommendations"))
	properties.Set("deliverables", schemaProp("string", "deliverables"))
	properties.Set("completion_quality", schemaProp("string", "completion_quality"))
	properties.Set("blockers", schemaProp("string", "blockers"))
	properties.Set("impact_on_parent", schemaProp("string", "impact_on_parent"))
	properties.Set("user_id", schemaProp("string", "user_id"))

	m := entities.NewOrderedMap[any]()
	m.Set("type", "object")
	m.Set("properties", properties)
	m.Set("required", []string{"action"})
	m.Set("additionalProperties", false)
	return m
}()

func schemaProp(typ, key string) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("type", typ)
	p.Set("description", omGetStr(MANAGE_SUBTASK_PARAMETERS_DESCRIPTION, key))
	return p
}

// GetManageSubtaskParameters ports get_manage_subtask_parameters.
func GetManageSubtaskParameters() *entities.OrderedMap[any] {
	props, _ := MANAGE_SUBTASK_PARAMS.Get("properties")
	return props.(*entities.OrderedMap[any])
}

// GetManageSubtaskDescription ports get_manage_subtask_description.
func GetManageSubtaskDescription() string { return MANAGE_SUBTASK_DESCRIPTION }

// SUBTASK_DESCRIPTION is the backward-compatibility alias.
const SUBTASK_DESCRIPTION = MANAGE_SUBTASK_DESCRIPTION

// PARAMETER_DESCRIPTIONS ports the expected-format parameter description dict.
var PARAMETER_DESCRIPTIONS = func() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	add := func(key, typ string, required bool) {
		d := entities.NewOrderedMap[any]()
		d.Set("description", omGetStr(MANAGE_SUBTASK_PARAMETERS_DESCRIPTION, key))
		d.Set("type", typ)
		d.Set("required", required)
		m.Set(key, d)
	}
	add("action", "string", true)
	add("task_id", "string", false)
	add("subtask_id", "string", false)
	add("title", "string", false)
	add("description", "string", false)
	add("status", "string", false)
	add("priority", "string", false)
	add("assignees", "string", false)
	add("progress_percentage", "integer", false)
	add("progress_notes", "string", false)
	add("completion_summary", "string", false)
	add("testing_notes", "string", false)
	add("insights_found", "string", false)
	add("challenges_overcome", "string", false)
	add("skills_learned", "string", false)
	add("next_recommendations", "string", false)
	add("deliverables", "string", false)
	add("completion_quality", "string", false)
	add("blockers", "string", false)
	add("impact_on_parent", "string", false)
	add("user_id", "string", false)
	return m
}()

// MANAGE_SUBTASK_PARAMETERS ports the legacy parameter description dict.
var MANAGE_SUBTASK_PARAMETERS = func() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("action", "Action: create, update, delete, get, list, complete. Required. (string)")
	m.Set("task_id", "Parent task ID. Required for all actions. (string)")
	m.Set("subtask_id", "Subtask ID for operations. Required for update, delete, get, complete actions. (string)")
	m.Set("title", "Subtask title. Required for create, optional for update. (string)")
	m.Set("description", "Detailed subtask description explaining what needs to be done. Include acceptance criteria if relevant. Optional for: create, update")
	m.Set("status", "Subtask status: 'todo', 'in_progress', 'done'. Optional - use progress_percentage instead for automatic status mapping.")
	m.Set("priority", "Subtask priority: 'low', 'medium', 'high', 'urgent', 'critical'. Optional for: create, update. Default: inherits from parent")
	m.Set("assignees", "List of assignee identifiers. Optional for: create, update. Example: ['user1', 'user2']")
	m.Set("completion_summary", "Detailed summary of what was accomplished. BE SPECIFIC! Required for complete action. Example: 'Implemented JWT authentication with refresh tokens, 2-hour expiry, and secure httpOnly cookies'")
	m.Set("progress_notes", "Brief description of current work status that builds progress history. MANDATORY for: update, complete. Creates timestamped progress entries automatically. Example: 'Completed UI mockup, starting on API integration'")
	m.Set("progress_percentage", "Integer 0-100 representing completion. Automatically maps to status (0=todo, 1-99=in_progress, 100=done). Use this instead of status field. Optional for: update")
	m.Set("blockers", "List any impediments or issues. Optional for: create, update. Example: ['Missing API documentation', 'Waiting for design approval']")
	m.Set("impact_on_parent", "How completing this subtask affects the parent task. Required for: complete. Example: 'Authentication backend now 75% complete, ready for testing phase'")
	m.Set("insights_found", "Important discoveries during subtask work. Optional for: create, update, complete. Example: ['Found existing utility function for validation', 'Discovered performance bottleneck in current approach']")
	m.Set("challenges_overcome", "Challenges faced and how they were resolved. Optional for: create, update, complete. Example: ['Resolved API timeout by implementing retry mechanism', 'Fixed authentication flow by updating token validation']")
	m.Set("skills_learned", "New skills or knowledge gained. Optional for: create, update, complete. Example: ['Learned advanced React hooks patterns', 'Mastered JWT token implementation']")
	m.Set("next_recommendations", "Suggestions for future work based on experience. Optional for: create, update, complete. Example: ['Consider implementing caching for API calls', 'Add comprehensive error logging']")
	m.Set("deliverables", "Specific artifacts or outputs created. Optional for: create, update, complete. Example: ['User authentication module', 'API endpoint documentation', 'Unit test suite']")
	m.Set("completion_quality", "Assessment of work quality. Optional for: complete. Example: 'Production-ready', 'Requires review', 'Prototype only'")
	m.Set("testing_notes", "Notes about testing performed. Optional for: complete. Example: 'Tested login flow with valid/invalid credentials, verified token refresh mechanism'")
	return m
}()

func omGetStr(o *entities.OrderedMap[any], key string) string {
	v, _ := o.Get(key)
	s, _ := v.(string)
	return s
}
