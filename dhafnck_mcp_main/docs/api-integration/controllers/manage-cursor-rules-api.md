# manage_rule - Cursor Rules Management API Documentation

## Overview

The `manage_rule` tool provides comprehensive management of IDE integration rules, hierarchical rule composition, client synchronization, and intelligent caching for AI agent development workflows. This system enables sophisticated rule orchestration across multiple IDE environments with automatic inheritance and conflict resolution.

## Base Information

- **Tool Name**: `manage_rule`
- **Controller**: `CursorRulesController`
- **Module**: `fastmcp.task_management.interface.mcp_controllers.cursor_rules_controller`
- **Handler**: `RuleManagementHandler`
- **Facade**: `RuleApplicationFacade`
- **Authentication**: Required (JWT-based)
- **Rate Limiting**: Applied per standard MCP limits
- **Multi-Tenant**: ✅ Full user isolation and rule separation

## Rule System Architecture

### Hierarchical Rule Structure
```
Core System Rules
├── Base IDE Rules (.cursorrules)
├── Project-Specific Rules
├── Agent-Specific Rules
└── User Customizations
```

### Rule Inheritance Chain
- **Core Rules**: Base system configuration
- **Project Rules**: Project-specific overrides and extensions  
- **Agent Rules**: Specialized AI agent configurations
- **User Rules**: Personal customizations and preferences

### Client Synchronization Model
- **Multi-Client Support**: Synchronize rules across multiple IDE instances
- **Conflict Resolution**: Automatic resolution with fallback strategies
- **Delta Sync**: Efficient incremental updates
- **Cache Invalidation**: Smart cache management for optimal performance

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
      "description": "[OPTIONAL] Target for action - rule path, client ID, or resource identifier"
    },
    "content": {
      "type": "string", 
      "description": "[OPTIONAL] Content or configuration data for the action"
    }
  },
  "required": ["action"],
  "additionalProperties": false
}
```

## Available Actions

### Core Rule Operations

| Action | Description | Target Format | Content Format |
|--------|-------------|---------------|----------------|
| `list` | List all available rules in system | Optional filter path | Optional JSON filter criteria |
| `backup` | Create backup of current rules | Optional backup name | Optional backup metadata |
| `restore` | Restore rules from backup | Backup identifier | Optional restore options |
| `clean` | Clean up obsolete/invalid rules | Optional scope filter | Optional cleanup criteria |
| `info` | Get basic rule system information | N/A | N/A |
| `enhanced_info` | Get comprehensive system status | N/A | N/A |

### Rule Analysis & Composition

| Action | Description | Target Format | Content Format |
|--------|-------------|---------------|----------------|
| `parse_rule` | Parse and validate specific rule | Rule file path | Optional validation options |
| `analyze_hierarchy` | Analyze rule dependency hierarchy | Optional root rule | Optional analysis depth |
| `get_dependencies` | Get dependencies for specific rule | Rule identifier | Optional dependency types |
| `compose_nested_rules` | Compose rules with inheritance | Target rule path | Source rules and options |
| `resolve_rule_inheritance` | Resolve inheritance chain | Rule identifier | Optional resolution options |
| `validate_rule_hierarchy` | Validate entire hierarchy integrity | Optional scope | Optional validation level |
| `build_hierarchy` | Build complete rule hierarchy tree | Optional root | Optional build options |
| `load_nested` | Load rules with nested dependencies | Rule set identifier | Optional load options |

### System Management

| Action | Description | Target Format | Content Format |
|--------|-------------|---------------|----------------|
| `load_core` | Load core system rules | Optional rule set | Optional load parameters |
| `cache_status` | Get rule cache status and metrics | Optional cache scope | N/A |

### Client Synchronization

| Action | Description | Target Format | Content Format |
|--------|-------------|---------------|----------------|
| `register_client` | Register new client for rule sync | Client identifier | Client configuration JSON |
| `authenticate_client` | Authenticate client for operations | Client identifier | Authentication credentials |
| `sync_client` | Synchronize rules with client | Client identifier | Sync options and preferences |
| `client_diff` | Get differences between client/server | Client identifier | Diff options |
| `resolve_conflicts` | Resolve rule conflicts for client | Client identifier | Resolution strategy |
| `client_status` | Get client synchronization status | Client identifier | N/A |
| `client_analytics` | Get client usage analytics | Client identifier | Analytics timeframe |

## JSON-RPC Request Format

### Basic Rule Information Request
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "manage_rule",
    "arguments": {
      "action": "info"
    }
  }
}
```

