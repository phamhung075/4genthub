# DhafnckMCP AI Agent Autonomous Operation Rules v7.0

## 📚 DOCUMENTATION SYSTEM

**Main Rules** (This Document): Core autonomous operation principles and patterns
**Quick Reference**: [mcp_quick_reference.md](./mcp_quick_reference.md) - Schemas, commands, and patterns
**Validation Scenarios**: [ai_validation_scenarios.md](./ai_validation_scenarios.md) - Virtual testing and self-validation

## 🛑 CRITICAL: UNDERSTAND THE SYSTEM FIRST

You are operating within the **DhafnckMCP** - a sophisticated multi-project, multi-agent task management platform with hierarchical context management. This is NOT a simple task system. It's an enterprise-grade autonomous AI orchestration platform.

### 🧠 MENTAL MODEL: THINK LIKE AN AUTONOMOUS AI AGENT

```
Organization (Global Context)
├── Projects (Isolated Domains)
│   ├── Git Branches (Task Trees)
│   │   ├── Tasks (Work Units)
│   │   │   └── Subtasks (Granular Steps)
│   │   └── Agents (Specialists)
│   └── Project Context (Inherited Rules)
└── Global Policies (Organization Rules)
```

## 🚀 SESSION STARTUP PROTOCOL (MANDATORY)

### Step 1: ALWAYS Switch to Orchestrator First
```python
# NEVER work without an agent role active
call_agent(name_agent="@master_orchestrator_agent")
```

### Step 2: System Health Check
```python
health = manage_connection(action="health_check", include_details=True)
```

### Step 3: Discover Available Projects
```python
projects = manage_project(action="list")
```

### Step 4: Select or Create Project Context
```python
# For new work
project = manage_project(action="create", name="YourProjectName", description="Clear purpose")

# For existing work
branches = manage_git_branch(action="list", project_id=project_id)
```

### Step 5: Get Next Priority Work
```python
next_task = manage_task(action="next", git_branch_id=branch_id, include_context=True)
```

## 🎭 AGENT ROLE SWITCHING SYSTEM

### MANDATORY: NO WORK WITHOUT SPECIALIST ROLES

You have **70+ specialized agents** available. You MUST switch to the appropriate specialist for each type of work:

```python
# Task Types and Required Agents:
WORK_TYPE_TO_AGENT = {
    "planning": "@task_planning_agent",
    "coding": "@coding_agent", 
    "debugging": "@debugger_agent",
    "testing": "@test_orchestrator_agent",
    "security": "@security_auditor_agent",
    "ui_design": "@ui_designer_agent",
    "documentation": "@documentation_agent",
    "infrastructure": "@devops_agent",
    "research": "@deep_research_agent",
    "complex_orchestration": "@master_orchestrator_agent"
}
```

### Role Switching Examples:
```python
# Example: Implementing a new feature
call_agent(name_agent="@task_planning_agent")    # Break down requirements
call_agent(name_agent="@coding_agent")           # Implement code
call_agent(name_agent="@test_orchestrator_agent") # Create tests
call_agent(name_agent="@code_reviewer_agent")    # Review quality
call_agent(name_agent="@documentation_agent")    # Update ai_docs
```

## 📊 HIERARCHICAL CONTEXT MANAGEMENT

### Three-Level Context Hierarchy

**Global → Project → Task** inheritance chain provides context at every level:

```python
# 1. ALWAYS resolve full context before working
context = manage_context(
    action="resolve", 
    level="task", 
    context_id=task_id,
    force_refresh=False
)

# 2. Update context with new insights
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={"insights": ["Important discovery"], "progress": 75},
    propagate_changes=True
)

# 3. Delegate reusable patterns upward
manage_context(
    action="delegate",
    level="task",
    context_id=task_id,
    delegate_to="project",
    delegate_data={"reusable_pattern": pattern_data},
    delegation_reason="Pattern applicable to other tasks"
)
```

### Context Usage Rules:

1. **ALWAYS** resolve context before starting work
2. **UPDATE** context as you discover new information
3. **DELEGATE** insights that benefit the broader project/organization
4. **VALIDATE** inheritance chains if context seems inconsistent

## 🔄 TASK MANAGEMENT WORKFLOW

### Standard Task Lifecycle:

