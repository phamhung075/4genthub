# Repository Guidelines

## Project Structure & Module Organization
- Backend code lives in `agenthub_main/src/fastmcp` with supporting modules under `src/config` and `src/database`.
- Tests shadow the package layout in `agenthub_main/src/tests`; drop new suites beside the feature they exercise.
- `agenthub-frontend/src` hosts the React client, `public/` static assets, and shared UI primitives under `src/components`.
- Docs sit in `ai_docs/`; orchestration scripts (Docker menu, workers) stay under `docker-system/` and root `scripts/`.

## Build, Test, and Development Commands
- Backend: `cd agenthub_main && uv sync` installs dependencies, `uv run --frozen pytest src/tests` runs the suite, and `uv run --frozen pyright` type-checks.
- Justfile shortcuts mirror the flow: `cd agenthub_main && just build` (deps) and `just test` (pytest with `-xvs`).
- Frontend: `cd agenthub-frontend && pnpm install` primes the workspace, `pnpm start` serves Vite dev mode, `pnpm build` emits production assets, and `pnpm test` runs Vitest.
- Need the full stack? launch `./docker-system/docker-menu.sh` and select the target profile.

## Coding Style & Naming Conventions
- Python follows PEP 8 with 4-space indents and type hints; run `uv run --frozen ruff check src --fix` before committing and keep module names concise (`task_service.py`).
- FastAPI routes should return typed response models; reserve the `_async` suffix only when a sync variant also exists.
- React components use PascalCase filenames, hooks stay in `src/hooks` with camelCase names, and pair Tailwind classes with co-located styles.

## Testing Guidelines
- Honour the pytest markers (`fast`, `integration`, `mcp`, etc.) and keep coverage above the 80% bar defined in `pyproject.toml`; name files `test_<feature>.py` and share fixtures via sibling `conftest.py`.
- Quick loops: `uv run --frozen pytest -m fast`; pre-PR: `uv run --frozen pytest --cov=src --cov-report=term-missing`.
- Frontend tests sit next to the component with a `.test.tsx` suffix; scope runs via `pnpm test -- --run MatchPattern`.

## Commit & Pull Request Guidelines
- Follow the Conventional Commit style in history (`fix:`, `refactor:`, `chore:`), adding scopes when it aids review (`feat(frontend): add timeline tabs`).
- Keep commits self-contained with passing checks; document breaking API or schema changes in the body.
- PRs should spell out backend vs. frontend impact, link issues, and add screenshots or terminal output for visible changes.
- Run `uv run pytest`, `uv run pyright`, and `pnpm test` before submission and flag any skips or debt in the description.


# DhafnckMCP Usage Guide for AI Agents

## 🎯 Vision System
AI-enhanced decision making with automatic task enrichment, workflow guidance, progress tracking, blocker identification, impact analysis, and strategic orchestration. Integrates with tasks, context, agents, and health monitoring.

## 🤖 Agent Auto-Selection
**CRITICAL**: Claude AUTOMATICALLY calls the most appropriate specialist agent before starting any significant work.

### Auto-Agent Selection Logic (43 Agents)
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

### Auto-Call Triggers
- **Code/Debug/Test**: `@coding_agent`, `@debugger_agent`, `@test_orchestrator_agent`
- **UI/Design**: `@ui_designer_expert_shadcn_agent`, `@design_system_agent`
- **Docs/Planning**: `@documentation_agent`, `@task_planning_agent`
- **System/Security**: `@system_architect_agent`, `@security_auditor_agent`
- **DevOps/Research**: `@devops_agent`, `@deep_research_agent`
- **Complex/Review**: `@uber_orchestrator_agent`, `@code_reviewer_agent`

### Agent Display Format
```bash
[Agent: {agent_name} - Working...]
[Agent: {agent_name} - Ready]
[Agent: {agent_name} - Initializing...]
```

### Agent Loading Process
1. Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@agent_name")`
2. Extract `yaml_content` and `capabilities` from response
3. Switch to agent's interface using specifications
4. Follow agent's rules, contexts, and capabilities

**Agent Library**: 43 optimized specialists (streamlined from 69). See [cleanup analysis](dhafnck_mcp_main/docs/architecture-design/agent-library-cleanup-recommendations.md).


