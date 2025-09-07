# DhafnckMCP Usage Guide for AI Agents

## 🎯 Vision System - AI-Enhanced Decision Making

The Vision System provides intelligent guidance, workflow hints, and progress tracking. It automatically enriches tasks, provides context-aware suggestions, and maintains strategic alignment.

**Key Features:**
- Automatic task enrichment with AI insights
- Context-aware workflow guidance and progress tracking
- Blocker identification and resolution suggestions
- Strategic orchestration with 6-phase implementation

## 🤖 Intelligent Agent Auto-Selection

### 🚀 MANDATORY: Auto-Call Appropriate Agent Before Working

**CRITICAL RULE**: Claude must AUTOMATICALLY call the most appropriate specialist agent before starting any significant work.

### Complete Auto-Agent Selection Logic (43 Agents)
```python
def auto_select_agent(user_request, work_context):
    request_lower = user_request.lower()
    
    # CORE DEVELOPMENT
    if any(kw in request_lower for kw in ["implement", "code", "write", "program", "develop", "build", "create", "function", "class", "method", "api", "endpoint", "service", "component", "module", "coding", "programming", "backend", "frontend"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
    
    elif any(kw in request_lower for kw in ["debug", "fix", "error", "bug", "broken", "issue", "problem", "crash", "failure", "exception", "troubleshoot", "resolve", "repair", "analyze", "investigate", "diagnose"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@debugger_agent")
    
    elif any(kw in request_lower for kw in ["review", "code review", "pull request", "pr", "merge", "quality", "refactor", "clean code", "check", "validate", "inspect"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@code_reviewer_agent")
    
    # TESTING & QA
    elif any(kw in request_lower for kw in ["test", "testing", "unit test", "integration test", "e2e test", "end-to-end test", "test case", "test suite", "test coverage", "quality assurance", "qa", "testing framework", "jest", "mocha", "pytest", "cypress", "playwright"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@test_orchestrator_agent")
    
    elif any(kw in request_lower for kw in ["performance test", "load test", "stress test", "benchmark"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@performance_load_tester_agent")
    
    elif any(kw in request_lower for kw in ["uat", "user acceptance", "acceptance test"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@uat_coordinator_agent")
    
    # UI/DESIGN
    elif any(kw in request_lower for kw in ["design", "ui", "ux", "interface", "component", "layout", "responsive", "mobile", "dashboard", "form", "navigation", "shadcn", "tailwind", "frontend", "react component", "user experience", "user interface"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@ui_designer_expert_shadcn_agent")
    
    elif any(kw in request_lower for kw in ["design system", "component library", "design token"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@design_system_agent")
    
    elif any(kw in request_lower for kw in ["prototype", "mockup", "wireframe", "interactive"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@prototyping_agent")
    
    # DEVOPS & INFRASTRUCTURE
    elif any(kw in request_lower for kw in ["devops", "infrastructure", "docker", "kubernetes", "ci/cd", "continuous integration", "continuous deployment", "pipeline", "monitoring", "cloud", "aws", "azure", "gcp"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@devops_agent")
    
    elif any(kw in request_lower for kw in ["deploy", "deployment", "release", "rollout", "production", "staging", "deployment strategy", "blue-green deployment", "canary deployment", "rolling deployment"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@adaptive_deployment_strategist_agent")
    
    elif any(kw in request_lower for kw in ["mcp", "server", "configuration", "setup"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@mcp_configuration_agent")
    
    # SECURITY & COMPLIANCE
    elif any(kw in request_lower for kw in ["security", "secure", "vulnerability", "audit", "penetration test", "penetration", "compliance", "encryption", "security review", "gdpr", "hipaa", "authentication", "authorization"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@security_auditor_agent")
    
    elif any(kw in request_lower for kw in ["compliance", "regulatory", "gdpr", "hipaa", "legal"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@compliance_scope_agent")
    
    elif any(kw in request_lower for kw in ["ethics", "ethical", "bias", "fairness"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@ethical_review_agent")
    
    # RESEARCH & ANALYSIS
    elif any(kw in request_lower for kw in ["research", "analyze", "investigate", "study", "explore", "competitive analysis", "market research", "data analysis", "trend analysis", "insights"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@deep_research_agent")
    
    elif any(kw in request_lower for kw in ["mcp research", "tool research", "platform research"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@mcp_researcher_agent")
    
    elif any(kw in request_lower for kw in ["technology", "tech stack", "framework", "library"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@technology_advisor_agent")
    
    # ARCHITECTURE & PLANNING
    elif any(kw in request_lower for kw in ["architecture", "system design", "technical architecture", "scalability", "microservices", "distributed systems", "cloud architecture", "infrastructure design", "system integration", "technology stack", "architectural patterns"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@system_architect_agent")
    
    elif any(kw in request_lower for kw in ["plan", "planning", "breakdown", "tasks", "project plan", "task management", "organize", "schedule", "task", "organize", "project"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@task_planning_agent")
    
    elif any(kw in request_lower for kw in ["tech spec", "specification", "technical requirement"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@tech_spec_agent")
    
    elif any(kw in request_lower for kw in ["prd", "product requirement", "product spec"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@prd_architect_agent")
    
    # DOCUMENTATION
    elif any(kw in request_lower for kw in ["documentation", "docs", "readme", "guide", "manual", "wiki", "help", "instructions", "api docs", "document", "tutorial", "reference", "specification"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@documentation_agent")
    
    # MARKETING & BUSINESS
    elif any(kw in request_lower for kw in ["marketing", "campaign", "promotion", "brand"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@marketing_strategy_orchestrator_agent")
    
    elif any(kw in request_lower for kw in ["seo", "sem", "search", "keyword", "optimization"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@seo_sem_agent")
    
    elif any(kw in request_lower for kw in ["growth", "growth hack", "viral", "acquisition"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@growth_hacking_idea_agent")
    
    elif any(kw in request_lower for kw in ["brand", "branding", "identity", "logo"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@branding_agent")
    
    elif any(kw in request_lower for kw in ["content", "content strategy", "editorial"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@content_strategy_agent")
    
    elif any(kw in request_lower for kw in ["community", "engagement", "social"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@community_strategy_agent")
    
    # AI & MACHINE LEARNING
    elif any(kw in request_lower for kw in ["ml", "machine learning", "ai", "neural", "brain.js"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@brainjs_ml_agent")
    
    # IDEATION & CONCEPTS
    elif any(kw in request_lower for kw in ["idea", "brainstorm", "concept", "innovation"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@idea_generation_agent")
    
    elif any(kw in request_lower for kw in ["refine", "improve", "enhance", "iterate"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@idea_refinement_agent")
    
    elif any(kw in request_lower for kw in ["core concept", "value proposition", "essence"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@core_concept_agent")
    
    # REQUIREMENTS & ELICITATION
    elif any(kw in request_lower for kw in ["requirements", "gather", "elicit", "clarify"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@elicitation_agent")
    
    # PROJECT & PROCESS
    elif any(kw in request_lower for kw in ["project init", "project start", "onboard"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@project_initiator_agent")
    
    # MONITORING & OPERATIONS
    elif any(kw in request_lower for kw in ["health", "monitor", "status", "uptime"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@health_monitor_agent")
    
    elif any(kw in request_lower for kw in ["analytics", "tracking", "dashboard", "metrics", "data collection", "events", "monitoring", "statistics", "insights", "reporting", "google analytics", "performance tracking", "user analytics", "conversion tracking"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@analytics_setup_agent")
    
    elif any(kw in request_lower for kw in ["efficiency", "optimize", "performance", "improve"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@efficiency_optimization_agent")
    
    elif any(kw in request_lower for kw in ["remediation", "fix", "resolve", "repair"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@remediation_agent")
    
    elif any(kw in request_lower for kw in ["root cause", "analysis", "investigate"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@root_cause_analysis_agent")
    
    elif any(kw in request_lower for kw in ["scale", "scaling", "swarm", "distributed"]):
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@swarm_scaler_agent")
    
    else:
        # Default to orchestrator for complex or unclear requests
        return mcp__dhafnck_mcp_http__call_agent(name_agent="@uber_orchestrator_agent")
```

