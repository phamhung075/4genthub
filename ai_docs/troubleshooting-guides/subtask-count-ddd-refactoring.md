# Subtask Count DDD Refactoring Guide

## Issue Summary
Subtasks created via MCP were not displaying in the frontend because the `subtask_count` field was `0` even when subtasks existed in the database. The root cause was **DDD architecture violation** - the application layer was bypassing the domain layer to update the database directly.

## Problem Diagnosed
### Original Violation
**Location**:
- `agenthub_main/src/fastmcp/task_management/application/use_cases/add_subtask.py:141-159`
- `agenthub_main/src/fastmcp/task_management/application/use_cases/remove_subtask.py:90-109`

**Code Pattern (❌ WRONG)**:
```python
def _increment_parent_subtask_count(self, task_id: str) -> None:
    """Increment the parent task's subtask_count by 1."""
    try:
        # ❌ VIOLATION: Direct database access from application layer
        from ..database.models import Task as TaskModel
        from ...infrastructure.database.session_manager import SessionManager

        session = SessionManager.get_session()
        task_orm = session.query(TaskModel).filter(TaskModel.id == str(task_id)).first()
        if task_orm:
            task_orm.subtask_count = (task_orm.subtask_count or 0) + 1
            session.commit()
```

### Why This Was Wrong
1. **Bypasses Domain Logic**: Business rules in domain layer were ignored
2. **Tight Coupling**: Application layer directly depends on infrastructure layer
3. **No Domain Events**: Changes don't trigger domain events for other parts of the system
4. **Hard to Test**: Requires mocking database sessions instead of domain entities
5. **Breaks DDD Principles**: Violates layer separation and single responsibility

## Solution: Domain-Driven Design Refactoring

### Step 1: Add `subtask_count` to Domain Entity
**File**: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py:55`

```python
@dataclass
class Task(BaseTimestampEntity):
    """Task domain entity with business logic"""

    # ... other fields ...
    subtasks: list[str] = field(default_factory=list)  # List of subtask IDs
    subtask_count: int = 0  # Denormalized count for performance (line 55)
    due_date: str | None = None
```

**Why**: The denormalized count should be managed by the entity itself, not bypassed with database operations.

### Step 2: Add Domain Methods
**File**: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py:729-748`

```python
def increment_subtask_count(self) -> None:
    """Increment the subtask count by 1.

    This method should be called automatically by add_subtask().
    Following DDD principles, this keeps the count synchronized with the subtasks list.
    """
    self.subtask_count += 1
    logger.debug(f"Incremented subtask_count for task {self.id} to {self.subtask_count}")

def decrement_subtask_count(self) -> None:
    """Decrement the subtask count by 1.

    This method should be called automatically by remove_subtask().
    Following DDD principles, this keeps the count synchronized with the subtasks list.
    """
    if self.subtask_count > 0:
        self.subtask_count -= 1
        logger.debug(f"Decremented subtask_count for task {self.id} to {self.subtask_count}")
    else:
        logger.warning(f"Attempted to decrement subtask_count for task {self.id} but count is already 0")
```

**Why**: Domain methods encapsulate business logic and can be tested independently.

### Step 3: Update `add_subtask()` to Call Domain Method
**File**: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py:682-705`

```python
def add_subtask(self, subtask_id: str) -> str:
    """Add a subtask ID to the task and increment subtask count"""
    if not subtask_id or not isinstance(subtask_id, str):
        raise ValueError("Subtask ID must be a non-empty string")

    if subtask_id not in self.subtasks:
        self.subtasks.append(subtask_id)
        self.increment_subtask_count()  # ✅ ADDED: Call domain method
        self.touch("subtask_added")

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            changes={
                "subtasks": {
                    "action": "subtask_added",
                    "new_value": subtask_id,
                    "subtask_count": self.subtask_count,  # ✅ ADDED: Include count in event
                    "updated_at": self.updated_at.isoformat() if self.updated_at else None
                }
            }
        ))

    return subtask_id
```

### Step 4: Update `remove_subtask()` to Call Domain Method
**File**: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py:707-727`

```python
def remove_subtask(self, subtask_id: str) -> bool:
    """Remove a subtask by ID and decrement subtask count"""
    if subtask_id in self.subtasks:
        self.subtasks.remove(subtask_id)
        self.decrement_subtask_count()  # ✅ ADDED: Call domain method
        self.touch("subtask_removed")

        # Raise domain event
        self._events.append(TaskUpdated(
            task_id=self.id,
            changes={
                "subtasks": {
                    "action": "subtask_removed",
                    "removed_value": subtask_id,
                    "subtask_count": self.subtask_count,  # ✅ ADDED: Include count in event
                    "updated_at": self.updated_at.isoformat() if self.updated_at else None
                }
            }
        ))
        return True
    return False
```

