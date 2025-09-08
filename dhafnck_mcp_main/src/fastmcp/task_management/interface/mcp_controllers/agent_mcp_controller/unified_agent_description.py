"""
Unified Agent Management Tool Description

This module contains the comprehensive documentation for the unified agent management MCP tool
that combines both agent management (register, assign, update, etc.) and agent invocation (call_agent) operations.
"""

UNIFIED_AGENT_DESCRIPTION = """
🤖 UNIFIED AGENT MANAGEMENT SYSTEM - Complete Agent Operations

⭐ WHAT IT DOES: Provides comprehensive agent management including registration, assignment, lifecycle management, and direct agent invocation for task execution. Automatically enriches tasks with vision insights, progress tracking, and intelligent context updates.
📋 WHEN TO USE: All agent operations including registration, assignment, updates, project management, and dynamic agent invocation.
🎯 CRITICAL FOR: Multi-agent orchestration, dynamic agent assignment, and specialized task delegation.
🚀 ENHANCED FEATURES: Integrated progress tracking, automatic parent context updates, blocker management, insight propagation, and intelligent workflow hints.

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
| call        | name_agent                          | project_id                         | Load and invoke specific agent by name           |

💡 USAGE GUIDELINES:
• Provide all required identifiers for each action (see table above).
• Optional parameters can be omitted unless updating values.
• For call action, use @ prefix for agent names (e.g., '@uber_orchestrator_agent').
• The tool returns detailed error messages for missing or invalid parameters, unknown actions, and internal errors.
• All business logic is delegated to the application layer (AgentApplicationFacade and CallAgentUseCase).

🔍 DECISION TREES FOR AGENT INVOCATION:
IF work_type matches "debug|fix|error|bug|troubleshoot":
    USE @debugger_agent
ELIF work_type matches "implement|code|build|develop|create":
    USE @coding_agent
ELIF work_type matches "test|verify|validate|qa":
    USE @test_orchestrator_agent
ELIF work_type matches "plan|analyze|breakdown|organize":
    USE @task_planning_agent
ELIF work_type matches "design|ui|interface|ux|frontend":
    USE @ui_designer_agent
ELIF work_type matches "security|audit|vulnerability|penetration":
    USE @security_auditor_agent
ELIF work_type matches "deploy|infrastructure|devops|ci/cd":
    USE @devops_agent
ELIF work_type matches "document|guide|manual|readme":
    USE @documentation_agent
ELIF work_type matches "research|investigate|explore|study":
    USE @deep_research_agent
ELIF work_type matches "complex|orchestrate|coordinate|multi-step":
    USE @uber_orchestrator_agent
ELIF work_type matches "ml|machine learning|ai|neural":
    USE @brainjs_ml_agent
ELIF work_type matches "algorithm|optimize|performance":
    USE @algorithmic_problem_solver_agent
ELIF work_type matches "marketing|campaign|growth|seo":
    USE @marketing_strategy_orchestrator_agent
ELIF work_type matches "compliance|regulatory|legal":
    USE @compliance_scope_agent
ELIF work_type matches "architecture|system|design patterns":
    USE @system_architect_agent
ELIF work_type matches "workflow|process|automation":
    USE @workflow_architect_agent
ELIF work_type matches "api|integration|mcp":
    USE @mcp_configuration_agent
ELIF work_type matches "incident|postmortem|root cause":
    USE @root_cause_analysis_agent
ELIF work_type matches "project|initiative|kickoff":
    USE @project_initiator_agent
ELIF work_type matches "prototype|poc|proof of concept":
    USE @prototyping_agent
ELSE:
    USE @uber_orchestrator_agent  # Default fallback

🎯 USE CASES:
• Register and manage agents across projects (register, assign, update)
• Invoke @uber_orchestrator_agent for complex multi-step workflows
• Call specialized agents like @code_architect_agent for code design
• Call @task_planning_agent to plan a task, split it into subtasks, and assign them
• Switch between role-specific agents for different task phases
• Discover available agents before task delegation
• Multi-agent collaboration and handoff scenarios
• Project-wide agent management and lifecycle operations

📊 WORKFLOW PATTERNS:
1. Complex Task Orchestration:
   - Start with @uber_orchestrator_agent
   - Delegate to @task_planning_agent for breakdown
   - Switch to specialized agents for execution
   - Return to @uber_orchestrator_agent for integration

2. Feature Development:
   - @task_planning_agent → @system_architect_agent → @coding_agent → @test_orchestrator_agent → @documentation_agent

3. Bug Resolution:
   - @debugger_agent → @root_cause_analysis_agent → @coding_agent → @test_orchestrator_agent

4. Security Audit:
   - @security_auditor_agent → @security_penetration_tester_agent → @compliance_testing_agent

💡 BEST PRACTICES FOR AI:
• Call agent BEFORE starting any work to ensure proper specialization
• Use descriptive work type keywords to match decision tree
• Switch agents when task nature changes significantly
• Default to @uber_orchestrator_agent when unsure
• Chain multiple agents for complex workflows
• Maintain context between agent switches
• Register agents to projects for persistent availability
• Use assignment operations to bind agents to specific task trees

🛑 ERROR HANDLING:
• If required fields are missing, a clear error message is returned specifying which fields are needed.
• Unknown actions return an error listing valid actions.
• Invalid agent names will result in an error with available agents list.
• Internal errors are logged and returned with a generic error message.
• Agent loading failures provide fallback to @uber_orchestrator_agent.

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
• Switch to a role agent if no role is specified; otherwise, the default agent @uber_orchestrator_agent will be used
• Each agent has specialized knowledge and capabilities
• Agents can collaborate as specified in their connectivity
• Invalid agent names will result in an error with available agents list
• Agents maintain context during task execution

🔍 AVAILABLE AGENTS:
    "@adaptive_deployment_strategist_agent"
    "@algorithmic_problem_solver_agent"
    "@analytics_setup_agent"
    "@brainjs_ml_agent"
    "@branding_agent"
    "@campaign_manager_agent"
    "@code_reviewer_agent"
    "@coding_agent"
    "@community_strategy_agent"
    "@compliance_scope_agent"
    "@compliance_testing_agent"
    "@content_strategy_agent"
    "@core_concept_agent"
    "@debugger_agent"
    "@deep_research_agent"
    "@design_qa_analyst"
    "@design_qa_analyst_agent"
    "@design_system_agent"
    "@development_orchestrator_agent"
    "@devops_agent"
    "@documentation_agent"
    "@efficiency_optimization_agent"
    "@elicitation_agent"
    "@ethical_review_agent"
    "@exploratory_tester_agent"
    "@functional_tester_agent"
    "@generic_purpose_agent"
    "@graphic_design_agent"
    "@growth_hacking_idea_agent"
    "@health_monitor_agent"
    "@idea_generation_agent"
    "@idea_refinement_agent"
    "@incident_learning_agent"
    "@knowledge_evolution_agent"
    "@lead_testing_agent"
    "@market_research_agent"
    "@marketing_strategy_orchestrator"
    "@marketing_strategy_orchestrator_agent"
    "@mcp_configuration_agent"
    "@mcp_researcher_agent"
    "@nlu_processor_agent"
    "@performance_load_tester_agent"
    "@prd_architect_agent"
    "@project_initiator_agent"
    "@prototyping_agent"
    "@remediation_agent"
    "@root_cause_analysis_agent"
    "@scribe_agent"
    "@security_auditor_agent"
    "@security_penetration_tester_agent"
    "@seo_sem_agent"
    "@social_media_setup_agent"
    "@swarm_scaler_agent"
    "@system_architect_agent"
    "@task_deep_manager_agent"
    "@task_planning_agent"
    "@task_sync_agent"
    "@tech_spec_agent"
    "@technology_advisor_agent"
    "@test_case_generator_agent"
    "@test_orchestrator_agent"
    "@uat_coordinator_agent"
    "@uber_orchestrator_agent"
    "@ui_designer_agent"
    "@ui_designer_expert_shadcn_agent"
    "@usability_heuristic_agent"
    "@user_feedback_collector_agent"
    "@ux_researcher_agent"
    "@video_production_agent"
    "@visual_regression_testing_agent"
    "@workflow_architect_agent"
"""

UNIFIED_AGENT_PARAMETERS_DESCRIPTION = {
    "action": "Agent operation to perform. Valid values: register, assign, get, list, update, unassign, unregister, rebalance, call",
    "project_id": "[REQUIRED for management actions] Project identifier for agent management. Optional for call action",
    "agent_id": "[OPTIONAL] Agent identifier. Required for most management actions except register/list/rebalance/call",
    "name": "[OPTIONAL] Agent name. Required for register, optional for update",
    "call_agent": "[OPTIONAL] Call agent string or configuration. Optional, for register/update actions",
    "git_branch_id": "[OPTIONAL] Task tree identifier. Required for assign/unassign actions",
    "user_id": "[OPTIONAL] User identifier for authentication and audit trails",
    "name_agent": "[REQUIRED for call action] Name of the agent to load and invoke. Must be a valid, registered agent name with @ prefix (e.g., '@uber_orchestrator_agent')"
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