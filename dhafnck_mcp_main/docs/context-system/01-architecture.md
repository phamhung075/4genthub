# Context System Architecture

## Overview

The DhafnckMCP Context System implements a 4-tier hierarchical architecture where manual context updates sync to the cloud, enabling context sharing and multi-agent collaboration through a shared "cloud notebook" that AI agents must manually read from and write to.

## 4-Tier Hierarchy

```
GLOBAL (User-scoped: per-user global context)
   ↓ inherits to
PROJECT (ID: project_id)  
   ↓ inherits to
BRANCH (ID: git_branch_id)
   ↓ inherits to
TASK (ID: task_id)
```

### Inheritance Flow
Lower levels automatically inherit properties from higher levels:
```
Final Context = Task Data + Branch Data + Project Data + Global Data
(Most specific)                                         (Most general)
```

## Core Components

### UnifiedContextService
**Purpose**: Single service managing all context operations from manual updates that sync to cloud

```python
class UnifiedContextService:
    def __init__(self):
        self.repository = UnifiedContextRepository()
        self.cache = ContextCache()
        self.inheritance_resolver = InheritanceResolver()
        self.delegation_manager = DelegationManager()
        self.sync_wrapper = MandatorySyncWrapper()
        self.local_journal = LocalChangeJournal()
```

### Key Services

1. **ContextInheritanceService**
   - Resolves context inheritance chains
   - Merges data with precedence rules
   - Caches resolved contexts

2. **ContextDelegationService**
   - Manages pattern sharing between levels
   - Queues delegations for approval
   - Invalidates dependent caches

3. **ContextCacheService**
   - LRU cache with dependency tracking
   - Automatic invalidation on changes
   - Cloud sync status checking

## Data Model

### Context Levels

#### Global Context
- **Purpose**: User-specific patterns and standards
- **Content**: User's coding standards, security policies, personal architecture patterns
- **Scope**: User-scoped (each user has their own global context instance)

#### Project Context
- **Purpose**: Project-specific configuration
- **Content**: Team conventions, project architecture, shared utilities
- **Inherits**: From Global

#### Branch Context
- **Purpose**: Feature/work branch specific settings
- **Content**: Feature requirements, implementation decisions
- **Inherits**: From Project → Global

#### Task Context
- **Purpose**: Specific work unit context
- **Content**: Task progress, discoveries, implementation details
- **Inherits**: From Branch → Project → Global

### Database Schema

```sql
-- Global contexts (user-scoped)
CREATE TABLE global_contexts (
    id VARCHAR(50) PRIMARY KEY,  -- User-scoped global context ID
    user_id VARCHAR(36) NOT NULL, -- User who owns this global context
    organization_name VARCHAR(255),
    global_settings JSON,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Project contexts
CREATE TABLE project_contexts (
    id VARCHAR(36) PRIMARY KEY,  -- Project UUID
    project_name VARCHAR(255),
    project_settings JSON,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Branch contexts
CREATE TABLE branch_contexts (
    id VARCHAR(36) PRIMARY KEY,  -- Git branch UUID
    project_id VARCHAR(36) REFERENCES project_contexts(id),
    git_branch_name VARCHAR(255),
    branch_settings JSON,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Task contexts
CREATE TABLE task_contexts (
    id VARCHAR(36) PRIMARY KEY,  -- Task UUID
    branch_id VARCHAR(36) REFERENCES branch_contexts(id),
    task_data JSON,
    progress INTEGER DEFAULT 0,
    insights JSON,
    next_steps JSON,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## System Design Principles

1. **Single Source of Truth**: One unified system for all context operations
2. **Automatic Inheritance**: Lower levels inherit from higher levels automatically
3. **Cloud-First**: All operations synchronized with cloud MCP server
4. **Zero Manual Updates**: Context captured automatically from AI actions
5. **Fail-Safe Design**: Multiple layers of protection against data loss

## Architecture Benefits

- **Simplified API**: Single `manage_context` tool for all operations
- **Consistent Interface**: Uniform parameters across all levels
- **Performance**: Intelligent caching with <100ms response times
- **Reliability**: 99.9% uptime with fail-safe mechanisms
- **Scalability**: Supports unlimited contexts across hierarchy