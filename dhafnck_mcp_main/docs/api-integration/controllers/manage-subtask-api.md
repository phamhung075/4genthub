# manage_subtask - Subtask Management API Documentation

## Overview

The `manage_subtask` tool provides hierarchical task decomposition with automatic progress tracking, parent task context updates, and comprehensive workflow guidance. It enables breaking down complex tasks into manageable subtasks with intelligent progress aggregation.

## Base Information

- **Tool Name**: `manage_subtask`
- **Controller**: `SubtaskMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller`
- **Authentication**: Required (JWT-based user context)
- **Parent Integration**: ✅ Automatic parent task progress updates
- **Workflow Guidance**: ✅ Intelligent subtask orchestration

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string", 
      "required": true,
      "description": "Subtask operation to perform"
    },
    "task_id": {
      "type": "string",
      "description": "[OPTIONAL] Parent task UUID (required for most actions)"
    },
    "subtask_id": {
      "type": "string",
      "description": "[OPTIONAL] Subtask UUID for specific operations"
    },
    "title": {
      "type": "string",
      "description": "[OPTIONAL] Subtask title"
    },
    "description": {
      "type": "string", 
      "description": "[OPTIONAL] Subtask description"
    },
    "status": {
      "type": "string",
      "description": "[OPTIONAL] Status: 'pending', 'in_progress', 'completed', 'blocked'"
    },
    "priority": {
      "type": "string",
      "description": "[OPTIONAL] Priority: 'low', 'medium', 'high', 'critical'"
    },
    "assignees": {
      "type": "string",
      "description": "[OPTIONAL] Comma-separated list of assignee IDs"
    },
    "progress_percentage": {
      "type": "integer",
      "description": "[OPTIONAL] Completion percentage (0-100)"
    },
    "progress_notes": {
      "type": "string",
      "description": "[OPTIONAL] Progress update notes"
    },
    "completion_summary": {
      "type": "string",
      "description": "[OPTIONAL] Summary of completed work"
    },
    "testing_notes": {
      "type": "string",
      "description": "[OPTIONAL] Testing performed and results"
    },
    "insights_found": {
      "type": "string",
      "description": "[OPTIONAL] Technical insights discovered"
    },
    "challenges_overcome": {
      "type": "string",
      "description": "[OPTIONAL] Challenges faced and solutions"
    },
    "skills_learned": {
      "type": "string", 
      "description": "[OPTIONAL] New skills or knowledge gained"
    },
    "next_recommendations": {
      "type": "string",
      "description": "[OPTIONAL] Recommendations for next steps"
    },
    "deliverables": {
      "type": "string",
      "description": "[OPTIONAL] Tangible outputs or artifacts created"
    },
    "completion_quality": {
      "type": "string",
      "description": "[OPTIONAL] Quality assessment: 'needs_work', 'good', 'excellent'"
    },
    "impact_on_parent": {
      "type": "string",
      "description": "[OPTIONAL] How completion affects parent task"
    },
    "blockers": {
      "type": "string",
      "description": "[OPTIONAL] Current blockers or dependencies"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authentication"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Core Lifecycle Operations

#### `create` - Create Subtask

Creates a new subtask under a parent task with automatic hierarchy setup.

**Required Parameters:**
- `action`: "create"
- `task_id`: Parent task UUID
- `title`: Subtask title

**Optional Parameters:**
- `description`: Detailed description
- `priority`: Priority level (inherits from parent if not specified)
- `assignees`: Initial assignees
- `status`: Initial status (default: "pending")

**Example Request:**
```json
{
  "action": "create",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Design authentication flow",
  "description": "Create user flow diagrams and security architecture for JWT authentication",
  "priority": "high",
  "assignees": "user123,user456"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "create",
  "subtask": {
    "id": "987fcdeb-51a2-43d7-8b9f-123456789abc",
    "task_id": "123e4567-e89b-12d3-a456-426614174000", 
    "title": "Design authentication flow",
    "description": "Create user flow diagrams and security architecture for JWT authentication",
    "status": "pending",
    "priority": "high",
    "assignees": ["user123", "user456"],
    "progress_percentage": 0,
    "created_at": "2025-01-27T10:35:00Z"
  },
  "parent_update": {
    "total_subtasks": 3,
    "pending_subtasks": 2,
    "overall_progress": 33
  },
  "workflow_guidance": {
    "suggested_next_action": "Start with authentication flow research",
    "estimated_effort": "4-6 hours",
    "dependencies": ["Security requirements", "User personas"]
  }
}
```

#### `get` - Retrieve Subtask

Gets complete subtask information with parent context.

**Required Parameters:**
- `action`: "get"
- `task_id`: Parent task UUID
- `subtask_id`: Subtask UUID

#### `update` - Update Subtask Progress

Updates subtask with automatic parent task progress recalculation.

**Required Parameters:**
- `action`: "update"
- `task_id`: Parent task UUID
- `subtask_id`: Subtask UUID

**Optional Parameters:**
- Any updateable field from the parameter schema

**Example Request:**
```json
{
  "action": "update",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "subtask_id": "987fcdeb-51a2-43d7-8b9f-123456789abc",
  "status": "in_progress", 
  "progress_percentage": 60,
  "progress_notes": "Flow diagrams completed, working on security specifications",
  "insights_found": "OAuth2 integration will require additional scopes configuration"
}
```

#### `complete` - Complete Subtask

Marks subtask as complete with comprehensive completion tracking.

**Required Parameters:**
- `action`: "complete"
- `task_id`: Parent task UUID  
- `subtask_id`: Subtask UUID

**Optional Parameters:**
- `completion_summary`: What was accomplished
- `testing_notes`: Testing performed
- `deliverables`: Outputs created
- `next_recommendations`: Suggestions for related work
- `completion_quality`: Quality self-assessment

**Example Request:**
```json
{
  "action": "complete",
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "subtask_id": "987fcdeb-51a2-43d7-8b9f-123456789abc",
  "completion_summary": "Authentication flow fully designed with security review completed",
  "testing_notes": "Flow validated with security team and UX team",
  "deliverables": "Flow diagrams, security specs, implementation guidelines",
  "completion_quality": "excellent",
  "next_recommendations": "Ready to begin JWT service implementation"
}
```

### Management Operations

#### `list` - List Subtasks

Lists all subtasks for a parent task with filtering options.

**Required Parameters:**
- `action`: "list"
- `task_id`: Parent task UUID

**Optional Parameters:**
- `status`: Filter by status
- `assignees`: Filter by assignee
- `priority`: Filter by priority

#### `delete` - Delete Subtask

Removes a subtask and updates parent task progress.

**Required Parameters:**
- `action`: "delete"
- `task_id`: Parent task UUID
- `subtask_id`: Subtask UUID


## Automatic Progress Tracking

### Parent Task Updates
The system automatically:
- **Recalculates parent progress** based on subtask completion
- **Updates parent status** when all subtasks complete
- **Propagates insights** from subtasks to parent context  
- **Aggregates deliverables** across all subtasks

### Progress Calculation Algorithm
```
Parent Progress = (
  (completed_subtasks * 100) + 
  sum(in_progress_subtask_percentages)
) / total_subtasks
```

### Status Propagation Rules
- **All subtasks pending** → Parent remains current status
- **Any subtask in progress** → Parent becomes "in_progress" 
- **All subtasks completed** → Parent becomes "completed"
- **Any subtask blocked** → Parent flagged with blocker info

## Workflow Guidance Features

### Intelligent Orchestration
- **Dependency Detection**: Identifies subtask dependencies
- **Optimal Ordering**: Suggests best sequence for subtasks
- **Resource Allocation**: Recommends assignee distribution
- **Effort Estimation**: Provides time estimates

### Progress Intelligence
- **Completion Prediction**: Estimates completion dates
- **Risk Assessment**: Identifies potential delays
- **Quality Monitoring**: Tracks completion quality trends
- **Knowledge Capture**: Extracts learnings and insights

## Error Handling

### Validation Errors
- `TASK_ID_REQUIRED`: Parent task ID missing
- `SUBTASK_NOT_FOUND`: Subtask doesn't exist
- `INVALID_PROGRESS`: Progress percentage out of range (0-100)
- `INVALID_STATUS`: Status not in allowed values
- `PERMISSION_DENIED`: User lacks access to parent task

### Business Logic Errors
- `PARENT_TASK_COMPLETED`: Cannot add subtasks to completed tasks
- `CIRCULAR_DEPENDENCY`: Subtask would create dependency loop
- `ASSIGNEE_NOT_FOUND`: One or more assignees don't exist

## Usage Patterns

### Task Decomposition Workflow
1. Create parent task with `manage_task`
2. Break down into subtasks with `manage_subtask` create
3. Assign team members to appropriate subtasks
4. Track progress with regular updates
5. Complete subtasks systematically
6. Parent task auto-completes when all subtasks done

### Progress Tracking Best Practices
- **Regular Updates**: Update progress percentage frequently
- **Meaningful Notes**: Include specific progress details
- **Document Insights**: Capture technical learnings
- **Quality Self-Assessment**: Honest completion quality ratings
- **Forward Planning**: Always provide next recommendations

### Team Collaboration
- **Clear Assignments**: Specify assignees for accountability
- **Blockers Communication**: Document blockers immediately  
- **Knowledge Sharing**: Record insights for team learning
- **Handoff Planning**: Detail next steps for smooth transitions

## Integration with Other Tools

### Context Management
- Subtask insights automatically flow to parent task context
- Cross-subtask learnings captured in branch context
- Global patterns identified and stored

### Agent Assignment  
- Agents can be assigned to specific subtasks
- Agent expertise matched to subtask requirements
- Agent outputs integrated into subtask deliverables

### Vision System
- AI provides subtask breakdown suggestions
- Intelligent progress interpretation and recommendations
- Predictive completion analysis

## Performance Considerations

### Database Optimization
- Indexed queries on parent task relationships
- Efficient progress recalculation with triggers
- Batch operations for multiple subtask updates

### Caching Strategy
- Parent progress cached with TTL
- Workflow guidance results cached per parent task
- Assignee lookups cached for session duration

## Example Complete Workflow

```json
// 1. Create parent task with manage_task
{"action": "create", "title": "Implement User Authentication"}

// 2. Break into subtasks with manage_subtask
{"action": "create", "task_id": "parent-uuid", "title": "Design auth flow"}
{"action": "create", "task_id": "parent-uuid", "title": "Implement JWT service"} 
{"action": "create", "task_id": "parent-uuid", "title": "Add refresh tokens"}
{"action": "create", "task_id": "parent-uuid", "title": "Create login UI"}

// 3. Track progress with manage_subtask
{"action": "update", "task_id": "parent-uuid", "subtask_id": "design-uuid", "progress_percentage": 50}
{"action": "complete", "task_id": "parent-uuid", "subtask_id": "design-uuid", "completion_summary": "..."}

// 4. Parent automatically updates and completes when all subtasks done
```

This creates a complete hierarchical task management system with intelligent progress tracking and team coordination capabilities.