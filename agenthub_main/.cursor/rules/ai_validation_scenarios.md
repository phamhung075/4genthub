# AI Agent Validation Scenarios for agenthub

## 📚 Documentation Navigation
- **Main Rules**: [agenthub.md](./agenthub.md) - Complete autonomous operation rules
- **Quick Reference**: [mcp_quick_reference.md](./mcp_quick_reference.md) - Commands and schemas
- **Validation**: This document - Self-testing and scenario validation

---

## 🧪 Virtual Testing Protocol

Before taking actions in the real system, AI agents should mentally simulate these scenarios to validate their understanding of the rules and patterns.

## 📝 Scenario 1: New Feature Implementation

### Context:
User requests: "Add a user profile editing feature to our e-commerce app"

### Expected AI Agent Response Pattern:

#### Phase 1: Initial Setup ✓
```python
# 1. MANDATORY: Switch to orchestrator first
call_agent(name_agent="master-orchestrator-agent")

# 2. System health check
health = manage_connection(action="health_check")

# 3. Find the right project
projects = manage_project(action="list")
# Select e-commerce project based on context

# 4. Check task trees
branches = manage_git_branch(action="list", project_id=ecommerce_project_id)
# Choose or create appropriate branch for user features
```

#### Phase 2: Planning ✓
```python
# 5. Switch to planning specialist
call_agent(name_agent="@task_planning_agent")

# 6. Get full context
context = manage_context(action="resolve", level="project", 
                                     context_id=ecommerce_project_id)

# 7. Create main task
task = manage_task(action="create", git_branch_id=user_features_branch_id,
                  title="Implement user profile editing feature",
                  description="Allow users to edit their profile information including name, email, preferences",
                  priority="high")

# 8. Break into subtasks
subtasks = [
    manage_subtask(action="create", task_id=task_id, 
                  title="Design profile editing UI"),
    manage_subtask(action="create", task_id=task_id,
                  title="Implement backend profile update API"),
    manage_subtask(action="create", task_id=task_id,
                  title="Add client-side validation"),
    manage_subtask(action="create", task_id=task_id,
                  title="Create comprehensive tests")
]
```

#### Phase 3: Implementation ✓
```python
# 9. For each subtask, switch to appropriate specialist
# UI Design:
call_agent(name_agent="@ui_designer_agent")
manage_subtask(action="update", subtask_id=ui_subtask_id, status="in_progress")
# ... design work ...
manage_subtask(action="complete", subtask_id=ui_subtask_id,
              completion_summary="Created responsive profile editing form with modern UI")

# Backend API:
call_agent(name_agent="@coding_agent") 
manage_subtask(action="update", subtask_id=api_subtask_id, status="in_progress")
# ... implementation work ...
manage_subtask(action="complete", subtask_id=api_subtask_id,
              completion_summary="Implemented PUT /api/user/profile endpoint with validation")

# Testing:
call_agent(name_agent="@test_orchestrator_agent")
# ... testing work ...
```

#### Phase 4: Context Updates and Delegation ✓
```python
# 10. Update context with insights
manage_context(action="update", level="task", context_id=task_id,
                           data={
                               "architecture_decisions": ["REST API pattern", "Client-side validation"],
                               "reusable_components": ["ProfileForm", "ValidationUtils"],
                               "performance_notes": ["Optimized for mobile", "Lazy loading"]
                           })

# 11. Delegate reusable patterns
manage_context(action="delegate", level="task", context_id=task_id,
                           delegate_to="project",
                           delegate_data={
                               "ui_pattern": "responsive_form_design",
                               "validation_strategy": "client_server_validation",
                               "api_pattern": "restful_user_operations"
                           },
                           delegation_reason="Patterns applicable to other user features")
```

### ❌ Common Violations to Avoid:
- Starting work without switching to master-orchestrator-agent first
- Not resolving hierarchical context before planning
- Skipping agent role switches for different work types
- Weak completion summaries ("Fixed profile editing")
- Not delegating insights for future reuse

---

## 📝 Scenario 2: Multi-Project Context Switching

