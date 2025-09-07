# DhafnckMCP Usage Guide for AI Agents

## 🎯 Vision System - AI-Enhanced Decision Making

The Vision System provides intelligent guidance, workflow hints, and progress tracking throughout all operations. It automatically enriches tasks, provides context-aware suggestions, and maintains strategic alignment across the platform.

### Key Vision System Features:
- **Automatic Task Enrichment**: AI-generated insights and recommendations for every task
- **Workflow Guidance**: Context-aware hints and next action suggestions
- **Progress Tracking**: Intelligent milestone detection and completion analysis
- **Blocker Identification**: Automatic detection and resolution suggestions for impediments
- **Impact Analysis**: Understanding how changes affect related tasks and project goals
- **Strategic Orchestration**: 6-phase implementation for optimal AI coordination

### Vision System Integration Points:
- Task creation and updates (automatic enrichment)
- Context management (intelligent delegation and inheritance)
- Agent operations (workflow hints and guidance)
- Project health monitoring (predictive analytics)
- Test execution (intelligent test prioritization)

## 🤖 Intelligent Agent Auto-Selection

### 🚀 MANDATORY: Auto-Call Appropriate Agent Before Working

**CRITICAL RULE**: Claude must AUTOMATICALLY call the most appropriate specialist agent before starting any significant work. This ensures optimal expertise and better results.

### Complete Auto-Agent Selection Logic (All 43 Agents)
```python
# COMPREHENSIVE AGENT SELECTION - Uses all 43 optimized agents
def auto_select_agent(user_request, work_context):
    request_lower = user_request.lower()
    
    # CORE DEVELOPMENT AGENTS
    if any(keyword in request_lower for keyword in ["implement", "code", "write", "program", "develop", "build", "create", "function", "class", "method", "api", "endpoint", "service", "component", "module", "coding", "programming", "backend", "frontend"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
    
    elif any(keyword in request_lower for keyword in ["debug", "fix", "error", "bug", "broken", "issue", "problem", "crash", "failure", "exception", "troubleshoot", "resolve", "repair", "analyze", "investigate", "diagnose"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
    
    elif any(keyword in request_lower for keyword in ["review", "code review", "pull request", "pr", "merge", "quality", "refactor", "clean code", "check", "validate", "inspect"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@code_reviewer_agent")
    
    # TESTING & QA AGENTS
    elif any(keyword in request_lower for keyword in ["test", "testing", "unit test", "integration test", "e2e test", "end-to-end test", "test case", "test suite", "test coverage", "quality assurance", "qa", "testing framework", "jest", "mocha", "pytest", "cypress", "playwright"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")
    
    elif any(keyword in request_lower for keyword in ["performance test", "load test", "stress test", "benchmark"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@performance_load_tester_agent")
    
    elif any(keyword in request_lower for keyword in ["uat", "user acceptance", "acceptance test"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@uat_coordinator_agent")
    
    # UI/DESIGN AGENTS
    elif any(keyword in request_lower for keyword in ["design", "ui", "ux", "interface", "component", "layout", "responsive", "mobile", "dashboard", "form", "navigation", "shadcn", "tailwind", "frontend", "react component", "user experience", "user interface"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@ui_designer_expert_shadcn_agent")
    
    elif any(keyword in request_lower for keyword in ["design system", "component library", "design token"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@design_system_agent")
    
    elif any(keyword in request_lower for keyword in ["prototype", "mockup", "wireframe", "interactive"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@prototyping_agent")
    
    # DEVOPS & INFRASTRUCTURE AGENTS  
    elif any(keyword in request_lower for keyword in ["devops", "infrastructure", "docker", "kubernetes", "ci/cd", "continuous integration", "continuous deployment", "pipeline", "monitoring", "cloud", "aws", "azure", "gcp"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@devops_agent")
    
    elif any(keyword in request_lower for keyword in ["deploy", "deployment", "release", "rollout", "production", "staging", "deployment strategy", "blue-green deployment", "canary deployment", "rolling deployment"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@adaptive_deployment_strategist_agent")
    
    elif any(keyword in request_lower for keyword in ["mcp", "server", "configuration", "setup"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@mcp_configuration_agent")
    
    # SECURITY & COMPLIANCE AGENTS
    elif any(keyword in request_lower for keyword in ["security", "secure", "vulnerability", "audit", "penetration test", "penetration", "compliance", "encryption", "security review", "gdpr", "hipaa", "authentication", "authorization"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@security_auditor_agent")
    
    elif any(keyword in request_lower for keyword in ["compliance", "regulatory", "gdpr", "hipaa", "legal"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@compliance_scope_agent")
    
    elif any(keyword in request_lower for keyword in ["ethics", "ethical", "bias", "fairness"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@ethical_review_agent")
    
    # RESEARCH & ANALYSIS AGENTS
    elif any(keyword in request_lower for keyword in ["research", "analyze", "investigate", "study", "explore", "competitive analysis", "market research", "data analysis", "trend analysis", "insights"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@deep_research_agent")
    
    elif any(keyword in request_lower for keyword in ["mcp research", "tool research", "platform research"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@mcp_researcher_agent")
    
    elif any(keyword in request_lower for keyword in ["technology", "tech stack", "framework", "library"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@technology_advisor_agent")
    
    # ARCHITECTURE & PLANNING AGENTS
    elif any(keyword in request_lower for keyword in ["architecture", "system design", "technical architecture", "scalability", "microservices", "distributed systems", "cloud architecture", "infrastructure design", "system integration", "technology stack", "architectural patterns"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@system_architect_agent")
    
    elif any(keyword in request_lower for keyword in ["plan", "planning", "breakdown", "tasks", "project plan", "task management", "organize", "schedule", "task", "organize", "project"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@task_planning_agent")
    
    elif any(keyword in request_lower for keyword in ["tech spec", "specification", "technical requirement"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@tech_spec_agent")
    
    elif any(keyword in request_lower for keyword in ["prd", "product requirement", "product spec"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@prd_architect_agent")
    
    # DOCUMENTATION AGENTS
    elif any(keyword in request_lower for keyword in ["documentation", "docs", "readme", "guide", "manual", "wiki", "help", "instructions", "api docs", "document", "tutorial", "reference", "specification"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@documentation_agent")
    
    # MARKETING & BUSINESS AGENTS
    elif any(keyword in request_lower for keyword in ["marketing", "campaign", "promotion", "brand"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@marketing_strategy_orchestrator_agent")
    
    elif any(keyword in request_lower for keyword in ["seo", "sem", "search", "keyword", "optimization"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@seo_sem_agent")
    
    elif any(keyword in request_lower for keyword in ["growth", "growth hack", "viral", "acquisition"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@growth_hacking_idea_agent")
    
    elif any(keyword in request_lower for keyword in ["brand", "branding", "identity", "logo"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@branding_agent")
    
    elif any(keyword in request_lower for keyword in ["content", "content strategy", "editorial"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@content_strategy_agent")
    
    elif any(keyword in request_lower for keyword in ["community", "engagement", "social"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@community_strategy_agent")
    
    # AI & MACHINE LEARNING AGENTS
    elif any(keyword in request_lower for keyword in ["ml", "machine learning", "ai", "neural", "brain.js"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@brainjs_ml_agent")
    
    # IDEATION & CONCEPT AGENTS
    elif any(keyword in request_lower for keyword in ["idea", "brainstorm", "concept", "innovation"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@idea_generation_agent")
    
    elif any(keyword in request_lower for keyword in ["refine", "improve", "enhance", "iterate"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@idea_refinement_agent")
    
    elif any(keyword in request_lower for keyword in ["core concept", "value proposition", "essence"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@core_concept_agent")
    
    # REQUIREMENTS & ELICITATION AGENTS
    elif any(keyword in request_lower for keyword in ["requirements", "gather", "elicit", "clarify"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@elicitation_agent")
    
    # PROJECT & PROCESS AGENTS
    elif any(keyword in request_lower for keyword in ["project init", "project start", "onboard"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@project_initiator_agent")
    
    # MONITORING & OPERATIONS AGENTS
    elif any(keyword in request_lower for keyword in ["health", "monitor", "status", "uptime"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@health_monitor_agent")
    
    elif any(keyword in request_lower for keyword in ["analytics", "tracking", "dashboard", "metrics", "data collection", "events", "monitoring", "statistics", "insights", "reporting", "google analytics", "performance tracking", "user analytics", "conversion tracking"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@analytics_setup_agent")
    
    elif any(keyword in request_lower for keyword in ["efficiency", "optimize", "performance", "improve"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@efficiency_optimization_agent")
    
    elif any(keyword in request_lower for keyword in ["remediation", "fix", "resolve", "repair"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@remediation_agent")
    
    elif any(keyword in request_lower for keyword in ["root cause", "analysis", "investigate"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@root_cause_analysis_agent")
    
    elif any(keyword in request_lower for keyword in ["scale", "scaling", "swarm", "distributed"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@swarm_scaler_agent")
    
    else:
        # Default to orchestrator for complex or unclear requests
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")
```