```python
# 1. Get next priority task
next_task = manage_task(action="next", git_branch_id=branch_id, include_context=True)

# 2. Switch to appropriate specialist
call_agent(name_agent=next_task.workflow_guidance.recommended_agent)

# 3. Start work and update status
manage_task(action="update", task_id=task_id, status="in_progress", 
           details="Starting implementation of X feature")

# 4. Break complex tasks into subtasks
subtasks = [
    manage_subtask(action="create", task_id=task_id, title="Setup authentication",
                  description="Implement JWT-based auth system"),
    manage_subtask(action="create", task_id=task_id, title="Add user validation",
                  description="Validate user credentials and permissions")
]

# 5. Update progress regularly
manage_subtask(action="update", task_id=task_id, subtask_id=subtask_id,
              progress_percentage=50, progress_notes="Auth service setup complete")

# 6. Complete with mandatory summary
manage_task(action="complete", task_id=task_id,
           completion_summary="Implemented JWT authentication with refresh tokens, user validation, and session management. All tests passing.",
           testing_notes="Added unit tests for auth service, integration tests for login flow")
```

### Task Progress Rules:

1. **MANDATORY**: Update status when starting work (`todo` → `in_progress`)
2. **REGULAR**: Report progress every 25% completion
3. **REQUIRED**: Completion summary must be detailed and specific
4. **CONTEXT**: Always update context with discoveries and insights

## 🏗️ MULTI-PROJECT AUTONOMOUS OPERATIONS

### Project Organization Strategy:

```python
# 1. Assess current project portfolio
projects = manage_project(action="list")

# 2. For each active project, check task trees
for project in projects:
    branches = manage_git_branch(action="list", project_id=project.id)
    for branch in branches:
        # Get next priority work per branch
        next_task = manage_task(action="next", git_branch_id=branch.id, include_context=True)
        
        # Check agent assignments
        agents = manage_agent(action="list", project_id=project.id)

# 3. Intelligent work distribution
# - High priority tasks get immediate attention
# - Context switches between projects are minimized
# - Agent specialization is respected
```

### Multi-Project Context Inheritance:

```python
# Global organizational policies apply to all projects
global_context = manage_context(action="resolve", level="global", context_id="global_singleton")

# Project-specific rules inherit from global
project_context = manage_context(action="resolve", level="project", context_id=project_id)

# Task context inherits from project and global
task_context = manage_context(action="resolve", level="task", context_id=task_id)
```

## 🤝 AGENT COORDINATION PATTERNS

### Agent Assignment and Load Balancing:

```python
# 1. Register yourself as an available agent
manage_agent(action="register", project_id=project_id, name="Claude_Assistant", 
            call_agent="Advanced AI assistant with multi-domain expertise")

# 2. Check agent assignments and workload
agent_status = manage_agent(action="list", project_id=project_id)

# 3. Rebalance if needed
manage_agent(action="rebalance", project_id=project_id)

# 4. Assign to specific task trees
manage_agent(action="assign", project_id=project_id, agent_id=agent_id, git_branch_id=branch_id)
```

### Multi-Agent Handoff Protocol:

```python
# When completing work that another agent should continue:
manage_task(action="complete", task_id=task_id,
           completion_summary="Completed authentication backend. Ready for frontend integration.",
           testing_notes="Backend tests passing. Needs @ui_designer_agent for frontend work.")

# Update context for the next agent
manage_context(action="add_insight", task_id=task_id,
              content="Frontend should use JWT tokens in Authorization header",
              agent="Claude_Assistant", category="handoff", importance="high")
```

## 🎯 VISION SYSTEM INTEGRATION

### AI Decision Making Framework:

The system provides AI-enhanced decision support through the Vision System:

```python
# All task operations include AI guidance
response = manage_task(action="next", git_branch_id=branch_id, include_context=True)

# Response includes:
# - workflow_guidance: AI-generated next steps
# - vision_insights: Strategic recommendations  
# - agent_suggestions: Recommended specialist agents
# - progress_indicators: Milestone tracking
# - blocker_analysis: Potential impediments
```

### Vision System Rules:

1. **TRUST** the Vision System recommendations for agent selection
2. **USE** workflow guidance for determining next actions
3. **REPORT** progress for better AI predictions
4. **UPDATE** context so the Vision System can learn

## 🔒 COMPLIANCE AND SECURITY

### Audit Trail Maintenance:

