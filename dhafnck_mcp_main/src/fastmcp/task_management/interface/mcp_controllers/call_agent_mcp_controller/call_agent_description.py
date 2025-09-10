"""
Agent Documentation Standards (from 00_RULES/core/P00-S00-T03-Agents Information.md)

- Each agent has specific expertise and can be invoked using @agent-name syntax.
- MUST switch to a role agent if no role is specified; otherwise, the default agent @master_orchestrator_agent will be used.
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
• Invoke @master_orchestrator_agent for complex multi-step workflows
• Call specialized agents like @code_architect_agent for code design
• Call @task_planning_agent to plan a task, split it into subtasks, and assign them to the appropriate agents.
• Switch between role-specific agents for different task phases
• Discover available agents before task delegation
• Multi-agent collaboration and handoff scenarios

💡 USAGE GUIDELINES:
• Provide valid agent name for invocation
• Switch to a role agent if no role is specified; otherwise, the default agent @master_orchestrator_agent will be used.

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
    USE @ui_specialist_agent
ELIF work_type matches "security|audit|vulnerability|penetration":
    USE @security_auditor_agent
ELIF work_type matches "deploy|infrastructure|devops|ci/cd":
    USE @devops_agent
ELIF work_type matches "document|guide|manual|readme":
    USE @documentation_agent
ELIF work_type matches "research|investigate|explore|study":
    USE @deep_research_agent
ELIF work_type matches "orchestrate|coordinate|multi-step|complex":
    USE @master_orchestrator_agent
ELIF work_type matches "ml|machine learning|ai|neural":
    USE @ml_specialist_agent or @llm_ai_agents_research
ELIF work_type matches "performance|load|stress|benchmark":
    USE @performance_load_tester_agent
ELIF work_type matches "marketing|campaign|growth|seo":
    USE @marketing_strategy_orchestrator_agent
ELIF work_type matches "compliance|regulatory|legal":
    USE @compliance_scope_agent
ELIF work_type matches "architecture|system|design patterns":
    USE @system_architect_agent
ELIF work_type matches "efficiency|optimize|process":
    USE @efficiency_optimization_agent
ELIF work_type matches "incident|postmortem|root cause":
    USE @root_cause_analysis_agent
ELIF work_type matches "project|initiative|kickoff":
    USE @project_initiator_agent
ELIF work_type matches "prototype|poc|proof of concept":
    USE @prototyping_agent
ELIF work_type matches "brand|branding|identity":
    USE @branding_agent
ELIF work_type matches "community|social|engagement":
    USE @community_strategy_agent
ELIF work_type matches "creative|idea|ideation|brainstorm":
    USE @creative_ideation_agent
ELIF work_type matches "ethics|ethical|responsible":
    USE @ethical_review_agent
ELIF work_type matches "health|monitor|monitoring|status":
    USE @health_monitor_agent
ELIF work_type matches "technology|tech stack|framework":
    USE @technology_advisor_agent
ELIF work_type matches "elicit|requirements|gathering":
    USE @elicitation_agent
ELIF work_type matches "uat|acceptance testing|user testing":
    USE @uat_coordinator_agent
ELIF work_type matches "analytics|tracking|metrics":
    USE @analytics_setup_agent
ELIF work_type matches "design system|component library|ui patterns":
    USE @design_system_agent
ELIF work_type matches "core concept|fundamental|foundation":
    USE @core_concept_agent
ELSE:
    USE @master_orchestrator_agent  # Default fallback

📊 WORKFLOW PATTERNS:
1. Complex Task Orchestration:
   - Start with @master_orchestrator_agent
   - Delegate to @task_planning_agent for breakdown
   - Switch to specialized agents for execution
   - Return to @master_orchestrator_agent for integration

2. Feature Development:
   - @task_planning_agent → @system_architect_agent → @coding_agent → @test_orchestrator_agent → @documentation_agent

3. Bug Resolution:
   - @debugger_agent → @root_cause_analysis_agent → @coding_agent → @test_orchestrator_agent

4. Security Audit:
   - @security_auditor_agent → @compliance_scope_agent → @ethical_review_agent

💡 BEST PRACTICES FOR AI:
• Call agent BEFORE starting any work to ensure proper specialization
• Use descriptive work type keywords to match decision tree
• Switch agents when task nature changes significantly
• Default to @master_orchestrator_agent when unsure
• Chain multiple agents for complex workflows
• Maintain context between agent switches

🛡️ ERROR HANDLING:
• If agent name is invalid, error response includes available agents list
• Missing name_agent parameter returns clear error with field requirements
• Internal errors are logged and returned with generic error message
• Agent loading failures provide fallback to @master_orchestrator_agent

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

🚀 AVAILABLE AGENTS (33 Total - Based on agent-library):
  Development & Coding (4):
    @coding_agent - Implementation and feature development
    @debugger_agent - Bug fixing and troubleshooting
    @code_reviewer_agent - Code quality and review
    @prototyping_agent - Rapid prototyping and POCs
    
  Testing & QA (3):
    @test_orchestrator_agent - Comprehensive test management
    @uat_coordinator_agent - User acceptance testing
    @performance_load_tester_agent - Performance and load testing
    
  Architecture & Design (4):
    @system_architect_agent - System design and architecture
    @design_system_agent - Design system and UI patterns
    @ui_specialist_agent - UI/UX design and frontend development
    @core_concept_agent - Core concepts and fundamentals
    
  DevOps & Infrastructure (1):
    @devops_agent - CI/CD and infrastructure
    
  Documentation (1):
    @documentation_agent - Technical documentation
    
  Project & Planning (4):
    @project_initiator_agent - Project setup and kickoff
    @task_planning_agent - Task breakdown and planning
    @master_orchestrator_agent - Complex workflow orchestration
    @elicitation_agent - Requirements gathering
    
  Security & Compliance (3):
    @security_auditor_agent - Security audits and reviews
    @compliance_scope_agent - Regulatory compliance
    @ethical_review_agent - Ethical considerations
    
  Analytics & Optimization (3):
    @analytics_setup_agent - Analytics and tracking setup
    @efficiency_optimization_agent - Process optimization
    @health_monitor_agent - System health monitoring
    
  Marketing & Branding (3):
    @marketing_strategy_orchestrator_agent - Marketing strategy
    @community_strategy_agent - Community building
    @branding_agent - Brand identity
    
  Research & Analysis (4):
    @deep_research_agent - In-depth research
    @llm_ai_agents_research - AI/ML research and innovations
    @root_cause_analysis_agent - Problem analysis
    @technology_advisor_agent - Technology recommendations
    
  AI & Machine Learning (1):
    @ml_specialist_agent - Machine learning implementation
    
  Creative & Ideation (1):
    @creative_ideation_agent - Creative idea generation
"""

CALL_AGENT_PARAMETERS_DESCRIPTION = {
    "name_agent": "Name of the agent to load and invoke. Must be a valid, registered agent name (string). Use @ prefix for agent names (e.g., '@master_orchestrator_agent')"
}

CALL_AGENT_PARAMS = {
    "type": "object",
    "properties": {
        # Primary parameter (always required)
        "name_agent": {
            "type": "string",
            "description": CALL_AGENT_PARAMETERS_DESCRIPTION["name_agent"]
        }
    },
    "required": ["name_agent"],  # Only name_agent required
    "additionalProperties": False
}

def get_call_agent_parameters():
    """Get call agent parameters for use in controller."""
    return CALL_AGENT_PARAMS["properties"]

def get_call_agent_description():
    """Get call agent description for use in controller."""
    return CALL_AGENT_DESCRIPTION

# Legacy parameter descriptions for backward compatibility
CALL_AGENT_PARAMETERS = {
    "name_agent": "Name of the agent to load and invoke. Must be a valid, registered agent name (string). Use @ prefix for agent names (e.g., '@master_orchestrator_agent')"
} 