### Agent Display Format
```bash
[Agent: {agent_name} - Working...]
[Agent: {agent_name} - Ready]
[Agent: {agent_name} - Initializing...]
```

## 📊 Context Management - Share Information Between Sessions

### Context Hierarchy
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```

Each level inherits from above. Update context to share information between sessions, agents, and time periods.

### ⚠️ CRITICAL: Context Creation for Frontend Visibility
Tasks DO NOT automatically create context. You must explicitly create context for frontend visibility.

```python
# Create task and context
task = mcp__dhafnck_mcp_http__manage_task(action="create", git_branch_id=branch_id, title="My task")

# REQUIRED: Create context for frontend visibility
mcp__dhafnck_mcp_http__manage_context(
    action="create", level="task", context_id=task["task"]["id"], git_branch_id=branch_id,
    data={"branch_id": branch_id, "task_data": {"title": task["task"]["title"], "status": task["task"]["status"]}}
)
```

### Essential Context Operations
```python
# Update context with work
mcp__dhafnck_mcp_http__manage_context(
    action="update", level="branch", context_id=branch_id,
    data={"discoveries": ["API uses port 3800"], "decisions": ["Using React hooks"], "current_work": "Auth implementation"},
    propagate_changes=True
)

# Read previous work
context = mcp__dhafnck_mcp_http__manage_context(action="resolve", level="branch", context_id=branch_id)
```

## 🤖 Agent Loading Protocol

### MANDATORY Agent Switching Process
1. **Load Agent**: `mcp__dhafnck_mcp_http__call_agent(name_agent="@agent_name")`
2. **Extract Specifications**: Get yaml_content, capabilities, metadata from response
3. **Follow Interface**: Use agent's rules, contexts, and available tools only
4. **Respect Permissions**: Check capabilities.permissions before operations

```python
# Agent loading example
agent_response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")
agent_rules = agent_response["yaml_content"]["rules"]
available_tools = agent_response["capabilities"]["mcp_tools"]["tools"]
permissions = agent_response["capabilities"]["permissions"]
```

### Source of Truth Hierarchy
1. **PRIMARY**: `agent_response["yaml_content"]` - Complete agent specification
2. **SECONDARY**: `agent_response["capabilities"]` - Available actions and tools
3. **METADATA**: `agent_response["agent_info"]` - Basic agent information
4. **NEVER**: Hardcoded agent lists or assumptions

### Available Specialist Agents (43 Core Agents)

**Core Development (8):** @coding_agent, @debugger_agent, @code_reviewer_agent, @devops_agent, @system_architect_agent, @tech_spec_agent, @technology_advisor_agent, @prototyping_agent

**Core Testing (2):** @test_orchestrator_agent, @performance_load_tester_agent

**Core Design (3):** @ui_designer_expert_shadcn_agent, @design_system_agent, @branding_agent

**Core Strategy (2):** @uber_orchestrator_agent, @adaptive_deployment_strategist_agent

**Core Research (2):** @deep_research_agent, @mcp_researcher_agent

**Core Security (2):** @security_auditor_agent, @compliance_scope_agent

**Core Marketing (2):** @marketing_strategy_orchestrator_agent, @content_strategy_agent

**Core Management (7):** @documentation_agent, @task_planning_agent, @project_initiator_agent, @elicitation_agent, @prd_architect_agent, @task_sync_agent, @efficiency_optimization_agent

**Core Specialized (15):** @brainjs_ml_agent, @analytics_setup_agent, @community_strategy_agent, @ethical_review_agent, @health_monitor_agent, @remediation_agent, @root_cause_analysis_agent, @swarm_scaler_agent, @uat_coordinator_agent, @mcp_configuration_agent, @nlu_processor_agent, @seo_sem_agent, @idea_generation_agent, @idea_refinement_agent, @core_concept_agent

## 📝 Task Management

### Essential Task Operations
```python
# Create task
task = mcp__dhafnck_mcp_http__manage_task(
    action="create", git_branch_id=branch_id, title="Implement user auth", 
    description="Add JWT-based auth", priority="high"
)

