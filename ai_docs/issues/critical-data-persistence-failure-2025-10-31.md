# 🚨 CRITICAL BUG: Data Persistence Failure in MCP Operations

**Severity**: CRITICAL - Data Loss Issue
**Date Discovered**: 2025-10-31
**Session**: Comprehensive MCP Testing (Test Plan Execution)
**Impact**: All newly created entities (projects, branches, tasks) are not persisting to database

---

## Executive Summary

During comprehensive MCP testing, discovered that **ALL entity creation operations appear to succeed but entities are NOT persisted to the database**. This affects:
- ✅ Projects (appear to work - created 2 projects successfully)
- ❌ Git Branches (creation succeeds but branches not queryable afterward)
- ❌ Tasks (creation succeeds but tasks not queryable afterward)

**Root Cause Hypothesis**: Database transaction commit failure or session management issue in creation operations.

---

## Detailed Issue Report

### Issue 1: Git Branch Persistence Failure

**Test Steps**:
1. Create project "E-Commerce Platform" - **SUCCESS** ✅
   - Project ID: `960f2c53-daf5-4457-bd82-0ba61b1330d9`
   - Returned successfully with branch count: 1 (main branch)

2. Create git branch "feature/user-authentication" - **REPORTED SUCCESS** ✅
   - Branch ID: `068a779e-3aa1-4fe5-84c9-d6fad3152756`
   - Response: `"success": true`
   - Message: "Git branch 'feature/user-authentication' created successfully"

3. Create git branch "feature/payment-integration" - **REPORTED SUCCESS** ✅
   - Branch ID: `66e1f381-c0b0-4c86-b9da-d42a3e08e969`
   - Response: `"success": true`
   - Message: "Git branch 'feature/payment-integration' created successfully"

4. List branches for project - **SHOWS 3 BRANCHES** ✅
   ```json
   {
     "success": true,
     "total_count": 3,
     "git_branchs": [
       {"id": "bf105375-cd52-4305-a10d-bbe360231ada", "name": "main"},
       {"id": "068a779e-3aa1-4fe5-84c9-d6fad3152756", "name": "feature/user-authentication"},
       {"id": "66e1f381-c0b0-4c86-b9da-d42a3e08e969", "name": "feature/payment-integration"}
     ]
   }
   ```

5. Get statistics for branch - **FAILS** ❌
   ```json
   {
     "success": false,
     "error": "Branch 068a779e-3aa1-4fe5-84c9-d6fad3152756 not found",
     "error_code": "BRANCH_NOT_FOUND"
   }
   ```

**Observation**: Branch list shows the branches, but get_statistics cannot find them. This suggests:
- Branches exist in some cache/session storage
- Branches not committed to persistent database
- Different operations query different data sources

---

### Issue 2: Task Persistence Complete Failure

**Test Steps**:
1. Create 5 tasks on branch `068a779e-3aa1-4fe5-84c9-d6fad3152756` - **ALL REPORTED SUCCESS** ✅
   - Task 1: `037c31a0-d3b3-494f-82d7-1485407b05d2` - "Design JWT authentication schema"
   - Task 2: `9148faae-b8f0-4ed0-ba52-5ec3803a2d4f` - "Implement user registration endpoint"
   - Task 3: `16a0823d-ab13-4024-99e9-995339c7aa88` - "Implement login endpoint with JWT"
   - Task 4: `1c789290-b846-4179-854d-635fcc24b768` - "Add OAuth2 Google integration"
   - Task 5: `97ec2a18-85ea-46c9-b08b-bfe29d12eb0e` - "Create authentication middleware"

   **All responses**: `"success": true`, `"message": "Task created successfully"`

2. Create 2 tasks on branch `66e1f381-c0b0-4c86-b9da-d42a3e08e969` - **BOTH REPORTED SUCCESS** ✅
   - Task 6: `f2966e8a-8f9f-44c4-9802-39761fb9ee9f` - "Integrate Stripe payment SDK"
   - Task 7: `571fb85d-e304-454c-a493-1d0311ee02dc` - "Build checkout payment flow"