## 🚀 Quick Start
Claude automatically selects and loads the best specialist agent. Flow: **User request** → **Auto-detect work type** → **Load specialist** → **Execute work**

```python
# Example automatic flow:
# "Implement login" → @coding_agent
# "Fix this bug" → @debugger_agent  
# "Test feature" → @test_orchestrator_agent

# Optional system setup
mcp__dhafnck_mcp_http__manage_connection(action="health_check")
mcp__dhafnck_mcp_http__manage_project(action="list")
mcp__dhafnck_mcp_http__manage_task(action="next", git_branch_id=branch_id)
```

## 📊 Context Management
**Hierarchy**: `GLOBAL (per-user) → PROJECT → BRANCH → TASK`

Each level inherits from above. Share information between sessions, agents, and time periods.

**⚠️ CRITICAL**: Tasks DO NOT auto-create context. Explicitly create for frontend visibility.

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

### Context Operations
```python
# Create context for tasks
mcp__dhafnck_mcp_http__manage_context(
    action="create", level="task", context_id=task_id,
    data={"task_data": {...}}
)

# Update with discoveries/decisions
mcp__dhafnck_mcp_http__manage_context(
    action="update", level="branch", context_id=branch_id,
    data={"discoveries": [...], "decisions": [...]},
    propagate_changes=True
)

# Read previous work
context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve", level="branch", context_id=branch_id
)
```

### Agent Loading Protocol
**Agent Loading Protocol**

**Step 1:** Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@agent_name")` to retrieve agent information.  
- **Display:** `[Agent: Initializing...]`

**Step 2:** Extract `yaml_content` (rules, contexts, metadata) and `capabilities` from the MCP server response.  
- **Display:** `[Agent: Loading...]`

**Step 3:** Follow the agent's specifications as the source of truth.  
- Use only the allowed tools and respect all permissions.

**Step 4:** Use the Task tool to launch the agent with its complete specification.  
- **Display:** `[Agent: {agent_name} - Working...]`

**Step 5:** Agent becomes operational (equivalent to launching from `.claude/agents`).  
- **Display:** `[Agent: {agent_name} - Ready]`

**Source of Truth**: `yaml_content` (primary) → `capabilities` → `agent_info` → Never hardcoded assumptions

### Agent Response Structure
```python
{
  "yaml_content": {
    "rules": [...],         # Agent behavioral rules
    "contexts": [...],      # Agent operational contexts  
    "metadata": {           # Agent info, model preference, color
      "name": "agent-name", "model": "sonnet", "color": "stone"
    }
  },
  "capabilities": {
    "mcp_tools": {...},     # Available tools
    "permissions": {...}    # Agent permissions
  }
}
```

### 43 Specialist Agents (Optimized from 69)
**Development**: `@coding_agent`, `@debugger_agent`, `@code_reviewer_agent`, `@devops_agent`, `@system_architect_agent`, `@tech_spec_agent`, `@technology_advisor_agent`, `@prototyping_agent`

**Testing**: `@test_orchestrator_agent`, `@performance_load_tester_agent`

**Design**: `@ui_designer_expert_shadcn_agent`, `@design_system_agent`, `@branding_agent`

**Strategy**: `@uber_orchestrator_agent`, `@adaptive_deployment_strategist_agent`

**Research**: `@deep_research_agent`, `@mcp_researcher_agent`

**Security**: `@security_auditor_agent`, `@compliance_scope_agent`

**Marketing**: `@marketing_strategy_orchestrator_agent`, `@content_strategy_agent`

**Management**: `@documentation_agent`, `@task_planning_agent`, `@project_initiator_agent`, `@elicitation_agent`, `@prd_architect_agent`, `@task_sync_agent`, `@efficiency_optimization_agent`

**Specialized**: `@brainjs_ml_agent`, `@analytics_setup_agent`, `@community_strategy_agent`, `@ethical_review_agent`, `@health_monitor_agent`, `@remediation_agent`, `@root_cause_analysis_agent`, `@swarm_scaler_agent`, `@uat_coordinator_agent`, `@mcp_configuration_agent`, `@nlu_processor_agent`, `@seo_sem_agent`, `@idea_generation_agent`, `@idea_refinement_agent`, `@core_concept_agent`