# Update progress
mcp__dhafnck_mcp_http__manage_task(
    action="update", task_id=task_id, status="in_progress", 
    details="Login UI done, working on JWT validation"
)

# Complete task
mcp__dhafnck_mcp_http__manage_task(
    action="complete", task_id=task_id, 
    completion_summary="Full JWT auth with refresh tokens",
    testing_notes="Added unit tests, tested login/logout flow"
)
```

## 🔄 Quick Workflows

### Starting New Work
```python
# 1. Auto-select and load appropriate agent (happens automatically)
agent_response = mcp__dhafnck_mcp_http__call_agent(name_agent="@coding_agent")

# 2. Get context to understand current state
context = mcp__dhafnck_mcp_http__manage_context(action="resolve", level="branch", context_id=branch_id)

# 3. Get or create task
task = mcp__dhafnck_mcp_http__manage_task(action="next", git_branch_id=branch_id)

# 4. Execute work following agent specifications
# 5. Update context with findings
# 6. Complete task with detailed summary
```

### Project Context Database Structure
**PROJECT contexts have 4 predefined columns:**
- `team_preferences` - Team settings
- `technology_stack` - Tech choices (NOT `technical_stack`!)  
- `project_workflow` - Workflow definitions
- `local_standards` - Project standards

**Other fields go to `local_standards._custom`**

## 📋 Common Tool Patterns

```python
# Project management
mcp__dhafnck_mcp_http__manage_project(action="create", name="new-feature")
mcp__dhafnck_mcp_http__manage_project(action="list")

