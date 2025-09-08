# manage_rule - Rule Management API Documentation

## Overview

The `manage_rule` tool provides comprehensive rule orchestration functionality with hierarchical rule management, client synchronization, caching, and intelligent rule composition. It supports rule lifecycle operations, dependency analysis, inheritance resolution, and distributed rule consistency across clients.

## Base Information

- **Tool Name**: `manage_rule`
- **Controller**: `RuleOrchestrationController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.rule_orchestration_controller`
- **Authentication**: Optional (user_id parameter for audit trails)
- **Rule Storage**: File-based with cache layer
- **Multi-Client**: ✅ Distributed rule synchronization supported

## Rule Hierarchy System

The rule system supports hierarchical organization with inheritance:

```
Global Rules          ← Organization-wide policies
└── Project Rules     ← Project-specific configurations
    └── Component Rules  ← Component-level customizations
```

### Inheritance Rules
- **Most specific wins**: Component → Project → Global precedence
- **Automatic composition**: Rules inherit from parent levels
- **Conflict resolution**: Configurable merge strategies
- **Cache optimization**: Smart caching with dependency tracking

## Parameters Schema

```json
{
  "type": "object",
  "properties": {
    "action": {
      "type": "string",
      "required": true,
      "description": "Rule management action to perform"
    },
    "target": {
      "type": "string",
      "description": "[OPTIONAL] Rule name, path, client ID, or resource identifier"
    },
    "content": {
      "type": "string", 
      "description": "[OPTIONAL] Rule content, configuration data, or operation parameters"
    },
    "user_id": {
      "type": "string",
      "description": "[OPTIONAL] User identifier for authentication and audit trails"
    }
  },
  "required": ["action"]
}
```

## Available Actions

### Core Rule Operations

#### `list` - List Available Rules
Lists all available rules in the system.

**Parameters:**
- `target` (optional): Rule category or path filter
- `content` (optional): Additional listing options

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "list",
    "target": "security_rules"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "rules": [
    {
      "name": "security_rules",
      "path": "/rules/security/base.json",
      "type": "security",
      "last_modified": "2024-01-15T10:30:00Z",
      "size": 2048
    }
  ],
  "total_count": 15,
  "workflow_guidance": "Use 'info' action to get details about specific rules"
}
```

#### `info` - Get Rule System Information
Retrieves comprehensive information about the rule system state.

**Parameters:**
- `target` (optional): Specific rule or component to analyze
- `content` (optional): Information depth level

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "info",
    "target": "auth_system"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "system_info": {
    "total_rules": 25,
    "active_rules": 23,
    "cache_hit_rate": 0.85,
    "last_sync": "2024-01-15T09:45:00Z"
  },
  "rule_categories": ["security", "validation", "routing", "auth"],
  "hierarchy_depth": 3,
  "performance_metrics": {
    "avg_load_time": "15ms",
    "memory_usage": "2.1MB"
  }
}
```

### Rule Lifecycle Operations

#### `backup` - Create Rule Backup
Creates a backup of current rule configuration.

**Parameters:**
- `target` (optional): Specific rules to backup (default: all)
- `content` (optional): Backup metadata or options

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "backup",
    "target": "production_rules",
    "content": "{\"include_cache\": true, \"compression\": \"gzip\"}"
  }
}
```

#### `restore` - Restore Rules from Backup
Restores rules from a previous backup.

**Parameters:**
- `target` (optional): Backup identifier or path
- `content` (optional): Restore options and filters

#### `clean` - Clean Obsolete Rules
Removes obsolete or invalid rules from the system.

**Parameters:**
- `target` (optional): Specific rule category to clean
- `content` (optional): Cleanup criteria and options

### Rule Analysis and Hierarchy

#### `analyze_hierarchy` - Analyze Rule Dependencies
Analyzes rule hierarchy and dependencies before modifications.

**Parameters:**
- `target` (required): Rule or rule set to analyze
- `content` (optional): Analysis depth and options

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "analyze_hierarchy",
    "target": "security_rules",
    "content": "{\"include_dependents\": true, \"depth\": 5}"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "hierarchy_analysis": {
    "dependencies": [
      {
        "rule": "base_security",
        "type": "parent",
        "relationship": "inherits_from"
      },
      {
        "rule": "auth_rules",
        "type": "child",
        "relationship": "inherited_by"
      }
    ],
    "dependency_depth": 3,
    "circular_dependencies": [],
    "impact_scope": ["auth_system", "user_management"]
  },
  "modification_warnings": [
    "Changes will affect 5 dependent rules",
    "Consider testing in staging environment"
  ]
}
```

#### `get_dependencies` - Get Rule Dependency Graph
Returns the complete dependency graph for rules.

**Parameters:**
- `target` (optional): Starting rule for dependency traversal
- `content` (optional): Graph traversal options

