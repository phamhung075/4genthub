# Agent Assignment & Inheritance Enhancement

## Overview

This document describes the enhanced agent assignment and inheritance features implemented in the task management system. The enhancements support multiple agent assignment at creation time and automatic agent inheritance from parent tasks to subtasks.

## Features Implemented

### 1. Agent Assignment at Creation
- **Tasks**: Support assigning multiple agents during task creation
- **Subtasks**: Support assigning multiple agents during subtask creation
- **Validation**: All agent assignments validated using AgentRole enum
- **Error Handling**: Comprehensive validation with clear error messages

### 2. Agent Inheritance
- **Automatic Inheritance**: Subtasks without explicit assignees inherit from parent task
- **Conditional Logic**: Inheritance only applies when subtask has no assignees
- **Real-time Updates**: Changes to parent task assignees can trigger inheritance updates
- **Domain Events**: Inheritance actions generate appropriate domain events

### 3. Agent List Support
- **Multiple Agents**: Both tasks and subtasks support lists of agents
- **Normalization**: Automatic @ prefix normalization for agent roles
- **Legacy Support**: Backward compatibility with existing agent formats

### 4. Enhanced Validation
- **AgentRole Enum**: All agents validated against comprehensive enum (68+ roles)
- **Legacy Resolution**: Automatic resolution of legacy role names
- **Error Reporting**: Detailed error messages for invalid agents

## API Changes

### Task Creation

#### Before (existing)
```json
{
  "title": "Implement user authentication",
  "description": "Add login and registration",
  "assignees": ["coding-agent"]
}
```

#### After (enhanced)
```json
{
  "title": "Implement user authentication", 
  "description": "Add login and registration",
  "assignees": [
    "coding-agent",
    "@test-orchestrator-agent", 
    "security-auditor-agent",
    "documentation-agent"
  ]
}
```

### Subtask Creation

#### Scenario 1: Explicit Agent Assignment
```json
{
  "task_id": "task-123",
  "title": "Create login form",
  "assignees": ["@ui-designer-agent", "coding-agent"]
}
```

#### Scenario 2: Agent Inheritance (No assignees provided)
```json
{
  "task_id": "task-123", 
  "title": "Create login form"
  // No assignees - will inherit from parent task
}
```

**Response with inheritance:**
```json
{
  "success": true,
  "action": "create",
  "message": "Subtask 'Create login form' created for task task-123 with 3 inherited assignees",
  "subtask": {
    "id": "subtask-456",
    "title": "Create login form", 
    "assignees": ["coding-agent", "@test-orchestrator-agent", "documentation-agent"]
  },
  "agent_inheritance_applied": true,
  "inherited_assignees": ["coding-agent", "@test-orchestrator-agent", "documentation-agent"],
  "inheritance_info": {
    "applied": true,
    "inherited_from": "parent_task",
    "assignee_count": 3
  }
}
```

## Architecture

### Domain Layer Enhancements

#### Task Entity
```python
class Task:
    def get_inherited_assignees_for_subtasks(self) -> list[str]:
        """Get assignees that should be inherited by subtasks"""
        
    def validate_assignee_list(self, assignees: list[str]) -> list[str]:
        """Validate and normalize assignee list"""
```

#### Subtask Entity  
```python
class Subtask:
    def inherit_assignees_from_parent(self, parent_assignees: List[str]) -> None:
        """Inherit assignees from parent task"""
        
    def should_inherit_assignees(self) -> bool:
        """Check if subtask should inherit assignees"""
```

### Application Layer

#### Agent Inheritance Service
```python
class AgentInheritanceService:
    def apply_agent_inheritance(self, subtask: Subtask, parent_task: Optional[Task] = None) -> Subtask:
        """Apply inheritance logic to a subtask"""
        
    def apply_inheritance_to_all_subtasks(self, task_id: TaskId) -> List[Subtask]:
        """Apply inheritance to all subtasks of a task"""
        
    def get_inheritance_summary(self, task_id: TaskId) -> dict:
        """Get inheritance status summary"""
```

### Interface Layer

#### Enhanced Handlers
- **Task CRUD Handler**: Validates agents at creation
- **Subtask CRUD Handler**: Handles inheritance and validation
- **Error Handling**: Comprehensive validation error responses

## Validation Rules

### Agent Role Validation
1. **Valid Agents**: Must exist in AgentRole enum (68+ available agents)
2. **Format Normalization**: Automatic @ prefix addition
3. **Legacy Support**: Resolves legacy agent names to current format
4. **Error Messages**: Clear indication of invalid agents

### Agent Assignment Rules
1. **Task Creation**: Optional agent list, validated if provided
2. **Task Updates**: Agent list updates validated
3. **Subtask Creation**: Optional agent list or inheritance from parent
4. **Subtask Updates**: Agent list updates validated