# Branch management  
mcp__dhafnck_mcp_http__manage_git_branch(action="create", project_id=project_id, git_branch_name="feature/auth")

# Subtask management
mcp__dhafnck_mcp_http__manage_subtask(action="create", task_id=parent_task_id, title="Create login component")
```

## 🔧 Troubleshooting Context Issues

If "No context available for this task" in frontend:

1. **Check context exists**: `mcp__dhafnck_mcp_http__manage_context(action="get", level="task", context_id=task_id)`
2. **Create missing context**: Use create action for branch and task levels
3. **Link task to context**: `mcp__dhafnck_mcp_http__manage_task(action="update", task_id=task_id, context_id=task_id)`

**Known Issue**: Contexts are NOT auto-created. Manual creation required for frontend visibility.

## 🚨 Important Rules

### Core Operational Rules
1. **🤖 AUTOMATIC AGENT SELECTION** - MANDATORY: Auto-call appropriate specialist agent before significant work
2. **📋 No work without task** - Create/get task before starting (agents handle automatically)
3. **📝 Update CHANGELOG.md** - Document all changes (agents handle automatically)
4. **🔄 Update context regularly** - Share information for other sessions
5. **✅ Complete tasks properly** - Include summaries and testing notes
6. **👁️ Create context for visibility** - Tasks need explicit context creation
7. **⚙️ Follow agent capabilities** - Use only agent's defined tools/rules/permissions
8. **🎯 Agent Interface Compliance** - Agent yaml_content is source of truth

### Development Best Practices
- Follow DDD patterns, test before commit, document changes
- Preserve code conventions, security first, use existing utilities

### Vision System Rules
- All tasks get Vision System enrichment automatically
- Context inheritance: Global → Project → Branch → Task
- Follow Vision System workflow guidance and progress tracking

## 🏗️ System Architecture

### Domain-Driven Design Structure
- **Domain Layer**: Business logic and entities
- **Application Layer**: Use cases and services  
- **Infrastructure Layer**: Database, external services, repositories
- **Interface Layer**: MCP controllers, HTTP endpoints, UI

### 4-Tier Context Hierarchy
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```
- Each level inherits from parent, Global context is user-scoped
- UUID-based identification throughout

### Technology Stack
- **Backend**: Python, FastMCP, SQLAlchemy, DDD
- **Frontend**: React, TypeScript, Tailwind CSS
- **Database**: SQLite (dev), PostgreSQL (prod)
- **Authentication**: Dual-auth (Supabase JWT + Local JWT)
- **Container**: Docker with docker-compose
- **MCP Tools**: 60+ specialized agents

## 🔗 System Information

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3800  
- **Database**: `/data/dhafnck_mcp.db` (Docker)
- **Docs**: `dhafnck_mcp_main/docs/`
- **Tests**: `dhafnck_mcp_main/src/tests/`
- **Docker Menu**: `docker-system/docker-menu.sh`
- **Environment**: `.env` file in project root

### Security Guidelines
- Never expose passwords - use `.env` file only
- Access secrets via environment variables
- JWT tokens auto-expire and refresh
- Multi-tenant isolation enforced
- All operations logged for compliance

---

**Remember**: Update context after significant work. Every AI agent and session can access shared context, making your work persistent and discoverable.