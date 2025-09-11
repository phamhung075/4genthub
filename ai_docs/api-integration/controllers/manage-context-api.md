# manage_context - Unified Context Management API Documentation

## Overview

The `manage_context` tool provides a unified 4-tier hierarchical context system (Global → Project → Branch → Task) with automatic inheritance, smart caching, delegation queues, and seamless data flow across sessions. Each user has their own global context instance for complete isolation.

## Base Information

- **Tool Name**: `manage_context`
- **Controller**: `UnifiedContextMCPController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.unified_context_controller`
- **Authentication**: Required (JWT-based with user scoping)
- **Hierarchy Levels**: 4-tier system with inheritance
- **Multi-Tenant**: ✅ Complete user isolation with user-scoped global contexts

## Context Hierarchy Structure

```
GLOBAL (per-user) ↓ inherits to
PROJECT          ↓ inherits to  
BRANCH           ↓ inherits to
TASK
```

### Inheritance Rules
- **Child contexts inherit from parents**: Task inherits from Branch → Project → Global
- **User isolation**: Each user has their own global context instance
- **Automatic cascading**: Updates can propagate down the hierarchy
- **Smart caching**: Inheritance chains cached with invalidation on updates

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Context operation to perform"
    },
    "level": {
      "type": "string",
      "description": "[OPTIONAL] Hierarchy level: 'global', 'project', 'branch', 'task'"
    },
    "context_id": {
      "type": "string", 
      "description": "[OPTIONAL] Context identifier (user_id for global, project_id for project, etc.)"
    },
    "data": {
      "type": "string",
      "description": "[OPTIONAL] Context data as JSON string"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authentication and global context"
    },
    "project_id": {
      "type": "string",
      "description": "[OPTIONAL] Project identifier for project-level operations"
    },
    "git_branch_id": {
      "type": "string", 
      "description": "[OPTIONAL] Git branch identifier for branch-level operations"
    },
    "force_refresh": {
      "type": "string",
      "description": "[OPTIONAL] Bypass cache: 'true', 'false', '1', '0'"
    },
    "include_inherited": {
      "type": "string",
      "description": "[OPTIONAL] Include parent data: 'true', 'false', '1', '0'"
    },
    "propagate_changes": {
      "type": "string",
      "description": "[OPTIONAL] Cascade to children: 'true', 'false', '1', '0'"
    },
    "delegate_to": {
      "type": "string",
      "description": "[OPTIONAL] Target level for delegation: 'global', 'project', 'branch', 'task'"
    },
    "delegate_data": {
      "type": "string",
      "description": "[OPTIONAL] Data to delegate as JSON string"
    },
    "delegation_reason": {
      "type": "string",
      "description": "[OPTIONAL] Reason for delegation for audit trails"
    },
    "content": {
      "type": "string",
      "description": "[OPTIONAL] Content for insights or progress operations"
    },
    "category": {
      "type": "string",
      "description": "[OPTIONAL] Insight category: 'technical', 'business', 'performance', 'risk', 'discovery'"
    },
    "importance": {
      "type": "string",
      "description": "[OPTIONAL] Importance level: 'low', 'medium', 'high', 'critical'"
    },
    "agent": {
      "type": "string",
      "description": "[OPTIONAL] Agent identifier for tracking contributions"
    },
    "filters": {
      "type": "string", 
      "description": "[OPTIONAL] Filter criteria as JSON string for list operations"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Core Context Operations

#### `create` - Create Context

Creates a new context at the specified hierarchy level.

**Required Parameters:**
- `action`: "create"
- `level`: Context level
- `context_id`: Appropriate identifier for the level

**Optional Parameters:**
- `data`: Initial context data as JSON
- `user_id`, `project_id`, `git_branch_id`: Hierarchy identifiers

**Level-Specific Context IDs:**
- `global`: Use `user_id` as `context_id`
- `project`: Use `project_id` as `context_id`
- `branch`: Use `git_branch_id` as `context_id`  
- `task`: Use `task_id` as `context_id`

**Example Request:**
```json
{
  "action": "create",
  "level": "project",
  "context_id": "proj-123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-550e8400-e29b-41d4-a716-446655440000",
  "data": "{\"project_info\": {\"name\": \"E-commerce Platform\", \"tech_stack\": [\"React\", \"Node.js\", \"PostgreSQL\"]}, \"core_features\": [\"user_auth\", \"product_catalog\", \"payment_processing\"]}"
}
```

**Example Response:**
```json
{
  "success": true,
  "operation": "create",
  "context": {
    "id": "proj-123e4567-e89b-12d3-a456-426614174000",
    "level": "project", 
    "user_id": "user-550e8400-e29b-41d4-a716-446655440000",
    "data": {
      "project_info": {
        "name": "E-commerce Platform",
        "tech_stack": ["React", "Node.js", "PostgreSQL"]
      },
      "core_features": ["user_auth", "product_catalog", "payment_processing"]
    },
    "created_at": "2025-01-27T10:40:00Z"
  },
  "hierarchy_info": {
    "inherits_from": "global",
    "global_context_id": "user-550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### `get` - Retrieve Context

Gets context data with optional inheritance resolution.

**Required Parameters:**
- `action`: "get"
- `level`: Context level
- `context_id`: Context identifier

**Optional Parameters:**
- `include_inherited`: Include parent context data
- `force_refresh`: Bypass cache

**Example Request:**
```json
{
  "action": "get",
  "level": "task", 
  "context_id": "task-987fcdeb-51a2-43d7-8b9f-123456789abc",
  "include_inherited": "true"
}
```

**Example Response with Inheritance:**
```json
{
  "success": true,
  "operation": "get",
  "context": {
    "id": "task-987fcdeb-51a2-43d7-8b9f-123456789abc",
    "level": "task",
    "data": {
      "task_specific": "Implementation details for JWT service",
      "progress": 75,
      "blockers": []
    }
  },
  "inherited_data": {
    "branch": {
      "development_guidelines": "Use TypeScript, test coverage >80%",
      "active_sprint": "Sprint 3"
    },
    "project": {
      "tech_stack": ["React", "Node.js", "PostgreSQL"],
      "coding_standards": "ESLint + Prettier"
    },
    "global": {
      "user_preferences": {"theme": "dark", "notifications": true},
      "global_patterns": ["JWT for auth", "REST API design"]
    }
  },
  "resolved_context": {
    // Merged data with task taking precedence over branch over project over global
  }
}
```

#### `update` - Update Context  

Updates context data with optional propagation to child levels.

**Required Parameters:**
- `action`: "update"
- `level`: Context level
- `context_id`: Context identifier

**Optional Parameters:**
- `data`: Updated data as JSON
- `propagate_changes`: Whether to cascade changes down

**Example Request:**
```json
{
  "action": "update",
  "level": "branch",
  "context_id": "branch-456e7890-f12b-34c5-d678-901234567efg", 
  "data": "{\"discoveries\": [\"PostgreSQL connection pooling needed\", \"Redis cache implementation complete\"], \"technical_decisions\": [\"Using pg-pool for connections\", \"JWT tokens expire in 24h\"], \"blockers\": [\"Waiting for SSL certificates\"]}",
  "propagate_changes": "true"
}
```

#### `delete` - Delete Context

Removes a context from the specified level.

**Required Parameters:**
- `action`: "delete"
- `level`: Context level
- `context_id`: Context identifier

### Advanced Operations

#### `resolve` - Resolve Complete Context

Resolves the complete context inheritance chain for a given level and ID.

**Required Parameters:**
- `action`: "resolve"
- `level`: Context level
- `context_id`: Context identifier

**Optional Parameters:**
- `force_refresh`: Force fresh data retrieval
- `include_inherited`: Include full inheritance chain

This provides the most comprehensive context view, merging all parent contexts with proper precedence rules.

#### `delegate` - Delegate Context Data

Moves or copies context data between hierarchy levels using a queue-based system.

**Required Parameters:**
- `action`: "delegate"
- `level`: Source level
- `context_id`: Source context ID
- `delegate_to`: Target level
- `delegate_data`: Data to delegate as JSON

**Optional Parameters:**
- `delegation_reason`: Audit trail reason

**Example Request:**
```json
{
  "action": "delegate",
  "level": "branch", 
  "context_id": "branch-456e7890-f12b-34c5-d678-901234567efg",
  "delegate_to": "project",
  "delegate_data": "{\"reusable_pattern\": {\"jwt_refresh_implementation\": \"Complete JWT refresh token pattern with automatic renewal\", \"usage_guide\": \"How to implement refresh tokens in other features\", \"code_examples\": \"RefreshTokenService.ts\"}}",
  "delegation_reason": "Reusable authentication pattern for other project features"
}
```

### Insight and Progress Operations

#### `add_insight` - Add Categorized Insight

Adds structured insights to context for knowledge capture.

**Required Parameters:**
- `action`: "add_insight"
- `level`: Context level
- `context_id`: Context identifier
- `content`: Insight content

**Optional Parameters:**
- `category`: Insight type (technical, business, performance, risk, discovery)
- `importance`: Priority level
- `agent`: Contributing agent ID

**Example Request:**
```json
{
  "action": "add_insight",
  "level": "task",
  "context_id": "task-987fcdeb-51a2-43d7-8b9f-123456789abc",
  "content": "JWT refresh tokens should be stored as httpOnly cookies to prevent XSS attacks. This requires CORS configuration updates for cross-domain requests.",
  "category": "technical", 
  "importance": "high",
  "agent": "security-auditor-agent"
}
```

#### `add_progress` - Add Progress Information  

Records progress updates in context for tracking and continuity.

**Required Parameters:**
- `action`: "add_progress"
- `level`: Context level
- `context_id`: Context identifier
- `content`: Progress description

**Optional Parameters:**
- `agent`: Agent making the progress update

#### `list` - List Contexts

Lists contexts at a specified level with filtering options.

**Required Parameters:**
- `action`: "list"
- `level`: Context level

**Optional Parameters:**
- `filters`: JSON filter criteria
- `user_id`: User context for scoping

## Project Context Database Structure

**⚠️ CRITICAL**: Project contexts have 4 predefined database columns:

### Standard Columns
- **`team_preferences`**: Team settings and preferences
- **`technology_stack`**: Technology choices and decisions (NOT `technical_stack`!)
- **`project_workflow`**: Workflow and process definitions  
- **`local_standards`**: Project standards and conventions

### Custom Data Storage
Any other fields are automatically stored in **`local_standards._custom`**:

```json
// ✅ CORRECT - Maps to proper columns
{
  "team_preferences": {"review_required": true, "pair_programming": false},
  "technology_stack": {"frontend": ["React", "TypeScript"], "backend": ["Node.js", "Express"]}, 
  "project_workflow": {"phases": ["design", "develop", "test", "deploy"]},
  "local_standards": {"naming": "camelCase", "testing": "Jest"}
}

// ⚠️ CUSTOM - Goes to local_standards._custom
{
  "project_info": {...},        // -> local_standards._custom.project_info
  "core_features": {...},       // -> local_standards._custom.core_features
  "technical_stack": {...}      // -> local_standards._custom.technical_stack (wrong key!)
}
```

## Caching and Performance

### Smart Caching Strategy
- **Resolution Results**: Full inheritance chains cached with TTL
- **Individual Contexts**: Cached per level and ID
- **Invalidation**: Automatic cache clearing on updates
- **Preloading**: Common inheritance paths pre-cached

### Performance Optimizations
- **Batch Operations**: Multiple context operations in single transaction
- **Lazy Loading**: Child contexts loaded on demand
- **Efficient Queries**: Optimized database queries with proper indexing
- **Connection Pooling**: Database connection reuse

## Error Handling

### Common Error Codes
- `CONTEXT_NOT_FOUND`: Context doesn't exist at specified level
- `INVALID_LEVEL`: Level not in allowed values
- `INVALID_CONTEXT_ID`: Context ID format invalid
- `PERMISSION_DENIED`: User lacks access to context
- `INVALID_JSON`: Data parameter not valid JSON
- `DELEGATION_FAILED`: Delegation operation failed
- `INHERITANCE_ERROR`: Error resolving inheritance chain

### Example Error Response
```json
{
  "success": false,
  "error": "Invalid JSON in data parameter: Expecting ',' delimiter: line 2 column 15 (char 45)",
  "error_code": "INVALID_JSON",
  "operation": "create",
  "field": "data",
  "hint": "Ensure data parameter contains valid JSON"
}
```

## Usage Patterns

### Cross-Session Information Sharing
```json
// Session 1: Store discovery
{"action": "update", "level": "branch", "data": "{\"api_endpoints\": [\"/auth/login\", \"/auth/refresh\"]}"}

// Session 2: Retrieve and build upon
{"action": "resolve", "level": "branch", "include_inherited": "true"}
```

### Agent Coordination
```json
// Agent 1 adds technical insights
{"action": "add_insight", "content": "Database schema needs indexes", "agent": "@database_agent"}

// Agent 2 builds upon those insights  
{"action": "add_progress", "content": "Added indexes based on database analysis", "agent": "coding-agent"}
```

### Knowledge Delegation Workflow
```json
// 1. Discover pattern at task level
{"action": "add_insight", "level": "task", "content": "Reusable error handling pattern"}

// 2. Delegate to project level for reuse
{"action": "delegate", "level": "task", "delegate_to": "project", "delegation_reason": "Reusable across all features"}

// 3. Other tasks inherit the pattern
{"action": "resolve", "level": "task", "context_id": "other-task", "include_inherited": "true"}
```

## Integration with Other Tools

### Task and Subtask Integration
- Tasks automatically create context entries when needed
- Subtask insights flow up to parent task context
- Task completion updates propagate to branch context

### Agent Assignment
- Agents receive full resolved context for their assignments
- Agent contributions tracked in context with attribution
- Cross-agent collaboration facilitated through shared context

### Vision System Integration
- AI insights automatically captured in context
- Context provides historical knowledge for better AI recommendations
- Pattern recognition across context hierarchy levels

## Advanced Features

### Delegation Queue System
- **Asynchronous Processing**: Delegations processed via queue
- **Conflict Resolution**: Automatic handling of conflicting delegations  
- **Audit Trail**: Complete history of delegation operations
- **Rollback Support**: Ability to reverse delegation operations

### Inheritance Chain Optimization  
- **Path Caching**: Common inheritance paths cached
- **Incremental Updates**: Only changed data propagated
- **Conflict Resolution**: Child data takes precedence over parent
- **Schema Validation**: Data validated against level requirements

This unified context system enables persistent, shareable knowledge management across all levels of project organization with complete user isolation and intelligent data flow.