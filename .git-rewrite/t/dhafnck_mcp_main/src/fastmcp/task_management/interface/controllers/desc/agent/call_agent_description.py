"""
Agent Documentation Standards (from 00_RULES/core/P00-S00-T03-Agents Information.md)

- Each agent has specific expertise and can be invoked using @agent-name syntax.
- MUST switch to a role agent if no role is specified; otherwise, the default agent @uber_orchestrator_agent will be used.
- Use @agent-name to invoke a specific agent.
- Agents can collaborate as specified in their connectivity.
- Each agent has specialized knowledge and capabilities.
- Agent details can be found in `cursor_agent/yaml-lib/<agent-name>/**/*.yaml`.
- All documents created by agents must be saved as `.md` in `.cursor/rules/02_AI-DOCS/GENERATE_BY_AI`.
- After creating a document, update its info in `.cursor/rules/02_AI-DOCS/GENERATE_BY_AI/index.json`.
- Agent relatives can update these documents if needed.
- Agent document format:
    {
        document-(str): {
            name: str,
            category: str,
            description: str,
            usecase: str,
            task-id: str (actual Task ID or global),
            useby: [str] (list agent AI),
            created_at: ISOdate(format str),
            created_by: ISOdate(format str),
        }
    }

Refer to the rules file for more details and the list of available agents.
"""

CALL_AGENT_DESCRIPTION = """
🤖 AGENT INVOCATION SYSTEM - Dynamic Agent Loading and Execution

⭐ WHAT IT DOES: Loads and invokes specialized agents by name for task execution. Automatically enriches tasks with vision insights, progress tracking, and intelligent context updates.
📋 WHEN TO USE: Dynamic agent assignment and multi-agent orchestration.
🎯 CRITICAL FOR: Agent-based workflow management and specialized task delegation.
🚀 ENHANCED FEATURES: Integrated progress tracking, automatic parent context updates, blocker management, insight propagation, and intelligent workflow hints.

| Action | Required Parameters | Optional Parameters | Description |
|--------|-------------------|-------------------|-------------|
| call_agent | name_agent | | Load and invoke specific agent by name |

🎯 USE CASES:
• Invoke @uber_orchestrator_agent for complex multi-step workflows
• Call specialized agents like @code_architect_agent for code design
• Call @task_planning_agent to plan a task, split it into subtasks, and assign them to the appropriate agents.
• Switch between role-specific agents for different task phases
• Discover available agents before task delegation
• Multi-agent collaboration and handoff scenarios

💡 USAGE GUIDELINES:
• Provide valid agent name for invocation
• Switch to a role agent if no role is specified; otherwise, the default agent @uber_orchestrator_agent will be used.

🔍 DECISION TREES:
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

🛡️ ERROR HANDLING:
• If agent name is invalid, error response includes available agents list
• Missing name_agent parameter returns clear error with field requirements
• Internal errors are logged and returned with generic error message
• Agent loading failures provide fallback to @uber_orchestrator_agent

✅ VALIDATION CHECKPOINTS:
• Check: Is the agent name prefixed with @?
• Check: Does the agent exist in available agents list?
• Check: Is the work type appropriate for the selected agent?
• Pass: Agent invoked successfully
• Fail: Error with available agents and suggestions

⚠️ IMPORTANT NOTES:
• Agent names must include the @ prefix
• Invalid agent names will result in an error with available agents list
• Agents maintain context during task execution
• Switch agents when work type changes significantly
• Each agent has specialized knowledge and capabilities
• Agents can collaborate as specified in their connectivity

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

CALL_AGENT_PARAMETERS = {
    "name_agent": "Name of the agent to load and invoke. Must be a valid, registered agent name (string)."
} 