### 🎯 When to Auto-Call Agents

**ALWAYS AUTO-CALL when user requests involve:**
- **Coding/Implementation**: Auto-call `@coding_agent`
- **Debugging/Fixing**: Auto-call `@debugger_agent`  
- **Testing/QA**: Auto-call `@test_orchestrator_agent`
- **UI/Design Work**: Auto-call `@ui_designer_expert_shadcn_agent`
- **Documentation**: Auto-call `@documentation_agent`
- **System Design**: Auto-call `@system_architect_agent`
- **DevOps/Deploy**: Auto-call `@devops_agent`
- **Security**: Auto-call `@security_auditor_agent`
- **Research/Analysis**: Auto-call `@deep_research_agent`
- **Planning/Organization**: Auto-call `@task_planning_agent`
- **Code Review**: Auto-call `@code_reviewer_agent`
- **Complex Multi-step**: Auto-call `@uber_orchestrator_agent`

### 📋 Auto-Agent Workflow Example

```python
# Example: User says "Implement user authentication with JWT"
# Claude should AUTOMATICALLY do:

# 1. Detect this is implementation work
agent_response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# 2. Switch to coding agent interface
coding_specs = agent_response["yaml_content"]
available_tools = agent_response["capabilities"]["mcp_tools"]["tools"]
agent_rules = agent_response["yaml_content"]["rules"]

# 3. Follow coding agent specifications for implementation
# 4. Use coding agent's contexts, rules, and capabilities
# 5. Deliver results according to coding agent's output formats
```

