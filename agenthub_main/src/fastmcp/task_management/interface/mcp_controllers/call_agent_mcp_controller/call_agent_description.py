"""
Agent Documentation Standards (from 00_RULES/core/P00-S00-T03-Agents Information.md)

- Each agent has specific expertise and can be invoked using @agent-name syntax.
- MUST switch to a role agent if no role is specified; otherwise, the default agent master-orchestrator-agent will be used.
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
• Invoke master-orchestrator-agent for complex multi-step workflows
• Call specialized agents like @code_architect_agent for code design
• Call task-planning-agent to plan a task, split it into subtasks, and assign them to the appropriate agents.
• Switch between role-specific agents for different task phases
• Discover available agents before task delegation
• Multi-agent collaboration and handoff scenarios

💡 USAGE GUIDELINES:
• Provide valid agent name for invocation
• Switch to a role agent if no role is specified; otherwise, the default agent master-orchestrator-agent will be used.

🔍 DECISION TREES:
IF work_type matches "debug|fix|error|bug|troubleshoot":
    USE debugger-agent
ELIF work_type matches "implement|code|build|develop|create":
    USE coding-agent
ELIF work_type matches "test|verify|validate|qa":
    USE test-orchestrator-agent
ELIF work_type matches "plan|analyze|breakdown|organize":
    USE task-planning-agent
ELIF work_type matches "design|ui|interface|ux|frontend":
    USE shadcn-ui-expert-agent
ELIF work_type matches "security|audit|vulnerability|penetration":
    USE security-auditor-agent
ELIF work_type matches "deploy|infrastructure|devops|ci/cd":
    USE devops-agent
ELIF work_type matches "document|guide|manual|readme":
    USE documentation-agent
ELIF work_type matches "research|investigate|explore|study":
    USE deep-research-agent
ELIF work_type matches "orchestrate|coordinate|multi-step|complex":
    USE master-orchestrator-agent
ELIF work_type matches "ml|machine learning|ai|neural":
    USE ml-specialist-agent or llm-ai-agents-research
ELIF work_type matches "performance|load|stress|benchmark":
    USE performance-load-tester-agent
ELIF work_type matches "marketing|campaign|growth|seo":
    USE marketing-strategy-orchestrator-agent
ELIF work_type matches "compliance|regulatory|legal":
    USE compliance-scope-agent
ELIF work_type matches "architecture|system|design patterns":
    USE system-architect-agent
ELIF work_type matches "efficiency|optimize|process":
    USE efficiency-optimization-agent
ELIF work_type matches "incident|postmortem|root cause":
    USE root-cause-analysis-agent
ELIF work_type matches "project|initiative|kickoff":
    USE project-initiator-agent
ELIF work_type matches "prototype|poc|proof of concept":
    USE prototyping-agent
ELIF work_type matches "brand|branding|identity":
    USE branding-agent
ELIF work_type matches "community|social|engagement":
    USE community-strategy-agent
ELIF work_type matches "creative|idea|ideation|brainstorm":
    USE creative-ideation-agent
ELIF work_type matches "ethics|ethical|responsible":
    USE ethical-review-agent
ELIF work_type matches "health|monitor|monitoring|status":
    USE health-monitor-agent
ELIF work_type matches "technology|tech stack|framework":
    USE technology-advisor-agent
ELIF work_type matches "elicit|requirements|gathering":
    USE elicitation-agent
ELIF work_type matches "uat|acceptance testing|user testing":
    USE uat-coordinator-agent
ELIF work_type matches "analytics|tracking|metrics":
    USE analytics-setup-agent
ELIF work_type matches "design system|component library|ui patterns":
    USE design-system-agent
ELIF work_type matches "core concept|fundamental|foundation":
    USE core-concept-agent
ELSE:
    USE master-orchestrator-agent  # Default fallback

📊 WORKFLOW PATTERNS:
1. Complex Task Orchestration:
   - Start with master-orchestrator-agent
   - Delegate to task-planning-agent for breakdown
   - Switch to specialized agents for execution
   - Return to master-orchestrator-agent for integration

2. Feature Development:
   - task-planning-agent → system-architect-agent → coding-agent → test-orchestrator-agent → documentation-agent

3. Bug Resolution:
   - debugger-agent → root-cause-analysis-agent → coding-agent → test-orchestrator-agent

4. Security Audit:
   - security-auditor-agent → compliance-scope-agent → ethical-review-agent

💡 BEST PRACTICES FOR AI:
• Call agent BEFORE starting any work to ensure proper specialization
• Use descriptive work type keywords to match decision tree
• Switch agents when task nature changes significantly
• Default to master-orchestrator-agent when unsure
• Chain multiple agents for complex workflows
• Maintain context between agent switches

🛡️ ERROR HANDLING:
• If agent name is invalid, error response includes available agents list
• Missing name_agent parameter returns clear error with field requirements
• Internal errors are logged and returned with generic error message
• Agent loading failures provide fallback to master-orchestrator-agent

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
    coding-agent - Implementation and feature development
    debugger-agent - Bug fixing and troubleshooting
    code-reviewer-agent - Code quality and review
    prototyping-agent - Rapid prototyping and POCs
    
  Testing & QA (3):
    test-orchestrator-agent - Comprehensive test management
    uat-coordinator-agent - User acceptance testing
    performance-load-tester-agent - Performance and load testing
    
  Architecture & Design (4):
    system-architect-agent - System design and architecture
    design-system-agent - Design system and UI patterns
    shadcn-ui-expert-agent - UI/UX design and frontend development
    core-concept-agent - Core concepts and fundamentals
    
  DevOps & Infrastructure (1):
    devops-agent - CI/CD and infrastructure
    
  Documentation (1):
    documentation-agent - Technical documentation
    
  Project & Planning (4):
    project-initiator-agent - Project setup and kickoff
    task-planning-agent - Task breakdown and planning
    master-orchestrator-agent - Complex workflow orchestration
    elicitation-agent - Requirements gathering
    
  Security & Compliance (3):
    security-auditor-agent - Security audits and reviews
    compliance-scope-agent - Regulatory compliance
    ethical-review-agent - Ethical considerations
    
  Analytics & Optimization (3):
    analytics-setup-agent - Analytics and tracking setup
    efficiency-optimization-agent - Process optimization
    health-monitor-agent - System health monitoring
    
  Marketing & Branding (3):
    marketing-strategy-orchestrator-agent - Marketing strategy
    community-strategy-agent - Community building
    branding-agent - Brand identity
    
  Research & Analysis (4):
    deep-research-agent - In-depth research
    llm-ai-agents-research - AI/ML research and innovations
    root-cause-analysis-agent - Problem analysis
    technology-advisor-agent - Technology recommendations
    
  AI & Machine Learning (1):
    ml-specialist-agent - Machine learning implementation
    
  Creative & Ideation (1):
    creative-ideation-agent - Creative idea generation
"""

CALL_AGENT_PARAMETERS_DESCRIPTION = {
    "name_agent": "Name of the agent to load and invoke. Must be a valid, registered agent name (string). Use @ prefix for agent names (e.g., 'master-orchestrator-agent')"
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
    "name_agent": "Name of the agent to load and invoke. Must be a valid, registered agent name (string). Use @ prefix for agent names (e.g., 'master-orchestrator-agent')"
} 