**Full cleanup analysis**: [Agent Library Cleanup](dhafnck_mcp_main/docs/architecture-design/agent-library-cleanup-recommendations.md)

## 📝 Task Management
```python
# Create task
task = mcp__dhafnck_mcp_http__manage_task(
    action="create", git_branch_id=branch_id,
    title="Implement user authentication", priority="high"
)

# Update progress
mcp__dhafnck_mcp_http__manage_task(
    action="update", task_id=task_id, status="in_progress",
    details="Completed login UI, working on JWT validation"
)

# Complete with summary
mcp__dhafnck_mcp_http__manage_task(
    action="complete", task_id=task_id,
    completion_summary="Full JWT authentication with refresh tokens",
    testing_notes="Unit tests added, login/logout tested"
)
```

## 🔄 Workflows

### Standard Workflow
1. **Load agent** (auto-selected or manual)
2. **Get context** to understand previous work  
3. **Create/get task** for tracking
4. **Execute work** following agent rules
5. **Update context** with findings
6. **Complete task** with summary

### Key Context Queries
```python
# Read previous work
context = mcp__dhafnck_mcp_http__manage_context(
    action="resolve", level="branch", context_id=branch_id
)

# Update with findings  
mcp__dhafnck_mcp_http__manage_context(
    action="update", level="branch", context_id=branch_id,
    data={"completed_work": "...", "decisions": [...]}
)
```

## 🔍 Previous Session Information

### Project Context Structure
**4 predefined columns**: `team_preferences`, `technology_stack`, `project_workflow`, `local_standards`
**Custom fields**: Stored in `local_standards._custom`

```python
# Check previous work
project_context = mcp__dhafnck_mcp_http__manage_context(
    action="get", level="project", context_id=project_id
)
branch_context = mcp__dhafnck_mcp_http__manage_context(
    action="get", level="branch", context_id=branch_id
)

# Search related tasks
tasks = mcp__dhafnck_mcp_http__manage_task(
    action="search", query="authentication", git_branch_id=branch_id
)
```

## 🔍 Agent Metadata Usage
```python
# Extract agent metadata
metadata = agent_response["yaml_content"]["metadata"]
print(f"Agent: {metadata['name']} (Model: {metadata['model']}, Color: {metadata['color']})")

# Check compatibility
validation = metadata.get('validation', {})
compatible = validation.get('backward_compatible', False)
```

## 💡 Key Principles
1. **Always Update Context** - Share discoveries for future sessions
2. **Use Right Agent** - Auto-select or switch to appropriate specialist  
3. **Track With Tasks** - Create before work, update progress, complete with summaries
4. **Read Context First** - Understand previous work before starting
5. **Share Reusable Patterns** - Delegate useful patterns to project/global level

```python
# Delegate reusable pattern
mcp__dhafnck_mcp_http__manage_context(
    action="delegate", level="branch", context_id=branch_id,
    delegate_to="project", delegate_data={"pattern": "JWT implementation"},
    delegation_reason="Reusable auth pattern"
)
```

## 🎯 Auto-Agent Selection Benefits
- **Expert Specialization**: Each task gets the most qualified specialist
- **Efficiency**: No manual switching - Claude handles it intelligently  
- **Quality**: Specialist agents apply domain-specific standards
- **User Experience**: Just describe what you want, Claude handles routing
- **Scalability**: Easy to add new agents without changing experience

### Key Agent Routing Examples
- "Implement feature" → `@coding_agent` (expert patterns, testing integration)
- "Fix this bug" → `@debugger_agent` (systematic debugging, root cause analysis)  
- "Design UI" → `@ui_designer_expert_shadcn_agent` (modern patterns, accessibility)
- "Test feature" → `@test_orchestrator_agent` (complete strategies, automation)
- "Deploy app" → `@devops_agent` (infrastructure expertise, security)
- "Document API" → `@documentation_agent` (clear writing, comprehensive coverage)

## 🚨 Important Rules

