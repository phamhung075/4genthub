# manage_project - Project Management API Documentation

## Overview

The `manage_project` tool provides comprehensive project lifecycle management including creation, configuration, health monitoring, analytics, and coordination across the multi-tenant agenthub platform. It serves as the top-level organizational container for all project activities.

## Base Information

- **Tool Name**: `manage_project`  
- **Controller**: `ProjectMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.project_mcp_controller`
- **Authentication**: Required (JWT-based user context)
- **Multi-Tenant**: ✅ Complete user isolation and project scoping
- **Health Monitoring**: ✅ Comprehensive project analytics and health checks

## Parameters Schema

```json
{
  "type": "object", 
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Project operation to perform"
    },
    "project_id": {
      "type": "string",
      "description": "[OPTIONAL] Project UUID identifier"
    },
    "name": {
      "type": "string", 
      "description": "[OPTIONAL] Project name"
    },
    "description": {
      "type": "string",
      "description": "[OPTIONAL] Project description"
    },
    "force": {
      "type": "string", 
      "description": "[OPTIONAL] Force operation bypassing safety checks: 'true', 'false'"
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

#### `create` - Create New Project

Creates a new project with initial configuration and context setup.

**Required Parameters:**
- `action`: "create"
- `name`: Project name

**Optional Parameters:**  
- `description`: Project description

**Example Request:**
```json
{
  "action": "create",
  "name": "E-commerce Platform V2",
  "description": "Next generation e-commerce platform with microservices architecture"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "create",
  "project": {
    "id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "name": "E-commerce Platform V2", 
    "description": "Next generation e-commerce platform with microservices architecture",
    "owner_id": "user-550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-27T11:00:00Z"
  },
  "context_setup": {
    "project_context_created": true,
    "context_id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "inherits_from_global": true
  },
  "initialization": {
    "default_branches_created": false,
    "permissions_configured": true,
    "monitoring_enabled": true
  }
}
```

#### `get` - Retrieve Project Details

Gets complete project information including health metrics and statistics.

**Required Parameters:**
- `action`: "get"
- `project_id`: Project UUID

**Example Request:**
```json
{
  "action": "get",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "get", 
  "project": {
    "id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "name": "E-commerce Platform V2",
    "description": "Next generation e-commerce platform with microservices architecture",
    "owner_id": "user-550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-27T11:00:00Z",
    "updated_at": "2025-01-27T14:30:00Z"
  },
  "statistics": {
    "total_branches": 3,
    "active_branches": 2, 
    "total_tasks": 47,
    "completed_tasks": 23,
    "in_progress_tasks": 18,
    "blocked_tasks": 2,
    "team_members": 8,
    "completion_percentage": 48.9
  },
  "health_metrics": {
    "overall_health": "good",
    "velocity_trend": "increasing",
    "blocker_count": 2,
    "risk_level": "low",
    "last_activity": "2025-01-27T14:30:00Z"
  }
}
```

#### `update` - Update Project Configuration

Updates project properties and configuration settings.

**Required Parameters:**
- `action`: "update" 
- `project_id`: Project UUID

**Optional Parameters:**
- `name`: Updated name
- `description`: Updated description

**Example Request:**
```json
{
  "action": "update",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
  "description": "Next generation e-commerce platform with enhanced microservices architecture"
}
```

#### `delete` - Delete Project

Removes a project and all associated data (branches, tasks, contexts).

**Required Parameters:**
- `action`: "delete"
- `project_id`: Project UUID

**Optional Parameters:**
- `force`: Skip safety checks and confirmations

**⚠️ Warning**: This operation is irreversible and removes ALL project data including:
- All git branches and their tasks
- All project contexts and subtask hierarchies
- All agent assignments and execution history
- All analytics and health monitoring data

### Query and Analytics Operations

#### `list` - List Projects

Lists all projects accessible to the current user with filtering options.

**Required Parameters:**
- `action`: "list"

**Optional Parameters:**
- `limit`: Maximum results to return
- `offset`: Pagination offset

**Example Request:**
```json
{
  "action": "list"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "list",
  "projects": [
    {
      "id": "proj-123e4567-e89b-12d3-a456-426614174000",
      "name": "E-commerce Platform V2",
      "description": "Next generation e-commerce platform with microservices architecture",
      "created_at": "2025-01-27T11:00:00Z",
      "statistics": {
        "total_tasks": 47,
        "completion_percentage": 48.9,
        "team_members": 10
      },
      "health": "good"
    },
    {
      "id": "proj-456e7890-f12b-34c5-d678-901234567efg",
      "name": "Mobile App Redesign",
      "description": "Complete UX/UI overhaul of mobile application", 
      "created_at": "2025-01-20T09:15:00Z",
      "statistics": {
        "total_tasks": 32,
        "completion_percentage": 75.0,
        "team_members": 6
      },
      "health": "excellent"
    }
  ],
  "pagination": {
    "total": 2,
    "limit": 50,
    "offset": 0,
    "has_more": false
  }
}
```

#### `project_health_check` - Comprehensive Health Analysis

Performs detailed health assessment of project status, progress, and potential issues.

**Required Parameters:**
- `action`: "project_health_check"
- `project_id`: Project UUID

**Optional Parameters:**
- `include_recommendations`: Include AI-generated recommendations
- `detailed_analysis`: Provide detailed breakdown by component

**Example Request:**
```json
{
  "action": "project_health_check",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
  "include_recommendations": "true",
  "detailed_analysis": "true"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "project_health_check",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
  "overall_health": {
    "score": 78,
    "status": "good",
    "trend": "improving"
  },
  "component_analysis": {
    "task_completion": {
      "score": 85,
      "status": "excellent",  
      "metrics": {
        "completion_rate": 48.9,
        "velocity": "increasing",
        "overdue_tasks": 3
      }
    },
    "team_productivity": {
      "score": 75,
      "status": "good",
      "metrics": {
        "active_contributors": 8,
        "commits_per_day": 12,
        "pr_merge_rate": 0.87
      }
    },
    "blocker_management": {
      "score": 65, 
      "status": "needs_attention",
      "metrics": {
        "active_blockers": 2,
        "avg_resolution_time": "2.3 days",
        "blocker_trend": "stable"
      }
    },
    "context_health": {
      "score": 90,
      "status": "excellent",
      "metrics": {
        "contexts_created": 47,
        "inheritance_depth": 3.2,
        "delegation_efficiency": 0.92
      }
    }
  },
  "risk_assessment": {
    "high_risks": [],
    "medium_risks": [
      "2 tasks blocked for >48 hours",
      "Team member on vacation next week"
    ],
    "low_risks": [
      "Database migration pending",
      "SSL certificate renewal due in 30 days"
    ]
  },
  "ai_recommendations": [
    "Focus on resolving the 2 blocked tasks to maintain velocity",
    "Consider adding automated testing to reduce manual QA bottleneck",
    "Schedule knowledge sharing session for JWT implementation patterns",
    "Plan for team member coverage during upcoming vacation"
  ],
  "projected_completion": "2025-04-15T00:00:00Z",
  "confidence": 0.82
}
```

### Maintenance Operations

#### `cleanup_obsolete` - Clean Up Obsolete Resources

Removes obsolete tasks, files, and resources from the project.

**Required Parameters:**
- `action`: "cleanup_obsolete"
- `project_id`: Project UUID

**Optional Parameters:**
- `force`: Skip safety checks and confirmations

#### `validate_integrity` - Validate Project Integrity

Validates project structure, dependencies, and consistency.

**Required Parameters:**
- `action`: "validate_integrity"
- `project_id`: Project UUID

**Optional Parameters:**
- `force`: Skip safety checks and perform comprehensive validation

#### `rebalance_agents` - Optimize Agent Assignments

Optimizes agent assignments across task trees within the project.

**Required Parameters:**
- `action`: "rebalance_agents"
- `project_id`: Project UUID

**Optional Parameters:**
- `force`: Force rebalancing even if current assignments are optimal


## Health Monitoring System

### Health Scoring Algorithm
The health score (0-100) is calculated based on:

- **Task Progress** (30%): Completion rate, velocity, overdue tasks
- **Team Productivity** (25%): Active contributors, commit frequency, PR merge rate  
- **Blocker Management** (20%): Active blockers, resolution time, escalation rate
- **Context Quality** (15%): Context coverage, inheritance efficiency, delegation rate
- **System Health** (10%): Error rates, performance metrics, availability

### Health Status Levels
- **Excellent** (90-100): Project exceeding expectations
- **Good** (70-89): Project on track with minor issues
- **Needs Attention** (50-69): Some concerns requiring intervention
- **At Risk** (30-49): Significant issues affecting delivery
- **Critical** (0-29): Project in serious trouble requiring immediate action

### Automated Monitoring
- **Real-time Updates**: Health metrics updated with each operation
- **Trend Analysis**: Historical health tracking with trend detection
- **Predictive Analytics**: Early warning system for potential issues
- **Alert System**: Notifications when health drops below thresholds

## Error Handling

### Validation Errors
- `PROJECT_NOT_FOUND`: Project ID doesn't exist or user lacks access
- `INVALID_PROJECT_NAME`: Name validation failed (empty, too long, invalid characters)
- `DUPLICATE_PROJECT_NAME`: Project name already exists for this user

### Business Logic Errors  
- `PROJECT_HAS_ACTIVE_BRANCHES`: Cannot delete project with active branches
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions for operation

### Example Error Response
```json
{
  "success": false,
  "error": "Cannot delete project with active branches",
  "error_code": "PROJECT_HAS_ACTIVE_BRANCHES",
  "operation": "delete",
  "metadata": {
    "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "active_branches": 3,
    "hint": "Archive or complete all branches before deletion, or use force=true to override"
  }
}
```

## Integration Patterns

### With Git Branch Management
```json
// Create project first
{"action": "create", "name": "E-commerce Platform"}