### Rule Hierarchy Analysis Request
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "manage_rule",
    "arguments": {
      "action": "analyze_hierarchy",
      "target": "rules/project/auth.mdc",
      "content": "{\"depth\": 5, \"include_dependencies\": true}"
    }
  }
}
```

### Client Registration Request
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "manage_rule",
    "arguments": {
      "action": "register_client",
      "target": "vscode_client_001",
      "content": "{\"client_type\": \"vscode\", \"version\": \"1.0.0\", \"capabilities\": [\"rule_sync\", \"auto_update\"]}"
    }
  }
}
```

### Rule Composition Request
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "manage_rule",
    "arguments": {
      "action": "compose_nested_rules",
      "target": "rules/composed/full_stack.mdc",
      "content": "{\"inherit_from\": [\"base.mdc\", \"typescript.mdc\", \"react.mdc\"], \"merge_strategy\": \"recursive\"}"
    }
  }
}
```

### Backup and Restore Requests
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "manage_rule",
    "arguments": {
      "action": "backup",
      "target": "daily_backup_20240908",
      "content": "{\"include_cache\": true, \"compress\": true}"
    }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "method": "tools/call",
  "params": {
    "name": "manage_rule",
    "arguments": {
      "action": "restore",
      "target": "daily_backup_20240908",
      "content": "{\"validate_before_restore\": true, \"backup_current\": true}"
    }
  }
}
```

## Response Format Examples

### Successful Rule Information Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": true,
    "action": "info",
    "data": {
      "system_status": "healthy",
      "total_rules": 47,
      "active_clients": 3,
      "cache_hit_rate": 0.94,
      "last_sync": "2024-09-08T15:30:00Z",
      "rules_summary": {
        "core_rules": 12,
        "project_rules": 23,
        "user_rules": 12
      }
    },
    "metadata": {
      "timestamp": "2024-09-08T15:45:23Z",
      "execution_time_ms": 42,
      "cache_status": "hit"
    },
    "workflow_guidance": {
      "next_actions": ["analyze_hierarchy", "client_status"],
      "suggestions": ["Consider running cache cleanup", "Review client sync status"],
      "performance_tips": ["Enable rule caching for better performance"]
    }
  }
}
```

### Rule Hierarchy Analysis Response
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "success": true,
    "action": "analyze_hierarchy",
    "data": {
      "rule_path": "rules/project/auth.mdc",
      "hierarchy_depth": 3,
      "dependencies": [
        {
          "rule": "rules/base/security.mdc",
          "type": "parent",
          "relationship": "inherits_from"
        },
        {
          "rule": "rules/core/jwt.mdc", 
          "type": "dependency",
          "relationship": "imports"
        }
      ],
      "inheritance_chain": [
        "rules/core/base.mdc",
        "rules/base/security.mdc",
        "rules/project/auth.mdc"
      ],
      "conflicts": [],
      "validation_status": "valid"
    },
    "diagnostics": {
      "circular_dependencies": false,
      "missing_dependencies": [],
      "optimization_suggestions": [
        "Consider flattening inheritance chain for better performance"
      ]
    },
    "impact_analysis": {
      "affected_clients": ["vscode_client_001", "cursor_client_002"],
      "estimated_sync_time": "2.3s",
      "breaking_changes": false
    }
  }
}
```