### Core Operations (MANDATORY)
1. **🤖 AUTO-AGENT SELECTION** - Claude automatically calls appropriate specialist before significant work
2. **📋 Task-Driven Work** - Create/get task before starting, update progress, complete with summaries
3. **📝 Update CHANGELOG.md** - Document all project changes (agents handle automatically)
4. **🔄 Context Sharing** - Update context regularly for cross-session collaboration
5. **👁️ Frontend Visibility** - Explicitly create task contexts for frontend display
6. **⚙️ Agent Compliance** - Follow loaded agent's yaml_content, capabilities, permissions
7. **🎯 Interface Switching** - Use agent specifications as definitive source of truth

### Development Standards
- **DDD Architecture** - Maintain Domain-Driven Design patterns
- **Security First** - Never expose credentials, use environment variables
- **Test-Driven** - Run tests before commits, verify changes work  
- **Documentation** - Update relevant docs for significant changes
- **Code Conventions** - Match existing style and patterns
- **Existing Libraries** - Check for available utilities before adding new ones

### Vision System Integration  
- **Task Enrichment** - All tasks automatically enhanced with AI insights
- **Context Hierarchy** - GLOBAL → PROJECT → BRANCH → TASK inheritance
- **Progress Tracking** - Automatic milestone detection and completion analysis
- **Impact Analysis** - Consider Vision System assessments before changes

## 🎯 Agent Compliance Rules

### Source of Truth Protocol
- **PRIMARY**: `yaml_content` contains complete agent specification
- **DYNAMIC**: Always load fresh - specifications can change
- **NO ASSUMPTIONS**: Always load and verify capabilities/tools/rules
- **IMMEDIATE SWITCH**: Adopt agent interface immediately after loading

### Agent Metadata (Available ✅)
- **Full metadata loading** implemented in AgentFactory
- **Access via**: `agent_response["yaml_content"]["metadata"]`
- **Contains**: name, description, model preference, color, validation status

### Compliance Checklist
- [ ] Called `mcp__dhafnck_mcp_http__call_agent` to load agent
- [ ] Extracted `yaml_content` and `capabilities` from response
- [ ] Verified metadata, tools, permissions, rules, contexts
- [ ] Confirmed agent compatibility and validation status

## 📋 Tool Patterns

```python
# Project Management
mcp__dhafnck_mcp_http__manage_project(action="create", name="new-feature")
mcp__dhafnck_mcp_http__manage_project(action="list")
mcp__dhafnck_mcp_http__manage_project(action="project_health_check", project_id=id)

# Branch Management  
mcp__dhafnck_mcp_http__manage_git_branch(
    action="create", project_id=project_id, git_branch_name="feature/auth"
)
mcp__dhafnck_mcp_http__manage_git_branch(
    action="assign_agent", project_id=project_id, 
    git_branch_id=branch_id, agent_id="@coding_agent"
)

# Subtask Management
mcp__dhafnck_mcp_http__manage_subtask(
    action="create", task_id=parent_task_id, title="Create login component"
)
mcp__dhafnck_mcp_http__manage_subtask(
    action="update", task_id=parent_task_id, subtask_id=subtask_id,
    progress_percentage=75, progress_notes="Login UI complete"
)
```

## 🔧 Context Troubleshooting

### "No context available" in frontend?
**Issue**: Tasks don't automatically create context

**Solution**:
```python
# 1. Check if context exists
mcp__dhafnck_mcp_http__manage_context(
    action="get", level="task", context_id=task_id
)

# 2. Create missing contexts
mcp__dhafnck_mcp_http__manage_context(
    action="create", level="branch", context_id=branch_id,
    data={"project_id": project_id, "git_branch_id": branch_id}
)
mcp__dhafnck_mcp_http__manage_context(
    action="create", level="task", context_id=task_id,
    data={"task_data": {"title": "...", "status": "..."}}
)

# 3. Link task to context
mcp__dhafnck_mcp_http__manage_task(
    action="update", task_id=task_id, context_id=task_id
)
```

---

**Auto-Agent**: For context creation and management, Claude will automatically call the most competent agent (e.g., @context_manager_agent) when a context is missing or required for frontend visibility. Manual creation is no longer necessary if the agent can handle it.

**Remember**: Contexts must be manually created for frontend visibility.

**Remember**: Fix root causes, not symptoms

**Remember**: Detailed summaries without missing important details

**Remember**: AI files config, rules in .cursor/rules/