3. List tasks on branch `068a779e-3aa1-4fe5-84c9-d6fad3152756` - **RETURNS 0 TASKS** ❌
   ```json
   {
     "success": true,
     "data": {
       "count": 0,
       "filters_applied": {
         "git_branch_id": "068a779e-3aa1-4fe5-84c9-d6fad3152756"
       },
       "pagination": {"total": 0}
     }
   }
   ```

4. Get task by ID `037c31a0-d3b3-494f-82d7-1485407b05d2` - **FAILS** ❌
   ```json
   {
     "success": false,
     "error": {
       "message": "Task with ID 037c31a0-d3b3-494f-82d7-1485407b05d2 not found",
       "code": "OPERATION_FAILED"
     }
   }
   ```

5. Search for tasks with "authentication" - **RETURNS 0 RESULTS** ❌
   ```json
   {
     "success": true,
     "data": {
       "count": 0,
       "query": "authentication",
       "search_metadata": {"total_results": 0}
     }
   }
   ```

**Observation**: Complete data loss - all 7 tasks disappeared after creation.

---

## Technical Analysis

### Response Pattern Analysis

**Task Creation Response Example**:
```json
{
  "success": true,
  "data": {
    "task": {
      "id": "037c31a0-d3b3-494f-82d7-1485407b05d2",
      "title": "Design JWT authentication schema",
      "description": "...",
      "status": "todo",
      "git_branch_id": "068a779e-3aa1-4fe5-84c9-d6fad3152756",
      "context_id": "037c31a0-d3b3-494f-82d7-1485407b05d2",
      "context_data": { /* full context */ }
    },
    "message": "Task created successfully"
  },
  "meta": {
    "persisted": true,  // ← Claims to be persisted!
    "timestamp": "2025-10-31T16:53:15.981226+00:00",
    "operation": "create"
  }
}
```

**Key Observations**:
1. `"persisted": true` in meta - **BUT DATA NOT ACTUALLY PERSISTED**
2. Full task object returned with all fields populated
3. Context data created successfully
4. No error messages or warnings

### Hypothesis: Transaction Commit Failure

**Likely Root Causes**:

1. **Session/Transaction Not Committed**:
   - Create operation builds entity in memory
   - Returns success before database commit
   - Transaction rolls back or never commits
   - Data lost after response sent

2. **Database Session Management Issue**:
   - Using the fixed transaction pattern from nested context manager fix
   - Potential issue with `with self.transaction() as session:` not committing properly
   - Possible rollback happening in finally block

3. **Context Manager Interaction**:
   - Recently fixed nested context manager bug
   - Possible side effect from the fix
   - Session lifecycle may need adjustment

4. **Isolation Level or Lock Issue**:
   - Write operations succeed but reads use different isolation level
   - Phantom read scenario
   - Uncommitted changes visible only in creation transaction

---

## Code Locations to Investigate

### 1. Task Repository Create Method
**File**: `agenthub_main/src/fastmcp/task_management/infrastructure/repositories/orm/task_repository.py`
**Method**: `create_task()` (lines 304-463)

**Recently Modified**: Yes - removed nested context managers as part of bug fix

**Pattern to Check**:
```python
def create_task(self, ...):
    try:
        with self.transaction() as session:  # ← Was this properly tested?
            # ... create task ...
            # ... update branch counters ...
            # ... create assignees ...
            # ... create labels ...
            # return entity
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise
```

**Potential Issue**: Transaction may not be committing properly after nested context manager fix.

### 2. Base Repository Transaction Method
**File**: `agenthub_main/src/fastmcp/task_management/infrastructure/repositories/base_orm_repository.py`
**Method**: `transaction()` (lines 102-125)

