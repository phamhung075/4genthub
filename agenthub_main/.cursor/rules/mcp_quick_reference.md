# agenthub Quick Reference Schema

## 📚 Documentation Navigation
- **Main Rules**: [agenthub.md](./agenthub.md) - Complete autonomous operation rules
- **Quick Reference**: This document - Commands, schemas, and patterns
- **Validation**: [ai_validation_scenarios.md](./ai_validation_scenarios.md) - Self-testing scenarios

---

## 🚀 Essential Command Patterns

### Session Startup (Every Time)
```python
# 1. Establish your seat (rig whoami --json)
call_seat(room="<room>", seat="<orchestrator-seat>")

# 2. Health check
manage_connection(action="health_check")

# 3. Find work
next_task = manage_task(action="next", git_branch_id=branch_id, include_context=True)

# 4. Resolve the specialist seat
call_seat(room="<room>", seat="<specialist-seat>")
```

### Context Resolution Pattern
```python
# Get full inherited context
context = manage_context(
    action="resolve",
    level="task",
    context_id=task_id
)

# Update with insights
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={"insights": ["discovery"]},
    propagate_changes=True
)
```

### Task Lifecycle Pattern
```python
# 1. Start work
manage_task(action="update", task_id=task_id, status="in_progress")

# 2. Break down complex work
manage_subtask(action="create", task_id=task_id, title="Component A")

# 3. Report progress
manage_subtask(action="update", subtask_id=subtask_id, progress_percentage=50)

# 4. Complete with summary
manage_task(action="complete", task_id=task_id,
           completion_summary="Detailed description of what was accomplished")
```

## 🎭 Agent Role Quick Reference

| Work Type | Required Agent | When to Use |
|-----------|---------------|-------------|
| Planning | `@task_planning_agent` | Breaking down requirements, creating roadmaps |
| Coding | `@coding_agent` | Implementation, API development, algorithms |
| Debugging | `@debugger_agent` | Investigating bugs, troubleshooting issues |
| Testing | `@test_orchestrator_agent` | Creating tests, QA, validation |
| UI Design | `@ui_designer_agent` | Interface design, UX patterns |
| Security | `@security_auditor_agent` | Security review, vulnerability assessment |
| DevOps | `@devops_agent` | Infrastructure, deployment, CI/CD |
| Documentation | `@documentation_agent` | Writing ai_docs, API documentation |
| Research | `@deep_research_agent` | Technology analysis, requirements gathering |
| Complex Coordination | `master-orchestrator-agent` | Multi-step workflows, agent coordination |

## 📊 MCP Tool Schema Reference

### manage_task
```python
# Get next work
manage_task(action="next", git_branch_id=branch_id, include_context=True)

# Create new task
manage_task(action="create", git_branch_id=branch_id, title="Task Title",
           description="Detailed description", priority="high")

# Update progress
manage_task(action="update", task_id=task_id, status="in_progress",
           details="Current progress")

# Complete task
manage_task(action="complete", task_id=task_id,
           completion_summary="What was accomplished",
           testing_notes="Tests performed")
```

### manage_subtask
```python
# Create subtask
manage_subtask(action="create", task_id=task_id, title="Subtask Title",
              description="What needs to be done")

# Update progress
manage_subtask(action="update", task_id=task_id, subtask_id=subtask_id,
              progress_percentage=75, progress_notes="Almost complete")

# Complete subtask
manage_subtask(action="complete", task_id=task_id, subtask_id=subtask_id,
              completion_summary="What was accomplished")
```

### manage_context
```python
# Resolve full context
manage_context(action="resolve", level="task", context_id=task_id)

# Update context
manage_context(action="update", level="task", context_id=task_id,
                           data={"key": "value"}, propagate_changes=True)

# Delegate insights upward
manage_context(action="delegate", level="task", context_id=task_id,
                           delegate_to="project", delegate_data={"pattern": "reusable"})

# System health
manage_context(action="get_health")
```

### manage_project
```python
# List projects
manage_project(action="list")

# Create project
manage_project(action="create", name="Project Name", description="Purpose")

# Project health check
manage_project(action="project_health_check", project_id=project_id)
```

