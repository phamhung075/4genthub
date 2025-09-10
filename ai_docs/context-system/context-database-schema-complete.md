# Complete Context System Database Schema Documentation

## Overview
The DhafnckMCP Context System uses a 4-tier hierarchical structure where each level has specific database columns and field mappings. This document provides the definitive guide for working with contexts at each level.

## Database Tables and Column Structure

### 1. GLOBAL CONTEXT (`global_contexts` table)
**Purpose**: Organization-wide or user-specific global settings and standards

#### Database Columns:
```sql
- id: String(36) PRIMARY KEY
- organization_id: String(36) NULLABLE
- user_id: String NOT NULL (user isolation)
- autonomous_rules: JSON NOT NULL DEFAULT {}
- security_policies: JSON NOT NULL DEFAULT {}
- coding_standards: JSON NOT NULL DEFAULT {}
- workflow_templates: JSON NOT NULL DEFAULT {}
- delegation_rules: JSON NOT NULL DEFAULT {}
- created_at: DateTime
- updated_at: DateTime
- version: Integer DEFAULT 1
```

#### Field Mapping:
| Field Name | Database Column | Storage Behavior |
|------------|----------------|------------------|
| `autonomous_rules` | `autonomous_rules` | Direct storage in dedicated column |
| `security_policies` | `security_policies` | Direct storage in dedicated column |
| `coding_standards` | `coding_standards` | Direct storage in dedicated column |
| `workflow_templates` | `workflow_templates` | Direct storage in dedicated column |
| `delegation_rules` | `delegation_rules` | Direct storage in dedicated column |
| Any other field | `workflow_templates._custom.{field}` | Stored under _custom key |

#### Correct Usage Example:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="global",
    context_id="global-{user_id}",
    data={
        "autonomous_rules": {"auto_fix": True, "max_retries": 3},
        "security_policies": {"require_2fa": True, "session_timeout": 3600},
        "coding_standards": {"language": "python", "style": "pep8"},
        "workflow_templates": {"pr_template": "...", "issue_template": "..."},
        "delegation_rules": {"auto_delegate_threshold": 0.8}
    }
)
```

### 2. PROJECT CONTEXT (`project_contexts` table)
**Purpose**: Project-specific configuration and standards

#### Database Columns:
```sql
- id: String(36) PRIMARY KEY
- project_id: String(36) NULLABLE
- parent_global_id: String(36) FOREIGN KEY NULLABLE
- user_id: String NOT NULL (user isolation)
- data: JSON NULLABLE DEFAULT {}
- team_preferences: JSON NULLABLE DEFAULT {}
- technology_stack: JSON NULLABLE DEFAULT {}
- project_workflow: JSON NULLABLE DEFAULT {}
- local_standards: JSON NULLABLE DEFAULT {}
- global_overrides: JSON NULLABLE DEFAULT {}
- delegation_rules: JSON NULLABLE DEFAULT {}
- created_at: DateTime
- updated_at: DateTime
- version: Integer
- inheritance_disabled: Boolean DEFAULT False
```

#### Field Mapping:
| Field Name | Database Column | Storage Behavior |
|------------|----------------|------------------|
| `team_preferences` | `team_preferences` | Direct storage in dedicated column |
| `technology_stack` | `technology_stack` | Direct storage in dedicated column |
| `project_workflow` | `project_workflow` | Direct storage in dedicated column |
| `local_standards` | `local_standards` | Direct storage in dedicated column |
| `global_overrides` | `global_overrides` | Used for metadata |
| `delegation_rules` | `delegation_rules` | Used for metadata |
| Any other field | `local_standards._custom.{field}` | Stored under _custom key |

#### Common Mistake - Wrong Field Names:
```python
# ❌ INCORRECT - These fields will go to local_standards._custom
data={
    "technical_stack": {...},  # Wrong! Should be "technology_stack"
    "project_info": {...},      # Custom field - goes to _custom
    "core_features": {...}      # Custom field - goes to _custom
}
```

#### Correct Usage Example:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="project",
    context_id=project_id,
    data={
        "team_preferences": {
            "code_review_required": True,
            "min_reviewers": 2,
            "working_hours": "9-5 EST"
        },
        "technology_stack": {  # NOT "technical_stack"!
            "frontend": ["React", "TypeScript", "Tailwind"],
            "backend": ["Python", "FastAPI", "SQLAlchemy"],
            "database": ["PostgreSQL", "Redis"],
            "infrastructure": ["Docker", "Kubernetes"]
        },
        "project_workflow": {
            "branches": ["main", "develop", "feature/*"],
            "deployment_stages": ["dev", "staging", "production"],
            "release_cycle": "2 weeks"
        },
        "local_standards": {
            "naming_convention": "snake_case",
            "test_coverage_min": 80,
            "documentation_required": True
        }
    }
)
```