## 🤖 Manual Agent Switching - Use The Right Specialist

### ⚠️ CRITICAL: Agent Loading and Interface Compliance

Available agents: general-purpose, statusline-setup, output-style-setup, claude-code-troubleshooter and 43 core specialized agents on MCP server (need fetch information using mcp__dhafnck_mcp_http__call_agent). 

**📋 Agent Library Optimization (2025-09-06)**: Streamlined from 69 to 43 core agents for better maintainability and clearer specialization. See [Agent Cleanup Analysis](dhafnck_mcp_main/docs/architecture-design/agent-library-cleanup-recommendations.md) for details.


## **Actual Claude Code Style Agent Display:**

```bash
[Agent: {agent_name} - Working...]
[Agent: {agent_name} - Ready]
[Agent: {agent_name} - Initializing...]
```

- **Simple bracket notation**: `[Agent: name - status]`
- **Basic status words**: Working, Ready, Initializing, Error, etc.
- **Clean terminal output** without fancy graphics

## **Corrected Step-by-Step Process:**

**Step 1: Initialize MCP Agent**
- Call `mcp__dhafnck_mcp_http__call_agent` to get agent information
- **Display**: `[Agent: Initializing...]`

**Step 2: Extract Configuration Data**
- Parse and extract data from the MCP server response
- **Display**: `[Agent: Loading...]`

**Step 3: Launch Agent with Task Tool**
- Use the Task tool to launch complete agent specification
- **Display**: `[Agent: {agent_name} - Working...]`

**Step 4: Agent Operational**
- Agent equivalent to `.claude/agents` launches
- **Display**: `[Agent: {agent_name} - Ready]`


## 🚀 Quick Start - Automatic Agent Selection

**Claude automatically selects the best agent based on the user's request. No manual agent switching needed!**

```python
# AUTOMATIC FLOW - Claude does this automatically:

# 1. Analyze user request and auto-select appropriate agent
# Example: "Implement login functionality" → auto-calls @coding_agent
# Example: "Fix this bug" → auto-calls @debugger_agent  
# Example: "Test this feature" → auto-calls @test_orchestrator_agent

# 2. Check system health (when needed)
mcp__dhafnck_mcp_http__manage_connection(action="health_check")

# 3. List available projects (when needed)
mcp__dhafnck_mcp_http__manage_project(action="list")

# 4. Get or create a task to work on (when needed)
mcp__dhafnck_mcp_http__manage_task(
    action="next",
    git_branch_id=branch_id,
    include_context=True
)

# 5. Execute work using the specialist agent's expertise
# Agent follows its own rules, contexts, and capabilities
```

### 🎯 User Experience Flow

1. **User makes request** → "Implement user authentication"
2. **Claude auto-detects** → Implementation work detected  
3. **Claude auto-calls** → `@coding_agent` automatically loaded
4. **Claude switches interface** → Uses coding agent's specifications
5. **Work gets done** → Following coding agent's expertise and rules
6. **Results delivered** → In coding agent's output format

## 📊 Context Management - Share Information Between Sessions

### The Context Hierarchy
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```
Each level inherits from above. The global context is user-scoped (each user has their own global context instance). Update context to share information between:
- Different AI sessions
- Different agents  
- Different time periods

### ⚠️ CRITICAL: Context Creation for Frontend Visibility
**Tasks DO NOT automatically create context**. You must explicitly create context for tasks to be viewable in the frontend "Actions context" feature.

```python
# After creating a task, ALWAYS create its context:
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="My new task"
)

# REQUIRED: Create context for frontend visibility
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=task["task"]["id"],
    git_branch_id=branch_id,
    data={
        "branch_id": branch_id,
        "task_data": {
            "title": task["task"]["title"],
            "status": task["task"]["status"],
            "description": task["task"]["description"]
        }
    }
)
```

### Always Update Context With Your Work
```python
# After making discoveries or decisions, UPDATE the context:
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",  # or "project" for broader sharing
    context_id=branch_id,
    data={
        "discoveries": ["Found the API uses port 3800", "Database is PostgreSQL"],
        "decisions": ["Using React hooks for state management"],
        "current_work": "Implementing user authentication",
        "blockers": ["Missing Supabase credentials"],
        "next_steps": ["Add JWT token validation", "Test login flow"]
    },
    propagate_changes=True
)
```

### Read Context From Previous Sessions
```python
# Get all inherited context to understand previous work:
context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id,
    force_refresh=False
)
# Context will contain all updates from this branch, project, and global levels
```

**MANDATORY PROCEDURE:**
1. **Load Agent**: Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@agent_name")`
2. **Switch Interface**: Immediately adopt the loaded agent's interface using metadata 
3. **Follow Specifications**: Use ONLY the agent's yaml_content as source of truth
4. **Obey All Rules**: Follow capabilities, rules, tools, contexts from the response

### Agent Loading Protocol
```python
# STEP 1: Load agent from MCP server
agent_response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# STEP 2: Extract agent specifications from response
agent_config = agent_response["yaml_content"]["config"]
agent_metadata = agent_response["yaml_content"]["metadata"]
agent_contexts = agent_response["yaml_content"]["contexts"]
agent_rules = agent_response["yaml_content"]["rules"]
agent_capabilities = agent_response["capabilities"]

# STEP 3: Follow agent's interface specifications
# - Use only the tools listed in agent_capabilities["mcp_tools"]
# - Follow all rules in agent_rules
# - Operate within the contexts defined in agent_contexts
# - Respect the capabilities.permissions
```