### Context:
AI agent has tasks in 3 projects:
1. E-commerce app (critical bug)
2. Marketing website (new feature)
3. Internal tools (routine maintenance)

### Expected AI Agent Decision Process:

#### Phase 1: Assessment ✓
```python
# 1. Start with orchestrator
call_agent(name_agent="master-orchestrator-agent")

# 2. Get overview of all projects
projects = manage_project(action="list")

# 3. For each project, assess priority work
project_priorities = {}
for project in projects:
    branches = manage_git_branch(action="list", project_id=project.id)
    for branch in branches:
        next_task = manage_task(action="next", git_branch_id=branch.id, include_context=True)
        if next_task:
            project_priorities[project.name] = {
                "priority": next_task.priority,
                "urgency": next_task.workflow_guidance.urgency,
                "estimated_effort": next_task.estimated_effort
            }
```

#### Phase 2: Intelligent Prioritization ✓
```python
# 4. Apply priority rules:
# - CRITICAL/URGENT: E-commerce bug (affects customers)
# - HIGH: Marketing feature (business impact)  
# - MEDIUM: Internal tools (operational efficiency)

# 5. Start with highest impact
call_agent(name_agent="@debugger_agent")  # For the critical bug
# Work on e-commerce bug...

# 6. After critical work, assess remaining priorities
# Context switch cost vs. business value
```

#### Phase 3: Context Preservation ✓
```python
# 7. When switching projects, preserve context
current_project_context = manage_context(
    action="resolve", level="project", context_id=current_project_id
)

# 8. Save progress state
manage_task(action="update", task_id=current_task_id, 
           details="Switching to critical issue. Current progress: 60% complete, will resume after.")

# 9. Switch to new project with fresh context
new_context = manage_context(
    action="resolve", level="project", context_id=new_project_id
)
```

### ✅ Success Criteria:
- Priority-based project selection
- Proper context preservation during switches
- Minimal context switching overhead
- Clear progress documentation

---

## 📝 Scenario 3: Complex Debugging Session

### Context:
Production system has a critical bug affecting user authentication across multiple services.

### Expected AI Agent Response:

#### Phase 1: Emergency Response ✓
```python
# 1. IMMEDIATE: Switch to debugger
call_agent(name_agent="@debugger_agent")

# 2. Update task status
manage_task(action="update", task_id=auth_bug_task_id, status="blocked",
           details="CRITICAL: Authentication failing across multiple services. Users cannot log in.")

# 3. Create debugging context
manage_context(action="add_insight", task_id=auth_bug_task_id,
              content="Initial symptoms: 401 errors on login, JWT validation failing",
              category="debugging", importance="critical")
```

#### Phase 2: Systematic Investigation ✓
```python
# 4. Resolve full context for background
context = manage_context(action="resolve", level="task", context_id=auth_bug_task_id)

# 5. Document investigation process
manage_context(action="add_progress", task_id=auth_bug_task_id,
              content="Investigating auth service logs, checking JWT secret rotation")

# 6. Break down debugging steps
debug_subtasks = [
    manage_subtask(action="create", task_id=auth_bug_task_id,
                  title="Check auth service health and logs"),
    manage_subtask(action="create", task_id=auth_bug_task_id, 
                  title="Verify JWT secret configuration"),
    manage_subtask(action="create", task_id=auth_bug_task_id,
                  title="Test token generation and validation")
]
```

#### Phase 3: Root Cause and Resolution ✓
```python
# 7. Document findings
manage_context(action="add_insight", task_id=auth_bug_task_id,
              content="ROOT CAUSE: JWT secret was rotated but not updated in validation service",
              category="root_cause", importance="critical")

# 8. Fix and verify
call_agent(name_agent="@coding_agent")  # For implementing the fix
# ... fix implementation ...

# 9. Test thoroughly
call_agent(name_agent="@test_orchestrator_agent")
# ... testing ...

# 10. Complete with detailed post-mortem
manage_task(action="complete", task_id=auth_bug_task_id,
           completion_summary="""
           CRITICAL BUG RESOLVED: Authentication service restored
           
           Root Cause: JWT secret rotation completed in auth service but validation
           service still using old secret, causing all token validations to fail.
           
           Fix Applied:
           - Updated JWT_SECRET environment variable in validation service
           - Implemented secret rotation coordination mechanism
           - Added monitoring alerts for JWT validation failures
           
           Prevention Measures:
           - Created deployment checklist for secret rotations
           - Added automated secret sync verification
           - Implemented circuit breaker for auth service failures
           """,
           testing_notes="""
           Verification completed:
           - Manual login test: PASS
           - Automated auth flow test: PASS  
           - Load test with 1000 concurrent logins: PASS
           - Verified across all dependent services: PASS
           """)
```

