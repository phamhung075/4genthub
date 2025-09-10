# Subtask Persistence Debugging Guide

## Critical Issue: Zero Database Persistence

**Problem**: Subtasks report successful creation but are never persisted to PostgreSQL database.

## Investigation Checklist

### 1. Database Connection Verification
```bash
# Test database connectivity
docker exec dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_test -c "SELECT version();"

# Verify table exists and is accessible
docker exec dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_test -c "\d task_subtasks"

# Test manual insert to verify table functionality
docker exec dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_test -c "
INSERT INTO task_subtasks (id, task_id, title, description, status, priority, user_id, created_at, updated_at) 
VALUES ('test-uuid', '686627ae-55d4-4f32-8cbc-b9f74949552a', 'Test Manual Insert', 'Manual test', 'todo', 'high', 'test-user', now(), now());
"
```

### 2. Repository Pattern Investigation

#### Check SubtaskRepository Implementation
File: `dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/repositories/orm/subtask_repository.py`

Key areas to debug:
```python
# Look for these patterns in create() method:
1. Session management - is session.commit() called?
2. Entity creation - is Subtask entity properly instantiated?
3. Session.add() - is entity added to session?
4. Exception handling - are exceptions silently caught?
5. Return value - does method return success when it shouldn't?
```

#### Repository Factory Check
File locations to investigate:
- Repository factory instantiation
- Dependency injection configuration
- Session management in factory pattern

### 3. Application Layer Investigation

#### Facade Pattern
Check: `task_application_facade.py` subtask creation method
- Transaction boundary management
- Exception handling
- Success/failure logic

#### Service Layer
Verify application services are properly calling repository methods with correct parameters.

### 4. Debug with Logging

Add extensive logging to subtask creation flow:
```python
# In SubtaskRepository.create():
logger.info(f"Creating subtask: {subtask_data}")
logger.info(f"Session state: {session.is_active}")
logger.info(f"Entity created: {subtask_entity}")
logger.info(f"Pre-commit entity ID: {subtask_entity.id}")

session.add(subtask_entity)
logger.info(f"Entity added to session")

session.commit()
logger.info(f"Session committed")

# Verify persistence immediately
result = session.query(Subtask).filter(Subtask.id == subtask_entity.id).first()
logger.info(f"Post-commit query result: {result}")
```

### 5. Transaction Management Debug

Common issues to check:
```python
# Issue 1: Missing commit
session.add(entity)
# Missing: session.commit()

# Issue 2: Exception rollback without re-raise
try:
    session.add(entity)
    session.commit()
except Exception as e:
    session.rollback()
    # Issue: returning success instead of re-raising

# Issue 3: Session scope issues
# Different session used for add vs commit
```

### 6. SQLAlchemy Session State

Debug session lifecycle:
```python
# Check session state throughout operation
print(f"Session new: {session.new}")
print(f"Session dirty: {session.dirty}")  
print(f"Session deleted: {session.deleted}")
print(f"Session identity map: {session.identity_map}")
```

### 7. Entity Mapping Verification

Check if Subtask entity is properly mapped to database:
```python
# Verify ORM mapping
from sqlalchemy import inspect
mapper = inspect(Subtask)
print(f"Table name: {mapper.local_table}")
print(f"Columns: {[col.name for col in mapper.columns]}")
```

## Quick Diagnostic Commands

### Database Level
```bash
# Check if any data exists in related tables
docker exec dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_test -c "
SELECT 
  (SELECT COUNT(*) FROM tasks) as tasks,
  (SELECT COUNT(*) FROM task_subtasks) as subtasks,
  (SELECT COUNT(*) FROM task_contexts) as task_contexts;
"

# Check database constraints that might block inserts
docker exec dhafnck-postgres psql -U dhafnck_user -d dhafnck_mcp_test -c "
SELECT conname, contype, confupdtype, confdeltype 
FROM pg_constraint 
WHERE conrelid = 'task_subtasks'::regclass;
"
```

### Application Level
```python
# Test subtask creation with minimal data
minimal_subtask = {
    "task_id": "686627ae-55d4-4f32-8cbc-b9f74949552a",
    "title": "Debug Test Subtask", 
    "description": "Testing persistence",
    "status": "todo",
    "priority": "high"
}

# Call create and immediately verify
result = manage_subtask(action='create', **minimal_subtask)
print(f"Create result: {result}")

# Direct database check
db_result = session.query(Subtask).filter(
    Subtask.task_id == minimal_subtask['task_id']
).all()
print(f"Database query result: {db_result}")
```

## Expected Fix Areas

### Most Likely Issues (Priority Order)

1. **Missing session.commit()** in SubtaskRepository.create()
2. **Exception handling** that silently catches and returns success
3. **Transaction boundary** issues in application layer
4. **Entity mapping** problems between domain and infrastructure
5. **Session management** in repository factory pattern

### Fix Pattern Template
```python
# Correct implementation pattern:
def create(self, subtask_data):
    try:
        # Create entity
        subtask_entity = Subtask(**subtask_data)
        
        # Add to session
        self.session.add(subtask_entity)
        
        # Commit transaction
        self.session.commit()
        
        # Refresh to get database-generated values
        self.session.refresh(subtask_entity)
        
        # Verify persistence
        verification = self.session.query(Subtask).filter(
            Subtask.id == subtask_entity.id
        ).first()
        
        if not verification:
            raise PersistenceError("Entity not persisted")
            
        return subtask_entity
        
    except Exception as e:
        self.session.rollback()
        logger.error(f"Subtask creation failed: {e}")
        raise  # Re-raise, don't return success
```

## Testing After Fix

1. **Create single subtask** and verify database persistence
2. **List subtasks** and verify returned data matches database
3. **Update subtask** and verify changes persist  
4. **Delete subtask** and verify removal from database
5. **Run full Phase 5 test suite** to ensure all operations work

---

**Next Steps**: Implement debugging, identify root cause, apply fix, and re-test Phase 5 completely.