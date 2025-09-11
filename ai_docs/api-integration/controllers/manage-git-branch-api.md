# manage_git_branch - Git Branch Management API Documentation

## Overview

The `manage_git_branch` tool manages git branches as task trees, providing branch lifecycle operations, agent assignments, and hierarchical project organization. Branches serve as logical containers for related tasks within projects, enabling parallel development streams and feature isolation.

## Base Information

- **Tool Name**: `manage_git_branch`
- **Controller**: `GitBranchMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.git_branch_mcp_controller`
- **Authentication**: Required (JWT-based user context)
- **Project Integration**: ✅ Branches belong to projects for organization
- **Agent Assignment**: ✅ Specialized agents can be assigned to branches
- **Task Tree Concept**: ✅ Branches contain and organize related tasks

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Git branch operation to perform"
    },
    "project_id": {
      "type": "string",
      "description": "[OPTIONAL] Project UUID that owns the branch"
    },
    "git_branch_id": {
      "type": "string", 
      "description": "[OPTIONAL] Branch UUID identifier"
    },
    "git_branch_name": {
      "type": "string",
      "description": "[OPTIONAL] Branch name (e.g., 'feature/user-authentication') - DEPRECATED: Use git_branch_id (UUID) instead"
    },
    "git_branch_description": {
      "type": "string",
      "description": "[OPTIONAL] Branch description and purpose"
    },
    "agent_id": {
      "type": "string",
      "description": "[OPTIONAL] Agent identifier for branch assignment"
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

### Core Branch Operations

#### `create` - Create New Branch

Creates a new git branch within a project as a task tree container.

**Required Parameters:**
- `action`: "create"
- `project_id`: Project UUID
- `git_branch_name`: Branch name

**Optional Parameters:**
- `git_branch_description`: Branch description
- `agent_id`: Initial agent assignment

**Branch Naming Conventions:**
- `feature/description` - New feature development
- `bugfix/issue-description` - Bug fixes
- `hotfix/critical-issue` - Production hotfixes
- `release/version` - Release preparation
- `experiment/research-topic` - Experimental work

**Example Request:**
```json
{
  "action": "create",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
  "git_branch_name": "feature/user-authentication",
  "git_branch_description": "Implement JWT-based user authentication system with refresh tokens, password reset, and multi-factor authentication support",
  "agent_id": "@security_auditor_agent"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "create",
  "branch": {
    "id": "branch-456e7890-f12b-34c5-d678-901234567efg",
    "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "name": "feature/user-authentication",
    "description": "Implement JWT-based user authentication system with refresh tokens, password reset, and multi-factor authentication support",
    "status": "active",
    "assigned_agent": "@security_auditor_agent",
    "created_by": "user-550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-27T11:30:00Z",
    "task_count": 0,
    "completion_percentage": 0
  },
  "context_setup": {
    "branch_context_created": true,
    "inherits_from_project": true,
    "context_id": "branch-456e7890-f12b-34c5-d678-901234567efg"
  },
  "workflow_guidance": {
    "suggested_first_tasks": [
      "Define authentication requirements",
      "Design JWT token structure", 
      "Plan database schema for users"
    ],
    "recommended_agents": ["@coding_agent", "@database_agent", "@ui_designer_agent"],
    "estimated_duration": "2-3 weeks"
  }
}
```

#### `get` - Retrieve Branch Details

Gets complete branch information including statistics and agent assignments.

**Required Parameters:**
- `action`: "get"
- `git_branch_id`: Branch UUID

**Example Request:**
```json
{
  "action": "get", 
  "git_branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "get",
  "branch": {
    "id": "branch-456e7890-f12b-34c5-d678-901234567efg",
    "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "name": "feature/user-authentication", 
    "description": "Implement JWT-based user authentication system with refresh tokens, password reset, and multi-factor authentication support",
    "status": "active",
    "assigned_agent": "@security_auditor_agent",
    "created_by": "user-550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-27T11:30:00Z",
    "updated_at": "2025-01-27T14:45:00Z"
  },
  "statistics": {
    "total_tasks": 12,
    "pending_tasks": 3,
    "in_progress_tasks": 6,
    "completed_tasks": 3,
    "blocked_tasks": 0,
    "completion_percentage": 45.8,
    "active_contributors": 3
  },
  "agent_activity": {
    "current_agent": "@coding_agent",
    "last_activity": "2025-01-27T14:45:00Z", 
    "tasks_completed": 3,
    "insights_contributed": 8
  },
  "project_context": {
    "project_name": "E-commerce Platform V2",
    "project_health": "good"
  }
}
```

#### `update` - Update Branch Configuration

Updates branch properties and configuration.

**Required Parameters:**
- `action`: "update"
- `git_branch_id`: Branch UUID

**Optional Parameters:**
- `git_branch_name`: Updated name
- `git_branch_description`: Updated description
- `agent_id`: New agent assignment

**Example Request:**
```json
{
  "action": "update",
  "git_branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
  "git_branch_description": "Implement comprehensive JWT-based user authentication system with refresh tokens, password reset, multi-factor authentication, and OAuth2 integration for social login",
  "agent_id": "@coding_agent"
}
```

#### `delete` - Delete Branch

Removes a branch and all associated tasks and contexts.

**Required Parameters:**
- `action`: "delete"
- `git_branch_id`: Branch UUID

**⚠️ Warning**: This operation removes ALL branch data including:
- All tasks and subtasks within the branch
- All branch-level context data
- All agent assignments and execution history

### Query Operations

#### `list` - List Branches

Lists branches within a project with filtering and statistics.

**Required Parameters:**
- `action`: "list"
- `project_id`: Project UUID

**Optional Parameters:**
- `status`: Filter by branch status
- `assigned_agent`: Filter by assigned agent

**Example Request:**
```json
{
  "action": "list",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "list",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
  "branches": [
    {
      "id": "branch-456e7890-f12b-34c5-d678-901234567efg",
      "name": "feature/user-authentication",
      "description": "Implement JWT-based user authentication system...",
      "status": "active",
      "assigned_agent": "@coding_agent",
      "created_at": "2025-01-27T11:30:00Z",
      "statistics": {
        "total_tasks": 12,
        "completion_percentage": 45.8,
        "last_activity": "2025-01-27T14:45:00Z"
      }
    },
    {
      "id": "branch-789abcde-f012-3456-789a-bcdef0123456", 
      "name": "feature/product-catalog",
      "description": "Build product catalog with search and filtering",
      "status": "active",
      "assigned_agent": "@database_agent",
      "created_at": "2025-01-26T09:15:00Z",
      "statistics": {
        "total_tasks": 18,
        "completion_percentage": 72.2,
        "last_activity": "2025-01-27T13:20:00Z"
      }
    }
  ],
  "summary": {
    "total_branches": 2,
    "active_branches": 2,
    "average_completion": 59.0
  }
}
```

#### `get_statistics` - Get Branch Statistics

Provides detailed analytics and metrics for a specific branch.

**Required Parameters:**
- `action`: "get_statistics"
- `git_branch_id`: Branch UUID

**Optional Parameters:**
- `include_tasks`: Include task breakdown
- `include_timeline`: Include activity timeline

**Example Request:**
```json
{
  "action": "get_statistics",
  "git_branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
  "include_tasks": "true",
  "include_timeline": "true"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "get_statistics",
  "branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
  "overview": {
    "name": "feature/user-authentication",
    "age_days": 3,
    "completion_percentage": 45.8,
    "velocity": "good",
    "health": "on_track"
  },
  "task_breakdown": {
    "total_tasks": 12,
    "by_status": {
      "pending": 3,
      "in_progress": 6, 
      "completed": 3,
      "blocked": 0
    },
    "by_priority": {
      "critical": 1,
      "high": 4,
      "medium": 5,
      "low": 2
    }
  },
  "productivity_metrics": {
    "tasks_per_day": 1.8,
    "average_task_completion_time": "1.2 days",
    "contributor_count": 3,
    "commits_count": 47,
    "lines_changed": "+2,341 -892"
  },
  "timeline": [
    {
      "date": "2025-01-27",
      "events": [
        {"time": "14:45", "type": "task_completed", "description": "JWT service implementation completed"},
        {"time": "12:30", "type": "task_started", "description": "Password reset flow implementation started"},
        {"time": "10:15", "type": "agent_switch", "description": "Agent changed from @security_auditor_agent to @coding_agent"}
      ]
    }
  ],
  "predictions": {
    "estimated_completion": "2025-02-10T00:00:00Z",
    "confidence": 0.78,
    "risk_factors": ["Dependency on external OAuth service", "Database schema finalization pending"]
  }
}
```

### Agent Management Operations

#### `assign_agent` - Assign Agent to Branch

Assigns a specialized agent to work on branch tasks.

**Required Parameters:**
- `action`: "assign_agent"
- `git_branch_id`: Branch UUID
- `agent_id`: Agent identifier (e.g., "@coding_agent")

**Available Agent Types:**
- `@coding_agent` - Implementation and development work
- `@ui_designer_agent` - Frontend and user interface work  
- `@database_agent` - Database design and optimization
- `@security_auditor_agent` - Security reviews and compliance
- `@test_orchestrator_agent` - Testing and quality assurance
- `@devops_agent` - Deployment and infrastructure
- `@documentation_agent` - Documentation and guides

**Example Request:**
```json
{
  "action": "assign_agent",
  "git_branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
  "agent_id": "@security_auditor_agent"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "assign_agent",
  "branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
  "previous_agent": "@coding_agent", 
  "new_agent": "@security_auditor_agent",
  "assignment_reason": "Security review phase for authentication system",
  "agent_context": {
    "specialized_for": ["security_audit", "vulnerability_assessment", "compliance_check"],
    "previous_experience": "12 authentication system reviews",
    "estimated_focus_time": "2-3 days"
  },
  "handoff_notes": {
    "current_progress": "JWT implementation 80% complete",
    "next_priorities": ["Security audit of token handling", "Password complexity validation", "Rate limiting implementation"],
    "context_transferred": true
  }
}
```

#### `unassign_agent` - Remove Agent Assignment

Removes agent assignment from branch, making it available for manual task management.

**Required Parameters:**
- `action`: "unassign_agent"
- `git_branch_id`: Branch UUID


## Branch as Task Tree Concept

### Hierarchical Organization
```
Project
├── feature/user-authentication (Branch)
│   ├── Design auth flow (Task)
│   │   ├── Create wireframes (Subtask)
│   │   └── Security review (Subtask)
│   ├── Implement JWT service (Task)
│   │   ├── Token generation (Subtask)
│   │   └── Token validation (Subtask)
│   └── Add password reset (Task)
└── feature/product-catalog (Branch)
    ├── Database schema (Task)
    └── Search functionality (Task)
```

### Branch Lifecycle States
- **Active**: Currently being worked on
- **On Hold**: Temporarily paused
- **Review**: Ready for review/testing
- **Merged**: Completed and merged to main
- **Archived**: Historical reference only

### Task Organization Benefits
- **Logical Grouping**: Related tasks organized under feature branches
- **Progress Tracking**: Branch completion based on task completion
- **Agent Specialization**: Different agents can focus on different branches
- **Context Isolation**: Branch-specific knowledge and decisions

## Integration Patterns

### With Project Management
```json
// 1. Create project
{"action": "create", "name": "E-commerce Platform"}

// 2. Create branches within project
{"action": "create", "project_id": "proj-uuid", "git_branch_name": "feature/auth"}
{"action": "create", "project_id": "proj-uuid", "git_branch_name": "feature/catalog"}

// 3. Project health aggregates branch metrics
```

### With Task Management  
```json
// 1. Create branch first
{"action": "create", "git_branch_name": "feature/user-auth"}

// 2. Create tasks within branch
// manage_task: {"action": "create", "git_branch_id": "branch-uuid", "title": "Implement JWT"}

// 3. Branch statistics automatically include task progress
```

### With Context Management
```json
// 1. Branch automatically creates branch-level context
// 2. Add branch-specific decisions and discoveries
{"action": "update", "level": "branch", "context_id": "branch-uuid", 
 "data": "{\"tech_decisions\": [\"Using bcrypt for password hashing\"]}"}

// 3. Tasks inherit branch context automatically
```

### With Agent Assignment
```json
// 1. Assign specialist agent to branch
{"action": "assign_agent", "git_branch_id": "branch-uuid", "agent_id": "@coding_agent"}

// 2. Agent receives full branch context and task list
// 3. Agent works on tasks within their specialization
// 4. Switch agents as work phases change
{"action": "assign_agent", "agent_id": "@security_auditor_agent"}
```

## Workflow Guidance Features

### Intelligent Branch Suggestions
- **Task Breakdown**: AI suggests logical task decomposition for new branches
- **Agent Matching**: Recommends optimal agents based on branch type and requirements
- **Timeline Estimation**: Provides completion estimates based on task complexity
- **Dependency Detection**: Identifies dependencies between branches

### Progress Intelligence
- **Velocity Tracking**: Monitors task completion rate and trends
- **Bottleneck Identification**: Detects where branches are getting stuck
- **Resource Optimization**: Suggests agent reassignments for better efficiency
- **Risk Assessment**: Early warning for branches falling behind schedule

## Error Handling

### Validation Errors
- `BRANCH_NOT_FOUND`: Branch ID doesn't exist or user lacks access
- `PROJECT_NOT_FOUND`: Project ID invalid or inaccessible  
- `INVALID_BRANCH_NAME`: Branch name format invalid or already exists
- `AGENT_NOT_FOUND`: Agent ID not recognized
- `PERMISSION_DENIED`: User lacks required permissions

### Business Logic Errors
- `BRANCH_HAS_ACTIVE_TASKS`: Cannot delete branch with incomplete tasks
- `AGENT_ALREADY_ASSIGNED`: Agent already assigned to this branch
- `PROJECT_ARCHIVED`: Cannot create branches in archived projects
- `INVALID_BRANCH_STATUS`: Status transition not allowed

### Example Error Response
```json
{
  "success": false,
  "error": "Branch name already exists in project",
  "error_code": "INVALID_BRANCH_NAME", 
  "operation": "create",
  "metadata": {
    "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "branch_name": "feature/user-authentication",
    "existing_branch_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
    "hint": "Choose a different branch name or update the existing branch"
  }
}
```

## Performance Considerations

### Database Optimization
- **Indexed Queries**: Fast lookups on project_id, branch_name, and agent assignments
- **Aggregate Caching**: Branch statistics cached with TTL and invalidation triggers  
- **Lazy Loading**: Task details loaded only when requested
- **Batch Operations**: Multiple branch operations grouped efficiently

### Agent Assignment Performance
- **Context Caching**: Agent context cached per branch assignment
- **Activity Tracking**: Efficient logging of agent activities and contributions
- **Handoff Optimization**: Quick context transfer between agent switches

## Usage Best Practices

### Branch Organization
1. **Descriptive Names**: Use clear branch naming conventions (feature/bugfix/hotfix)
2. **Focused Scope**: Keep branches focused on specific features or fixes
3. **Regular Updates**: Update branch descriptions as scope evolves
4. **Agent Specialization**: Match agents to branch requirements
5. **Progress Monitoring**: Review branch statistics regularly

### Task Tree Management
- **Logical Grouping**: Group related tasks under appropriate branches
- **Dependency Mapping**: Consider task dependencies when creating branches
- **Parallel Development**: Use multiple branches for parallel feature development
- **Integration Planning**: Plan branch merging and integration points

### Agent Collaboration
- **Clear Handoffs**: Document progress when switching agents
- **Context Preservation**: Ensure agent context is properly transferred
- **Specialization Benefits**: Leverage agent expertise for optimal results
- **Activity Monitoring**: Track agent contributions and effectiveness

This branch management system provides a powerful foundation for organizing development work into logical containers with specialized agent support and comprehensive progress tracking.