### Source of Truth Hierarchy
1. **PRIMARY**: `agent_response["yaml_content"]` - Complete agent specification
2. **SECONDARY**: `agent_response["capabilities"]` - Available actions and tools
3. **METADATA**: `agent_response["agent_info"]` - Basic agent information
4. **NEVER**: Hardcoded agent lists or assumptions

### Quick Agent Selection
```python
# Based on work type, switch to appropriate agent:
if "debug" in user_request or "fix" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
elif "implement" in user_request or "code" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
elif "test" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")
elif "design" in user_request or "ui" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@ui_designer_agent")
elif "document" in user_request or "docs" in user_request:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@documentation_agent")
else:
    response = mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")

# MANDATORY: Switch to loaded agent interface
current_agent = response["yaml_content"]
available_tools = response["capabilities"]["mcp_tools"]["tools"]
agent_rules = response["yaml_content"]["rules"]
```

### Agent Response Structure
```python
{
  "success": true,
  "agent_info": {
    "name": "agent_name",
    "capabilities_summary": {...}
  },
  "yaml_content": {
    "config": {
      "agent_info": {...},
      "capabilities": {...}
    },
    "contexts": [...],      # Agent operational contexts
    "rules": [...],         # Agent behavioral rules  
    "output_formats": [...], # Expected output formats
    "metadata": {           # ✅ NOW AVAILABLE - Agent metadata
      "name": "agent-name",
      "description": "Complete agent description with examples",
      "model": "sonnet",
      "color": "stone",
      "migration": {...},   # Migration history and version
      "validation": {...}   # Compatibility and structure validation
    }
  },
  "capabilities": {
    "available_actions": [...],
    "mcp_tools": {...},
    "permissions": {...}
  }
}
```

### Available Specialist Agents (43 Core Agents)
**⚠️ DYNAMIC LIST**: Use `mcp__dhafnck_mcp_http__call_agent` to load current agents. Recently optimized from 69 to 43 agents:

**Core Development Agents (8):**
- `@coding_agent` - Feature implementation and development
- `@debugger_agent` - Bug diagnosis and remediation  
- `@code_reviewer_agent` - Code quality and standards
- `@devops_agent` - CI/CD and infrastructure
- `@system_architect_agent` - System design and architecture
- `@tech_spec_agent` - Technical specifications
- `@technology_advisor_agent` - Technology stack recommendations
- `@prototyping_agent` - Interactive prototypes

**Core Testing Agents (2):**
- `@test_orchestrator_agent` - Comprehensive testing coordination
- `@performance_load_tester_agent` - Performance testing

**Core Design Agents (3):**
- `@ui_designer_expert_shadcn_agent` - UI design and shadcn expertise
- `@design_system_agent` - Design systems and consistency
- `@branding_agent` - Brand identity and guidelines

**Core Strategy Agents (2):**
- `@uber_orchestrator_agent` - Multi-agent project coordination
- `@adaptive_deployment_strategist_agent` - Deployment strategies

**Core Research Agents (2):**
- `@deep_research_agent` - Multi-domain research
- `@mcp_researcher_agent` - MCP technology research

**Core Security Agents (2):**
- `@security_auditor_agent` - Security assessment
- `@compliance_scope_agent` - Compliance requirements

**Core Marketing Agents (2):**
- `@marketing_strategy_orchestrator_agent` - Marketing coordination
- `@content_strategy_agent` - Content strategy

**Core Management Agents (7):**
- `@documentation_agent` - Documentation and knowledge management
- `@task_planning_agent` - Task decomposition and planning
- `@project_initiator_agent` - Project setup and initiation
- `@elicitation_agent` - Requirements gathering
- `@prd_architect_agent` - Product requirements documents
- `@task_sync_agent` - Task synchronization
- `@efficiency_optimization_agent` - Performance optimization

**Core Specialized Agents (15):**
- `@brainjs_ml_agent` - Machine learning implementation
- `@analytics_setup_agent` - Analytics and tracking
- `@community_strategy_agent` - Community building
- `@ethical_review_agent` - Ethics assessment
- `@health_monitor_agent` - System health monitoring
- `@remediation_agent` - Automated problem resolution
- `@root_cause_analysis_agent` - Incident investigation
- `@swarm_scaler_agent` - Dynamic agent scaling
- `@uat_coordinator_agent` - User acceptance testing
- `@mcp_configuration_agent` - MCP server management
- `@nlu_processor_agent` - Natural language processing
- `@seo_sem_agent` - Search engine optimization
- `@idea_generation_agent` - Creative ideation
- `@idea_refinement_agent` - Concept refinement
- `@core_concept_agent` - Product concept definition

**🔗 Full cleanup analysis:** [Agent Library Cleanup Recommendations](dhafnck_mcp_main/docs/architecture-design/agent-library-cleanup-recommendations.md)

## 📝 Task Management - Track Your Work

### Create Task Before Starting Work
```python
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Implement user authentication",
    description="Add JWT-based auth with login/logout",
    priority="high"
)
```