#### `validate_rule_hierarchy` - Validate Rule Structure
Validates the integrity of rule hierarchy and relationships.

**Parameters:**
- `target` (optional): Specific rule branch to validate
- `content` (optional): Validation criteria

### Rule Composition and Inheritance

#### `compose_nested_rules` - Compose Rules with Inheritance
Composes rules applying inheritance and composition rules.

**Parameters:**
- `target` (required): Rule path or identifier
- `content` (optional): Composition options (e.g., "inherit:base_security")

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "compose_nested_rules",
    "target": "auth_rules",
    "content": "inherit:base_security,merge_strategy:recursive"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "composed_rules": {
    "auth_rules": {
      "base_rules": ["base_security", "user_validation"],
      "composed_content": {
        "authentication": {
          "jwt_expiry": "24h",
          "refresh_token": true,
          "encryption": "AES256"
        }
      },
      "inheritance_chain": ["global", "project", "component"]
    }
  },
  "composition_metadata": {
    "rules_merged": 3,
    "conflicts_resolved": 1,
    "final_size": "4.2KB"
  }
}
```

#### `resolve_rule_inheritance` - Resolve Inheritance Chain
Resolves and flattens rule inheritance chain.

**Parameters:**
- `target` (required): Rule identifier
- `content` (optional): Resolution strategy

#### `build_hierarchy` - Build Complete Rule Hierarchy
Builds the complete rule hierarchy structure.

**Parameters:**
- `target` (optional): Root rule or scope
- `content` (optional): Hierarchy build options

#### `load_nested` - Load Nested Rule Structures
Loads complex nested rule structures with dependencies.

**Parameters:**
- `target` (required): Root rule identifier
- `content` (optional): Loading strategy and depth

### Performance and Caching

#### `cache_status` - Get Cache Status and Metrics
Returns rule cache status and performance metrics.

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "cache_status"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "cache_metrics": {
    "hit_rate": 0.87,
    "miss_rate": 0.13,
    "total_requests": 1520,
    "cache_size": "3.2MB",
    "max_size": "10MB"
  },
  "performance_data": {
    "avg_lookup_time": "2ms",
    "slowest_rules": [
      {"rule": "complex_validation", "load_time": "45ms"}
    ]
  },
  "optimization_suggestions": [
    "Consider pre-loading frequently used rules",
    "Rule 'complex_validation' may benefit from simplification"
  ]
}
```

### Client Synchronization

#### `register_client` - Register Synchronization Client
Registers a client for rule synchronization.

**Parameters:**
- `target` (required): Client identifier
- `content` (required): Client configuration as JSON string

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "register_client",
    "target": "frontend_app_v2",
    "content": "{\"sync_frequency\": \"5m\", \"rule_categories\": [\"ui\", \"validation\"], \"auth_token\": \"jwt_token_here\"}"
  }
}
```

#### `authenticate_client` - Authenticate Client
Authenticates a client for secure rule access.

**Parameters:**
- `target` (required): Client identifier
- `content` (required): Authentication credentials

#### `sync_client` - Synchronize Rules with Client
Synchronizes rules between server and client.

**Parameters:**
- `target` (required): Client identifier
- `content` (optional): Sync operation ("push", "pull", "bidirectional")

**Example Request:**
```json
{
  "method": "manage_rule",
  "params": {
    "action": "sync_client",
    "target": "mobile_app_v1",
    "content": "push"
  }
}
```

**Example Response:**
```json
{
  "success": true,
  "sync_result": {
    "operation": "push",
    "rules_synchronized": 12,
    "conflicts_resolved": 2,
    "sync_duration": "340ms",
    "client_version": "1.2.3",
    "server_version": "2.1.0"
  },
  "sync_summary": {
    "added": 3,
    "updated": 8,
    "deleted": 1,
    "conflicts": 2
  }
}
```

#### `client_diff` - Get Client-Server Differences
Compares client and server rule versions.

**Parameters:**
- `target` (required): Client identifier
- `content` (optional): Comparison options

#### `resolve_conflicts` - Resolve Rule Conflicts
Automatically resolves conflicts between client and server rules.

**Parameters:**
- `target` (required): Client identifier or conflict context
- `content` (optional): Resolution strategy

#### `client_status` - Get Client Synchronization Status
Returns the synchronization status of a specific client.

**Parameters:**
- `target` (required): Client identifier

#### `client_analytics` - Get Client Usage Analytics
Returns usage analytics and performance metrics for clients.

**Parameters:**
- `target` (optional): Specific client or "all"
- `content` (optional): Analytics time range and metrics

## Advanced Rule Operations

#### `load_core` - Load Core System Rules
Loads essential core system rules.

**Parameters:**
- `target` (optional): Core rule category
- `content` (optional): Loading options

#### `parse_rule` - Parse and Validate Rule Syntax
Parses rule content and validates syntax.

**Parameters:**
- `target` (optional): Rule identifier
- `content` (required): Rule content to parse and validate

#### `enhanced_info` - Get Enhanced Rule Information
Returns detailed rule information with AI-generated insights.

**Parameters:**
- `target` (optional): Rule or system component
- `content` (optional): Information detail level

## Usage Patterns and Best Practices

### Rule Discovery Workflow
```json
// 1. Get system overview
{"action": "info"}

