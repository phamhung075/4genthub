# Agent Bridge Usage Examples

This document provides practical examples of using the Claude Code & DhafnckMCP bridge agents.

## Example 1: Complex Project Orchestration

**User Request:** "I need to implement a new user authentication system with proper testing and documentation."

**Claude Code Response:**
I'll activate the uber-orchestrator bridge agent to coordinate this multi-phase project.

```python
# Connect to the orchestration system
mcp__dhafnck_mcp_http__call_agent(name_agent="master-orchestrator-agent")

# Check existing project context
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="project", 
    context_id=project_id,
    include_inherited=true
)

# Create master task for the authentication system
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Implement User Authentication System",
    description="JWT-based authentication with login, logout, session management, testing, and documentation",
    priority="high"
)

# Break down into coordinated subtasks
mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=main_task_id,
    title="Architecture Design - Authentication System"
)

mcp__dhafnck_mcp_http__manage_subtask(
    action="create", 
    task_id=main_task_id,
    title="Backend Implementation - JWT Service"
)

mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=main_task_id,
    title="Frontend Integration - Login/Logout UI"
)
```

The orchestrator will now coordinate with specialized agents for each phase.

## Example 2: Code Implementation with Task Tracking

**User Request:** "Implement the JWT authentication service."

**Claude Code Response:**
I'll use the coding-specialist bridge agent for this implementation work.

```python
# Connect to coding specialist
mcp__dhafnck_mcp_http__call_agent(name_agent="coding-agent")

# Check branch context for requirements
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id, 
    include_inherited=true
)

# Create task for this coding work
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Implement JWT Authentication Service",
    description="Create JWT service with token generation, validation, and refresh capabilities"
)
```

The coding agent will implement the service and update context with technical decisions.

## Example 3: Systematic Debugging

**User Request:** "The authentication system is throwing intermittent login failures."

**Claude Code Response:**
I'll activate the debugging-expert bridge agent to systematically investigate this issue.

```python
# Connect to debugging specialist
mcp__dhafnck_mcp_http__call_agent(name_agent="debugger-agent")

# Check context for system information
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id,
    include_inherited=true
)

# Create debugging task
mcp__dhafnck_mcp_http__manage_task(
    action="create", 
    git_branch_id=branch_id,
    title="Debug: Intermittent Authentication Failures",
    description="Systematic analysis of login failure patterns and root cause identification",
    priority="urgent"
)

# Document the debugging process
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "issue_symptoms": "Intermittent login failures",
        "reproduction_steps": "Steps to reproduce the issue",
        "initial_hypothesis": "Possible causes identified"
    }
)
```

The debugging agent will conduct systematic analysis and document findings.

## Example 4: Comprehensive Testing Strategy

**User Request:** "Set up comprehensive testing for the authentication system."

**Claude Code Response:**
I'll use the testing-orchestrator bridge agent to create a multi-layered testing approach.

```python
# Connect to testing orchestrator
mcp__dhafnck_mcp_http__call_agent(name_agent="test-orchestrator-agent")

# Assess current testing context
mcp__dhafnck_mcp_http__manage_context(
    action="resolve",
    level="branch",
    context_id=branch_id,
    include_inherited=true
)

# Create comprehensive testing task
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Comprehensive Testing Strategy - Authentication System",
    description="Multi-layer testing including unit, integration, security, and user acceptance tests"
)

# Break down into testing subtasks
mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=testing_task_id,
    title="Unit Tests - JWT Service"
)

mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=testing_task_id, 
    title="Integration Tests - Authentication Flow"
)

mcp__dhafnck_mcp_http__manage_subtask(
    action="create",
    task_id=testing_task_id,
    title="Security Testing - Authentication Vulnerabilities"
)
```

The testing orchestrator will coordinate multiple testing specialists.

## Example 5: Multi-Agent Coordination

**User Request:** "I need to fix a performance issue in the authentication system and add monitoring."

**Claude Code Response:**
I'll coordinate multiple bridge agents for this complex requirement.

```python
# Start with orchestrator for coordination
mcp__dhafnck_mcp_http__call_agent(name_agent="master-orchestrator-agent")

# Create master coordination task
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Authentication Performance Optimization & Monitoring",
    description="Identify and fix performance issues, add comprehensive monitoring"
)

# Phase 1: Performance debugging
mcp__dhafnck_mcp_http__call_agent(name_agent="performance-load-tester-agent")

# Phase 2: Implementation fixes
mcp__dhafnck_mcp_http__call_agent(name_agent="coding-agent")

# Phase 3: Monitoring setup
mcp__dhafnck_mcp_http__call_agent(name_agent="health-monitor-agent")

# Update context with coordination plan
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "coordination_plan": "3-phase approach: analyze, fix, monitor",
        "agents_involved": ["performance_load_tester", "coding-agent", "health_monitor"],
        "expected_timeline": "Performance analysis -> Implementation -> Monitoring setup"
    }
)
```

## Benefits Demonstrated

### 1. Seamless Integration
- Claude Code's natural language interface
- Your advanced agent system's capabilities
- Automatic task tracking and context management

### 2. Workflow Preservation
- Your existing task management continues working
- Context is preserved across sessions
- Multi-agent coordination remains intact

### 3. Enhanced Capabilities
- IDE integration with project orchestration
- Automatic agent selection based on request type
- Comprehensive documentation and tracking

### 4. Scalable Architecture
- Easy to add new bridge agents
- Supports your full 60+ agent ecosystem
- Maintains both system's unique strengths

## Usage Tips

1. **Let Claude Code choose** - The system will automatically select appropriate bridge agents
2. **Be specific** - Clear requests help with better agent selection
3. **Check context** - Bridge agents always check and update project context
4. **Track progress** - All work is automatically tracked in your task management system
5. **Coordinate complex work** - Use the uber-orchestrator for multi-phase projects

This bridge architecture gives you the best of both worlds: Claude Code's intuitive interface with your powerful multi-agent orchestration system.