### 3. BRANCH CONTEXT (`branch_contexts` table)
**Purpose**: Git branch or feature-specific settings

#### Database Columns:
```sql
- id: String(36) PRIMARY KEY
- branch_id: String(36) FOREIGN KEY NULLABLE
- parent_project_id: String(36) FOREIGN KEY NULLABLE
- user_id: String NOT NULL (user isolation)
- data: JSON NULLABLE DEFAULT {}
- branch_workflow: JSON NULLABLE DEFAULT {}
- feature_flags: JSON NULLABLE DEFAULT {}
- active_patterns: JSON NULLABLE DEFAULT {}
- local_overrides: JSON NULLABLE DEFAULT {}
- delegation_rules: JSON NULLABLE DEFAULT {}
- inheritance_disabled: Boolean DEFAULT False
- created_at: DateTime
- updated_at: DateTime
- version: Integer
```

#### Field Mapping:
| Field Name | Database Column | Storage Behavior |
|------------|----------------|------------------|
| `branch_workflow` | `branch_workflow` | Direct storage in dedicated column |
| `feature_flags` | `feature_flags` | Direct storage in dedicated column |
| `active_patterns` | `active_patterns` | Direct storage in dedicated column |
| `local_overrides` | `local_overrides` | Direct storage in dedicated column |
| `delegation_rules` | `delegation_rules` | Used for metadata |
| Any other field | `feature_flags._custom.{field}` | Stored under _custom key |

#### Repository Implementation Note:
The branch repository maps some fields differently internally:
- `branch_standards` → stored in `feature_flags`
- `agent_assignments` → stored in `active_patterns`

