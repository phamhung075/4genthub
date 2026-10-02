// Package agent_mcp_controller ports
// task_management/interface/mcp_controllers/agent_mcp_controller/unified_agent_description.py.
package agent_mcp_controller

import "agenthub/fastmcp/task_management/domain/entities"

// UnifiedAgentDescription is UNIFIED_AGENT_DESCRIPTION (Python).
const UnifiedAgentDescription = `
🤖 AGENT MANAGEMENT SYSTEM - Agent Registration and Assignment (32 Specialized Agents)

⭐ WHAT IT DOES: Manages agent registration, assignment, and lifecycle within projects. Coordinates 32 specialized agents from development to deployment.
📋 WHEN TO USE: Agent registration, assignment, updates, and project agent management.
🎯 CRITICAL FOR: Multi-agent orchestration and dynamic agent assignment.
📝 NOTE: For agent invocation, use separate 'call_agent' tool.

🚀 AVAILABLE AGENTS (32 Total):

| Category | Agents | Purpose |
|----------|--------|---------|
| **Development** (4) | coding-agent, debugger-agent, code-reviewer-agent, prototyping-agent | Implementation, debugging, code review, POCs |
| **Testing** (3) | test-orchestrator-agent, uat-coordinator-agent, performance-load-tester-agent | Test management, UAT, performance testing |
| **Architecture** (4) | system-architect-agent, design-system-agent, @ui_designer_expert_shadcn_agent, core-concept-agent | System design, UI patterns, Shadcn/UI, fundamentals |
| **DevOps** (3) | devops-agent, @adaptive_deployment_strategist_agent, @swarm_scaler_agent | CI/CD, deployment strategies, scaling |
| **Documentation** (3) | documentation-agent, @tech_spec_agent, @prd_architect_agent | Technical docs, specifications, PRDs |
| **Planning** (4) | project-initiator-agent, task-planning-agent, master-orchestrator-agent, elicitation-agent | Project setup, task breakdown, orchestration, requirements |
| **Security** (3) | security-auditor-agent, compliance-scope-agent, ethical-review-agent | Security audits, compliance, ethics |
| **Analytics** (3) | analytics-setup-agent, efficiency-optimization-agent, health-monitor-agent | Analytics setup, optimization, monitoring |
| **Marketing** (6) | marketing-strategy-orchestrator-agent, @seo_sem_agent, @growth_hacking_idea_agent, @content_strategy_agent, community-strategy-agent, branding-agent | Marketing, SEO/SEM, growth, content, community, branding |
| **Research** (4) | deep-research-agent, @mcp_researcher_agent, root-cause-analysis-agent, technology-advisor-agent | Research, MCP tools, problem analysis, tech recommendations |
| **AI/ML** (1) | @brainjs_ml_agent | Machine learning with Brain.js |
| **Config** (1) | @mcp_configuration_agent | MCP setup and configuration |
| **Creative** (2) | @idea_generation_agent, @idea_refinement_agent | Idea generation, refinement |
| **Resolution** (1) | @remediation_agent | Issue remediation |

| Action | Required Parameters | Optional Parameters | Description |
|--------|-------------------|-------------------|-------------|
| register | project_id, name | agent_id, call_agent | Register agent to project |
| assign | project_id, agent_id, git_branch_id | | Assign agent to branch |
| get | project_id, agent_id | | Retrieve agent details |
| list | project_id | | List all project agents |
| update | project_id, agent_id | name, call_agent | Update agent metadata |
| unassign | project_id, agent_id, git_branch_id | | Remove agent from branch |
| unregister | project_id, agent_id | | Remove agent from project |
| rebalance | project_id | | Rebalance assignments |

💡 USAGE GUIDELINES:
• Provide required identifiers per action (see table)
• Optional parameters: omit unless updating values
• Returns detailed error messages for validation failures
• Business logic delegated to AgentApplicationFacade
• For agent invocation: use 'call_agent' tool separately

**Pattern**: {register → assign → work → unassign → unregister}
**Example**: Register coding-agent → Assign to feature branch → Complete work → Unassign → Cleanup

🛑 ERROR HANDLING:
• Missing required fields: Clear error with needed parameters
• Unknown actions: Error listing valid actions
• Invalid agent names: Error with available agents list
• Internal errors: Logged and returned with generic message

⚠️ IMPORTANT:
• project_id required for all management actions
• Agent names use @ prefix (e.g., @ui_designer_expert_shadcn_agent)
• Each agent has specialized knowledge and capabilities
• Agents maintain context during task execution
`