**Pattern**:
```python
@contextmanager
def transaction(self):
    session = get_session()
    self._session = session
    try:
        yield session
        session.commit()  # ← Is this being reached?
    except SQLAlchemyError as e:
        session.rollback()
        raise
    finally:
        self._session = None
        session.close()
```

**Questions to Investigate**:
- Is `session.commit()` being called?
- Are exceptions being swallowed somewhere?
- Is session.close() being called before commit completes?

### 3. Git Branch Repository Create Method
**File**: `agenthub_main/src/fastmcp/task_management/infrastructure/repositories/orm/project_repository.py`
**Method**: `create_git_branch()` or similar

**Check**: Same transaction pattern issues may affect branch creation.

---

## Reproduction Steps

### Minimal Reproduction Case

```python
# 1. Create project (seems to work)
project = mcp__agenthub_http__manage_project(
    action="create",
    name="Test Project",
    description="Test description"
)
project_id = project["data"]["project"]["id"]

# 2. Create git branch
branch = mcp__agenthub_http__manage_git_branch(
    action="create",
    project_id=project_id,
    git_branch_name="test-branch",
    git_branch_description="Test branch"
)
branch_id = branch["data"]["git_branch"]["id"]
# ✅ Returns success with branch ID

# 3. List branches - shows the branch
branches = mcp__agenthub_http__manage_git_branch(
    action="list",
    project_id=project_id
)
# ✅ Branch appears in list

# 4. Get branch statistics - FAILS
stats = mcp__agenthub_http__manage_git_branch(
    action="get_statistics",
    project_id=project_id,
    git_branch_id=branch_id
)
# ❌ Error: "Branch not found"

# 5. Create task on branch
task = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id=branch_id,
    title="Test Task",
    description="Test description",
    assignees="coding-agent"
)
task_id = task["data"]["task"]["id"]
# ✅ Returns success with task ID

# 6. List tasks on branch - RETURNS EMPTY
tasks = mcp__agenthub_http__manage_task(
    action="list",
    git_branch_id=branch_id
)
# ❌ Returns 0 tasks

# 7. Get task by ID - FAILS
task_detail = mcp__agenthub_http__manage_task(
    action="get",
    task_id=task_id
)
# ❌ Error: "Task not found"
```

---

## Impact Assessment

### Severity: **CRITICAL**

**Data Loss**: Complete loss of all created tasks and partial loss of branch data.

**Affected Operations**:
- ❌ Task creation (100% data loss)
- ❌ Git branch creation (partial - list works, but get/statistics fail)
- ✅ Project creation (appears to work correctly)

**User Impact**:
- Cannot create and persist tasks
- Cannot manage task workflows
- Cannot use task dependencies or subtasks
- System appears broken for primary use case

**System State**:
- Database may contain orphaned data
- In-memory cache may be out of sync with database
- Data inconsistency between operations

---

## Recommended Investigation Steps

### 1. Check Database Directly

```bash
# Connect to PostgreSQL
docker exec -it agenthub-postgres psql -U agenthub_user -d agenthub

# Check if tasks exist
SELECT id, title, status, git_branch_id FROM tasks
WHERE git_branch_id = '068a779e-3aa1-4fe5-84c9-d6fad3152756';

# Check if branches exist
SELECT id, name, project_id FROM project_git_branchs
WHERE id = '068a779e-3aa1-4fe5-84c9-d6fad3152756';

# Check transaction logs
SELECT * FROM pg_stat_activity WHERE state = 'idle in transaction';
```

### 2. Add Logging to Transaction Methods

Add debug logging to `base_orm_repository.py`:
```python
@contextmanager
def transaction(self):
    session = get_session()
    self._session = session
    logger.debug(f"Transaction started: {id(session)}")
    try:
        yield session
        logger.debug(f"Attempting commit: {id(session)}")
        session.commit()
        logger.debug(f"Commit successful: {id(session)}")
    except SQLAlchemyError as e:
        logger.error(f"Transaction rollback: {id(session)}, error: {e}")
        session.rollback()
        raise
    finally:
        logger.debug(f"Transaction cleanup: {id(session)}")
        self._session = None
        session.close()
```