// 2. List available rules
{"action": "list", "target": "security"}

// 3. Analyze specific rule hierarchy
{"action": "analyze_hierarchy", "target": "auth_rules"}

// 4. Get dependency information
{"action": "get_dependencies", "target": "auth_rules"}
```

### Rule Modification Workflow
```json
// 1. Create backup
{"action": "backup", "target": "production_rules"}

// 2. Analyze impact
{"action": "analyze_hierarchy", "target": "target_rule"}

// 3. Validate before changes
{"action": "validate_rule_hierarchy", "target": "target_rule"}

// 4. Apply composition
{"action": "compose_nested_rules", "target": "target_rule", "content": "inherit:base_rules"}

// 5. Sync with clients
{"action": "sync_client", "target": "all_clients", "content": "push"}
```

### Client Onboarding Workflow
```json
// 1. Register new client
{"action": "register_client", "target": "new_client", "content": "{...client_config...}"}

// 2. Authenticate client
{"action": "authenticate_client", "target": "new_client", "content": "{...auth_credentials...}"}

// 3. Initial sync
{"action": "sync_client", "target": "new_client", "content": "pull"}

// 4. Verify client status
{"action": "client_status", "target": "new_client"}
```

## Error Handling

### Common Error Responses

#### Invalid Action
```json
{
  "success": false,
  "error": "Unknown action 'invalid_action'",
  "error_code": "INVALID_ACTION",
  "available_actions": ["list", "info", "backup", "restore", "clean", "..."]
}
```

#### Rule Not Found
```json
{
  "success": false,
  "error": "Rule 'non_existent_rule' not found",
  "error_code": "RULE_NOT_FOUND",
  "suggestions": ["auth_rules", "security_rules", "validation_rules"]
}
```

#### Validation Error
```json
{
  "success": false,
  "error": "Rule validation failed",
  "error_code": "VALIDATION_ERROR",
  "validation_errors": [
    {
      "field": "authentication.jwt_secret",
      "message": "JWT secret must be at least 32 characters",
      "line": 15
    }
  ]
}
```

#### Client Sync Error
```json
{
  "success": false,
  "error": "Client synchronization failed",
  "error_code": "SYNC_ERROR", 
  "details": {
    "client_id": "mobile_app_v1",
    "reason": "Authentication token expired",
    "retry_after": "300s"
  }
}
```

## Response Enhancements

All responses can include additional metadata for better AI integration:

```json
{
  "success": true,
  "data": "...",
  "workflow_guidance": "Consider validating rule hierarchy after composition",
  "hierarchy_insights": "This rule affects 3 downstream components",
  "conflict_analysis": "No conflicts detected in current operation",
  "performance_metrics": {
    "operation_time": "125ms",
    "cache_hits": 5,
    "cache_misses": 1
  },
  "security_analysis": "Rule changes meet security compliance requirements",
  "optimization_suggestions": [
    "Consider caching frequently accessed rules",
    "Rule complexity could be reduced by 20%"
  ]
}
```

## Security and Authentication

- **User Isolation**: Rules can be scoped to specific users via `user_id` parameter
- **Audit Trails**: All operations logged with user attribution
- **Client Authentication**: JWT-based authentication for client synchronization
- **Rule Validation**: Automatic security validation for rule content
- **Access Control**: Role-based access to rule operations

## Performance Considerations

- **Smart Caching**: Automatic caching with dependency-based invalidation
- **Lazy Loading**: Rules loaded on demand with predictive pre-loading
- **Compression**: Rule content compressed for efficient storage and transfer
- **Batch Operations**: Multiple rules can be processed in single operations
- **Performance Monitoring**: Built-in metrics and optimization suggestions

## Integration Examples

### JSON-RPC 2.0 Format
All requests follow JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "manage_rule",
  "params": {
    "action": "compose_nested_rules",
    "target": "auth_system",
    "content": "inherit:base_security,merge_strategy:deep",
    "user_id": "user_123"
  }
}
```

Response:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "success": true,
    "composed_rules": "...",
    "workflow_guidance": "..."
  }
}
```

This comprehensive API documentation covers all aspects of the `manage_rule` tool, providing developers with complete information needed for integration and usage.