// UnifiedAgentParametersDescription is UNIFIED_AGENT_PARAMETERS_DESCRIPTION (Python); key order preserved.
var UnifiedAgentParametersDescription = func() *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	m.Set("action", "Agent operation to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance")
	m.Set("project_id", "[REQUIRED] Project identifier for agent management")
	m.Set("agent_id", "[OPTIONAL] Agent identifier. Required for most actions except register/list/rebalance")
	m.Set("name", "[OPTIONAL] Agent name. Required for register, optional for update")
	m.Set("call_agent", "[OPTIONAL] Call agent string or configuration. Optional, for register/update actions")
	m.Set("git_branch_id", "[OPTIONAL] Task tree identifier. Required for assign/unassign actions")
	m.Set("user_id", "[OPTIONAL] User identifier for authentication and audit trails")
	m.Set("name_agent", "[REQUIRED for call action] Name of the agent to load and invoke. Must be a valid, registered agent name with @ prefix (e.g., 'master-orchestrator-agent')")
	return m
}()

func unifiedParamDesc(key string) string {
	value, _ := UnifiedAgentParametersDescription.Get(key)
	return value
}

func unifiedAgentStringProperty(description string) *entities.OrderedMap[any] {
	p := entities.NewOrderedMap[any]()
	p.Set("type", "string")
	p.Set("description", description)
	return p
}

func buildUnifiedAgentProperties() *entities.OrderedMap[any] {
	props := entities.NewOrderedMap[any]()
	props.Set("action", unifiedAgentStringProperty(unifiedParamDesc("action")))
	props.Set("project_id", unifiedAgentStringProperty(unifiedParamDesc("project_id")))
	props.Set("agent_id", unifiedAgentStringProperty(unifiedParamDesc("agent_id")))
	props.Set("name", unifiedAgentStringProperty(unifiedParamDesc("name")))
	props.Set("call_agent", unifiedAgentStringProperty(unifiedParamDesc("call_agent")))
	props.Set("git_branch_id", unifiedAgentStringProperty(unifiedParamDesc("git_branch_id")))
	props.Set("user_id", unifiedAgentStringProperty(unifiedParamDesc("user_id")))
	props.Set("name_agent", unifiedAgentStringProperty(unifiedParamDesc("name_agent")))
	return props
}

// UnifiedAgentParams is UNIFIED_AGENT_PARAMS (Python); key order preserved.
var UnifiedAgentParams = func() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("type", "object")
	m.Set("properties", buildUnifiedAgentProperties())
	m.Set("required", []any{"action"})
	m.Set("additionalProperties", false)
	return m
}()

// GetUnifiedAgentParameters returns UNIFIED_AGENT_PARAMS["properties"].
func GetUnifiedAgentParameters() *entities.OrderedMap[any] {
	props, _ := UnifiedAgentParams.Get("properties")
	return props.(*entities.OrderedMap[any])
}

// GetUnifiedAgentDescription returns UNIFIED_AGENT_DESCRIPTION.
func GetUnifiedAgentDescription() string { return UnifiedAgentDescription }

// ManageAgentParameters is MANAGE_AGENT_PARAMETERS (Python legacy); key order preserved.
var ManageAgentParameters = func() *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	m.Set("action", "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance, call. (string)")
	m.Set("project_id", "Project identifier for agent management. Required for management actions, optional for call. (string)")
	m.Set("agent_id", "Agent identifier. Required for most management actions except register/list/rebalance/call. (string)")
	m.Set("name", "Agent name. Required for register, optional for update. (string)")
	m.Set("call_agent", "Call agent string or configuration. Optional, for register/update actions. (string)")
	m.Set("git_branch_id", "Task tree identifier. Required for assign/unassign actions. (string)")
	m.Set("name_agent", "Name of the agent to load and invoke. Required for call action. Use @ prefix. (string)")
	return m
}()
