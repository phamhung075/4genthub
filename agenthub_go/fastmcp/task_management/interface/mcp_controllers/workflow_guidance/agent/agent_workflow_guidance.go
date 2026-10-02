package agent

// Agent Workflow Guidance Implementation
// (Python workflow_guidance/agent/agent_workflow_guidance.py).

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_guidance"
)

// AgentWorkflowGuidanceImpl ports AgentWorkflowGuidance. The name carries the
// Impl suffix because the package already declares an AgentWorkflowGuidance
// interface (in agent_workflow_factory.go).
type AgentWorkflowGuidanceImpl struct {
	workflow_guidance.BaseWorkflowGuidance
}

func init() {
	NewAgentWorkflowGuidanceFunc = func() AgentWorkflowGuidance {
		return &AgentWorkflowGuidanceImpl{}
	}
}

// GenerateGuidance ports generate_guidance.
func (g *AgentWorkflowGuidanceImpl) GenerateGuidance(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("current_state", g.determineState(action, context))
	out.Set("rules", g.getAgentRules())
	out.Set("next_actions", g.getNextActions(action, context))
	out.Set("hints", g.getHints(action))
	out.Set("warnings", g.getWarnings(action))
	out.Set("examples", g.getExamples(action, context))
	out.Set("parameter_guidance", g.getParameterGuidance(action))
	return out
}

func (g *AgentWorkflowGuidanceImpl) determineState(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	phase := map[string]string{
		"register":   "agent_registration",
		"assign":     "agent_assignment",
		"get":        "agent_retrieval",
		"list":       "agent_listing",
		"update":     "agent_modification",
		"unassign":   "agent_removal",
		"unregister": "agent_deregistration",
		"rebalance":  "agent_rebalancing",
	}
	phaseName, ok := phase[action]
	if !ok {
		phaseName = "unknown"
	}
	out := entities.NewOrderedMap[any]()
	out.Set("phase", phaseName)
	out.Set("action", action)
	out.Set("context", "agent_management")
	return out
}

func (g *AgentWorkflowGuidanceImpl) getAgentRules() []any {
	return []any{
		"🤖 RULE: Each agent must have a unique identifier within a project",
		"📋 RULE: Agents must be registered before they can be assigned to branches",
		"🌿 RULE: Agents can be assigned to multiple branches for parallel work",
		"🔄 RULE: Agent workload is tracked across all assigned branches",
		"👥 RULE: Multiple agents can collaborate on the same branch",
		"🎯 RULE: Agents should have specialized roles (e.g., @frontend_agent, @testing_agent)",
		"⚖️ RULE: Use rebalance to distribute work evenly among agents",
		"🏷️ RULE: Agent names should reflect their specialization or role",
	}
}

func (g *AgentWorkflowGuidanceImpl) getNextActions(action string, context *entities.OrderedMap[any]) []any {
	projectID := workflow_guidance.ContextGet(context, "project_id")
	agentID := workflow_guidance.ContextGet(context, "agent_id")

	nextActions := []any{}

	switch action {
	case "register":
		nextActions = append(nextActions,
			agentNext("high", "Assign agent to a branch", "Put the agent to work on a specific branch",
				agentExample("manage_git_branch", agentParams(
					"action", "assign_agent",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", "branch_id",
					"agent_id", "registered_agent_id",
				))),
			agentNext("medium", "List available branches", "See which branches need agents",
				agentExample("manage_git_branch", agentParams(
					"action", "list",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
				))),
			agentNext("low", "Update agent details", "Modify agent name or capabilities",
				agentExample("manage_agent", agentParams(
					"action", "update",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"agent_id", "registered_agent_id",
					"name", "specialized-agent-v2",
				))),
		)
	case "list":
		nextActions = append(nextActions,
			agentNext("high", "Get specific agent details", "View detailed information about an agent",
				agentExample("manage_agent", agentParams(
					"action", "get",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"agent_id", "selected_agent_id",
				))),
			agentNext("medium", "Register a new agent", "Add a new specialized agent to the project",
				agentExample("manage_agent", agentParams(
					"action", "register",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"name", "new-specialist-agent",
					"call_agent", "@specialist_agent",
				))),
			agentNext("medium", "Rebalance workload", "Redistribute work among agents",
				agentExample("manage_agent", agentParams(
					"action", "rebalance",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
				))),
		)
	case "assign":
		nextActions = append(nextActions,
			agentNext("high", "Have agent get next task", "Agent should start working on tasks",
				agentExample("manage_task", agentParams(
					"action", "next",
					"git_branch_id", "assigned_branch_id",
					"include_context", true,
				))),
			agentNext("medium", "Check agent workload", "See all branches this agent is working on",
				agentExample("manage_agent", agentParams(
					"action", "get",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"agent_id", workflow_guidance.OrValue(agentID, "agent_id"),
				))),
		)
	case "unassign":
		nextActions = append(nextActions,
			agentNext("high", "Reassign to another agent", "Assign a different agent to continue the work",
				agentExample("manage_git_branch", agentParams(
					"action", "assign_agent",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", "branch_id",
					"agent_id", "replacement_agent_id",
				))),
			agentNext("medium", "Check branch status", "Review work status on the branch",
				agentExample("manage_git_branch", agentParams(
					"action", "get_statistics",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
					"git_branch_id", "branch_id",
				))),
		)
	case "rebalance":
		nextActions = append(nextActions,
			agentNext("high", "Review agent assignments", "Check the new workload distribution",
				agentExample("manage_agent", agentParams(
					"action", "list",
					"project_id", workflow_guidance.OrValue(projectID, "project_id"),
				))),
			agentNext("medium", "Monitor agent progress", "Track how agents handle their new workload",
				agentExample("manage_task", agentParams(
					"action", "list",
					"status", "in_progress",
				))),
		)
	}
	return nextActions
}