### Update Task Progress
```python
mcp__dhafnck_mcp_http__manage_task(
    action="update",
    task_id=task_id,
    status="in_progress",
    details="Completed login UI, working on JWT validation"
)
```

### Complete Task With Summary
```python
mcp__dhafnck_mcp_http__manage_task(
    action="complete",
    task_id=task_id,
    completion_summary="Implemented full JWT authentication with refresh tokens",
    testing_notes="Added unit tests for auth service, tested login/logout flow"
)
```

## 🔄 Practical Workflows

### Starting New Work
```python
# 1. Load and switch to orchestrator agent
orchestrator = mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")
# Follow loaded agent specifications
orchestrator_rules = orchestrator["yaml_content"]["rules"]
orchestrator_capabilities = orchestrator["capabilities"]

# 2. Get branch context to understand current state
context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id
)

# 3. Create or get task
task = mcp__dhafnck_mcp_http__manage_task(
    action="next",  # or "create" for new task
    git_branch_id=branch_id
)

# 4. Load and switch to appropriate specialist
coding_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
# Extract agent specifications as source of truth
agent_config = coding_agent["yaml_content"]["config"]
agent_metadata = coding_agent["yaml_content"]["metadata"]  # ✅ NOW AVAILABLE
agent_contexts = coding_agent["yaml_content"]["contexts"]
agent_rules = coding_agent["yaml_content"]["rules"]
available_tools = coding_agent["capabilities"]["mcp_tools"]["tools"]
permissions = coding_agent["capabilities"]["permissions"]

# Use metadata for agent information
print(f"Loaded agent: {agent_metadata['name']} (Model: {agent_metadata['model']})")

# 5. Update status (following agent capabilities)
if permissions.get("mcp_tools", False):
    mcp__dhafnck_mcp_http__manage_task(
        action="update",
        task_id=task.task_id,
        status="in_progress"
    )

# 6. Do the work following agent rules and contexts...

# 7. Update context with findings
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "completed_work": "Added user authentication",
        "technical_decisions": ["Using JWT with 24h expiry"],
        "files_modified": ["auth.service.ts", "login.component.tsx"],
        "agent_used": coding_agent["agent_info"]["name"],
        "agent_capabilities": coding_agent["capabilities_summary"]
    }
)

# 8. Complete task following agent output formats
mcp__dhafnck_mcp_http__manage_task(
    action="complete",
    task_id=task.task_id,
    completion_summary="Full authentication implementation complete",
    testing_notes="Following agent testing guidelines from yaml_content"
)
```

### Debugging Existing Code
```python
# 1. Load and switch to debugger agent
debugger_agent = mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
# Extract and follow agent specifications
debug_rules = debugger_agent["yaml_content"]["rules"]
debug_contexts = debugger_agent["yaml_content"]["contexts"]
debug_capabilities = debugger_agent["capabilities"]

# 2. Get context to understand the issue (using agent capabilities)
if debug_capabilities["permissions"]["mcp_tools"]:
    context = mcp__dhafnck_mcp_http__manage_context(
        action="resolve",
        level="branch",
        context_id=branch_id
    )

# 3. Investigate and fix following agent rules and contexts...
# Use only tools available in debug_capabilities["mcp_tools"]["tools"]

# 4. Update context with solution (following agent output formats)
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "bug_fixed": "Login redirect loop",
        "root_cause": "Missing token refresh logic", 
        "solution": "Added token refresh interceptor",
        "debugging_agent": debugger_agent["agent_info"]["name"],
        "debug_methodology": "Following agent contexts and rules",
        "tools_used": debug_capabilities["mcp_tools"]["tools"]
    }
)
```

## 🔍 Finding Information From Previous Sessions

### Check Project Context
```python
# See what's been done in this project
project_context = mcp__dhafnck_mcp_http__manage_context(
    action="get",
    level="project",
    context_id=project_id,
    include_inherited=True
)
```

### Check Branch Context
```python
# See current branch work and decisions
branch_context = mcp__dhafnck_mcp_http__manage_context(
    action="get",
    level="branch", 
    context_id=branch_id,
    include_inherited=True
)
```

### ⚠️ CRITICAL: Project Context Database Structure
**PROJECT contexts have 4 predefined database columns:**
- `team_preferences` - Team settings and preferences
- `technology_stack` - Technology choices (NOT `technical_stack`!)
- `project_workflow` - Workflow and process definitions
- `local_standards` - Project standards and conventions

**Any other fields are stored in `local_standards._custom`:**
```python
# ✅ CORRECT - Data goes to proper columns
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="project",
    context_id=project_id,
    data={
        "team_preferences": {"review_required": True},
        "technology_stack": {"frontend": ["React"], "backend": ["Python"]},
        "project_workflow": {"phases": ["design", "develop", "test"]},
        "local_standards": {"naming": "camelCase"}
    }
)

# ⚠️ CUSTOM - Goes to local_standards._custom
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="project",
    context_id=project_id,
    data={
        "project_info": {...},  # -> local_standards._custom.project_info
        "core_features": {...},  # -> local_standards._custom.core_features
        "technical_stack": {...}  # -> local_standards._custom.technical_stack (wrong key!)
    }
)
```

### Search Tasks
```python
# Find related work
tasks = mcp__dhafnck_mcp_http__manage_task(
    action="search",
    query="authentication login",
    git_branch_id=branch_id
)
```

