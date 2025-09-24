"""
Agent Management Tool Description

This module contains the comprehensive documentation for the agent management MCP tool
that handles agent management operations (register, assign, update, etc.).
Agent invocation is handled separately by the call_agent tool.
"""

UNIFIED_AGENT_DESCRIPTION = """
🤖 AGENT MANAGEMENT SYSTEM - Registration and Assignment for 32 Specialized Agents

⭐ WHAT IT DOES: Manages agent registration, assignment, and lifecycle within projects. Coordinates 32 specialized agents covering development, testing, architecture, DevOps, documentation, and more.
📋 WHEN TO USE: Agent registration, assignment, updates, and project agent management operations.
🎯 CRITICAL FOR: Multi-agent orchestration, dynamic agent assignment, and project organization.
📝 NOTE: For agent invocation/calling, use the separate 'call_agent' tool.
🚀 AVAILABLE AGENTS (32 Total):
  Development & Coding:
    coding-agent - Implementation and feature development
    debugger-agent - Bug fixing and troubleshooting
    code-reviewer-agent - Code quality and review
    prototyping-agent - Rapid prototyping and POCs
    
  Testing & QA:
    test-orchestrator-agent - Comprehensive test management
    uat-coordinator-agent - User acceptance testing
    performance-load-tester-agent - Performance and load testing
    
  Architecture & Design:
    system-architect-agent - System design and architecture
    design-system-agent - Design system and UI patterns
    @ui_designer_expert_shadcn_agent - Shadcn/UI components and frontend
    core-concept-agent - Core concepts and fundamentals
    
  DevOps & Deployment:
    devops-agent - CI/CD and infrastructure
    @adaptive_deployment_strategist_agent - Deployment strategies
    @swarm_scaler_agent - Distributed systems scaling
    
  Documentation & Specs:
    documentation-agent - Technical documentation
    @tech_spec_agent - Technical specifications
    @prd_architect_agent - Product requirements documents
    
  Project & Planning:
    project-initiator-agent - Project setup and kickoff
    task-planning-agent - Task breakdown and planning
    master-orchestrator-agent - Complex workflow orchestration
    elicitation-agent - Requirements gathering
    
  Security & Compliance:
    security-auditor-agent - Security audits and reviews
    compliance-scope-agent - Regulatory compliance
    ethical-review-agent - Ethical considerations
    
  Analytics & Optimization:
    analytics-setup-agent - Analytics and tracking setup
    efficiency-optimization-agent - Process optimization
    health-monitor-agent - System health monitoring
    
  Marketing & Growth:
    marketing-strategy-orchestrator-agent - Marketing strategy
    @seo_sem_agent - SEO and SEM optimization
    @growth_hacking_idea_agent - Growth strategies
    @content_strategy_agent - Content planning
    community-strategy-agent - Community building
    branding-agent - Brand identity
    
  Research & Analysis:
    deep-research-agent - In-depth research
    @mcp_researcher_agent - MCP and tool research
    root-cause-analysis-agent - Problem analysis
    technology-advisor-agent - Technology recommendations
    
  AI & Machine Learning:
    @brainjs_ml_agent - Machine learning with Brain.js
    
  Configuration & Integration:
    @mcp_configuration_agent - MCP setup and configuration
    
  Creative & Ideation:
    @idea_generation_agent - Creative idea generation
    @idea_refinement_agent - Idea improvement
    
  Problem Resolution:
    @remediation_agent - Issue remediation and fixes

| Action      | Required Parameters                  | Optional Parameters                | Description                                      |
|-------------|-------------------------------------|------------------------------------|--------------------------------------------------|
| register    | project_id, name                    | agent_id (auto-generated if blank), call_agent | Register a new agent to a project                |
| assign      | project_id, agent_id, git_branch_id  |                                    | Assign an agent to a task tree (branch)          |
| get         | project_id, agent_id                |                                    | Retrieve agent details                           |
| list        | project_id                          |                                    | List all agents in a project                     |
| update      | project_id, agent_id                | name, call_agent                   | Update agent metadata                            |
| unassign    | project_id, agent_id, git_branch_id  |                                   | Remove agent from a task tree (branch)           |
| unregister  | project_id, agent_id                |                                    | Remove agent from a project                      |
| rebalance   | project_id                          |                                    | Rebalance agent assignments in a project         |

💡 USAGE GUIDELINES:
• Provide all required identifiers for each action (see table above).
• Optional parameters can be omitted unless updating values.
• The tool returns detailed error messages for missing or invalid parameters, unknown actions, and internal errors.
• All business logic is delegated to the application layer (AgentApplicationFacade).
• For invoking agents, use the separate 'call_agent' tool with agent names.

🎯 USE CASES:
• Register agents to projects for specialized task handling
• Assign agents to specific git branches (task trees)
• Manage agent lifecycle (update, unassign, unregister)
• List all agents in a project
• Rebalance agent assignments across projects

📊 MANAGEMENT PATTERNS:
1. Project Setup:
   - Register required agents to project
   - Assign agents to initial branches
   - Configure agent metadata

2. Team Expansion:
   - Register additional specialized agents
   - Assign to specific task areas
   - Update agent configurations

3. Project Cleanup:
   - Unassign agents from completed branches
   - Unregister unused agents
   - Rebalance remaining assignments

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed.
• Unknown actions return an error listing valid actions.
• Invalid agent names will result in an error with available agents list.
• Internal errors are logged and returned with a generic error message.
• Agent loading failures provide fallback to master-orchestrator-agent.

✅ VALIDATION CHECKPOINTS:
• Check: Are all required parameters provided for the action?
• Check: Is the agent name prefixed with @ (for call action)?
• Check: Does the agent exist in available agents list (for call action)?
• Check: Is the work type appropriate for the selected agent?
• Pass: Operation executed successfully
• Fail: Error with clear guidance and suggestions

⚠️ IMPORTANT NOTES:
• Agent names must include the @ prefix for call action
• project_id is required for all management actions (register, assign, get, list, update, unassign, unregister, rebalance)
• Switch to a role agent if no role is specified; otherwise, the default agent master-orchestrator-agent will be used
• Each agent has specialized knowledge and capabilities
• Agents can collaborate as specified in their connectivity
• Invalid agent names will result in an error with available agents list
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
    "name_agent": "[REQUIRED for call action] Name of the agent to load and invoke. Must be a valid, registered agent name with @ prefix (e.g., 'master-orchestrator-agent')"
}

UNIFIED_AGENT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "action": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["action"]
        },
        
        # Agent identification parameters
        "project_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["project_id"]
        },
        "agent_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["agent_id"]
        },
        
        # Agent configuration parameters
        "name": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["name"]
        },
        "call_agent": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["call_agent"]
        },
        
        # Context parameters
        "git_branch_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["git_branch_id"]
        },
        
        # Authentication parameters
        "user_id": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["user_id"]
        },
        
        # Agent invocation parameters
        "name_agent": {
            "type": "string",
            "description": UNIFIED_AGENT_PARAMETERS_DESCRIPTION["name_agent"]
        }
    },
    "required": ["action"],  # Only action required at schema level - business logic validates per action
    "additionalProperties": False
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
    "name_agent": "Name of the agent to load and invoke. Required for call action. Use @ prefix. (string)"
}
