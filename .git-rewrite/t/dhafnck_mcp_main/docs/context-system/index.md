# Context System Documentation Index

## Core Documentation

### Essential Reading (Start Here)
1. **[Understanding MCP Context](00-understanding-mcp-context.md)** - What the context system actually is and how it works
2. **[Complete Database Schema](context-database-schema-complete.md)** ⭐ - **CRITICAL**: Exact field mappings for all context levels
3. **[Architecture Overview](01-architecture.md)** - System design and components

### Implementation Guides
4. **[Implementation Guide](04-implementation-guide.md)** - How to implement context in your code
5. **[API Reference](03-api-reference.md)** - Complete API documentation
6. **[Workflow Patterns](05-workflow-patterns.md)** - Common usage patterns

### Advanced Topics
7. **[Synchronization](02-synchronization.md)** - How context synchronization works

## Quick Reference

### Context Hierarchy
```
GLOBAL (User-scoped)
   ↓
PROJECT (Project-wide settings)
   ↓
BRANCH (Feature/branch specific)
   ↓
TASK (Individual task context)
```

### Critical Field Names by Level

#### Project Context - Use These Exact Names:
- `team_preferences` (NOT team_settings)
- `technology_stack` (NOT technical_stack)
- `project_workflow` (NOT workflow)
- `local_standards` (NOT standards)

#### Branch Context - Use These Exact Names:
- `branch_workflow`
- `feature_flags`
- `active_patterns`
- `local_overrides`

#### Task Context - Most Flexible:
- `task_data`
- `execution_context`
- `discovered_patterns`
- `local_decisions`
- `implementation_notes`

## Common Issues

### Why is my data in `local_standards._custom`?
You're using field names that don't match the database columns exactly. See [Complete Database Schema](context-database-schema-complete.md) for correct field names.

### Context not showing in frontend?
Contexts must be explicitly created - they're not auto-created with tasks. Use:
```python
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="task",
    context_id=task_id,
    data={...}
)
```

## Recent Updates
- **2025-08-28**: Added complete database schema documentation with exact field mappings
- **2025-08-27**: Reorganized documentation structure
- **2025-08-26**: Fixed context hierarchy initialization

## Need Help?
1. Start with [Understanding MCP Context](00-understanding-mcp-context.md)
2. Check [Complete Database Schema](context-database-schema-complete.md) for field mappings
3. Review [Workflow Patterns](05-workflow-patterns.md) for examples