### Client Synchronization Response
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "success": true,
    "action": "sync_client",
    "data": {
      "client_id": "vscode_client_001",
      "sync_status": "completed",
      "rules_updated": 15,
      "rules_added": 3,
      "rules_removed": 1,
      "conflicts_resolved": 2,
      "sync_duration_ms": 1847
    },
    "client_impact": {
      "requires_restart": false,
      "affects_active_sessions": false,
      "new_capabilities": ["enhanced_completion", "rule_validation"]
    },
    "next_sync_recommendation": "2024-09-08T18:00:00Z"
  }
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "success": false,
    "error": "Rule validation failed: Circular dependency detected",
    "error_code": "VALIDATION_ERROR", 
    "details": {
      "rule": "rules/project/circular.mdc",
      "circular_path": ["rule_a.mdc", "rule_b.mdc", "rule_c.mdc", "rule_a.mdc"],
      "resolution_suggestions": [
        "Remove dependency from rule_c.mdc to rule_a.mdc",
        "Refactor common dependencies into shared base rule"
      ]
    },
    "diagnostics": {
      "validation_level": "strict",
      "affected_rules": 3,
      "suggested_actions": ["analyze_hierarchy", "resolve_conflicts"]
    }
  }
}
```

## IDE-Specific Rule Configurations

### Visual Studio Code Integration
```json
{
  "client_type": "vscode",
  "rule_format": ".cursorrules",
  "sync_interval": "5m",
  "auto_reload": true,
  "conflict_resolution": "merge_with_user_priority"
}
```

### Cursor IDE Integration
```json
{
  "client_type": "cursor",
  "rule_format": ".cursorrules", 
  "sync_interval": "2m",
  "auto_reload": true,
  "conflict_resolution": "server_priority"
}
```

### JetBrains Integration
```json
{
  "client_type": "jetbrains",
  "rule_format": ".ai-rules",
  "sync_interval": "10m", 
  "auto_reload": false,
  "conflict_resolution": "manual_review"
}
```

## Rule Priority and Override Patterns

### Priority Hierarchy (Highest to Lowest)
1. **User Override Rules** - Personal customizations
2. **Project-Specific Rules** - Project configuration
3. **Agent-Specialized Rules** - AI agent specific settings
4. **Core System Rules** - Base system configuration

### Override Strategies
- **Replace**: Completely override parent rule
- **Merge**: Combine with parent rule (arrays merged, objects deep merged)  
- **Extend**: Add to parent rule without replacement
- **Conditional**: Override based on conditions (file type, context, etc.)

### Example Rule Override
```markdown
# Project Rule Override
inherit_from: "core/typescript.mdc"
override_strategy: "merge"

# Custom project settings
project_specific:
  - Use strict TypeScript configuration
  - Enforce React hooks best practices  
  - Enable performance optimizations

# Override specific core rules
formatting:
  override: true
  tab_size: 2
  semicolons: required
```

## Workflow Patterns

### Initial System Setup
```bash
# 1. Get system status
action: "info"

# 2. Load core rules
action: "load_core"

# 3. Build hierarchy
action: "build_hierarchy" 

# 4. Validate system
action: "validate_rule_hierarchy"
```

### Rule Development Workflow
```bash
# 1. Backup current state
action: "backup"
target: "before_changes_backup"

# 2. Analyze current hierarchy
action: "analyze_hierarchy"
target: "rules/project/new_feature.mdc"

# 3. Compose new rules
action: "compose_nested_rules"
target: "rules/project/new_feature.mdc"
content: '{"inherit_from": ["base.mdc", "typescript.mdc"]}'

# 4. Validate changes
action: "validate_rule_hierarchy"

# 5. Sync with clients
action: "sync_client"
target: "all_clients"
```

### Client Onboarding Workflow  
```bash
# 1. Register client
action: "register_client"
target: "new_vscode_client"
content: '{"client_type": "vscode", "version": "1.0.0"}'

