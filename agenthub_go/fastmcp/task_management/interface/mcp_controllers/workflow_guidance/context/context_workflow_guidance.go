package context

// Context Management Workflow Guidance
// (Python workflow_guidance/context/context_workflow_guidance.py).

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_guidance"
)

// ContextWorkflowGuidance ports ContextWorkflowGuidance.
type ContextWorkflowGuidance struct {
	workflow_guidance.BaseWorkflowGuidance
}

// GenerateGuidance ports generate_guidance.
func (g *ContextWorkflowGuidance) GenerateGuidance(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if context == nil {
		context = entities.NewOrderedMap[any]()
	}
	taskID := workflow_guidance.ContextGetDefault(context, "task_id", "your-task-id")

	out := entities.NewOrderedMap[any]()
	out.Set("current_state", g.determineState(action, context))
	out.Set("rules", g.getContextRules())
	out.Set("next_actions", g.getNextActions(action, taskID))
	out.Set("hints", g.getHints(action))
	out.Set("warnings", g.getWarnings(action))
	out.Set("examples", g.getExamples(action, taskID))
	out.Set("parameter_guidance", g.getParameterGuidance(action))
	return out
}

func (g *ContextWorkflowGuidance) determineState(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	stateMap := map[string]string{
		"create":       "creating_context",
		"update":       "updating_context",
		"get":          "retrieving_context",
		"delete":       "removing_context",
		"add_insight":  "adding_insight",
		"add_progress": "tracking_progress",
		"list":         "browsing_contexts",
	}
	phase, ok := stateMap[action]
	if !ok {
		phase = "context_operation"
	}
	out := entities.NewOrderedMap[any]()
	out.Set("phase", phase)
	out.Set("action", action)
	return out
}

func (g *ContextWorkflowGuidance) getContextRules() []any {
	return []any{
		"📋 Always create context before completing tasks",
		"📝 Use meaningful titles and descriptions",
		"🔄 Update context regularly with progress",
		"🔗 Link context to proper project and branch",
		"💡 Add insights to share knowledge with team",
	}
}

func (g *ContextWorkflowGuidance) getNextActions(action string, taskID any) []any {
	switch action {
	case "create":
		return []any{
			contextNext("high", "Add initial progress", "Document your starting point",
				contextExample("manage_context", contextParams(
					"action", "add_progress",
					"task_id", taskID,
					"content", "Started working on [describe initial work]",
					"agent", "your_agent_name",
				))),
			contextNext("medium", "Update task status", "Mark task as in progress",
				contextExample("manage_task", contextParams(
					"action", "update",
					"task_id", taskID,
					"status", "in_progress",
				))),
		}
	case "update":
		return []any{
			contextNext("high", "Continue work", "Proceed with task implementation",
				contextExample("manage_context", contextParams(
					"action", "add_progress",
					"task_id", taskID,
					"content", "Completed X, working on Y",
				))),
		}
	case "add_progress":
		return []any{
			contextNext("medium", "Update task details", "Keep task current with latest progress",
				contextExample("manage_task", contextParams(
					"action", "update",
					"task_id", taskID,
					"details", "Latest progress: [describe current state]",
				))),
		}
	default:
		return []any{
			contextNext("medium", "Continue context management", "Use context to track task progress",
				contextExample("manage_context", contextParams(
					"action", "add_progress",
					"task_id", taskID,
					"content", "Describe your progress",
				))),
		}
	}
}

func (g *ContextWorkflowGuidance) getHints(action string) []any {
	hintsMap := map[string][]any{
		"create": {
			"💡 Context is required before completing tasks",
			"🎯 Use descriptive titles for better organization",
			"📁 Group related contexts by project",
		},
		"update": {
			"📝 Update context regularly to maintain accuracy",
			"🔄 Use data_status to track task progression",
		},
		"add_progress": {
			"📈 Regular progress updates help team coordination",
			"🎯 Be specific about what was accomplished",
		},
		"add_insight": {
			"💡 Share important discoveries with insights",
			"🏷️ Use categories to organize insights by topic",
		},
		"get": {
			"🔍 Use context to understand task history",
			"📊 Check progress timeline for task evolution",
		},
	}
	if v, ok := hintsMap[action]; ok {
		return v
	}
	return []any{
		"📋 Context management helps track task progress",
		"🔗 Keep context synchronized with task status",
	}
}

func (g *ContextWorkflowGuidance) getWarnings(action string) []any {
	if action == "delete" {
		return []any{
			"⚠️ Deleting context removes all progress history",
			"💾 Consider backing up important insights first",
		}
	}
	return []any{}
}