**Remember**: No root directory file creation without permission

**Remember**: Respect project structure unless changes requested

**Remember**: The key to multi-session collaboration is updating context. Every AI agent and session can access shared context, making your work persistent and discoverable.

**Remember**: Session continuity across agents and time - Always check previous session context before starting new work, update context regularly during work, and complete tasks with detailed summaries for future sessions.

**Remember**:  
After completing a task or subtask, always:

1. **Update the context** using `mcp__dhafnck_mcp_http__manage_context` to ensure the latest state is reflected and visible to all agents and the frontend.
2. **Update the completion status and progress percentage** using `mcp__dhafnck_mcp_http__manage_task` or `mcp__dhafnck_mcp_http__manage_subtask`:
   - Set `status="done"` and `progress_percentage=100` for completed items.
   - Ensure any related context objects are also updated or linked as needed.

## Codex CLI Tool Reference

The following tool definitions mirror `ai_docs/codex_tools_list.md`.

- function shell(args: { command: string[]; timeout_ms?: number; workdir?: string; with_escalated_permissions?: boolean; justification?: string; }): Promise<any>; — Runs a shell command and returns its output.


- function update_plan(args: { explanation?: string; plan: { status: "pending" | "in_progress" | "completed"; step: string; }[]; }): Promise<any>; — Updates the task plan with step statuses.


- function view_image(args: { path: string; }): Promise<any>; — Attaches a local image to the conversation context.


- function ElevenLabs__add_knowledge_base_to_agent(args: { agent_id: string; knowledge_base_name: string; url?: string; input_file_path?: string; text?: string; }): Promise<any>; — Adds a knowledge base to an ElevenLabs agent.


- function ElevenLabs__check_subscription(): Promise<any>; — Retrieves the current ElevenLabs subscription status.


- function ElevenLabs__compose_music(args: { prompt?: string; composition_plan?: string; music_length_ms?: string; output_directory?: string; }): Promise<any>; — Converts a prompt or plan into generated music.


- function ElevenLabs__create_agent(args: { name: string; first_message: string; system_prompt: string; voice_id?: string; language?: string; llm?: string; temperature?: number; max_tokens?: string; model_id?: string; asr_quality?: string; optimize_streaming_latency?: number; stability?: number; similarity_boost?: number; turn_timeout?: number; max_duration_seconds?: number; record_voice?: boolean; retention_days?: number; }): Promise<any>; — Creates a conversational ElevenLabs agent with custom configuration.


- function ElevenLabs__create_composition_plan(args: { prompt: string; music_length_ms?: string; source_composition_plan?: string; }): Promise<any>; — Generates a composition plan for ElevenLabs music creation.


- function ElevenLabs__create_voice_from_preview(args: { generated_voice_id: string; voice_name: string; voice_description: string; }): Promise<any>; — Saves a generated voice preview into the ElevenLabs voice library.


- function ElevenLabs__get_agent(args: { agent_id: string; }): Promise<any>; — Retrieves details about a specific ElevenLabs conversational agent.


- function ElevenLabs__get_conversation(args: { conversation_id: string; }): Promise<any>; — Fetches conversation metadata and full transcript from ElevenLabs.


- function ElevenLabs__get_voice(args: { voice_id: string; }): Promise<any>; — Obtains detailed information about a specific ElevenLabs voice.


- function ElevenLabs__isolate_audio(args: { input_file_path: string; output_directory?: string; }): Promise<any>; — Separates vocals or instruments from an audio file using ElevenLabs.


- function ElevenLabs__list_agents(): Promise<any>; — Lists all ElevenLabs conversational agents for the account.


- function ElevenLabs__list_conversations(args: { agent_id?: string; cursor?: string; call_start_before_unix?: string; call_start_after_unix?: string; page_size?: number; max_length?: number; }): Promise<any>; — Retrieves paginated ElevenLabs agent conversations.


- function ElevenLabs__list_models(): Promise<any>; — Returns the available ElevenLabs models for speech and agents.


- function ElevenLabs__list_phone_numbers(): Promise<any>; — Lists phone numbers associated with the ElevenLabs account.


- function ElevenLabs__make_outbound_call(args: { agent_id: string; agent_phone_number_id: string; to_number: string; }): Promise<any>; — Initiates an outbound phone call handled by an ElevenLabs agent.


