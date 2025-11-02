"""
Agent Management Tool Description

This module contains the comprehensive documentation for the manage_agent MCP tool.
Separated from the controller logic for better maintainability and organization.
"""

MANAGE_AGENT_DESCRIPTION = """
AGENT MANAGEMENT SYSTEM - Agent Registration and Assignment (33 Specialized Agents)

WHAT IT DOES: Manages agent registration, assignment, and lifecycle within projects. Coordinates 33 specialized agents from the agent-library including coding, debugging, testing, architecture, DevOps, documentation, security, ML, and orchestration agents.
WHEN TO USE: Agent registration, assignment, updates, and project agent management.
CRITICAL FOR: Multi-agent orchestration and dynamic agent assignment.

AVAILABLE AGENTS (33 Specialized Agents):

| Category | Agent | Purpose |
|----------|-------|---------|
| **Development & Coding (4)** | coding-agent | Implementation and feature development |
| | debugger-agent | Bug fixing and troubleshooting |
| | code-reviewer-agent | Code quality and review |
| | prototyping-agent | Rapid prototyping and POCs |
| **Testing & QA (3)** | test-orchestrator-agent | Comprehensive test management |
| | uat-coordinator-agent | User acceptance testing |
| | performance-load-tester-agent | Performance and load testing |
| **Architecture & Design (4)** | system-architect-agent | System design and architecture |
| | design-system-agent | Design system and UI patterns |
| | shadcn-ui-expert-agent | UI/UX design and frontend development |
| | core-concept-agent | Core concepts and fundamentals |
| **DevOps & Infrastructure (1)** | devops-agent | CI/CD and infrastructure |
| **Documentation (1)** | documentation-agent | Technical documentation |
| **Project & Planning (4)** | project-initiator-agent | Project setup and kickoff |
| | task-planning-agent | Task breakdown and planning |
| | master-orchestrator-agent | Complex workflow orchestration |
| | elicitation-agent | Requirements gathering |
| **Security & Compliance (3)** | security-auditor-agent | Security audits and reviews |
| | compliance-scope-agent | Regulatory compliance |
| | ethical-review-agent | Ethical considerations |
| **Analytics & Optimization (3)** | analytics-setup-agent | Analytics and tracking setup |
| | efficiency-optimization-agent | Process optimization |
| | health-monitor-agent | System health monitoring |
| **Marketing & Branding (3)** | marketing-strategy-orchestrator-agent | Marketing strategy |
| | community-strategy-agent | Community building |
| | branding-agent | Brand identity |
| **Research & Analysis (4)** | deep-research-agent | In-depth research |
| | llm-ai-agents-research | AI/ML research and innovations |
| | root-cause-analysis-agent | Problem analysis |
| | technology-advisor-agent | Technology recommendations |
| **AI & Machine Learning (1)** | ml-specialist-agent | Machine learning implementation |
| **Creative & Ideation (1)** | creative-ideation-agent | Creative idea generation |

| Action | Required Parameters | Optional Parameters | Description |
|--------|-------------------|-------------------|-------------|
| register | project_id, name | agent_id (auto-generated if blank), call_agent | Register a new agent to a project |
| assign | project_id, agent_id, git_branch_id | | Assign an agent to a task tree (branch) |
| get | project_id, agent_id | | Retrieve agent details |
| list | project_id | | List all agents in a project |
| update | project_id, agent_id | name, call_agent | Update agent metadata |
| unassign | project_id, agent_id, git_branch_id | | Remove agent from a task tree (branch) |
| unregister | project_id, agent_id | | Remove agent from a project |
| rebalance | project_id | | Rebalance agent assignments in a project |

USAGE GUIDELINES:
• Provide all required identifiers for each action (see table)
• Optional parameters can be omitted unless updating values
• Returns detailed error messages for missing/invalid parameters, unknown actions, and internal errors
• All business logic delegated to AgentApplicationFacade

ERROR HANDLING:
• Missing required fields: Clear error specifying needed fields
• Unknown actions: Error listing valid actions
• Internal errors: Logged and returned with generic error message
"""

MANAGE_AGENT_PARAMETERS_DESCRIPTION = {
    "action": "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance",
    "project_id": "[REQUIRED] Project identifier for agent management. No default value - must be provided",
    "agent_id": "[OPTIONAL] Agent identifier. Required for most actions except register/list/rebalance",
    "name": "[OPTIONAL] Agent name. Required for register, optional for update",
    "call_agent": "[OPTIONAL] Call agent string or configuration. Optional, for register/update actions",
    "git_branch_id": "[OPTIONAL] Task tree identifier. Required for assign/unassign actions",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails",
}

MANAGE_AGENT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["action"],
        },
        # Agent identification parameters
        "project_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["project_id"],
        },
        "agent_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["agent_id"],
        },
        # Agent configuration parameters
        "name": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["name"],
        },
        "call_agent": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["call_agent"],
        },
        # Context parameters
        "git_branch_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["git_branch_id"],
        },
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": MANAGE_AGENT_PARAMETERS_DESCRIPTION["user_id"],
        },
    },
    "required": [
        "action"
    ],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False,
}


def get_manage_agent_parameters():
    """Get manage agent parameters for use in controller."""
    return MANAGE_AGENT_PARAMS["properties"]


def get_manage_agent_description():
    """Get manage agent description for use in controller."""
    return MANAGE_AGENT_DESCRIPTION


# Legacy support for existing imports
MANAGE_AGENT_PARAMETERS = {
    "action": "Agent management action to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance. (string)",
    "project_id": "Project identifier for agent management. Required for all actions. Must be provided. (string)",
    "agent_id": "Agent identifier. Required for most actions except register/list/rebalance. (string)",
    "name": "Agent name. Required for register, optional for update. (string)",
    "call_agent": "Call agent string or configuration. Optional, for register/update actions. (string)",
    "git_branch_id": "Task tree identifier. Required for assign/unassign actions. (string)",
}
