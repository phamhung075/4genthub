# manage_project - Project Management API Documentation

## Overview

The `manage_project` tool provides comprehensive project lifecycle management including creation, configuration, health monitoring, analytics, and coordination across the multi-tenant DhafnckMCP platform. It serves as the top-level organizational container for all project activities.

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
    "status": {
      "type": "string",
      "description": "[OPTIONAL] Project status: 'active', 'inactive', 'archived', 'completed'"
    },
    "settings": {
      "type": "string",
      "description": "[OPTIONAL] Project configuration as JSON string"
    },
    "metadata": {
      "type": "string",
      "description": "[OPTIONAL] Additional metadata as JSON string"
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
- `settings`: Initial configuration as JSON
- `metadata`: Additional metadata as JSON
- `status`: Initial status (default: "active")

**Example Request:**
```json
{
  "action": "create",
  "name": "E-commerce Platform V2",
  "description": "Next generation e-commerce platform with microservices architecture",
  "settings": "{\"tech_stack\": [\"React\", \"Node.js\", \"PostgreSQL\", \"Redis\"], \"deployment\": \"AWS\", \"ci_cd\": \"GitHub Actions\"}",
  "metadata": "{\"client\": \"Acme Corp\", \"timeline\": \"6 months\", \"team_size\": 8, \"budget\": \"$250k\"}"
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
    "status": "active",
    "owner_id": "user-550e8400-e29b-41d4-a716-446655440000",
    "settings": {
      "tech_stack": ["React", "Node.js", "PostgreSQL", "Redis"],
      "deployment": "AWS",
      "ci_cd": "GitHub Actions"
    },
    "metadata": {
      "client": "Acme Corp",
      "timeline": "6 months", 
      "team_size": 8,
      "budget": "$250k"
    },
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
    "status": "active",
    "owner_id": "user-550e8400-e29b-41d4-a716-446655440000",
    "settings": {...},
    "metadata": {...},
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
- `status`: New status  
- `settings`: Updated settings as JSON
- `metadata`: Updated metadata as JSON

**Example Request:**
```json
{
  "action": "update",
  "project_id": "proj-123e4567-e89b-12d3-a456-426614174000",
  "status": "active",
  "settings": "{\"tech_stack\": [\"React\", \"Node.js\", \"PostgreSQL\", \"Redis\"], \"deployment\": \"AWS\", \"ci_cd\": \"GitHub Actions\", \"monitoring\": \"DataDog\"}",
  "metadata": "{\"client\": \"Acme Corp\", \"timeline\": \"6 months\", \"team_size\": 10, \"budget\": \"$280k\"}"
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
- `status`: Filter by project status
- `limit`: Maximum results to return
- `offset`: Pagination offset

**Example Request:**
```json
{
  "action": "list",
  "status": "active"
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
      "status": "active",
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
      "status": "active", 
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

### Advanced Operations  

#### `archive` - Archive Completed Project

Archives a completed project while preserving data for historical reference.

**Required Parameters:**
- `action`: "archive"
- `project_id`: Project UUID

**Optional Parameters:**
- `archive_reason`: Reason for archiving
- `preserve_contexts`: Whether to keep context data

#### `restore` - Restore Archived Project

Restores an archived project back to active status.

**Required Parameters:**
- `action`: "restore"
- `project_id`: Project UUID

#### `clone` - Clone Project Structure

Creates a new project based on an existing project's structure and configuration.

**Required Parameters:**
- `action`: "clone"
- `project_id`: Source project UUID
- `name`: New project name

**Optional Parameters:**
- `clone_tasks`: Whether to clone tasks (default: false)
- `clone_contexts`: Whether to clone context data (default: false)

## Project Configuration Schema

### Settings Structure
The `settings` parameter accepts JSON with these common fields:

```json
{
  "tech_stack": ["React", "Node.js", "PostgreSQL"],
  "deployment": "AWS",
  "ci_cd": "GitHub Actions", 
  "monitoring": "DataDog",
  "testing": {
    "framework": "Jest",
    "coverage_threshold": 80,
    "e2e_tools": ["Cypress", "Playwright"]
  },
  "code_quality": {
    "linter": "ESLint",
    "formatter": "Prettier", 
    "type_checking": "TypeScript"
  },
  "security": {
    "vulnerability_scanning": true,
    "dependency_checks": true,
    "code_analysis": "SonarQube"
  }
}
```

### Metadata Structure
The `metadata` parameter accepts JSON with project-specific information:

```json
{
  "client": "Acme Corporation",
  "timeline": "6 months",
  "budget": "$250,000",
  "team_size": 8,
  "priority": "high",
  "stakeholders": ["john.doe@acme.com", "jane.smith@acme.com"],
  "business_objectives": [
    "Increase online sales by 30%",
    "Improve customer satisfaction",
    "Reduce cart abandonment by 20%"
  ],
  "success_metrics": {
    "performance": "Page load < 2s",
    "availability": "99.9% uptime", 
    "user_growth": "25% increase in MAU"
  }
}
```

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
- `INVALID_STATUS`: Status not in allowed values
- `INVALID_JSON`: Settings or metadata not valid JSON

### Business Logic Errors  
- `PROJECT_HAS_ACTIVE_BRANCHES`: Cannot delete project with active branches
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions for operation
- `ARCHIVE_FAILED`: Cannot archive project with incomplete tasks
- `CLONE_FAILED`: Source project clone operation failed

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
2. **Comprehensive Settings**: Configure tech stack and tools upfront  
3. **Regular Health Checks**: Monitor project health weekly
4. **Metadata Maintenance**: Keep stakeholder and timeline info current
5. **Status Updates**: Update project status as work progresses

### Team Collaboration
- **Shared Context**: Use project-level context for team knowledge
- **Health Monitoring**: Regular team review of health metrics
- **Blocker Management**: Address blockers promptly to maintain health
- **Documentation**: Maintain project metadata for historical reference

### Lifecycle Management  
- **Proper Archiving**: Archive completed projects with comprehensive metadata
- **Clean Deletion**: Only delete projects that are truly no longer needed
- **Cloning Strategy**: Use cloning for similar project structures
- **Status Progression**: Follow logical status progression (active → completed → archived)