# Role-Based Tool Assignment System

**Document Type**: Architecture Documentation  
**Created**: 2025-09-09  
**Last Updated**: 2025-09-09  
**Status**: Implemented  

## Overview

The agenthub agent library implements a role-based tool assignment system that addresses the binary constraint of tool permissions while enabling specialized agent workflows through delegation patterns.

## Problem Statement

**Binary Tool Constraint**: Tools in the MCP (Model Context Protocol) system operate on a binary permission model - agents either have full access to a tool or no access at all. There is no capability to restrict tool usage by file type, operation type, or domain-specific constraints.

**Challenge**: Different agent roles require different capabilities:
- **Security auditors** should analyze code but not modify it
- **Task planners** should coordinate work but not write implementation files
- **Coding agents** need full file creation and modification capabilities
- **Documentation agents** should write ai_docs but have limited code access

## Solution: Delegation-Based Role Architecture

### Role Categories

#### 1. COORDINATORS/ANALYZERS
**Characteristics**: Read-only analysis, task creation, delegation responsibilities
**Tool Profile**: 
- File operations: `read: true, write: false, create: false, delete: false`
- Command execution: Limited to read-only commands
- MCP tools: Task management tools for delegation

**Examples**:
- `security-auditor-agent`: Analyzes security, creates remediation tasks
- `deep-research-agent`: Researches information, delegates implementation
- `task-planning-agent`: Plans work, assigns to implementation agents

#### 2. FILE CREATORS
**Characteristics**: Full file implementation capabilities within their domain
**Tool Profile**:
- File operations: `read: true, write: true, create: true, delete: varies`
- Command execution: Domain-appropriate commands
- MCP tools: Specialized tools for their domain + task management

**Examples**:
- `coding-agent`: Full development tools + IDE integration
- `test-orchestrator-agent`: Test creation + browser automation tools
- `documentation-agent`: Documentation creation + web research tools

#### 3. SPECIALISTS
**Characteristics**: Domain-specific tools and workflows
**Tool Profile**: Customized based on specialization
**Examples**:
- `ui_designer_expert_shadcn_agent`: UI components + design tools
- `devops-agent`: Infrastructure + deployment tools

### Implementation Architecture

#### YAML Configuration Structure
```yaml
# COORDINATOR Example (security-auditor-agent)
file_operations:
  enabled: true
  permissions:
    read: true
    write: false      # Read-only access
    create: false     # Cannot create files
    delete: false

command_execution:
  enabled: true
  restrictions:
    - sandbox_mode
    - read_only_commands

mcp_tools:
  enabled: true
  tools:
    - mcp__agenthub_http__manage_task      # Delegation tools
    - mcp__agenthub_http__manage_subtask   # Task breakdown
    - mcp__agenthub_http__manage_agent     # Agent assignment
    - mcp__sequential-thinking__sequentialthinking

# FILE CREATOR Example (test-orchestrator-agent)
file_operations:
  enabled: true
  permissions:
    read: true
    write: true       # Can modify files
    create: true      # Can create files
    delete: false

command_execution:
  enabled: true
  restrictions:
    - sandbox_mode
    - testing_only
  allowed_commands:
    - npm test
    - pytest
    - jest

mcp_tools:
  enabled: true
  tools:
    - mcp__browsermcp__browser_navigate       # Specialized tools
    - mcp__browsermcp__browser_click
    - mcp__agenthub_http__manage_task      # + Task management
    - mcp__agenthub_http__manage_subtask
    - mcp__agenthub_http__manage_agent
```

#### Dynamic Tool Resolution

The `call_agent.py` implementation reads YAML configurations and dynamically assigns tools:

```python
def _get_role_based_tools(self, agent_info: Dict[str, Any], capabilities_config: Dict[str, Any]) -> List[str]:
    """Get tools based on YAML configuration permissions"""
    tools = ['Read', 'Grep', 'Glob']  # Base tools for all agents
    
    # File operations based on YAML permissions
    file_ops = capabilities_config.get('file_operations', {})
    if file_ops.get('enabled', False):
        permissions = file_ops.get('permissions', {})
        if permissions.get('write', False):
            tools.append('Edit')
        if permissions.get('create', False):
            tools.extend(['Write', 'MultiEdit'])
    
    # Command execution based on YAML configuration
    cmd_exec = capabilities_config.get('command_execution', {})
    if cmd_exec.get('enabled', False):
        tools.append('Bash')
    
    # MCP Tools from YAML configuration
    mcp_config = capabilities_config.get('mcp_tools', {})
    if mcp_config.get('enabled', False) and 'tools' in mcp_config:
        tools.extend(mcp_config['tools'])
    
    return list(dict.fromkeys(tools))  # Remove duplicates
```