func (g *AgentWorkflowGuidanceImpl) getHints(action string) []any {
	hints := map[string][]any{
		"register": {
			"💡 Use descriptive agent names that indicate their specialization",
			"🔍 The call_agent parameter should match the agent's @handle format",
			"🤖 Consider creating agents for specific roles: frontend, backend, testing, ai_docs",
		},
		"list": {
			"📊 Review agent workload to identify who might need help",
			"🎯 Look for agents with fewer assignments for new work",
			"⚖️ Consider rebalancing if workload is uneven",
		},
		"get": {
			"📈 Check agent's current branch assignments and workload",
			"🔗 Agent details show all active assignments",
			"📋 Use this to understand an agent's specialization",
		},
		"assign": {
			"🌿 Agents can work on multiple branches simultaneously",
			"🤝 Multiple agents can collaborate on the same branch",
			"🎯 Match agent specialization to branch requirements",
		},
		"update": {
			"✏️ Update agent names to reflect evolved capabilities",
			"🏷️ Keep agent metadata current for better organization",
			"📝 Document agent capabilities in the name or metadata",
		},
		"unassign": {
			"🔄 Agent's completed work remains on the branch",
			"📋 Consider documenting handoff in task context",
			"✅ Ensure critical tasks are completed or handed off",
		},
		"unregister": {
			"⚠️ Unassign agent from all branches first",
			"📦 Agent's work history is preserved in tasks",
			"🔄 Can re-register the agent later if needed",
		},
		"rebalance": {
			"⚖️ Automatically redistributes work based on capacity",
			"📊 Considers task priorities and agent specializations",
			"🔄 Run periodically for optimal performance",
		},
	}
	if v, ok := hints[action]; ok {
		return v
	}
	return []any{"💡 Check action parameter for available operations"}
}

func (g *AgentWorkflowGuidanceImpl) getWarnings(action string) []any {
	warnings := []any{}
	switch action {
	case "register":
		warnings = append(warnings,
			"🚨 Agent ID must be unique within the project",
			"📋 Agent name should clearly indicate its purpose")
	case "assign":
		warnings = append(warnings,
			"⚠️ Ensure agent exists before assignment",
			"🔄 Agent will start processing tasks immediately")
	case "unassign":
		warnings = append(warnings,
			"📋 In-progress work should be completed or reassigned",
			"⚠️ Agent will stop processing new tasks on this branch")
	case "unregister":
		warnings = append(warnings,
			"🚨 Agent must be unassigned from all branches first",
			"⚠️ This removes the agent from the project completely")
	case "rebalance":
		warnings = append(warnings,
			"🔄 This may reassign tasks between agents",
			"📋 In-progress tasks are not affected")
	}
	return warnings
}