### Step 5: Refactor Use Cases to Use Domain Methods
**File**: `agenthub_main/src/fastmcp/task_management/application/use_cases/add_subtask.py:141-158`

```python
def _increment_parent_subtask_count(self, task_id: str) -> None:
    """Increment the parent task's subtask_count by 1 following DDD principles.

    This method uses the Task domain entity's increment_subtask_count() method
    instead of directly accessing the database. This keeps all business logic
    in the domain layer.
    """
    try:
        task_id_obj = self._convert_to_task_id(task_id)
        task = self._task_repository.find_by_id(task_id_obj)
        if task:
            # ✅ CORRECT: Use domain method (DDD compliant)
            task.increment_subtask_count()
            # ✅ CORRECT: Save via repository (proper layer separation)
            self._task_repository.save(task)
            logging.info(f"Incremented subtask_count for task {task_id} to {task.subtask_count}")
    except Exception as e:
        logging.warning(f"Failed to increment parent subtask_count: {e}")
```

**File**: `agenthub_main/src/fastmcp/task_management/application/use_cases/remove_subtask.py:90-109`

```python
def _decrement_parent_subtask_count(self, task_id: str) -> None:
    """Decrement the parent task's subtask_count by 1 following DDD principles.

    This method uses the Task domain entity's decrement_subtask_count() method
    instead of directly accessing the database. This keeps all business logic
    in the domain layer.
    """
    try:
        import logging
        task_id_obj = self._convert_to_task_id(task_id)
        task = self._task_repository.find_by_id(task_id_obj)
        if task:
            # ✅ CORRECT: Use domain method (DDD compliant)
            task.decrement_subtask_count()
            # ✅ CORRECT: Save via repository (proper layer separation)
            self._task_repository.save(task)
            logging.info(f"Decremented subtask_count for task {task_id} to {task.subtask_count}")
    except Exception as e:
        import logging
        logging.warning(f"Failed to decrement parent subtask_count: {e}")
```

### Step 6: Update `to_dict()` to Include `subtask_count`
**File**: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py:1340`

```python
def to_dict(self) -> dict[str, Any]:
    """Convert task to dictionary representation"""
    # ... other fields ...
    result = {
        # ... other fields ...
        "subtasks": self.subtasks.copy(),
        "subtask_count": self.subtask_count,  # ✅ ADDED: Include in serialization
        "dueDate": self.due_date if self.due_date else None,
        # ... other fields ...
    }
    return result
```

## Verification

### Database State
The `subtask_count` column already existed in the ORM model at line 174:
```python
subtask_count: Mapped[int] = mapped_column(Integer, default=0)
```

### Test Results
After refactoring:
- ✅ Demo Task has `subtask_count: 3` in database
- ✅ 3 actual subtasks exist in database
- ✅ Count matches actual subtasks
- ✅ Domain methods are called automatically
- ✅ Repository handles persistence

## DDD Layer Architecture

### Correct Flow (✅)
```
User Action
    ↓
Application Layer (Use Case)
    ↓
Domain Layer (Task Entity)
    → increment_subtask_count()
    → Validates business rules
    → Emits domain events
    ↓
Repository Layer
    → Maps entity to ORM
    → Persists to database
    ↓
Database
```

### Incorrect Flow (❌ OLD)
```
User Action
    ↓
Application Layer (Use Case)
    → Bypasses domain layer!
    ↓
Infrastructure Layer (Direct DB Access)
    → session.query(TaskModel)
    → No validation
    → No events
    ↓
