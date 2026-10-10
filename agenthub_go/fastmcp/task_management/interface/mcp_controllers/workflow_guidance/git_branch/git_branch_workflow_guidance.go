package git_branch

// Git Branch Workflow Guidance Implementation
// (Python workflow_guidance/git_branch/git_branch_workflow_guidance.py).

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_guidance"
)

// GitBranchWorkflowGuidance ports GitBranchWorkflowGuidance.
type GitBranchWorkflowGuidance struct {
	workflow_guidance.BaseWorkflowGuidance
}

// GenerateGuidance ports generate_guidance.
func (g *GitBranchWorkflowGuidance) GenerateGuidance(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("current_state", g.determineState(action, context))
	out.Set("rules", g.getGitBranchRules())
	out.Set("next_actions", g.getNextActions(action, context))
	out.Set("hints", g.getHints(action))
	out.Set("warnings", g.getWarnings(action))
	out.Set("examples", g.getExamples(action, context))
	out.Set("parameter_guidance", g.getParameterGuidance(action))
	return out
}

func (g *GitBranchWorkflowGuidance) determineState(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	phaseMap := map[string]string{
		"create":         "branch_creation",
		"get":            "branch_retrieval",
		"list":           "branch_listing",
		"update":         "branch_modification",
		"delete":         "branch_removal",
		"assign_agent":   "agent_assignment",
		"unassign_agent": "agent_removal",
		"get_statistics": "statistics_retrieval",
		"archive":        "branch_archival",
		"restore":        "branch_restoration",
	}
	phase, ok := phaseMap[action]
	if !ok {
		phase = "unknown"
	}
	out := entities.NewOrderedMap[any]()
	out.Set("phase", phase)
	out.Set("action", action)
	out.Set("context", "git_branch_management")
	return out
}

func (g *GitBranchWorkflowGuidance) getGitBranchRules() []any {
	return []any{
		"🌿 RULE: Branch names should be descriptive and follow naming conventions (e.g., feature/user-auth, bugfix/login-issue)",
		"📋 RULE: Always assign branches to specific projects - branches cannot exist without a project",
		"🚀 RULE: Active branches should have assigned agents for autonomous work",
		"🔄 RULE: Branch statistics update automatically when tasks are created/completed",
		"⚠️ RULE: Deleting a branch will cascade delete all associated tasks - use archive instead for soft delete",
		"🏷️ RULE: Branch description should clearly state the purpose and scope of work",
		"👥 RULE: Multiple agents can be assigned to a branch for collaboration",
		"📊 RULE: Use get_statistics to monitor branch progress and task completion",
	}
}

func (g *GitBranchWorkflowGuidance) getNextActions(action string, context *entities.OrderedMap[any]) []any {
	projectID := workflow_guidance.ContextGet(context, "project_id")
	gitBranchID := workflow_guidance.ContextGet(context, "git_branch_id")

	nextActions := []any{}

	switch action {
	case "create":
		nextActions = append(nextActions,
			gbNext("high", "Assign an agent to the branch", "Assign specialized AI agent to work on this branch",
				gbExample("manage_git_branch", gbParams(
					"action", "assign_agent",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", "created_branch_id",
					"agent_id", "agent_id",
				))),
			gbNext("high", "Create initial tasks", "Create tasks for the work to be done on this branch",
				gbExample("manage_task", gbParams(
					"action", "create",
					"git_branch_id", "created_branch_id",
					"title", "Implement feature X",
					"description", "Detailed requirements...",
				))),
			gbNext("medium", "Check branch statistics", "Monitor branch progress and task completion",
				gbExample("manage_git_branch", gbParams(
					"action", "get_statistics",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", "created_branch_id",
				))),
		)
	case "list":
		nextActions = append(nextActions,
			gbNext("high", "Select a branch to work on", "Choose a specific branch and get its details",
				gbExample("manage_git_branch", gbParams(
					"action", "get",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", "selected_branch_id",
				))),
			gbNext("medium", "Create a new branch", "Create a new branch for new work",
				gbExample("manage_git_branch", gbParams(
					"action", "create",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_name", "feature/new-feature",
					"git_branch_description", "Implement new feature X",
				))),
		)
	case "get":
		nextActions = append(nextActions,
			gbNext("high", "List tasks on this branch", "See all tasks associated with this branch",
				gbExample("manage_task", gbParams(
					"action", "list",
					"git_branch_id", workflow_guidance.OrValue(gitBranchID, "branch_id"),
				))),
			gbNext("medium", "Get branch statistics", "Check progress and completion metrics",
				gbExample("manage_git_branch", gbParams(
					"action", "get_statistics",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", workflow_guidance.OrValue(gitBranchID, "branch_id"),
				))),
			gbNext("medium", "Update branch details", "Modify branch name or description",
				gbExample("manage_git_branch", gbParams(
					"action", "update",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", workflow_guidance.OrValue(gitBranchID, "branch_id"),
					"git_branch_description", "Updated description",
				))),
		)
	case "assign_agent":
		nextActions = append(nextActions,
			gbNext("high", "Get next task for agent", "Agent should start working on tasks",
				gbExample("manage_task", gbParams(
					"action", "next",
					"git_branch_id", workflow_guidance.OrValue(gitBranchID, "branch_id"),
					"include_context", true,
				))),
		)
	case "delete":
		nextActions = append(nextActions,
			gbNext("high", "Create a new branch", "Start work on a different feature",
				gbExample("manage_git_branch", gbParams(
					"action", "create",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_name", "feature/next-feature",
					"git_branch_description", "Next feature to implement",
				))),
			gbNext("medium", "List remaining branches", "See what other branches exist",
				gbExample("manage_git_branch", gbParams(
					"action", "list",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
				))),
		)
	}
	return nextActions
}