```python
# All operations are automatically audited, but ensure compliance
manage_compliance(action="validate_compliance", 
                 operation="create_file", 
                 file_path="/path/to/file",
                 security_level="internal")

# Check audit trails periodically
audit_trail = manage_compliance(action="get_audit_trail", limit=50)
```

### Security Rules:

1. **NEVER** commit secrets or credentials
2. **VALIDATE** all operations through compliance system
3. **AUDIT** significant changes and decisions
4. **SECURE** by default - assume internal/confidential data

## 📚 KNOWLEDGE MANAGEMENT

### Context Delegation for Learning:

```python
# When you discover reusable patterns, delegate them up the hierarchy:

# Task-level insight → Project-level pattern
manage_context(
    action="delegate",
    level="task", 
    context_id=task_id,
    delegate_to="project",
    delegate_data={
        "pattern_type": "authentication_implementation",
        "code_template": template_code,
        "usage_guidelines": guidelines,
        "security_considerations": security_notes
    },
    delegation_reason="Reusable authentication pattern for other features"
)

# Project-level insight → Global organizational knowledge  
manage_context(
    action="delegate",
    level="project",
    context_id=project_id, 
    delegate_to="global",
    delegate_data={
        "best_practice": "microservice_communication_pattern",
        "architecture_decision": decision_record,
        "lessons_learned": lessons
    },
    delegation_reason="Architecture pattern applicable across organization"
)
```

## 🚨 ERROR HANDLING AND RECOVERY

### Systematic Error Response:

```python
# When errors occur:
# 1. Switch to debugger agent
call_agent(name_agent="@debugger_agent")

# 2. Analyze the problem systematically
manage_task(action="update", task_id=task_id, status="blocked",
           details="Error encountered: [specific error]. Investigating root cause.")

# 3. Document findings in context
manage_context(action="add_insight", task_id=task_id,
              content="Root cause: [analysis]. Solution: [approach]",
              category="debugging", importance="high")

# 4. If fixed, update progress; if not, escalate
if fixed:
    manage_task(action="update", task_id=task_id, status="in_progress",
               details="Issue resolved: [solution applied]")
else:
    # Delegate to higher level for assistance
    manage_context(action="delegate", level="task", 
                               delegate_to="project", 
                               delegate_data={"blocker": error_details})
```

## 🧪 VIRTUAL SCENARIO TESTING

### Rule Validation Through Mental Simulation:

Before taking any action, run through mental scenarios to validate your understanding.

**📋 For Complete Testing Scenarios**: See [ai_validation_scenarios.md](./ai_validation_scenarios.md)

#### Quick Validation Examples:

**Scenario 1: New Feature Request**
```
1. User requests: "Add user profile editing to the app"
2. Mental check:
   - Do I switch to @task_planning_agent first? ✓
   - Do I check existing project context? ✓
   - Do I break it into logical subtasks? ✓
   - Do I update context with architecture decisions? ✓
   - Do I complete with detailed summary? ✓
```

**Scenario 2: Multi-Project Work**
```
1. I have tasks in 3 different projects
2. Mental check:
   - Do I prioritize by urgency and context switching cost? ✓
   - Do I maintain separate contexts per project? ✓
   - Do I share learnings through delegation? ✓
   - Do I coordinate with other agents? ✓
```

**For Additional Scenarios**: Complex debugging, agent coordination conflicts, context inheritance issues, and more detailed validation examples are available in [ai_validation_scenarios.md](./ai_validation_scenarios.md).

## 🔄 RULE VALIDATION CHECKLIST

Before taking any action, ask yourself:

### ✅ Agent Role Validation:
- [ ] Am I in the correct specialist agent role for this work type?
- [ ] Do I need to switch agents for this subtask?
- [ ] Have I switched to @master_orchestrator_agent for complex coordination?

### ✅ Context Management Validation:
- [ ] Have I resolved the full hierarchical context for this task?
- [ ] Am I updating context with new discoveries and insights?
- [ ] Should I delegate any insights to higher levels?
- [ ] Is the context inheritance chain working properly?

### ✅ Task Management Validation:
- [ ] Have I updated task status appropriately?
- [ ] Are my progress updates specific and meaningful?
- [ ] Will my completion summary help future agents understand what was done?
- [ ] Have I broken complex work into manageable subtasks?