#### Phase 4: Knowledge Preservation ✓
```python
# 11. Delegate lessons learned
manage_context(action="delegate", level="task", context_id=auth_bug_task_id,
                           delegate_to="global",
                           delegate_data={
                               "incident_type": "secret_rotation_coordination_failure",
                               "prevention_checklist": rotation_checklist,
                               "monitoring_requirements": monitoring_alerts,
                               "deployment_process": updated_process
                           },
                           delegation_reason="Critical pattern to prevent organization-wide")
```

### ✅ Success Criteria:
- Immediate agent role switch to @debugger_agent
- Systematic investigation with documented steps
- Root cause analysis with prevention measures
- Knowledge delegation for future prevention

---

## 🎯 Self-Validation Checklist

### Before Starting Any Work:
```
□ Did I switch to master-orchestrator-agent first?
□ Did I check system health?
□ Did I resolve hierarchical context?
□ Am I in the right specialist agent role for this work type?
□ Have I updated task status to "in_progress"?
```

### During Work:
```
□ Am I updating progress regularly (every 25% completion)?
□ Am I documenting insights and discoveries?
□ Do I switch agent roles when work type changes?
□ Am I breaking complex work into manageable subtasks?
□ Am I maintaining proper project context boundaries?
```

### After Completing Work:
```
□ Is my completion summary detailed and specific?
□ Did I include testing notes with what was verified?
□ Should I delegate any insights or patterns upward?
□ Have I updated context with learnings for future work?
□ Did I properly hand off to the next agent if needed?
```

### Multi-Project Operations:
```
□ Am I prioritizing work based on business impact and urgency?
□ Am I minimizing context switching overhead?
□ Am I preserving project contexts properly during switches?
□ Are my actions consistent with global and project-specific rules?
□ Am I coordinating effectively with other agents?
```

## 🏆 Advanced Validation Scenarios

### Scenario A: Agent Coordination Conflict
**Situation**: Two agents trying to work on the same task
**Expected Response**: Proper agent coordination through assignment system

### Scenario B: Context Inheritance Issues
**Situation**: Task context seems inconsistent with project rules
**Expected Response**: Validate inheritance chain, fix conflicts

### Scenario C: Cross-Project Pattern Discovery
**Situation**: Solution in Project A applicable to Project B
**Expected Response**: Proper delegation to global level for reuse

### Scenario D: System Performance Degradation
**Situation**: Operations becoming slow, cache misses increasing
**Expected Response**: Health check, cache cleanup, system optimization

## 💡 Mental Model Validation

**Correct Mental Model:**
```
I am an autonomous AI agent operating within a sophisticated multi-project 
orchestration platform. I must:
- Always work through specialized agent roles
- Maintain hierarchical context awareness
- Contribute to organizational learning through delegation
- Coordinate effectively with other agents
- Think strategically about multi-project priorities
```

**Incorrect Mental Model:**
```
I am using a simple task tracker. I can:
- Work directly without role switching
- Focus only on individual tasks
- Keep discoveries to myself
- Work in isolation
- Handle requests linearly without strategic thinking
```

By mentally running through these scenarios and validating against the checklists, AI agents can ensure they understand and will correctly apply the agenthub autonomous operation rules.

## 🔗 Related Documentation
- **Main Operation Rules**: [agenthub.md](./agenthub.md) - Complete autonomous operation guidelines
- **Command Reference**: [mcp_quick_reference.md](./mcp_quick_reference.md) - Quick lookup for commands and patterns