func (g *ContextWorkflowGuidance) getExamples(action string, taskID any) *entities.OrderedMap[any] {
	tid := value_objects.PyStr(taskID)

	examples := map[string]*entities.OrderedMap[any]{
		"create": contextExamples(
			"basic_create", contextCommandExample(
				"Create context for a task",
				"manage_context(action='create', task_id='"+tid+"', project_id='your_project')",
			),
			"detailed_create", contextCommandExample(
				"Create context with initial data",
				"manage_context(action='create', task_id='"+tid+"', data_title='Task Title', data_description='Detailed description')",
			),
		),
		"update": contextExamples(
			"status_update", contextCommandExample(
				"Update context status",
				"manage_context(action='update', task_id='"+tid+"', data_status='in_progress')",
			),
			"progress_update", contextCommandExample(
				"Update context with progress",
				"manage_context(action='update', task_id='"+tid+"', data_description='Updated progress description')",
			),
		),
		"add_progress": contextExamples(
			"track_progress", contextCommandExample(
				"Add progress note",
				"manage_context(action='add_progress', task_id='"+tid+"', content='Completed database setup')",
			),
		),
		"add_insight": contextExamples(
			"share_insight", contextCommandExample(
				"Add insight for team",
				"manage_context(action='add_insight', task_id='"+tid+"', content='Found better approach using X', category='solution')",
			),
		),
	}
	if v, ok := examples[action]; ok {
		return v
	}
	fallback := entities.NewOrderedMap[any]()
	fallback.Set("general", contextCommandExample(
		"Context management operation",
		"manage_context(action='"+action+"', task_id='"+tid+"')",
	))
	return fallback
}

func (g *ContextWorkflowGuidance) getParameterGuidance(action string) *entities.OrderedMap[any] {
	baseParams := []any{"task_id", "user_id", "project_id", "git_branch_name"}

	actionParams := map[string][]any{
		"create":       append(append([]any{}, baseParams...), "data_title", "data_description", "data_status", "data_priority"),
		"update":       append(append([]any{}, baseParams...), "data_title", "data_description", "data_status"),
		"add_progress": append(append([]any{}, baseParams...), "content", "agent"),
		"add_insight":  append(append([]any{}, baseParams...), "content", "agent", "category", "importance"),
		"get":          baseParams,
		"delete":       baseParams,
	}

	applicable, ok := actionParams[action]
	if !ok {
		applicable = baseParams
	}

	tips := entities.NewOrderedMap[any]()
	tips.Set("task_id", contextTip(
		"REQUIRED",
		"Must be a valid task UUID",
		[]any{"66b7b56abb3b4cccab12cd3c9890d7e7"},
		nil,
	))
	tips.Set("content", contextTip(
		"REQUIRED for add_progress/add_insight",
		"Be specific and descriptive",
		[]any{
			"Completed user authentication module",
			"Found performance issue in database queries",
		},
		nil,
	))
	tips.Set("data_status", contextTip(
		"Optional",
		"Tracks task progression",
		nil,
		[]any{"todo", "in_progress", "done", "blocked"},
	))
	tips.Set("category", contextTip(
		"Optional for insights",
		"Organizes insights by topic",
		[]any{"solution", "blocker", "discovery", "performance"},
		nil,
	))

	out := entities.NewOrderedMap[any]()
	out.Set("applicable_parameters", applicable)
	out.Set("parameter_tips", tips)
	return out
}

// --- local builders (unique to package context) ---

func contextParams(kv ...any) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		om.Set(kv[i].(string), kv[i+1])
	}
	return om
}

func contextExample(tool string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("tool", tool)
	e.Set("params", params)
	return e
}

func contextNext(priority, action, description string, example *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	a := entities.NewOrderedMap[any]()
	a.Set("priority", priority)
	a.Set("action", action)
	a.Set("description", description)
	a.Set("example", example)
	return a
}

func contextCommandExample(description, command string) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("description", description)
	e.Set("command", command)
	return e
}

func contextExamples(kv ...any) *entities.OrderedMap[any] { return contextParams(kv...) }

// contextTip builds a parameter tip; examples/values are omitted when nil,
// matching the Python literals that include only one of the two.
func contextTip(requirement, tip string, examples, values []any) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("requirement", requirement)
	p.Set("tip", tip)
	if examples != nil {
		p.Set("examples", examples)
	}
	if values != nil {
		p.Set("values", values)
	}
	return p
}
