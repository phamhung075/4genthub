# User-Scoped Global Context Architecture

## Overview
The 4genthub context hierarchy implements a **user-scoped global context** system, not a system-wide singleton. This document clarifies the correct implementation.

## Context Hierarchy

```
User's Global Context (unique per user)
    ↓
User's Projects
    ↓
Project Branches
    ↓
Branch Tasks
```

## Key Principles

### 1. One Global Context Per User
- Each user has **exactly ONE** global context
- Global context ID is **unique per user** (UUID)
- Not a singleton pattern (`00000000-0000-0000-0000-000000000001` is incorrect)

### 2. Global Context Lifecycle
```python
# First time user creates anything:
if not user_has_global_context():
    global_context_id = generate_unique_uuid()
    create_global_context(user_id, global_context_id)

# Subsequent operations:
global_context = get_user_global_context(user_id)
# User can only update, not create another
```

### 3. Project Context Inheritance
- Each project context must reference the user's global context
- `parent_global_id` should be the user's global context ID, not a singleton

## Implementation Details

### Global Context Creation
```python
# CORRECT: User-scoped global context
global_context = GlobalContext(
    id=str(uuid.uuid4()),  # Unique ID per user
    user_id=user_id,        # Scoped to specific user
    organization_id="default",
    metadata={
        "purpose": f"User-scoped global context for {user_id}"
    }
)
```

### Project Context Linking
```python
# CORRECT: Link to user's global context
user_global = get_user_global_context(user_id)
project_context = ProjectContext(
    project_id=project_id,
    parent_global_id=user_global.id,  # User's global context
    user_id=user_id
)
```

## Database Schema

### GlobalContext Table
- `id`: UUID (unique per user, not singleton)
- `user_id`: String (required, ensures one per user)
- `organization_id`: String
- `metadata`: JSON
- Unique constraint on `user_id` ensures one global context per user

### ProjectContext Table
- `id`: UUID
- `project_id`: UUID
- `parent_global_id`: UUID (references user's global context)
- `user_id`: String

## Migration Considerations

### From Singleton to User-Scoped
If migrating from an incorrect singleton implementation:

1. **Identify Singleton References**: Find all uses of hardcoded singleton UUID
2. **Create User Contexts**: For each user, create their unique global context
3. **Update References**: Update project contexts to reference user's global context
4. **Remove Singleton**: Remove the singleton global context if it exists

### Migration Script Updates
The migration script (`migrate_project_contexts.py`) has been updated to:
- Create unique global contexts per user
- Link project contexts to user's global context (not singleton)
- Handle multi-user scenarios correctly

## API Usage

### Creating Global Context (First Time Only)
```python
# Automatically handled during first project creation
manage_context(
    action="create",
    level="global",
    context_id=str(uuid.uuid4()),  # Unique ID
    user_id=current_user_id,
    data={"organization": "User Organization"}
)
```

### Updating Global Context (After Creation)
```python
# Users can only update their existing global context
manage_context(
    action="update",
    level="global",
    context_id=user_global_context_id,
    user_id=current_user_id,
    data={"updated_settings": {...}}
)
```

## Common Mistakes to Avoid

### ❌ DON'T: Use Singleton Pattern
```python
# WRONG: System-wide singleton
GLOBAL_SINGLETON_UUID = "00000000-0000-0000-0000-000000000001"
```

### ❌ DON'T: Allow Multiple Global Contexts Per User
```python
# WRONG: Creating multiple global contexts
for project in user_projects:
    create_global_context()  # Should reuse existing
```

### ❌ DON'T: Share Global Context Between Users
```python
# WRONG: All users share same global context
all_projects.parent_global_id = SINGLETON_ID
```

### ✅ DO: Maintain User Isolation
```python
# CORRECT: Each user has their own context hierarchy
user_global = get_or_create_user_global_context(user_id)
project.parent_global_id = user_global.id
```

## Benefits of User-Scoped Approach

1. **User Isolation**: Each user's settings and preferences are isolated
2. **Security**: No cross-user context leakage
3. **Scalability**: Context operations scale per-user, not system-wide
4. **Flexibility**: Users can have different organizational settings
5. **Multi-tenancy**: Supports multiple organizations/teams naturally

## Testing Checklist

- [ ] Each user can create exactly one global context
- [ ] Second creation attempt returns existing context
- [ ] Projects inherit from user's global context
- [ ] No hardcoded singleton UUIDs in codebase
- [ ] Context queries are user-scoped
- [ ] Migration handles existing singleton data correctly