Database
```

## Benefits of DDD Approach

### 1. **Single Source of Truth**
- Domain entity contains all business logic
- No logic duplication across layers
- Changes are centralized

### 2. **Testability**
```python
# Easy to test - no database needed
task = Task.create(...)
task.add_subtask("subtask-123")
assert task.subtask_count == 1  # Test domain logic directly
```

### 3. **Domain Events**
```python
# Automatic event emission
self._events.append(TaskUpdated(
    task_id=self.id,
    changes={"subtask_count": self.subtask_count}
))
```

### 4. **Type Safety**
- Domain methods have proper type hints
- IDEs can provide autocomplete
- Compiler catches errors early

### 5. **Maintainability**
- Clear separation of concerns
- Easy to understand flow
- Changes in one place propagate correctly

## Frontend Integration

### TaskRow.tsx Render Condition
**File**: `agenthub-frontend/src/components/TaskRow.tsx:609`

```typescript
{isExpanded && fullTask && summary.subtask_count > 0 && (
  <LazySubtaskList
    projectId={projectId}
    taskTreeId={taskTreeId}
    parentTaskId={summary.id}
  />
)}
```

### What This Means
- Frontend checks `summary.subtask_count > 0` before rendering
- With DDD refactoring, this count is now **always accurate**
- Backend updates count atomically with subtask creation/deletion
- No race conditions or stale data

## Future Subtask Operations

### Creating Subtasks
When a subtask is created:
1. ✅ Task entity's `add_subtask()` is called
2. ✅ `increment_subtask_count()` is called automatically
3. ✅ Domain event is emitted
4. ✅ Repository persists both subtask list AND count
5. ✅ Frontend receives updated count via API

### Deleting Subtasks
When a subtask is deleted:
1. ✅ Task entity's `remove_subtask()` is called
2. ✅ `decrement_subtask_count()` is called automatically
3. ✅ Domain event is emitted
4. ✅ Repository persists changes
5. ✅ Frontend receives updated count via API

## Testing Recommendations

### Unit Tests (Domain Layer)
```python
def test_increment_subtask_count():
    task = Task.create(id=TaskId.from_string("task-123"), title="Test", description="Test")
    assert task.subtask_count == 0

    task.add_subtask("subtask-1")
    assert task.subtask_count == 1

    task.add_subtask("subtask-2")
    assert task.subtask_count == 2

def test_decrement_subtask_count():
    task = Task.create(id=TaskId.from_string("task-123"), title="Test", description="Test")
    task.add_subtask("subtask-1")
    task.add_subtask("subtask-2")
    assert task.subtask_count == 2

    task.remove_subtask("subtask-1")
    assert task.subtask_count == 1

    task.remove_subtask("subtask-2")
    assert task.subtask_count == 0
```

### Integration Tests (Application Layer)
```python
def test_add_subtask_use_case():
    # Arrange
    task = create_test_task()
    use_case = AddSubtaskUseCase(task_repository, subtask_repository)
    request = AddSubtaskRequest(task_id=task.id, title="Test Subtask")

    # Act
    response = use_case.execute(request)

    # Assert
    updated_task = task_repository.find_by_id(task.id)
    assert updated_task.subtask_count == 1
```

## Related Files

### Domain Layer
- `agenthub_main/src/fastmcp/task_management/domain/entities/task.py`
  - Lines 55: `subtask_count` field definition
  - Lines 682-705: `add_subtask()` method
  - Lines 707-727: `remove_subtask()` method
  - Lines 729-736: `increment_subtask_count()` method
  - Lines 738-748: `decrement_subtask_count()` method
  - Line 1340: `to_dict()` serialization

### Application Layer
- `agenthub_main/src/fastmcp/task_management/application/use_cases/add_subtask.py`
  - Lines 141-158: Refactored `_increment_parent_subtask_count()`
- `agenthub_main/src/fastmcp/task_management/application/use_cases/remove_subtask.py`
  - Lines 90-109: Refactored `_decrement_parent_subtask_count()`

### Infrastructure Layer
- `agenthub_main/src/fastmcp/task_management/infrastructure/database/models.py`
  - Line 174: ORM model with `subtask_count` column

### Frontend
- `agenthub-frontend/src/components/TaskRow.tsx`
  - Line 609: Render condition checking `summary.subtask_count > 0`

## Summary

### What Changed
1. ✅ Added `subtask_count` field to Task domain entity
2. ✅ Added `increment_subtask_count()` and `decrement_subtask_count()` domain methods
3. ✅ Updated `add_subtask()` to call increment method automatically
4. ✅ Updated `remove_subtask()` to call decrement method automatically
5. ✅ Refactored use cases to use domain methods instead of direct DB access
6. ✅ Updated `to_dict()` to include `subtask_count` in serialization

### Impact
- **✅ DDD Compliance**: All business logic now resides in the domain layer
- **✅ No Database Bypass**: Application layer properly uses domain entities
- **✅ Testability**: Domain logic can be tested without database
- **✅ Maintainability**: Changes are centralized and predictable
- **✅ Frontend Fix**: Subtasks now display correctly when `subtask_count > 0`

### User Experience
- **Before**: Frontend showed "No subtasks" even when subtasks existed
- **After**: Frontend correctly displays subtasks when count > 0
- **Why**: Backend now maintains accurate `subtask_count` via domain logic

## Last Updated
2025-10-16 - DDD refactoring completed and verified