### Inheritance Rules
1. **Trigger Condition**: Subtask has no assignees AND parent has assignees
2. **Inheritance Source**: Parent task's assignees copied to subtask
3. **Timing**: Applied at subtask creation time
4. **Updates**: Parent assignee changes can trigger re-inheritance

## Backward Compatibility

### Existing Functionality Preserved
- ✅ Single agent assignment continues to work
- ✅ Existing agent validation logic preserved
- ✅ Legacy agent names automatically resolved
- ✅ Existing API endpoints unchanged (only enhanced)

### Migration Considerations
- **No Breaking Changes**: All existing code continues to work
- **Optional Enhancement**: New features are opt-in
- **Data Migration**: No database schema changes required
- **API Compatibility**: All existing API calls remain valid

## Error Handling

### Validation Errors
```json
{
  "success": false,
  "error": "Invalid assignees: ['invalid-agent', 'another-invalid']. Valid assignees must be from AgentRole enum.",
  "operation": "create_task",
  "error_code": "VALIDATION_ERROR",
  "metadata": {
    "field": "assignees",
    "hint": "Provide valid agent roles from AgentRole enum"
  }
}
```

### Inheritance Errors
- Parent task not found: Graceful handling with warning
- Repository errors: Inheritance fails silently, subtask still created
- Service errors: Logged but don't prevent subtask creation

## Examples

### Complete Workflow Example

1. **Create Task with Multiple Agents**
```bash
POST /api/tasks
{
  "title": "Build authentication system",
  "description": "Complete user auth implementation",
  "git_branch_id": "auth-feature-branch",
  "assignees": [
    "coding-agent",
    "@test-orchestrator-agent", 
    "@security-auditor-agent",
    "documentation-agent"
  ]
}
```

2. **Create Subtask with Inheritance**
```bash 
POST /api/subtasks
{
  "task_id": "auth-task-123",
  "title": "Implement password validation"
  // No assignees - inherits from parent
}
```

3. **Create Subtask with Explicit Agents**
```bash
POST /api/subtasks  
{
  "task_id": "auth-task-123",
  "title": "Design login UI",
  "assignees": ["@ui-designer-agent", "@usability-heuristic-agent"]
}
```

### Agent Role Examples
```python
# Valid agent roles (sample)
VALID_AGENTS = [
    "coding-agent",
    "@test-orchestrator-agent", 
    "@security-auditor-agent",
    "documentation-agent",
    "@ui-designer-agent",
    "system-architect-agent",
    "devops-agent",
    "@performance-load-tester-agent"
    # ... and 60+ more
]
```

## Testing

### Test Coverage
- **Unit Tests**: Domain entity methods, validation logic
- **Integration Tests**: End-to-end assignment and inheritance flow
- **Error Cases**: Invalid agents, missing parents, service failures
- **Edge Cases**: Large agent lists, complex inheritance scenarios

### Test Files
- `/tests/unit/agent_inheritance_test.py` - Domain logic tests
- `/tests/integration/agent_assignment_flow_test.py` - Complete flow tests

## Performance Considerations

### Optimization Strategies
1. **Lazy Inheritance**: Inheritance applied only when needed
2. **Batch Updates**: Multiple subtask inheritance in single operation
3. **Caching**: Agent validation results cached per request
4. **Event Sourcing**: Domain events for audit and rollback capability

### Monitoring
- **Inheritance Metrics**: Track inheritance application rates
- **Validation Metrics**: Monitor invalid agent submission rates
- **Performance Metrics**: Measure inheritance service performance

## Future Enhancements

### Planned Features
1. **Dynamic Inheritance Rules**: Configurable inheritance logic
2. **Agent Workflows**: Agent-specific task routing and notifications
3. **Agent Load Balancing**: Distribute tasks across agents
4. **Agent Specialization**: Task-agent matching based on requirements

### Extensibility Points
- **Custom Validation**: Pluggable agent validation strategies
- **Inheritance Policies**: Configurable inheritance rules
- **Event Handlers**: Custom logic on inheritance events
- **Agent Metadata**: Extended agent information and capabilities

## Troubleshooting

### Common Issues

#### Invalid Agent Errors
**Problem**: `Invalid assignees: ['invalid-agent']`
**Solution**: Use valid agent roles from AgentRole enum

#### Inheritance Not Working
**Problem**: Subtask doesn't inherit parent agents
**Solution**: Ensure subtask has no explicit assignees and parent has assignees

#### Performance Issues
**Problem**: Slow subtask creation with inheritance
**Solution**: Check agent inheritance service configuration and parent task lookup

### Debug Information
- Enable debug logging for agent inheritance service
- Use inheritance summary endpoint for troubleshooting
- Check domain events for inheritance audit trail