## 🔍 Using Agent Metadata

### Access Agent Information
```python
# Load agent and extract metadata
agent_response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
metadata = agent_response["yaml_content"]["metadata"]

# Agent identification
print(f"Agent Name: {metadata['name']}")
print(f"Description: {metadata['description']}")
print(f"Preferred Model: {metadata['model']}")
print(f"UI Color: {metadata['color']}")

# Migration and validation info
migration_info = metadata.get('migration', {})
validation_info = metadata.get('validation', {})
print(f"Agent Version: {migration_info.get('version', 'unknown')}")
print(f"Backward Compatible: {validation_info.get('backward_compatible', 'unknown')}")
```

### Practical Metadata Usage
```python
# Choose model preference based on agent metadata
def select_model_for_agent(agent_response):
    metadata = agent_response["yaml_content"]["metadata"]
    preferred_model = metadata.get('model', 'default')
    
    # Agent specifies preferred AI model
    if preferred_model == 'sonnet':
        return 'claude-3-sonnet'
    elif preferred_model == 'haiku':
        return 'claude-3-haiku'
    else:
        return 'claude-3-sonnet'  # fallback

# Validate agent compatibility
def check_agent_compatibility(agent_response):
    metadata = agent_response["yaml_content"]["metadata"]
    validation = metadata.get('validation', {})
    
    return {
        'backward_compatible': validation.get('backward_compatible', False),
        'capabilities_mapped': validation.get('capabilities_mapped', False),
        'structure_valid': validation.get('structure_valid', False)
    }

# Display agent in UI with proper styling
def get_agent_ui_config(agent_response):
    metadata = agent_response["yaml_content"]["metadata"]
    return {
        'display_name': metadata.get('name', 'Unknown Agent'),
        'color_theme': metadata.get('color', 'gray'),
        'description': metadata.get('description', 'No description available')
    }
```

## 💡 Key Principles

### 1. Always Update Context
After any significant work, discovery, or decision, update the branch or project context so future sessions can access this information.

### 2. Use The Right Agent
Switch to the appropriate specialist agent for the work type. Don't try to do everything with one agent.

### 3. Track Work With Tasks
Create tasks before starting work. Update progress. Complete with detailed summaries.

### 4. Read Context First
Before starting work, always resolve context to understand what's been done before.