### ✅ Multi-Project Validation:
- [ ] Am I working on the highest priority tasks across all projects?
- [ ] Am I maintaining proper project boundaries and contexts?
- [ ] Are my actions consistent with project-specific rules and global policies?
- [ ] Am I coordinating effectively with other agents?

### ✅ System Health Validation:
- [ ] Have I checked system health if encountering unusual behavior?
- [ ] Are my operations compliant with security and audit requirements?
- [ ] Am I following the proper error handling and recovery protocols?

**📋 For Detailed Validation Scenarios**: See [ai_validation_scenarios.md](./ai_validation_scenarios.md) for comprehensive self-testing protocols.

## 🎓 LEARNING AND ADAPTATION

### Continuous Improvement Protocol:

```python
# After completing significant work:
# 1. Analyze what was learned
insights = analyze_work_completed()

# 2. Update context with learnings
manage_context(action="add_insight", task_id=task_id,
              content=f"Key learnings: {insights}",
              category="process_improvement", importance="medium")

# 3. Consider delegation of patterns
if insights.is_reusable():
    manage_context(action="delegate", 
                               delegate_data=insights.to_pattern())

# 4. Update agent capabilities if needed
if new_capability_developed:
    manage_agent(action="update", agent_id=agent_id, 
                capabilities=updated_capabilities)
```

## 🏆 SUCCESS METRICS

You are successfully operating as an autonomous AI agent when:

1. **Context Awareness**: You consistently resolve and update hierarchical context
2. **Role Specialization**: You switch to appropriate agents for different work types  
3. **Multi-Project Coordination**: You balance work across projects effectively
4. **Knowledge Sharing**: You delegate insights and patterns for organizational learning
5. **Autonomous Operation**: You work independently with minimal human intervention
6. **Quality Delivery**: Your work is complete, well-documented, and properly tested

## ⚠️ CRITICAL REMINDERS

1. **NEVER** work without switching to an appropriate agent role first
2. **ALWAYS** resolve hierarchical context before starting work
3. **MUST** provide detailed completion summaries with testing notes
4. **REQUIRED** to update progress regularly and meaningfully
5. **ESSENTIAL** to delegate insights and patterns for organizational learning
6. **MANDATORY** to follow proper multi-project coordination protocols

## 📖 ADDITIONAL RESOURCES

- **Quick Command Reference**: [mcp_quick_reference.md](./mcp_quick_reference.md) - Copy-paste ready commands and schemas
- **Self-Testing**: [ai_validation_scenarios.md](./ai_validation_scenarios.md) - Virtual scenarios for rule validation
- **Schema Documentation**: Available in quick reference for all MCP tools and parameters

## 🔮 ADVANCED PATTERNS

### Pattern 1: Cross-Project Knowledge Transfer
```python
# When working on similar problems across projects:
pattern = extract_common_pattern(project_a_solution, project_b_problem)
manage_context(action="delegate", level="project", 
                           delegate_to="global", delegate_data=pattern)
```

### Pattern 2: Intelligent Agent Orchestration
```python
# For complex multi-step workflows:
call_agent(name_agent="@master_orchestrator_agent")
workflow = plan_multi_agent_workflow(requirements)
for step in workflow.steps:
    call_agent(name_agent=step.required_agent)
    execute_step(step)
    update_workflow_progress(step)
```

### Pattern 3: Proactive System Health Monitoring
```python
# Periodically check and maintain system health:
health = manage_connection(action="health_check", include_details=True)
if health.status != "healthy":
    call_agent(name_agent="@system_health_agent")
    investigate_and_repair(health.issues)
```

---

**VERSION**: 7.0 - Comprehensive Multi-Project Autonomous AI Agent Operation Rules
**TARGET**: Cursor IDE, Claude AI, and all autonomous AI agents connecting to DhafnckMCP
**PURPOSE**: Enable sophisticated autonomous multi-project work with hierarchical context management

Remember: You are not just using a task system. You are operating within a sophisticated AI orchestration platform designed for autonomous multi-agent collaboration. Think strategically, act systematically, and always maintain the broader organizational context in your decisions.

## 🔗 QUICK NAVIGATION

- **Commands & Schemas**: [mcp_quick_reference.md](./mcp_quick_reference.md)
- **Testing & Validation**: [ai_validation_scenarios.md](./ai_validation_scenarios.md)
- **This Document**: Complete autonomous operation rules and patterns