// Then create branches within the project
// manage_git_branch: {"action": "create", "project_id": "proj-uuid", "name": "feature/user-auth"}
```

### With Context Management
```json  
// Project automatically creates project-level context
// Use manage_context to add project-wide information
{"action": "update", "level": "project", "data": "{\"coding_standards\": \"ESLint + Prettier\"}"}
```

### With Task Management
```json
// Tasks are created within branches which belong to projects
// Project health automatically aggregates task metrics across all branches
```

## Performance Considerations

### Database Optimization
- **Indexed Queries**: Optimized lookups on project_id, owner_id, status
- **Aggregation Caching**: Health metrics cached with TTL and invalidation
- **Batch Operations**: Multiple project operations grouped efficiently
- **Connection Pooling**: Database connections reused across requests

### Health Monitoring Performance  
- **Incremental Updates**: Health scores updated incrementally vs full recalculation
- **Background Processing**: Heavy analytics computed asynchronously
- **Caching Strategy**: Frequently accessed metrics cached aggressively
- **Query Optimization**: Health queries optimized with proper indexes

## Usage Best Practices

### Project Organization
1. **Descriptive Names**: Use clear, specific project names
2. **Regular Health Checks**: Monitor project health weekly
3. **Regular Maintenance**: Run cleanup and validation operations periodically

### Team Collaboration
- **Shared Context**: Use project-level context for team knowledge
- **Health Monitoring**: Regular team review of health metrics
- **Blocker Management**: Address blockers promptly to maintain health
- **Documentation**: Maintain project metadata for historical reference

### Maintenance Management
- **Regular Cleanup**: Use cleanup_obsolete to remove unused resources
- **Integrity Checks**: Run validate_integrity periodically to ensure data consistency  
- **Agent Optimization**: Use rebalance_agents when team composition changes
- **Clean Deletion**: Only delete projects that are truly no longer needed