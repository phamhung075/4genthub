# Project Ownership Security Bug
**Date**: 2025-10-29
**Severity**: HIGH - Multi-tenant isolation violation at project level
**Status**: 🔴 ACTIVE BUG - Temporary fix applied, root cause fix needed

## Executive Summary

A security bug was discovered where auto-created default projects are assigned `user_id = "default-user-001"` instead of the authenticated user's ID. This violates multi-tenant isolation at the project level, causing tasks and branches to be hidden from the frontend even though they belong to the correct user.

### Impact Assessment

**Severity**: HIGH
- Multi-tenant isolation violated at project level
- User data becomes invisible in frontend
- Tasks and branches orphaned in projects with wrong ownership

**Scope**:
- ✅ Task-level security: Working correctly (all tasks have proper user_ids)
- ✅ Branch-level security: Working correctly (all branches have proper user_ids)
- ❌ Project-level security: **BUG** - Auto-created projects have wrong owner

**Affected Users**: Any user whose tasks are created via auto-project-creation flow

## Bug Description

### The Issue

When the system auto-creates a default project (typically named "My First Project"), it assigns:
- **Project `user_id`**: `"default-user-001"` ❌ (test/default user)
- **Branch `user_id`**: Correct authenticated user ✅
- **Task `user_id`**: Correct authenticated user ✅

This creates a situation where:
1. Tasks and branches belong to the correct user
2. But the PROJECT belongs to a test user
3. Frontend filters projects by `user_id` → Can't display the project
4. Result: User's tasks become invisible even though they exist with correct ownership

### Discovery Timeline

**2025-10-29 11:00-11:38**: Full investigation timeline

1. **Initial Report**: User reported "tasks not visible on frontend"
2. **First Investigation**: Suspected JWT authentication issue
3. **Security Audit**: Confirmed JWT authentication working perfectly
4. **Database Analysis**: Found 48 tasks with correct user_ids
5. **Branch Discovery**: Found 5 branches, sidebar only showing 1
6. **Project Analysis**: Discovered tasks split across 2 projects
7. **Root Cause**: "My First Project" owned by "default-user-001"

### Concrete Example

**Database State**:
```sql
-- Project Table
id: abb4a6c0-c422-4603-a05e-b20bd832f8d7
name: "My First Project"
user_id: "default-user-001"  ← WRONG! Should be authenticated user

-- Branches in that project
git_branch_id: d8825fb2-24a9-4d92-82fb-f7f94d9e48d2
user_id: "f0de4c5d-2a97-4324-abcd-9dae3922761e"  ← CORRECT

-- Tasks in those branches
task_id: 117472e5-c37e-4bbe-8e91-38f25ec46c0c
user_id: "f0de4c5d-2a97-4324-abcd-9dae3922761e"  ← CORRECT
```

**Frontend Behavior**:
```javascript
// Frontend queries projects
SELECT * FROM projects WHERE user_id = 'f0de4c5d...'

// Returns: ONLY "4genthub" project
// "My First Project" filtered out (wrong owner)

// Result: Can't see branches in "My First Project"
// 34 tasks become invisible
```

## Temporary Fix Applied

**Immediate Resolution** (2025-10-29 11:38):
```sql
UPDATE projects
SET user_id = 'f0de4c5d-2a97-4324-abcd-9dae3922761e'
WHERE id = 'abb4a6c0-c422-4603-a05e-b20bd832f8d7'
AND name = 'My First Project';
```

**Result**: User can now see "My First Project" in frontend with all 4 branches and 34 tasks.

**Status**: ✅ User's data now visible
**Remaining**: ❌ Root cause not fixed - will affect other users

## Root Cause Analysis

### Where "default-user-001" Comes From

Need to investigate these areas:

1. **Project Auto-Creation Logic**:
   - File: `task_application_facade.py:207-234`
   - When creating tasks without project_id
   - System queries: `SELECT id FROM projects LIMIT 1`
   - May be using first project found regardless of owner

2. **Default Project Initialization**:
   - When system starts or user first accesses
   - May create default project with hardcoded test user
   - Search for: "default-user-001", "My First Project", "default project"

3. **Project Creation Use Cases**:
   - File: `create_project.py`
   - Check if user_id properly passed and validated
   - Look for fallback logic that uses default user

### Hypothesized Flow:

```
User creates task via MCP/API
  ↓
No project_id specified
  ↓
System needs project → Auto-create flow
  ↓
BUG: Creates project with user_id = "default-user-001"
  ↓
Branches created with CORRECT user_id (from JWT)
  ↓
Tasks created with CORRECT user_id (from JWT)
  ↓
Result: Orphaned project with wrong owner
```

## Files to Investigate

### High Priority:
1. **`task_application_facade.py`** (lines 207-234)
   - Project selection logic for auto-creation
   - `SELECT id FROM projects LIMIT 1` query

2. **`create_project.py`** (use case)
   - User_id validation and default handling
   - Where "default-user-001" might be set

3. **Project initialization/bootstrap code**
   - System startup logic
   - Default project creation

### Search Patterns:
```bash
# Find where "default-user-001" is defined
grep -r "default-user-001" agenthub_main/src/

# Find default project creation
grep -r "My First Project" agenthub_main/src/
grep -r "default.*project" agenthub_main/src/ -i

# Find project auto-creation logic
grep -r "auto.*create.*project" agenthub_main/src/ -i
```

## Proper Fix Required

### 1. Fix Auto-Project-Creation Flow