#### Correct Usage Example:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="branch",
    context_id=branch_id,
    data={
        "branch_workflow": {
            "merge_strategy": "squash",
            "require_ci_pass": True,
            "auto_delete_after_merge": True
        },
        "feature_flags": {
            "enable_new_auth": True,
            "use_experimental_api": False,
            "debug_mode": True
        },
        "active_patterns": {
            "repository_pattern": True,
            "factory_pattern": True,
            "observer_pattern": False
        },
        "local_overrides": {
            "bypass_review": False,
            "custom_deploy_script": "deploy-feature.sh"
        }
    }
)
```

### 4. TASK CONTEXT (`task_contexts` table)
**Purpose**: Individual task execution context and discoveries

#### Database Columns:
```sql
- id: String(36) PRIMARY KEY
- task_id: String(36) FOREIGN KEY NULLABLE
- parent_branch_id: String(36) FOREIGN KEY NULLABLE
- parent_branch_context_id: String(36) FOREIGN KEY NULLABLE
- user_id: String NOT NULL (user isolation)
- data: JSON NULLABLE DEFAULT {}
- task_data: JSON NULLABLE DEFAULT {}
- execution_context: JSON NULLABLE DEFAULT {}
- discovered_patterns: JSON NULLABLE DEFAULT {}
- local_decisions: JSON NULLABLE DEFAULT {}
- delegation_queue: JSON NULLABLE DEFAULT {}
- local_overrides: JSON NULLABLE DEFAULT {}
- implementation_notes: JSON NULLABLE DEFAULT {}
- delegation_triggers: JSON NULLABLE DEFAULT {}
- inheritance_disabled: Boolean DEFAULT False
- force_local_only: Boolean DEFAULT False
- created_at: DateTime
- updated_at: DateTime
- version: Integer
```

#### Field Mapping:
| Field Name | Database Column | Storage Behavior |
|------------|----------------|------------------|
| `task_data` | `task_data` | Direct storage in dedicated column |
| `execution_context` | `execution_context` | Direct storage in dedicated column |
| `discovered_patterns` | `discovered_patterns` | Direct storage in dedicated column |
| `local_decisions` | `local_decisions` | Direct storage in dedicated column |
| `delegation_queue` | `delegation_queue` | Direct storage in dedicated column |
| `local_overrides` | `local_overrides` | Direct storage in dedicated column |
| `implementation_notes` | `implementation_notes` | Direct storage in dedicated column |
| `delegation_triggers` | `delegation_triggers` | Direct storage in dedicated column |
| Any other field | `data.{field}` | Stored directly in data column |

#### Correct Usage Example:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "task_data": {
            "title": "Implement JWT authentication",
            "status": "in_progress",
            "assignee": "@coding_agent",
            "priority": "high"
        },
        "execution_context": {
            "environment": "development",
            "python_version": "3.11",
            "dependencies_installed": ["pyjwt", "cryptography"]
        },
        "discovered_patterns": {
            "auth_flow": "OAuth2 + JWT",
            "token_storage": "Redis with TTL",
            "refresh_strategy": "Sliding window"
        },
        "local_decisions": {
            "token_expiry": "15 minutes",
            "refresh_expiry": "7 days",
            "algorithm": "RS256"
        },
        "implementation_notes": {
            "files_modified": ["auth/jwt_handler.py", "auth/middleware.py"],
            "tests_added": ["test_jwt_generation", "test_token_refresh"],
            "blockers": "Need Redis connection string from DevOps"
        }
    }
)
```

## Important Notes on Custom Fields

### Where Custom Fields Are Stored:
1. **Global Context**: Custom fields → `workflow_templates._custom`
2. **Project Context**: Custom fields → `local_standards._custom`
3. **Branch Context**: Custom fields → `feature_flags._custom`
4. **Task Context**: Custom fields → `data` (direct storage)

### Why This Happens:
The repository implementation preserves ALL data you send, even if it doesn't match predefined columns. This ensures no data loss, but it means you need to use exact field names to get data into the intended columns.

## Repository Pattern for Custom Fields

All context repositories follow this pattern:

```python
# 1. Define known fields for the level
known_fields = {'field1', 'field2', 'field3', ...}

# 2. Separate custom fields
custom_fields = {}
for key, value in input_data.items():
    if key not in known_fields:
        custom_fields[key] = value

# 3. Store custom fields in a designated location
if custom_fields:
    designated_field['_custom'] = custom_fields
```

## Migration and Compatibility

### Legacy Field Names
The system maintains backward compatibility but internally maps to correct columns:
- Task context: `task_settings` → various specific columns
- Branch context: `branch_settings` → various specific columns
- Project context: `project_settings` → various specific columns
- Global context: `global_settings` → various specific columns

### Field Name Corrections
Common mistakes and their corrections:
- `technical_stack` → `technology_stack` (Project level)
- `project_info` → Use specific fields or store as custom
- `core_features` → Use specific fields or store as custom
- `branch_standards` → `feature_flags` (Branch level)
- `agent_assignments` → `active_patterns` (Branch level)

## Best Practices

1. **Always use exact field names** to ensure data goes to intended columns
2. **Check field mapping tables** before creating/updating contexts
3. **Custom fields are preserved** but won't have dedicated columns
4. **Task level is most flexible** - custom fields go directly to `data`
5. **Test your field names** by checking where data appears in Supabase

## Validation and Type Safety

Each level enforces:
- Required `user_id` for isolation
- UUID format for all IDs
- JSON validity for all JSON columns
- Foreign key constraints where applicable
- Check constraints on enum values

## Summary

The context system preserves all data but requires exact field names for proper column storage. When in doubt:
1. Use the field mapping tables above
2. Check where your data appears in the database
3. Adjust field names if data is in `_custom` but you want it in a dedicated column