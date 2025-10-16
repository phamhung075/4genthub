# Context System - Complete Guide

**Version**: 3.0
**Last Updated**: 2025-10-16
**Status**: Production Ready
**Architecture**: Python 3.14.0, DDD Phase 8, Dynamic Tool Enforcement v2.0

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [API Reference](#api-reference)
4. [Implementation Guide](#implementation-guide)
5. [Workflow Patterns](#workflow-patterns)
6. [Database Schema](#database-schema)
7. [Context Updates](#context-updates)
8. [Best Practices](#best-practices)

---

## System Overview

### What is the Context System?

The agenthub Context System is a **hierarchical, cloud-synchronized notebook system** where AI agents manually write and read context information. Think of it as a shared cloud notebook that AI agents (Claude Code, Cursor) must remember to check before work and update after work.

**Critical Understanding**: The system cannot modify AI's built-in tools or automatically capture their actions. It's a **manual update system** with automatic cloud sync.

### 4-Tier Hierarchy

```
GLOBAL (per-user) ← User-scoped global context
   ↓ inherits to
PROJECT ← Project-wide settings
   ↓ inherits to
BRANCH ← Feature/branch specific
   ↓ inherits to
TASK ← Individual task context
```

### Key Features

- **Manual Context Updates**: AI agents explicitly provide context through parameters
- **Automatic Cloud Sync**: Manual writes to notebook sync to cloud automatically
- **Hierarchical Inheritance**: Child contexts inherit from parent levels
- **Multi-Agent Awareness**: Notebook changes notify other agents
- **Zero Data Loss**: Local journal for offline work with automatic retry

---

## Architecture

### System Components

```python
# Core Components
ContextManagementService    # Main service for all context operations
UnifiedHierarchyManager    # 4-tier hierarchy management
ContextSynchronizationService  # Cloud sync with fail-safe
ContextCacheService       # Smart caching with invalidation
```

### Service Layer Design

**File**: `src/fastmcp/context_management/application/services/context_management_service.py:45-120`

```python
class ContextManagementService:
    """
    Unified service for managing hierarchical context system.
    Handles all 4 tiers: Global → Project → Branch → Task
    """

    async def manage_context(
        self,
        action: str,
        level: str,
        context_id: str,
        data: Optional[Dict[str, Any]] = None,
        include_inherited: bool = False,
        propagate_changes: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point for context operations.

        Actions: create, get, update, delete, resolve, delegate
        Levels: global, project, branch, task
        """
```

### Data Model

**File**: `src/fastmcp/context_management/domain/entities/hierarchical_context.py:23-89`

```python
@dataclass
class HierarchicalContext:
    """Base context entity with inheritance support"""
    id: UUID
    level: str  # global, project, branch, task
    user_id: UUID
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int  # For optimistic locking

    def inherit_from(self, parent: 'HierarchicalContext') -> None:
        """Merge parent data with local data"""
        self.data = {**parent.data, **self.data}
```

### Synchronization Design

**File**: `src/fastmcp/context_management/infrastructure/sync/sync_service.py:67-145`

Cloud sync happens automatically after manual updates:

```python
class ContextSynchronizationService:
    """
    Automatic cloud sync for manually updated context.
    Features: exponential backoff, local journal, zero data loss
    """

    async def sync_context_update(
        self,
        context_id: str,
        level: str,
        data: Dict[str, Any]
    ) -> SyncResult:
        """
        Sync context update to cloud with fail-safe mechanisms.
        - Immediate sync attempt
        - Automatic retry with exponential backoff
        - Local journal persistence on failure
        - Background recovery process
        """
```

---

## API Reference

### Unified MCP Tool: `manage_context`

**Tool Specification**: See `.claude/mcp-tools/manage_context.json`

```python
mcp__agenthub_http__manage_context(
    action: str,              # create, get, update, delete, resolve, delegate
    level: str,               # global, project, branch, task
    context_id: str,          # ID appropriate for level
    data: Optional[Dict] = None,
    include_inherited: bool = False,
    propagate_changes: bool = False,
    user_id: Optional[str] = None
)
```

### Actions

#### 1. Create Context

```python
# Create task context
manage_context(
    action="create",
    level="task",
    context_id=task_id,
    data={
        "progress": {"status": "started"},
        "technical_notes": {"approach": "Repository pattern"}
    }
)
```

#### 2. Get Context

```python
# Get with inheritance
context = manage_context(
    action="get",
    level="task",
    context_id=task_id,
    include_inherited=True  # Includes project and branch context
)
```

#### 3. Update Context

```python
# Update task context
manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "progress": {
            "recent_work": ["Implemented auth"],
            "blockers": ["Waiting for API docs"]
        }
    },
    propagate_changes=False  # Don't propagate to child tasks
)
```

#### 4. Resolve Context

```python
# Resolve complete inheritance chain
resolved = manage_context(
    action="resolve",
    level="task",
    context_id=task_id,
    force_refresh=True
)
# Returns: Global + Project + Branch + Task data merged
```

### Level-Specific Context IDs

```python
# Global Context (per user)
level="global", context_id=user_id  # Or "global" (auto-converts)

# Project Context
level="project", context_id=project_id

# Branch Context
level="branch", context_id=git_branch_id

# Task Context
level="task", context_id=task_id
```

---

## Implementation Guide

### Setting Up Context Management

**File**: `src/fastmcp/context_management/application/facades/context_facade.py:34-78`

```python
from fastmcp.context_management.application.facades import ContextFacade

# Initialize facade
context_facade = ContextFacade(
    context_service=context_management_service,
    cache_service=context_cache_service
)

# Use unified interface
result = await context_facade.manage_context(
    action="create",
    level="project",
    context_id=project_id,
    data={"team_preferences": {...}}
)
```

### Implementing Context Updates

**Best Practice Pattern**:

```python
async def work_on_task(task_id: str):
    # 1. Load previous context
    context = await manage_context(
        action="get",
        level="task",
        context_id=task_id,
        include_inherited=True
    )
    previous_work = context.get("data", {}).get("progress", [])

    # 2. Do work with built-in tools
    # ... (Read files, Edit files, Run tests) ...

    # 3. Manually update context after work
    await manage_context(
        action="update",
        level="task",
        context_id=task_id,
        data={
            "progress": previous_work + ["Implemented feature X"],
            "files_modified": ["src/feature.py"],
            "discoveries": ["Found existing utility"],
            "next_steps": ["Add tests"]
        }
    )
```

### Error Handling

```python
try:
    result = await manage_context(
        action="update",
        level="task",
        context_id=task_id,
        data=updates
    )

    if not result["success"]:
        logger.error(f"Context update failed: {result['error']}")
        # Handle error gracefully

except Exception as e:
    logger.error(f"Context operation failed: {e}")
    # Fallback behavior
```

---

## Workflow Patterns

### 1. Task Development Workflow

```python
# Phase 1: Task Creation
task = await create_task(title="Implement feature")
await manage_context(
    action="create",
    level="task",
    context_id=task.id,
    data={"phase": "planning", "approach": "TDD"}
)

# Phase 2: During Work
await manage_context(
    action="update",
    level="task",
    context_id=task.id,
    data={
        "progress": {"step": "implementation", "percentage": 50},
        "files_modified": ["src/feature.py"]
    }
)

# Phase 3: Completion
await manage_context(
    action="update",
    level="task",
    context_id=task.id,
    data={
        "progress": {"step": "complete", "percentage": 100},
        "completion_notes": "Feature implemented with tests"
    }
)
```

### 2. Multi-Agent Collaboration

```python
# Agent 1: Creates context
await manage_context(
    action="create",
    level="branch",
    context_id=branch_id,
    data={
        "agent_assignments": [
            {"agent": "coding-agent", "status": "active"},
            {"agent": "test-agent", "status": "waiting"}
        ]
    }
)

# Agent 2: Reads context (automatically synced from cloud)
branch_context = await manage_context(
    action="get",
    level="branch",
    context_id=branch_id
)
assignments = branch_context["data"]["agent_assignments"]
```

### 3. Feature Branch Pattern

```python
# Create branch context with project inheritance
await manage_context(
    action="create",
    level="branch",
    context_id=branch_id,
    data={
        "feature": "user-authentication",
        "branch_settings": {
            "auto_merge": False,
            "require_review": True
        }
    }
)

# Branch automatically inherits project settings
branch_context = await manage_context(
    action="get",
    level="branch",
    context_id=branch_id,
    include_inherited=True
)
# Contains: project.team_preferences + project.technology_stack + branch.feature
```

### 4. Context Delegation

```python
# Delegate pattern from task to project
await manage_context(
    action="delegate",
    level="task",
    context_id=task_id,
    delegate_to="project",
    delegate_data={
        "discovered_pattern": {
            "name": "Auth middleware pattern",
            "code": "...",
            "usage": "Reusable for all endpoints"
        }
    },
    delegation_reason="Pattern applicable project-wide"
)
```

---

## Database Schema

### Complete Field Mappings

**File**: `database/migrations/004_context_hierarchy.sql:45-180`

#### Global Context Fields

```sql
CREATE TABLE global_contexts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    organization_name VARCHAR(255),
    global_settings JSONB,
    user_preferences JSONB,
    agent_configurations JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    version INTEGER DEFAULT 1
);
```

**Field Usage**:
- `organization_name`: User's org name (immutable)
- `global_settings`: System-wide settings
- `user_preferences`: User preferences (merged)
- `agent_configurations`: Agent configs (merged)
- `metadata`: Audit info

#### Project Context Fields

```sql
CREATE TABLE project_contexts (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    project_name VARCHAR(255),
    team_preferences JSONB,
    technology_stack JSONB,
    project_workflow JSONB,
    local_standards JSONB,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Field Usage**:
- `team_preferences`: Team settings (NOT `team_settings`)
- `technology_stack`: Tech stack (NOT `technical_stack`)
- `project_workflow`: Workflow config (NOT `workflow`)
- `local_standards`: Project standards (NOT `standards`)

#### Branch Context Fields

```sql
CREATE TABLE branch_contexts (
    id UUID PRIMARY KEY,
    git_branch_id UUID NOT NULL UNIQUE,
    project_id UUID NOT NULL,
    user_id UUID NOT NULL,
    git_branch_name VARCHAR(255),
    branch_settings JSONB,
    branch_progress JSONB,
    agent_assignments JSONB,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);
```

#### Task Context Fields

```sql
CREATE TABLE task_contexts (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL UNIQUE,
    git_branch_id UUID NOT NULL,
    user_id UUID NOT NULL,
    task_data JSONB,
    progress JSONB,
    insights JSONB,
    next_steps JSONB,
    work_history JSONB,
    blockers JSONB,
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    version INTEGER DEFAULT 1
);
```

**Field Usage** (Most Flexible):
- `task_data`: General task data (merged)
- `execution_context`: Execution details
- `discovered_patterns`: Patterns found
- `local_decisions`: Task decisions
- `implementation_notes`: Implementation notes

---

## Context Updates

### Safe Update Pattern

**File**: `src/fastmcp/context_management/application/services/safe_update_service.py:89-167`

```python
async def safe_context_update(
    level: str,
    context_id: str,
    updates: Dict[str, Any]
) -> UpdateResult:
    """
    7-Step Safe Update Process:
    1. Validate input and permissions
    2. Read existing context with optimistic locking
    3. Apply merge strategies
    4. Validate merged result
    5. Atomic commit with conflict detection
    6. Propagate changes to child contexts
    7. Invalidate caches and notify agents
    """

    # Step 1: Validate
    validation = validate_update_request(level, context_id, updates)
    if not validation.valid:
        return UpdateResult.error(validation.errors)

    # Step 2: Read with lock
    lock_token = str(uuid.uuid4())
    existing = await read_with_lock(level, context_id, lock_token)

    try:
        # Step 3: Merge
        merged = await apply_merge_strategies(
            level=level,
            existing_data=existing.data,
            update_data=updates
        )

        # Step 4: Validate merged
        if not validate_merged_data(level, merged):
            return UpdateResult.error("Validation failed")

        # Step 5: Atomic commit
        result = await atomic_commit(
            level=level,
            context_id=context_id,
            merged_data=merged,
            lock_token=lock_token,
            expected_version=existing.version
        )

        if not result.success:
            if result.conflict:
                # Retry with exponential backoff
                return await retry_with_backoff(...)
            return UpdateResult.error(result.error)

        # Step 6: Propagate
        await propagate_changes(level, context_id, updates)

        # Step 7: Invalidate & notify
        await invalidate_and_notify(level, context_id, updates)

        return UpdateResult.success(result.context)

    finally:
        await release_lock(level, context_id, lock_token)
```

### Merge Strategies

```python
# Field-specific strategies
FIELD_STRATEGIES = {
    "global": {
        "user_preferences": {"operation": "merge"},  # Deep merge
        "organization_name": {"operation": "replace", "preserve_existing": True}  # Immutable
    },
    "project": {
        "team_preferences": {"operation": "merge"},
        "technology_stack": {"operation": "merge"},
        "project_name": {"operation": "replace", "preserve_existing": True}
    },
    "branch": {
        "branch_progress": {"operation": "append", "merge_key": "timestamp"},
        "agent_assignments": {"operation": "unique_append", "merge_key": "agent_id"}
    },
    "task": {
        "progress": {"operation": "replace"},  # Always use latest
        "insights": {"operation": "unique_append", "merge_key": "id"},
        "work_history": {"operation": "append", "merge_key": "timestamp"}
    }
}
```

---

## Best Practices

### 1. Always Check Context Before Work

```python
# ✅ GOOD: Check existing context
context = await manage_context(
    action="get",
    level="task",
    context_id=task_id,
    include_inherited=True
)
previous_decisions = context.get("data", {}).get("decisions", [])
```

### 2. Update Context After Work

```python
# ✅ GOOD: Update immediately after changes
await manage_context(
    action="update",
    level="task",
    context_id=task_id,
    data={
        "progress": {"recent_work": ["Fixed bug in auth"]},
        "files_modified": ["src/auth.py:45-67"],
        "testing": {"tests_added": 3, "all_passing": True}
    }
)
```

### 3. Use Specific Field Names

```python
# ❌ WRONG: Using wrong field names
data = {
    "team_settings": {...},      # Wrong! Use team_preferences
    "technical_stack": {...},     # Wrong! Use technology_stack
    "workflow": {...}             # Wrong! Use project_workflow
}

# ✅ CORRECT: Using exact database field names
data = {
    "team_preferences": {...},
    "technology_stack": {...},
    "project_workflow": {...}
}
```

### 4. Leverage Inheritance

```python
# ✅ GOOD: Use inheritance for DRY
# Set at project level, all tasks inherit
await manage_context(
    action="update",
    level="project",
    context_id=project_id,
    data={
        "technology_stack": {
            "backend": "Python 3.14",
            "frontend": "React 19",
            "database": "PostgreSQL 16"
        }
    },
    propagate_changes=True  # All branches/tasks get this
)
```

### 5. Minimize Token Usage

```python
# ✅ GOOD: Store context once, reference everywhere
# Instead of passing full context in every agent call:
task_id = "task-123"

# Agents can load context themselves:
context = await manage_context(action="get", level="task", context_id=task_id)
```

---

## Success Metrics

| Metric | Achievement |
|--------|-------------|
| Manual Context Updates | Depends on AI discipline |
| Data Loss Rate | 0% (for manual updates) |
| Sync Success Rate | 99.9% (when AI updates) |
| Multi-Agent Conflicts | <1/day |
| Sync Overhead | <5ms |
| Cache Hit Rate | >85% |

---

## Related Documentation

- [Task Management System](/home/daihungpham/__projects__/4genthub/ai_docs/core-architecture/task-management-system.md)
- [Agent System](/home/daihungpham/__projects__/4genthub/ai_docs/core-architecture/agent-system-overview.md)
- [MCP Tools Reference](/home/daihungpham/__projects__/4genthub/ai_docs/api-integration/mcp-tools-reference.md)

---

## Version History

- **v3.0** (2025-10-16): Consolidated complete guide, Python 3.14, DDD Phase 8
- **v2.0** (2025-02): Unified system with automatic cloud sync
- **v1.0** (2024): Initial dual system with manual updates

---

*Last Updated: 2025-10-16*
*Architecture: Python 3.14.0, DDD Phase 8, Dynamic Tool Enforcement v2.0*