func (g *GitBranchWorkflowGuidance) getHints(action string) []any {
	hints := map[string][]any{
		"create": {
			"💡 Use descriptive branch names like 'feature/user-authentication' or 'bugfix/login-timeout'",
			"🔍 Include a clear description of what work will be done on this branch",
			"👥 Consider assigning an agent immediately after creation for autonomous work",
		},
		"list": {
			"📊 Review branch statistics to identify which branches need attention",
			"🎯 Look for branches with incomplete tasks that need work",
			"🔄 Consider archiving old branches instead of deleting them",
		},
		"get": {
			"📈 Use this to understand the current state and progress of a branch",
			"🔗 Branch ID is required - get it from list action first",
			"📋 Follow up with task list to see detailed work items",
		},
		"update": {
			"✏️ Update descriptions to reflect current work scope",
			"🏷️ Branch names can be updated if naming conventions change",
			"📝 Keep descriptions current for better team understanding",
		},
		"delete": {
			"⚠️ WARNING: This will delete ALL tasks on the branch",
			"💾 Consider using 'archive' action instead for soft delete",
			"🔄 Archived branches can be restored later if needed",
		},
		"assign_agent": {
			"🤖 Agents will autonomously work on tasks in this branch",
			"👥 Multiple agents can collaborate on the same branch",
			"🎯 Assign specialized agents based on the work type",
		},
		"unassign_agent": {
			"🔄 Agent's work will be preserved when unassigned",
			"📋 Consider reassigning to another agent for continuity",
			"✅ Complete or hand off tasks before unassigning",
		},
		"get_statistics": {
			"📊 Statistics update automatically as tasks progress",
			"📈 Use this to monitor branch health and progress",
			"🎯 Identify bottlenecks or stalled work",
		},
		"archive": {
			"💾 Soft delete - branch and tasks are preserved",
			"🔄 Can be restored later with 'restore' action",
			"📦 Good for completed features or abandoned work",
		},
		"restore": {
			"♻️ Brings back archived branches with all tasks intact",
			"📋 Review branch content before restoring",
			"🔄 Consider if work is still relevant before restoring",
		},
	}
	if v, ok := hints[action]; ok {
		return v
	}
	return []any{"💡 Check action parameter for available operations"}
}

func (g *GitBranchWorkflowGuidance) getWarnings(action string) []any {
	warnings := []any{}
	switch action {
	case "create":
		warnings = append(warnings,
			"🚨 Branch name must be unique within the project",
			"📋 Always provide a meaningful description for clarity")
	case "delete":
		warnings = append(warnings,
			"🚨 CRITICAL: This will permanently delete ALL tasks on the branch!",
			"⚠️ This action cannot be undone - consider 'archive' instead",
			"💡 Use: manage_git_branch(action='archive') for soft delete")
	case "update":
		warnings = append(warnings,
			"⚠️ Changing branch name may affect external references",
			"📋 Ensure updated info doesn't conflict with other branches")
	case "assign_agent":
		warnings = append(warnings,
			"🤖 Ensure agent exists before assignment",
			"📋 Agent will start processing tasks immediately")
	case "archive":
		warnings = append(warnings,
			"📦 Archived branches won't appear in normal listings",
			"🔄 Tasks remain intact but won't be processed")
	}
	return warnings
}