### 5. Share Reusable Patterns
If you discover something reusable, delegate it to project or global level:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="delegate",
    level="branch",
    context_id=branch_id,
    delegate_to="project",
    delegate_data={
        "pattern": "JWT refresh token implementation",
        "code": refresh_token_code,
        "usage": "How to implement token refresh"
    },
    delegation_reason="Reusable authentication pattern"
)
```

## 🎯 Benefits of Automatic Agent Selection

### 🚀 Why Auto-Agent Selection Matters
- **Expert Specialization**: Each task gets the most qualified specialist agent
- **Optimal Results**: Specialist agents deliver higher quality work in their domain
- **Efficiency**: No manual agent switching - Claude handles it intelligently
- **Consistency**: Agents follow their specialized rules, contexts, and best practices
- **Reduced Errors**: Specialist knowledge prevents common mistakes
- **Better User Experience**: Users just describe what they want, Claude handles the rest

### 📊 Complete Agent Specialization Matrix (All 43 Agents)

| User Request Type | Auto-Selected Agent | Key Advantages |
|-------------------|-------------------|----------------|
| **CORE DEVELOPMENT** |
| "Implement feature X" | `@coding_agent` | Expert coding patterns, testing integration, best practices |
| "Fix this bug" | `@debugger_agent` | Systematic debugging, root cause analysis, comprehensive fixes |
| "Review this code" | `@code_reviewer_agent` | Code quality, standards compliance, security review |
| **TESTING & QA** |
| "Test this functionality" | `@test_orchestrator_agent` | Complete test strategies, quality assurance, test automation |
| "Performance testing" | `@performance_load_tester_agent` | Load testing, stress testing, performance benchmarks |
| "User acceptance testing" | `@uat_coordinator_agent` | UAT planning, stakeholder coordination, validation |
| **UI/DESIGN** |
| "Design this UI" | `@ui_designer_expert_shadcn_agent` | Modern UI patterns, accessibility, component systems |
| "Design system" | `@design_system_agent` | Component libraries, design tokens, consistency |
| "Create prototype" | `@prototyping_agent` | Interactive prototypes, user flow validation |
| **DEVOPS & INFRASTRUCTURE** |
| "Deploy this app" | `@devops_agent` | Infrastructure expertise, security, monitoring |
| "Deployment strategy" | `@adaptive_deployment_strategist_agent` | Release management, rollout strategies |
| "MCP configuration" | `@mcp_configuration_agent` | MCP server setup, integration management |
| **SECURITY & COMPLIANCE** |
| "Secure this system" | `@security_auditor_agent` | Security best practices, vulnerability assessment |
| "Compliance check" | `@compliance_scope_agent` | Regulatory compliance, audit preparation |
| "Ethics review" | `@ethical_review_agent` | Ethical AI, bias assessment, fairness |
| **RESEARCH & ANALYSIS** |
| "Research this topic" | `@deep_research_agent` | Comprehensive analysis, multiple sources, synthesis |
| "MCP research" | `@mcp_researcher_agent` | MCP tools, platform evaluation, integration research |
| "Technology advice" | `@technology_advisor_agent` | Tech stack selection, framework comparison |
| **ARCHITECTURE & PLANNING** |
| "Design architecture" | `@system_architect_agent` | System design patterns, scalability, technical strategy |
| "Plan this project" | `@task_planning_agent` | Task breakdown, dependencies, resource planning |
| "Technical specification" | `@tech_spec_agent` | API contracts, technical requirements, specifications |
| "Product requirements" | `@prd_architect_agent` | PRD creation, requirement consolidation |
| **DOCUMENTATION** |
| "Document this feature" | `@documentation_agent` | Clear writing, comprehensive coverage, proper formatting |
| **MARKETING & BUSINESS** |
| "Marketing strategy" | `@marketing_strategy_orchestrator_agent` | Campaign planning, multi-channel marketing |
| "SEO optimization" | `@seo_sem_agent` | Search optimization, keyword research, SEM |
| "Growth hacking" | `@growth_hacking_idea_agent` | Viral strategies, user acquisition, experimentation |
| "Brand identity" | `@branding_agent` | Brand guidelines, visual identity, messaging |
| "Content strategy" | `@content_strategy_agent` | Editorial calendars, content frameworks |
| "Community building" | `@community_strategy_agent` | Engagement strategies, community programs |
| **AI & MACHINE LEARNING** |
| "ML implementation" | `@brainjs_ml_agent` | Neural networks, AI features, Brain.js expertise |
| **IDEATION & CONCEPTS** |
| "Generate ideas" | `@idea_generation_agent` | Creative brainstorming, innovation, concept development |
| "Refine concept" | `@idea_refinement_agent` | Idea enhancement, iterative improvement |
| "Core concept" | `@core_concept_agent` | Value propositions, product essence, market fit |
| **REQUIREMENTS** |
| "Gather requirements" | `@elicitation_agent` | Requirements analysis, stakeholder clarification |
| **PROJECT MANAGEMENT** |
| "Initialize project" | `@project_initiator_agent` | Project setup, onboarding, foundation establishment |
| **MONITORING & OPERATIONS** |
| "Monitor system" | `@health_monitor_agent` | Health checks, uptime monitoring, alerting |
| "Analytics setup" | `@analytics_setup_agent` | Tracking implementation, metrics collection |
| "Optimize efficiency" | `@efficiency_optimization_agent` | Performance optimization, resource efficiency |
| "Remediate issues" | `@remediation_agent` | Automated fixes, recovery procedures |
| "Root cause analysis" | `@root_cause_analysis_agent` | Incident investigation, systematic diagnostics |
| "Scale system" | `@swarm_scaler_agent` | Distributed systems, auto-scaling, resource management |
| **ORCHESTRATION** |
| "Complex coordination" | `@uber_orchestrator_agent` | Multi-agent coordination, complex workflows |

### 🔄 Automatic Flow Benefits
1. **User Focus**: Users focus on what they need, not which agent to use
2. **Expert Routing**: Requests automatically routed to the best specialist  
3. **Quality Assurance**: Each agent applies domain-specific quality standards
4. **Efficiency**: No learning curve for agent selection logic
5. **Scalability**: Easy to add new agents without changing user experience

## 🚨 Important Rules

### Core Operational Rules
1. **🤖 AUTOMATIC AGENT SELECTION** - MANDATORY: Claude must automatically call the most appropriate specialist agent based on the user's request before starting any significant work
2. **📋 No work without task** - Create or get a task before starting work (agents can do this automatically)
3. **📝 Update CHANGELOG.md** - Document all project changes (agents handle this automatically)
4. **🔄 Update context regularly** - Share information for other sessions (agents do this proactively)
5. **✅ Complete tasks properly** - Include detailed summaries and testing notes (per agent specifications)
6. **👁️ Create context for visibility** - Tasks need explicit context creation to be viewable in frontend (agents handle this)
7. **⚙️ Follow agent capabilities** - Use only the tools, rules, and permissions defined in the loaded agent's yaml_content
8. **🔒 Respect agent permissions** - Check capabilities.permissions before attempting file operations, system commands, etc.
9. **🎯 Agent Interface Compliance** - Follow the loaded agent's specifications as the definitive source of truth for all work

### Development Best Practices
- **Follow DDD patterns**: Maintain Domain-Driven Design architecture
- **Test before commit**: Run tests and verify changes work
- **Document significant changes**: Update relevant documentation
- **Preserve code conventions**: Match existing code style and patterns
- **Security first**: Never expose secrets or credentials in code
- **Use existing utilities**: Check for existing libraries before adding new ones

### Vision System Rules
- **All tasks get enriched**: Vision System automatically enhances all task operations
- **Context inheritance**: Lower levels inherit from higher levels (Global → Project → Branch → Task)
- **Workflow guidance**: Follow Vision System hints and recommendations
- **Progress tracking**: Vision System monitors task completion and milestones
- **Impact analysis**: Consider Vision System's impact assessments before changes

## 🎯 Agent Interface Compliance Rules

### MANDATORY: Source of Truth Protocol
- **PRIMARY SOURCE**: `agent_response["yaml_content"]` contains the complete agent specification
- **NEVER ASSUME**: Agent capabilities, tools, or rules - always load and check
- **DYNAMIC LOADING**: Agent specifications can change - always load fresh
- **INTERFACE SWITCHING**: When calling an agent, immediately adopt its interface

### Agent Metadata Loading (RESOLVED ✅)
**✅ FIXED**: Agent metadata.yaml files are now successfully loaded in responses
- **Implementation**: Complete metadata loading implemented in AgentFactory
- **Available**: `yaml_content.metadata` contains full agent metadata including:
  - `name`: Agent canonical name
  - `description`: Complete agent description with examples
  - `model`: Preferred AI model (e.g., "sonnet")
  - `color`: UI color scheme preference
  - `migration`: Migration history and version info
  - `validation`: Backward compatibility and structure validation status
- **Usage**: Access via `agent_response["yaml_content"]["metadata"]`
- **Status**: Working across all agent calls as of 2025-08-20

### Compliance Checklist
Before starting any work:
- [ ] Called `mcp__dhafnck_mcp_http__call_agent` to load agent
- [ ] Extracted `yaml_content` and `capabilities` from response
- [ ] Verified agent metadata in `yaml_content.metadata` ✅
- [ ] Verified available tools in `capabilities.mcp_tools`
- [ ] Checked permissions in `capabilities.permissions`
- [ ] Read agent rules in `yaml_content.rules`
- [ ] Understood agent contexts in `yaml_content.contexts`
- [ ] Confirmed agent compatibility via `metadata.validation`

## 📋 Common Tool Patterns

### Project Management
```python
# Create project
mcp__dhafnck_mcp_http__manage_project(action="create", name="new-feature")