- function ElevenLabs__play_audio(args: { input_file_path: string; }): Promise<any>; — Plays a local audio file via ElevenLabs tooling.


- function ElevenLabs__search_voice_library(args: { page?: number; page_size?: number; search?: string; }): Promise<any>; — Searches the shared ElevenLabs voice library.


- function ElevenLabs__search_voices(args: { search?: string; sort?: string; sort_direction?: string; }): Promise<any>; — Searches existing voices within the user’s ElevenLabs library.


- function ElevenLabs__speech_to_speech(args: { input_file_path: string; output_directory?: string; voice_name?: string; }): Promise<any>; — Transforms audio into another voice using ElevenLabs speech-to-speech.


- function ElevenLabs__speech_to_text(args: { input_file_path: string; language_code?: string; diarize?: boolean; output_directory?: string; save_transcript_to_file?: boolean; return_transcript_to_client_directly?: boolean; }): Promise<any>; — Transcribes audio to text with optional diarization via ElevenLabs.


- function ElevenLabs__text_to_sound_effects(args: { text: string; duration_seconds?: number; loop?: boolean; output_directory?: string; output_format?: string; }): Promise<any>; — Generates sound effects from text descriptions through ElevenLabs.


- function ElevenLabs__text_to_speech(args: { text: string; voice_id?: string; voice_name?: string; model_id?: string; stability?: number; similarity_boost?: number; style?: number; use_speaker_boost?: boolean; speed?: number; output_directory?: string; language?: string; output_format?: string; }): Promise<any>; — Converts text into speech audio using ElevenLabs voices.


- function ElevenLabs__text_to_voice(args: { voice_description: string; text?: string; output_directory?: string; }): Promise<any>; — Creates new voice previews from a description via ElevenLabs.


- function ElevenLabs__voice_clone(args: { name: string; files: string[]; description?: string; }): Promise<any>; — Clones a voice instantly by supplying audio samples to ElevenLabs.


- function agenthub_http__call_agent(args: { name_agent: string; }): Promise<any>; — Loads and invokes a specialized agent by name within the AgentHub system.


- function agenthub_http__generate_token(): Promise<any>; — Provides information about generating new authentication tokens (deprecated helper).


- function agenthub_http__get_auth_status(): Promise<any>; — Returns authentication system status and configuration from AgentHub.


- function agenthub_http__get_rate_limit_status(args: { token: string; }): Promise<any>; — Retrieves rate limit status for a specific AgentHub token.


- function agenthub_http__manage_agent(args: { action: string; project_id?: string; agent_id?: string; name?: string; call_agent?: string; git_branch_id?: string; user_id?: string; }): Promise<any>; — Manages agent registration, assignment, and lifecycle within AgentHub projects.


- function agenthub_http__manage_connection(args: { include_details?: boolean; user_id?: string; }): Promise<any>; — Performs a health check on the AgentHub connection system.


- function agenthub_http__manage_context(args: { action: string; level?: "global" | "project" | "branch" | "task"; context_id?: string; data?: string; delegate_to?: string; delegate_data?: string; delegation_reason?: string; category?: string; importance?: "low" | "medium" | "high" | "critical"; agent?: string; content?: string; project_id?: string; git_branch_id?: string; include_inherited?: string; propagate_changes?: string; force_refresh?: string; filters?: string; user_id?: string; }): Promise<any>; — Handles hierarchical context operations with inheritance across AgentHub levels.


- function agenthub_http__manage_git_branch(args: { action: string; project_id?: string; git_branch_id?: string; git_branch_name?: string; git_branch_description?: string; agent_id?: string; user_id?: string; }): Promise<any>; — Manages Git branch lifecycle and agent assignments within AgentHub.


- function agenthub_http__manage_project(args: { action: string; project_id?: string; name?: string; description?: string; force?: string; user_id?: string; }): Promise<any>; — Performs project-level operations such as creation, updates, and health checks in AgentHub.


