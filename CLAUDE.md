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
1. Call `mcp__dhafnck_mcp_http__call_agent(name_agent="@agent_name")`
2. Extract `yaml_content` (rules, contexts, metadata) and `capabilities`
3. Follow agent's specifications as source of truth
4. Use only allowed tools and respect permissions

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