**Current (WRONG)**:
```python
# Gets ANY project, may have wrong owner
result = session.execute(text("SELECT id FROM projects LIMIT 1"))
```

**Should Be**:
```python
# Get project for CURRENT USER only
result = session.execute(text(
    "SELECT id FROM projects WHERE user_id = :user_id LIMIT 1"
), {"user_id": user_id})

# If no project found, create one for THIS USER
if not row:
    create_default_project(user_id=user_id)
```

### 2. Fix Default Project Creation

**Ensure all default projects created with proper user_id**:
```python
def create_default_project(user_id: str) -> str:
    """Create default project for authenticated user"""
    project = Project(
        id=generate_uuid(),
        name="My First Project",
        description="Welcome to agenthub!",
        user_id=user_id,  # ← MUST use authenticated user
        created_at=datetime.now(timezone.utc)
    )
    # ... save and return
```

### 3. Add Validation

**Never allow projects with test user IDs in production**:
```python
def validate_user_id(user_id: str, operation: str) -> str:
    # Existing validation
    if user_id is None or not user_id.strip():
        raise ValueError("User ID required")

    # NEW: Reject test users in production
    if user_id == "default-user-001":
        raise ValueError(
            "Cannot use test user 'default-user-001' in production. "
            "Authenticated user ID required."
        )

    return user_id
```

### 4. Data Migration

**Fix existing orphaned projects**:
```sql
-- Find projects with test user that have branches/tasks with real users
SELECT DISTINCT
    p.id as project_id,
    p.name as project_name,
    p.user_id as wrong_owner,
    b.user_id as correct_owner
FROM projects p
JOIN project_git_branchs b ON p.id = b.project_id
WHERE p.user_id = 'default-user-001'
AND b.user_id != 'default-user-001';

-- Update project owners to match their branches/tasks
UPDATE projects p
SET user_id = (
    SELECT DISTINCT b.user_id
    FROM project_git_branchs b
    WHERE b.project_id = p.id
    LIMIT 1
)
WHERE p.user_id = 'default-user-001'
AND EXISTS (
    SELECT 1 FROM project_git_branchs b
    WHERE b.project_id = p.id
    AND b.user_id != 'default-user-001'
);
```

## Testing Requirements

### 1. Unit Tests

```python
def test_project_creation_uses_authenticated_user():
    """Verify projects always created with authenticated user_id"""
    user_id = "test-user-123"
    project = create_default_project(user_id=user_id)
    assert project.user_id == user_id
    assert project.user_id != "default-user-001"

def test_rejects_default_user_in_production():
    """Verify default-user-001 rejected in production"""
    with pytest.raises(ValueError, match="test user"):
        validate_user_id("default-user-001", "project creation")
```

### 2. Integration Tests

```python
def test_task_creation_with_auto_project(authenticated_user):
    """Verify task creation auto-creates project with correct owner"""
    task = create_task(
        title="Test task",
        user_id=authenticated_user.id,
        project_id=None  # Auto-create flow
    )

    # Verify project was created
    project = get_project_for_task(task.id)
    assert project is not None
    assert project.user_id == authenticated_user.id  # NOT default-user-001
```

### 3. E2E Tests

```python
def test_frontend_shows_all_user_projects(browser, authenticated_session):
    """Verify frontend displays all projects owned by user"""
    # Create tasks (triggers auto-project-creation)
    create_test_tasks(count=5)

    # Check frontend
    browser.navigate_to("/projects")
    projects = browser.find_elements(".project-item")

    # All projects should be visible
    assert len(projects) >= 1

    # No project should have default-user-001
    for project in projects:
        assert "default-user-001" not in project.get_attribute("data-owner")
```

## Monitoring & Alerts

### Add Monitoring

```python
# Log warning when default user detected
if project.user_id == "default-user-001":
    logger.error(
        f"SECURITY: Project {project.id} has default test user as owner. "
        f"This should not happen in production!"
    )
    # Send alert to ops team
```

### Database Query for Detection

```sql
-- Find orphaned projects (run daily)
SELECT
    p.id,
    p.name,
    p.user_id as project_owner,
    COUNT(DISTINCT b.user_id) as unique_branch_owners,
    COUNT(DISTINCT t.user_id) as unique_task_owners
FROM projects p
LEFT JOIN project_git_branchs b ON p.id = b.project_id
LEFT JOIN tasks t ON b.id = t.git_branch_id
WHERE p.user_id = 'default-user-001'
OR (p.user_id != b.user_id AND b.user_id IS NOT NULL)
GROUP BY p.id, p.name, p.user_id;
```

## Related Issues

- **Task-level security**: ✅ Working (verified 2025-10-29)
- **Branch-level security**: ✅ Working (verified 2025-10-29)
- **JWT authentication**: ✅ Working (verified 2025-10-29)
- **Project auto-creation**: ❌ This bug
- **Multi-tenant isolation**: ⚠️ Partially working (task/branch level OK, project level broken)

## Documentation Updates Needed

1. **CHANGELOG.md**: Document the bug and fix
2. **Security documentation**: Add project-level isolation requirements
3. **Developer guide**: Warn about auto-project-creation pitfalls
4. **API documentation**: Clarify project_id requirements for task creation

## Action Items

- [ ] Find where "default-user-001" is set in project creation
- [ ] Fix auto-project-creation to use authenticated user_id
- [ ] Add validation to reject test users in production
- [ ] Write tests for project ownership
- [ ] Run data migration to fix existing orphaned projects
- [ ] Add monitoring/alerts for project ownership issues
- [ ] Update documentation with security requirements
- [ ] Code review of all project creation flows