func (g *GitBranchWorkflowGuidance) getExamples(action string, context *entities.OrderedMap[any]) []any {
	examples := []any{}

	projectID := workflow_guidance.ContextGetStringDefault(context, "project_id", "project_id")
	gitBranchID := workflow_guidance.ContextGetStringDefault(context, "git_branch_id", "branch_id")

	switch action {
	case "create":
		examples = append(examples,
			gbCodeExample("Assign an agent to work on the branch",
				`manage_git_branch(
    action="assign_agent",
    project_id="`+projectID+`",
    git_branch_id="`+gitBranchID+`",
    agent_id="coding-agent"
)`),
			gbCodeExample("Create first task on the branch",
				`manage_task(
    action="create",
    git_branch_id="`+gitBranchID+`",
    title="Implement core functionality",
    description="Build the main feature components",
    assignees="coding-agent"
)`),
		)
	case "list":
		examples = append(examples, gbCodeExample("List all branches in a project",
			`manage_git_branch(
    action="list",
    project_id="my_project_id"
)`))
	case "get":
		examples = append(examples, gbCodeExample("Get branch details",
			`manage_git_branch(
    action="get",
    project_id="my_project_id",
    git_branch_id="branch_uuid"
)`))
	case "assign_agent":
		examples = append(examples, gbCodeExample("Assign an agent to work on a branch",
			`manage_git_branch(
    action="assign_agent",
    project_id="my_project_id",
    git_branch_id="branch_uuid",
    agent_id="agent_uuid"
)`))
	case "get_statistics":
		examples = append(examples, gbCodeExample("Check branch progress",
			`manage_git_branch(
    action="get_statistics",
    project_id="my_project_id",
    git_branch_id="branch_uuid"
)`))
	}
	return examples
}

func (g *GitBranchWorkflowGuidance) getParameterGuidance(action string) *entities.OrderedMap[any] {
	baseParams := entities.NewOrderedMap[any]()
	baseParams.Set("project_id", gbParamInfo(
		"REQUIRED for all actions",
		"UUID string",
		"Get from manage_project(action='list') or project context",
	))

	nextActionParams := map[string]*entities.OrderedMap[any]{
		"create": gbParams(
			"git_branch_id", gbParamInfo(
				"REQUIRED for next actions",
				"UUID string (returned from creation)",
				"Use the git_branch_id from create response",
			),
			"agent_id", gbParamInfo(
				"REQUIRED for agent assignment",
				"Agent identifier string",
				"Assign coding-agent, test-orchestrator-agent, or other specialists",
			),
			"title", gbParamInfo(
				"REQUIRED for task creation",
				"String",
				"Create initial tasks to define work on this branch",
			),
		),
		"get": gbParams(
			"git_branch_id", gbParamInfo(
				"REQUIRED for task listing",
				"UUID string",
				"List tasks on this branch to see work items",
			),
			"action", gbParamInfo(
				"REQUIRED",
				"String",
				"Use 'list' to see tasks, 'get_statistics' to check progress",
			),
		),
		"list": gbParams(
			"git_branch_id", gbParamInfo(
				"OPTIONAL for filtering",
				"UUID string",
				"Get details of a specific branch",
			),
		),
		"update": gbParams(
			"git_branch_id", gbParamInfo(
				"REQUIRED",
				"UUID string",
				"Branch was just updated - list tasks to continue work",
			),
		),
		"delete": gbParams(
			"project_id", gbParamInfo(
				"REQUIRED",
				"UUID string",
				"List remaining branches or create a new one",
			),
		),
		"assign_agent": gbParams(
			"git_branch_id", gbParamInfo(
				"REQUIRED",
				"UUID string",
				"Get next task for the assigned agent",
			),
			"include_context", gbParamInfo(
				"OPTIONAL",
				"Boolean",
				"Use manage_task(action='next') to get work for agent",
			),
		),
		"get_statistics": gbParams(
			"git_branch_id", gbParamInfo(
				"REQUIRED",
				"UUID string",
				"List tasks to continue work or archive if complete",
			),
		),
	}

	params := baseParams.Copy()
	if extra, ok := nextActionParams[action]; ok {
		for _, k := range extra.Keys() {
			v, _ := extra.Get(k)
			params.Set(k, v)
		}
	}
	return params
}

// --- local builders (unique to package git_branch) ---

func gbParams(kv ...any) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		om.Set(kv[i].(string), kv[i+1])
	}
	return om
}

func gbExample(tool string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("tool", tool)
	e.Set("params", params)
	return e
}

func gbNext(priority, action, description string, example *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	a := entities.NewOrderedMap[any]()
	a.Set("priority", priority)
	a.Set("action", action)
	a.Set("description", description)
	a.Set("example", example)
	return a
}

func gbCodeExample(description, code string) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("description", description)
	e.Set("code", code)
	return e
}

func gbParamInfo(requirement, format, tip string) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("requirement", requirement)
	p.Set("format", format)
	p.Set("tip", tip)
	return p
}
