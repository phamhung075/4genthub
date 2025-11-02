"""
Agent Management Tool Description

This module contains the comprehensive documentation for the agent management MCP tool
that handles agent management operations (register, assign, update, etc.).
Agent invocation is handled separately by the call_agent tool.
"""

UNIFIED_AGENT_DESCRIPTION = """
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
"""

UNIFIED_AGENT_PARAMETERS_DESCRIPTION = {
    "action": "Agent operation to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance",
    "project_id": "[REQUIRED] Project identifier for agent management",
    "agent_id": "[OPTIONAL] Agent identifier. Required for most actions except register/list/rebalance",
    "name": "[OPTIONAL] Agent name. Required for register, optional for update",
    "call_agent": "[OPTIONAL] Call agent string or configuration. Optional, for register/update actions",
    "git_branch_id": "[OPTIONAL] Task tree identifier. Required for assign/unassign actions",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails",
    "name_agent": "[REQUIRED for call action] Name of the agent to load and invoke. Must be a valid, registered agent name with @ prefix (e.g., 'master-orchestrator-agent')",
}

UNIFIED_AGENT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["action"],
        },
        # Agent identification parameters
        "project_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["project_id"],
        },
        "agent_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["agent_id"],
        },
        # Agent configuration parameters
        "name": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["name"],
        },
        "call_agent": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["call_agent"],
        },
        # Context parameters
        "git_branch_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["git_branch_id"],
        },
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["user_id"],
        },
        # Agent invocation parameters
        "name_agent": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["name_agent"],
        },
    },
    "required": [
        "action"
    ],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False,
}


def get_unified_agent_parameters():
    """Get unified agent parameters for use in controller."""
    return UNIFIED_AGENT_PARAMS["properties"]


def get_unified_agent_description():
    """Get unified agent description for use in controller."""
    return UNIFIED_AGENT_DESCRIPTION


# Legacy support for existing imports - maintain backward compatibility
MANAGE_AGENT_PARAMETERS = {
    "action": "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance, call. (string)",
    "project_id": "Project identifier for agent management. Required for management actions, optional for call. (string)",
    "agent_id": "Agent identifier. Required for most management actions except register/list/rebalance/call. (string)",
    "name": "Agent name. Required for register, optional for update. (string)",
    "call_agent": "Call agent string or configuration. Optional, for register/update actions. (string)",
    "git_branch_id": "Task tree identifier. Required for assign/unassign actions. (string)",
    "name_agent": "Name of the agent to load and invoke. Required for call action. Use @ prefix. (string)",
}