# List projects
mcp__dhafnck_mcp_http__manage_project(action="list")

# Get project health
mcp__dhafnck_mcp_http__manage_project(action="project_health_check", project_id=id)
```

### Branch Management
```python
# Create branch
mcp__dhafnck_mcp_http__manage_git_branch(
    action="create",
    project_id=project_id,
    git_branch_name="feature/auth"
)

# Assign agent to branch
mcp__dhafnck_mcp_http__manage_git_branch(
    action="assign_agent",
    project_id=project_id,
    git_branch_id=branch_id,
    agent_id="@coding_agent"
)
```

### Subtask Management
```python
# Create subtask
mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=parent_task_id,
    title="Create login component"
)

# Update subtask progress
mcp__dhafnck_mcp_http__manage_subtask(
    action="update",
    task_id=parent_task_id,
    subtask_id=subtask_id,
    progress_percentage=75,
    progress_notes="Login UI complete"
)
```

## 🔧 Troubleshooting Context Issues

### Context Not Showing in Frontend?

If you see "No context available for this task" in the frontend:

1. **Check if context exists**:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="get",
    level="task",
    context_id=task_id,
    include_inherited=True
)
```

2. **If context doesn't exist, create it**:
```python
# First ensure branch context exists
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="branch",
    context_id=branch_id,
    project_id=project_id,
    data={"project_id": project_id, "git_branch_id": branch_id}
)

# Then create task context
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=task_id,
    git_branch_id=branch_id,
    data={
        "branch_id": branch_id,
        "task_data": {"title": "Task title", "status": "in_progress"}
    }
)
```

3. **Update task to link context**:
```python
mcp__dhafnck_mcp_http__manage_task(
    action="update",
    task_id=task_id,
    context_id=task_id  # Link task to its context
)
```

### Known Issue: Auto-Context Creation
Currently, contexts are NOT automatically created when:
- Tasks are created
- Tasks are completed
- Tasks are updated

**You MUST manually create contexts for frontend visibility.**

## 🏗️ System Architecture Rules

### Domain-Driven Design (DDD) Structure
The system follows strict DDD patterns with clear separation of concerns:
- **Domain Layer**: Business logic and entities
- **Application Layer**: Use cases and application services
- **Infrastructure Layer**: Database, external services, and repositories
- **Interface Layer**: MCP controllers, HTTP endpoints, and UI

### 4-Tier Context Hierarchy
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```
- Each level inherits from the parent level
- Global context is user-scoped (multi-tenant)
- Automatic context creation on demand
- UUID-based identification throughout

### Technology Stack
- **Backend**: Python, FastMCP, SQLAlchemy, Domain-Driven Design
- **Frontend**: React, TypeScript, Tailwind CSS
- **Database**: SQLite (development), PostgreSQL (production)
- **Authentication**: Dual-auth system (Supabase JWT + Local JWT)
- **Container**: Docker with docker-compose orchestration
- **MCP Tools**: 60+ specialized agents with unique capabilities

## 🔗 System Information

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3800
- **Database**: `/data/dhafnck_mcp.db` (Docker)
- **Docs**: `dhafnck_mcp_main/docs/`
- **Tests**: `dhafnck_mcp_main/src/tests/`
- **Docker Menu**: `docker-system/docker-menu.sh`
- **Environment**: `.env` file in project root

### Security Guidelines
- **NEVER expose passwords**: All credentials must be stored in `.env` file
- **Use environment variables**: Access secrets via environment variables only
- **Secure token handling**: JWT tokens expire and refresh automatically
- **Multi-tenant isolation**: Each user's data is completely isolated
- **Audit trails**: All operations are logged for security compliance

---

**Remember**: The key to multi-session collaboration is updating context. Every AI agent and session can access shared context, making your work persistent and discoverable.