### manage_git_branch (Task Trees)
```python
# List branches in project
manage_git_branch(action="list", project_id=project_id)

# Create new task tree
manage_git_branch(action="create", project_id=project_id,
                 git_branch_name="feature-auth",
                 git_branch_description="Authentication system")
```

### manage_agent
```python
# List agents
manage_agent(action="list", project_id=project_id)

# Register as agent
manage_agent(action="register", project_id=project_id, name="Claude_Assistant")

# Assign to branch
manage_agent(action="assign", project_id=project_id, agent_id=agent_id,
            git_branch_id=branch_id)
```

### call_seat
```python
# Resolve a seat from the seat model
call_seat(room="<room>", seat="<dev-seat>")
call_seat(room="<room>", seat="<debugger-seat>")
call_seat(room="<room>", seat="<test-seat>")
```

## 🏗️ Context Hierarchy Schema

```
Global Context (Singleton)
├── id: "global_singleton"
├── data: {
│   ├── coding_standards: {...}
│   ├── security_policies: {...}
│   └── workflow_templates: {...}
│   }
└── inheritance: none

Project Context
├── id: project_id
├── data: {
│   ├── project_goals: {...}
│   ├── team_preferences: {...}
│   └── architecture_decisions: {...}
│   }
└── inheritance: Global

Task Context
├── id: task_id
├── data: {
│   ├── progress_tracking: {...}
│   ├── completion_notes: {...}
│   └── agent_insights: {...}
│   }
└── inheritance: Project + Global
```

## 🔄 Workflow Decision Tree

```
Start Session
    ↓
Switch to master-orchestrator-agent
    ↓
Health Check
    ↓
List Projects → Select/Create Project
    ↓
List Branches → Select/Create Branch
    ↓
Get Next Task (with context)
    ↓
Determine Task Type
    ↓
Switch to Specialist Agent
    ↓
Resolve Hierarchical Context
    ↓
Update Task Status (in_progress)
    ↓
Break into Subtasks (if complex)
    ↓
Execute Work
    ↓
Update Progress Regularly
    ↓
Complete with Summary
    ↓
Delegate Insights (if reusable)
    ↓
Get Next Task OR Switch Projects
```

## ⚠️ Critical Checkpoints

### Before Any Work:
- [ ] Am I in the right agent role?
- [ ] Have I resolved full hierarchical context?
- [ ] Is task status updated to in_progress?

### During Work:
- [ ] Am I updating progress regularly?
- [ ] Am I documenting insights and discoveries?
- [ ] Do I need to switch agent roles for different subtasks?

### After Work:
- [ ] Is completion summary detailed and specific?
- [ ] Should I delegate insights to higher levels?
- [ ] Have I updated context with learnings?

## 🎯 Success Patterns

### High-Quality Task Completion:
```python
manage_task(action="complete", task_id=task_id,
           completion_summary="""
           Implemented JWT authentication system with the following components:
           - User login endpoint with email/password validation
           - JWT token generation with 1-hour expiry
           - Refresh token mechanism for session persistence
           - Password hashing with bcrypt
           - Session management with Redis cache

           Architecture decisions:
           - Used industry-standard JWT library
           - Implemented proper error handling for invalid credentials
           - Added rate limiting to prevent brute force attacks
           """,
           testing_notes="""
           Created comprehensive test suite:
           - Unit tests for authentication service (95% coverage)
           - Integration tests for login/logout flow
           - Security tests for token validation
           - Performance tests for concurrent logins
           All tests passing with proper edge case coverage.
           """)
```

### Effective Context Delegation:
```python
manage_context(
    action="delegate",
    level="task",
    context_id=task_id,
    delegate_to="project",
    delegate_data={
        "reusable_pattern": "jwt_authentication_implementation",
        "code_template": jwt_service_code,
        "configuration": jwt_config,
        "security_checklist": security_requirements,
        "testing_strategy": test_approach
    },
    delegation_reason="JWT authentication pattern reusable for other services requiring auth"
)
```

This quick reference provides the essential schemas and patterns for effective autonomous operation within the agenthub system.

## 🔗 Related Documentation
- **Complete Rules**: [agenthub.md](./agenthub.md) - Full autonomous operation guidelines
- **Self-Testing**: [ai_validation_scenarios.md](./ai_validation_scenarios.md) - Virtual scenarios for validation