### 3. Test With Direct Database Queries

Bypass repository layer and test database directly:
```python
from agenthub_main.src.fastmcp.task_management.infrastructure.database.database_config import DatabaseConfig

db = DatabaseConfig()
with db.get_session() as session:
    from agenthub_main.src.fastmcp.task_management.infrastructure.database.models import Task

    # Create task directly
    task = Task(
        id="test-task-id",
        title="Direct DB Test",
        git_branch_id="branch-id"
    )
    session.add(task)
    session.commit()

    # Query immediately
    found = session.query(Task).filter(Task.id == "test-task-id").first()
    print(f"Task found: {found is not None}")
```

### 4. Check for Autocommit Settings

```python
# Check SQLAlchemy engine configuration
engine = create_engine(database_url, ...)
print(f"Autocommit: {engine.dialect.supports_statement_cache}")
print(f"Isolation level: {engine.dialect.default_isolation_level}")
```

### 5. Review Recent Nested Context Manager Fix

**Compare** the fixed code with original to identify if the fix introduced this issue:
- Was `session.commit()` being called in original code?
- Did we accidentally remove commit calls?
- Are we properly using the yielded session?

---

## Proposed Fixes

### Fix 1: Verify Transaction Commit is Being Called

**File**: `base_orm_repository.py`
```python
@contextmanager
def transaction(self):
    session = get_session()
    self._session = session
    try:
        yield session
        # CRITICAL: Ensure commit happens
        session.commit()
        session.flush()  # Force flush before closing
    except SQLAlchemyError as e:
        session.rollback()
        raise
    finally:
        self._session = None
        session.close()
```

### Fix 2: Add Explicit Flush After Create Operations

**File**: `task_repository.py` `create_task()` method
```python
def create_task(self, ...):
    try:
        with self.transaction() as session:
            # ... create task ...
            task_entity = self._model_to_entity(task)

            # EXPLICIT FLUSH before returning
            session.flush()
            session.commit()  # Extra safety

            return task_entity
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise
```

### Fix 3: Check Database Configuration

**File**: `database_config.py`
```python
# Verify autocommit is not disabled
engine = create_engine(
    database_url,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_pre_ping=pool_pre_ping,
    # ENSURE NO AUTOCOMMIT FALSE
    # isolation_level="AUTOCOMMIT",  # Do NOT set this
    ...
)
```

---

## Testing Checklist for Fix Verification

- [ ] Create task and immediately list - task should appear
- [ ] Create task and immediately get by ID - task should be found
- [ ] Create task and immediately search - task should be in results
- [ ] Create multiple tasks rapidly - all should persist
- [ ] Create task, restart server, query - task should still exist
- [ ] Create git branch and immediately get statistics - should work
- [ ] Check PostgreSQL directly - data should be in tables
- [ ] Verify no "idle in transaction" sessions in pg_stat_activity
- [ ] Test with nested context manager fix still applied
- [ ] Ensure no regression in previous bug fix

---

## Priority Actions

1. **IMMEDIATE**: Add debug logging to transaction methods
2. **URGENT**: Check database directly for persisted data
3. **HIGH**: Review recent nested context manager fix for side effects
4. **HIGH**: Test direct database operations to isolate repository vs database issue
5. **MEDIUM**: Add integration tests for create→read cycle
6. **MEDIUM**: Review session configuration and isolation levels

---

## Notes

- This issue was discovered during comprehensive MCP testing
- Previous nested context manager fix (2025-10-31) successfully resolved EOF errors
- This may be a side effect of that fix or an unrelated pre-existing issue
- Projects appear to persist correctly, suggesting issue is specific to tasks/branches
- No errors or warnings in responses - silent data loss is most concerning aspect

---

**Status**: 🚨 **CRITICAL - REQUIRES IMMEDIATE ATTENTION**
**Next Step**: Add logging and check database directly to determine if data is written at all