func (g *AgentWorkflowGuidanceImpl) getExamples(action string, context *entities.OrderedMap[any]) []any {
	examples := []any{}
	switch action {
	case "register":
		examples = append(examples, agentCodeExample("Register a frontend specialist agent",
			`manage_agent(
    action="register",
    project_id="my_project_id",
    name="frontend-react-specialist",
    call_agent="@react_expert"
)`))
	case "list":
		examples = append(examples, agentCodeExample("List all agents in a project",
			`manage_agent(
    action="list",
    project_id="my_project_id"
)`))
	case "assign":
		examples = append(examples, agentCodeExample("Assign agent to a branch",
			`manage_agent(
    action="assign",
    project_id="my_project_id",
    agent_id="agent_uuid",
    git_branch_id="branch_uuid"
)`))
	case "get":
		examples = append(examples, agentCodeExample("Get agent details and workload",
			`manage_agent(
    action="get",
    project_id="my_project_id",
    agent_id="agent_uuid"
)`))
	case "rebalance":
		examples = append(examples, agentCodeExample("Rebalance workload across agents",
			`manage_agent(
    action="rebalance",
    project_id="my_project_id"
)`))
	}
	return examples
}

func (g *AgentWorkflowGuidanceImpl) getParameterGuidance(action string) *entities.OrderedMap[any] {
	baseParams := entities.NewOrderedMap[any]()
	baseParams.Set("project_id", paramInfo(
		"OPTIONAL (default: 'default_project')",
		"String identifier",
		"Project to manage agents in",
	))

	actionParams := map[string]*entities.OrderedMap[any]{
		"register": paramPairs(
			"name", paramInfo(
				"REQUIRED",
				"Descriptive string",
				"Use format: role-specialization (e.g., 'frontend-vue-specialist')",
			),
			"agent_id", paramInfo(
				"OPTIONAL (auto-generated if blank)",
				"UUID string",
				"Leave blank for auto-generation",
			),
			"call_agent", paramInfo(
				"OPTIONAL",
				"String with @ prefix",
				"Agent handle for invocation (e.g., '@frontend_agent')",
			),
		),
		"get": paramPairs(
			"agent_id", paramInfo(
				"REQUIRED",
				"UUID string",
				"Get from list action or registration response",
			),
		),
		"update": paramPairs(
			"agent_id", paramInfo(
				"REQUIRED",
				"UUID string",
				"Agent to update",
			),
			"name", paramInfo(
				"OPTIONAL",
				"String",
				"New name for the agent",
			),
			"call_agent", paramInfo(
				"OPTIONAL",
				"String",
				"Updated invocation handle",
			),
		),
		"assign": paramPairs(
			"agent_id", paramInfo(
				"REQUIRED",
				"UUID string",
				"Agent to assign",
			),
			"git_branch_id", paramInfo(
				"REQUIRED",
				"UUID string",
				"Branch where agent will work",
			),
		),
		"unassign": paramPairs(
			"agent_id", paramInfo(
				"REQUIRED",
				"UUID string",
				"Agent to remove from branch",
			),
			"git_branch_id", paramInfo(
				"REQUIRED",
				"UUID string",
				"Branch to remove agent from",
			),
		),
		"unregister": paramPairs(
			"agent_id", paramInfo(
				"REQUIRED",
				"UUID string",
				"⚠️ Must be unassigned from all branches first",
			),
		),
	}

	params := baseParams.Copy()
	if extra, ok := actionParams[action]; ok {
		for _, k := range extra.Keys() {
			v, _ := extra.Get(k)
			params.Set(k, v)
		}
	}
	return params
}

// --- local builders (unique to package agent) ---

func agentParams(kv ...any) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		om.Set(kv[i].(string), kv[i+1])
	}
	return om
}

func agentExample(tool string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("tool", tool)
	e.Set("params", params)
	return e
}

func agentNext(priority, action, description string, example *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	a := entities.NewOrderedMap[any]()
	a.Set("priority", priority)
	a.Set("action", action)
	a.Set("description", description)
	a.Set("example", example)
	return a
}

func agentCodeExample(description, code string) *entities.OrderedMap[any] {
	e := entities.NewOrderedMap[any]()
	e.Set("description", description)
	e.Set("code", code)
	return e
}

func paramInfo(requirement, format, tip string) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("requirement", requirement)
	p.Set("format", format)
	p.Set("tip", tip)
	return p
}

func paramPairs(kv ...any) *entities.OrderedMap[any] { return agentParams(kv...) }