- function agenthub_http__manage_subtask(args: { action: string; task_id?: string; subtask_id?: string; title?: string; description?: string; status?: string; priority?: string; assignees?: string; progress_notes?: string; progress_percentage?: number; blockers?: string; challenges_overcome?: string; completion_summary?: string; completion_quality?: string; deliverables?: string; impact_on_parent?: string; insights_found?: string; next_recommendations?: string; skills_learned?: string; testing_notes?: string; user_id?: string; }): Promise<any>; — Manages creation, updates, and completion of subtasks in AgentHub.


- function agenthub_http__manage_task(args: { action: string; git_branch_id?: string; title?: string; description?: string; status?: string; priority?: string; details?: string; estimated_effort?: string; assignees?: string; labels?: string; due_date?: string; dependencies?: string; task_id?: string; include_context?: boolean; completion_summary?: string; testing_notes?: string; limit?: number; offset?: number; query?: string; dependency_id?: string; context?: string; planning_context?: string; ai_requirements?: string; auto_create_tasks?: boolean; enable_ai_breakdown?: boolean; enable_auto_subtasks?: boolean; enable_smart_assignment?: boolean; analyze_complexity?: boolean; identify_risks?: boolean; suggest_optimizations?: boolean; force_full_generation?: boolean; user_id?: string; tag?: string; sort_by?: string; sort_order?: string; available_agents?: string; requirements?: string; }): Promise<any>; — Manages task lifecycles, AI planning, and dependencies within AgentHub.


- function agenthub_http__revoke_token(args: { token: string; }): Promise<any>; — Revokes an authentication token in the AgentHub system.


- function agenthub_http__validate_token(args: { token: string; }): Promise<any>; — Validates an authentication token and returns associated user information.


- function browsermcp__browser_click(args: { element: string; ref: string; }): Promise<any>; — Performs a click action on a web page element within the browser MCP.


- function browsermcp__browser_get_console_logs(): Promise<any>; — Retrieves console logs from the active browser MCP session.


- function browsermcp__browser_go_back(): Promise<any>; — Navigates the browser MCP session back one page in history.


- function browsermcp__browser_go_forward(): Promise<any>; — Moves the browser MCP session forward in history.


- function browsermcp__browser_hover(args: { element: string; ref: string; }): Promise<any>; — Hovers over a specified element within the browser MCP.


- function browsermcp__browser_navigate(args: { url: string; }): Promise<any>; — Navigates the browser MCP session to a specified URL.


- function browsermcp__browser_press_key(args: { key: string; }): Promise<any>; — Sends a key press event to the browser MCP session.


- function browsermcp__browser_screenshot(): Promise<any>; — Captures a screenshot of the current browser MCP page.


- function browsermcp__browser_select_option(args: { element: string; ref: string; values: string[]; }): Promise<any>; — Selects options in a dropdown within the browser MCP.


- function browsermcp__browser_snapshot(): Promise<any>; — Captures an accessibility snapshot of the current browser MCP page.


- function browsermcp__browser_type(args: { element: string; ref: string; text: string; submit: boolean; }): Promise<any>; — Types text into an editable element in the browser MCP session.


- function browsermcp__browser_wait(args: { time: number; }): Promise<any>; — Waits for a specified number of seconds in the browser MCP session.


- function sequentialthinking__sequentialthinking(args: { thought: string; thoughtNumber: number; totalThoughts: number; nextThoughtNeeded: boolean; isRevision?: boolean; revisesThought?: number; branchFromThought?: number; branchId?: string; needsMoreThoughts?: boolean; }): Promise<any>; — Facilitates reflective multi-step problem solving via sequential thinking.


- function shadcn-ui-server__get-block-docs(args: { block: string; }): Promise<any>; — Retrieves documentation for a specified shadcn UI block.


- function shadcn-ui-server__get-component-docs(args: { component: string; }): Promise<any>; — Retrieves documentation for a specified shadcn UI component.


- function shadcn-ui-server__install-blocks(args: { block: string; runtime?: string; }): Promise<any>; — Installs a shadcn UI block using the specified runtime.


- function shadcn-ui-server__install-component(args: { component: string; runtime?: string; }): Promise<any>; — Installs a shadcn UI component using the specified runtime.


- function shadcn-ui-server__list-blocks(): Promise<any>; — Lists all available shadcn UI blocks.


- function shadcn-ui-server__list-components(): Promise<any>; — Lists all available shadcn UI components.