# 2. Authenticate client
action: "authenticate_client"
target: "new_vscode_client"

# 3. Initial sync
action: "sync_client" 
target: "new_vscode_client"

# 4. Verify sync status
action: "client_status"
target: "new_vscode_client"
```

### Troubleshooting Workflow
```bash
# 1. Get enhanced system info
action: "enhanced_info"

# 2. Check cache status
action: "cache_status"

# 3. Analyze hierarchy for issues
action: "analyze_hierarchy"

# 4. Get client analytics
action: "client_analytics"

# 5. Resolve any conflicts
action: "resolve_conflicts"
target: "affected_client_id"
```

## Error Codes and Troubleshooting

### Common Error Codes
- `MISSING_FIELD`: Required parameter missing
- `INVALID_ACTION`: Unknown action specified
- `VALIDATION_ERROR`: Rule validation failed
- `CIRCULAR_DEPENDENCY`: Circular dependency detected
- `CLIENT_NOT_FOUND`: Client identifier not registered
- `SYNC_CONFLICT`: Synchronization conflict occurred
- `CACHE_ERROR`: Cache operation failed
- `HIERARCHY_INVALID`: Rule hierarchy integrity compromised
- `AUTHENTICATION_FAILED`: Client authentication failed
- `INTERNAL_ERROR`: System internal error

### Troubleshooting Steps
1. **Check Action Validity**: Ensure action is in supported list
2. **Validate Parameters**: Verify required parameters provided
3. **Review Rule Syntax**: Use `parse_rule` for syntax validation
4. **Analyze Dependencies**: Use `analyze_hierarchy` to check dependencies
5. **Check Client Status**: Use `client_status` for sync issues
6. **Review Cache Health**: Use `cache_status` for performance issues
7. **Backup Before Changes**: Always backup before major modifications

## Performance Considerations

### Caching Strategy
- **Rule Cache**: Parsed rules cached for 1 hour
- **Hierarchy Cache**: Dependency trees cached for 30 minutes  
- **Client Cache**: Client-specific rules cached per sync interval
- **Invalidation**: Smart cache invalidation on rule updates

### Optimization Tips
- Use `enhanced_info` to monitor system performance
- Regular cache status monitoring with `cache_status`
- Batch client synchronization during low-usage periods
- Implement delta sync for large rule sets
- Use rule composition for reusable rule patterns

### Rate Limiting
- Standard MCP rate limits apply
- Client sync operations have dedicated limits
- Bulk operations (backup/restore) have extended timeouts
- Analytics requests have relaxed limits for monitoring

## Security Considerations

### Authentication
- JWT-based authentication required for all operations
- User-scoped rule access and isolation
- Client-specific authentication tokens
- Audit trail for all rule modifications

### Data Protection
- Rules encrypted in transit and at rest
- Client synchronization uses secure channels
- Backup encryption with user-managed keys
- Access control based on user permissions

### Best Practices
- Regularly rotate client authentication tokens
- Monitor client access patterns via analytics
- Implement rule change approval workflows
- Backup rules before major system updates
- Use conflict resolution strategies appropriate for team size

## Integration Examples

### CI/CD Pipeline Integration
```json
{
  "action": "sync_client",
  "target": "ci_pipeline_client", 
  "content": "{\"auto_deploy_rules\": true, \"validate_before_deploy\": true}"
}
```

### Team Collaboration Setup
```json
{
  "action": "register_client",
  "target": "team_shared_client",
  "content": "{\"shared_access\": true, \"conflict_resolution\": \"team_vote\", \"sync_interval\": \"1m\"}"
}
```

### Development Environment Sync
```json
{
  "action": "compose_nested_rules", 
  "target": "dev_environment.mdc",
  "content": "{\"inherit_from\": [\"base.mdc\", \"dev_tools.mdc\"], \"environment\": \"development\"}"
}
```