## Delegation Workflow Patterns

### Pattern 1: Security Analysis → Implementation
```
1. security-auditor-agent (COORDINATOR)
   ├─ Analyzes code for vulnerabilities
   ├─ Creates task: "Fix SQL injection in user.js:42"
   └─ Assigns: coding-agent

2. coding-agent (FILE CREATOR)
   ├─ Receives task assignment
   ├─ Implements security fix
   └─ Marks task complete

3. security-auditor-agent (COORDINATOR)
   └─ Validates fix (read-only verification)
```

### Pattern 2: Task Planning → Parallel Implementation
```
1. task-planning-agent (COORDINATOR)
   ├─ Breaks down feature into subtasks
   ├─ Creates subtask: "Implement API endpoints"
   ├─ Creates subtask: "Create UI components"  
   ├─ Creates subtask: "Write test suite"
   ├─ Assigns: coding-agent → API subtask
   ├─ Assigns: @ui_designer_expert_shadcn_agent → UI subtask
   └─ Assigns: test-orchestrator-agent → testing subtask

2. Multiple FILE CREATORS work in parallel
   └─ Each implements their assigned portion
```

### Pattern 3: Research → Documentation
```
1. deep-research-agent (COORDINATOR)
   ├─ Researches technology options
   ├─ Creates task: "Document API integration guide"
   └─ Assigns: documentation-agent

2. documentation-agent (FILE CREATOR)
   ├─ Creates comprehensive documentation
   └─ Updates project ai_docs structure
```

## Benefits

### 1. Security Through Constraint
- **COORDINATORS** cannot accidentally modify implementation files
- **FILE CREATORS** work within their domain expertise
- Clear separation of analysis vs. implementation responsibilities

### 2. Scalability Through Delegation
- **Parallel execution**: Multiple FILE CREATORS work simultaneously
- **Specialization**: Each agent optimized for their domain
- **Load distribution**: Work automatically distributed across specialized agents

### 3. Maintainability Through Clear Roles
- **Predictable behavior**: Each agent type has well-defined capabilities
- **Easy debugging**: Role boundaries make it clear which agent should handle what
- **Flexible assignment**: New tasks can be easily assigned to appropriate role types

## Agent Role Assignments

### COORDINATORS (Read-Only + Delegation)
- `security-auditor-agent` - Security analysis and remediation planning
- `deep-research-agent` - Research and information gathering
- `task-planning-agent` - Work breakdown and assignment coordination
- `compliance-scope-agent` - Regulatory analysis and compliance planning

### FILE CREATORS (Domain Implementation)
- `coding-agent` - Code implementation and development
- `test-orchestrator-agent` - Test creation and execution
- `documentation-agent` - Documentation creation and maintenance
- `system-architect-agent` - Architecture design and specification

### SPECIALISTS (Domain-Specific Tools)
- `ui_designer_expert_shadcn_agent` - UI/UX design and implementation
- `devops-agent` - Infrastructure and deployment
- `performance-load-tester-agent` - Performance testing and optimization

## Verification and Testing

The system has been verified through comprehensive testing:

```bash
# Test Results Summary
=== Security Auditor Agent (COORDINATOR) ===
Can Write Files: False ✓
Can Edit Files: False ✓  
Has Task Management: True ✓

=== Test Orchestrator Agent (FILE CREATOR) ===
Can Write Files: True ✓
Can Edit Files: True ✓
Has Browser Tools: True ✓

=== Coding Agent (FILE CREATOR) ===
Can Write Files: True ✓
Has IDE Tools: True ✓

=== Deep Research Agent (COORDINATOR) ===
Can Write Files: False ✓
Has Web Tools: True ✓
```

## Migration and Compatibility

### Backward Compatibility
- Existing agent configurations continue to work
- Gradual migration path for updating agent capabilities
- No breaking changes to existing MCP tool integrations

### Future Enhancements
- Additional role types can be easily added
- Tool assignment logic can be extended for new use cases
- Agent specializations can be refined based on usage patterns

## Conclusion

The role-based tool assignment system successfully addresses the binary tool constraint through intelligent delegation patterns. It enables secure, scalable, and maintainable agent workflows while preserving the simplicity of the underlying MCP tool model.

**Key Achievement**: Transformed a limitation (binary tools) into an architectural advantage (delegation patterns) that promotes separation of concerns and parallel execution efficiency.