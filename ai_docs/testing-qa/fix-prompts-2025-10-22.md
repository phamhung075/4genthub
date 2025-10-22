# Fix Prompts for Test Flow Issues - 2025-10-22

## Overview
This document contains detailed, actionable prompts for fixing each issue discovered during comprehensive MCP tools testing on 2025-10-22. Each prompt includes context, file locations with line numbers, expected changes, and test verification steps.

**Related Documentation**: See `test-flow-issues-2025-10-22.md` for full issue descriptions and reproduction steps.

---

## Fix Prompt #1: Date Parameter Timezone Handling

### Issue Reference
**Issue ID**: #1
**Severity**: HIGH
**File**: `test-flow-issues-2025-10-22.md` - Issue #1

### Prompt for New Chat Session

```
I need to fix a datetime timezone handling bug in the agenthub task management system.

**Context:**
When creating a task with a due_date parameter using naive datetime format (without timezone),
the system crashes with: "can't compare offset-naive and offset-aware datetimes"

**Expected Fix:**
The system should accept both timezone-aware and naive datetime formats, automatically
converting naive datetimes to UTC.

**Files to Modify:**

1. **Primary Fix Location:**
   - File: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py`
   - Search for: due_date validation or datetime comparison
   - Expected location: Task entity __init__ or validation method

2. **Supporting Files:**
   - File: `agenthub_main/src/fastmcp/task_management/domain/value_objects/task_metadata.py`
     (if due_date is handled as value object)
   - Search for: DueDate, TaskMetadata classes

**Required Changes:**

1. Add timezone normalization function:
```python
from datetime import datetime, timezone

def normalize_datetime(dt_input: str | datetime) -> datetime:
    """Convert naive or aware datetime to UTC-aware datetime."""
    if isinstance(dt_input, str):
        dt = datetime.fromisoformat(dt_input)
    else:
        dt = dt_input

    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # If aware but not UTC, convert to UTC
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)

    return dt
```

2. Update due_date assignment in Task entity:
```python
# Before:
self.due_date = due_date

# After:
self.due_date = normalize_datetime(due_date) if due_date else None
```

**Test Verification:**

Create test file: `agenthub_main/src/tests/unit/test_task_datetime_handling.py`

```python
import pytest
from datetime import datetime, timezone
from fastmcp.task_management.domain.entities.task import Task

def test_task_due_date_naive_datetime():
    """Test task creation with naive datetime string."""
    task = Task(
        title="Test Task",
        due_date="2025-10-29",  # Naive format
        # ... other required fields
    )
    # Should not crash
    assert task.due_date is not None
    assert task.due_date.tzinfo == timezone.utc

def test_task_due_date_aware_datetime():
    """Test task creation with timezone-aware datetime."""
    task = Task(
        title="Test Task",
        due_date="2025-10-29T23:59:59+00:00",  # Aware format
        # ... other required fields
    )
    assert task.due_date is not None
    assert task.due_date.tzinfo == timezone.utc

def test_task_due_date_comparison():
    """Test comparing due dates doesn't crash."""
    task1 = Task(title="Task 1", due_date="2025-10-29")
    task2 = Task(title="Task 2", due_date="2025-10-30T00:00:00+00:00")

    # Should not crash on comparison
    assert task1.due_date < task2.due_date
```

**Success Criteria:**
- ✅ Task creation accepts naive datetime: "2025-10-29"
- ✅ Task creation accepts aware datetime: "2025-10-29T23:59:59+00:00"
- ✅ All datetimes stored as UTC-aware
- ✅ No comparison errors between naive and aware datetimes
- ✅ All unit tests pass
- ✅ Integration test: Create task via MCP with both formats succeeds
```

---

## Fix Prompt #2: Labels Table Missing Timestamps

### Issue Reference
**Issue ID**: #2
**Severity**: CRITICAL
**File**: `test-flow-issues-2025-10-22.md` - Issue #2

### Prompt for New Chat Session

```
I need to fix a critical database constraint violation in the labels table of the agenthub task management system.

**Context:**
When creating a task with labels, the system attempts to insert NULL values for created_at
and updated_at columns, violating NOT NULL constraints. This completely breaks the labels feature.

**Error Message:**
```
(psycopg2.errors.NotNullViolation) null value in column "created_at" of relation "labels"
violates not-null constraint
DETAIL: Failing row contains (..., null, null).
```

**Files to Investigate and Modify:**

1. **Label Entity:**
   - File: `agenthub_main/src/fastmcp/task_management/domain/entities/label.py`
   - Search for: Label class, __init__ method
   - Add: Default timestamp population

2. **Label Repository:**
   - File: `agenthub_main/src/fastmcp/task_management/infrastructure/repositories/label_repository.py`
   - Search for: INSERT INTO labels, create_label method
   - Fix: Ensure timestamps populated before insert

3. **Database Migration:**
   - File: `agenthub_main/src/fastmcp/task_management/infrastructure/database/migrations/`
   - Search for: labels table creation migration
   - Consider: Adding server_default for timestamp columns

**Required Changes:**

1. Update Label Entity (`label.py`):
```python
from datetime import datetime, timezone
from dataclasses import dataclass, field

@dataclass
class Label:
    id: str
    name: str
    user_id: str
    color: str = "#0066cc"
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)
```

2. Update Label Repository (`label_repository.py`):
```python
def create_label(self, label: Label) -> Label:
    """Create a new label with automatic timestamps."""
    # Ensure timestamps are set
    if label.created_at is None:
        label.created_at = datetime.now(timezone.utc)
    if label.updated_at is None:
        label.updated_at = datetime.now(timezone.utc)

    # Existing insert logic...
    return label
```

3. Consider Migration Update (if needed):
```sql
-- Add server defaults as backup
ALTER TABLE labels
ALTER COLUMN created_at SET DEFAULT NOW(),
ALTER COLUMN updated_at SET DEFAULT NOW();
```

**Test Verification:**

Create test file: `agenthub_main/src/tests/integration/test_label_creation.py`

```python
import pytest
from datetime import datetime, timezone

def test_create_task_with_labels(task_service):
    """Test task creation with labels populates timestamps."""
    task = task_service.create_task(
        title="Test Task",
        labels=["documentation", "api", "frontend"],
        # ... other fields
    )

    # Verify task created
    assert task.id is not None

    # Verify labels created with timestamps
    labels = task_service.get_task_labels(task.id)
    assert len(labels) == 3

    for label in labels:
        assert label.created_at is not None
        assert label.updated_at is not None
        assert isinstance(label.created_at, datetime)
        assert label.created_at.tzinfo == timezone.utc

def test_label_timestamps_auto_populated(label_repository):
    """Test label creation automatically populates timestamps."""
    label = Label(
        id="test-id",
        name="test-label",
        user_id="user-123"
        # Note: No timestamps provided
    )

    created_label = label_repository.create_label(label)

    assert created_label.created_at is not None
    assert created_label.updated_at is not None
    assert created_label.created_at <= datetime.now(timezone.utc)

def test_label_update_timestamp(label_repository):
    """Test updating label updates the updated_at timestamp."""
    label = label_repository.create_label(Label(...))
    original_updated_at = label.updated_at

    time.sleep(0.1)  # Ensure time difference
    label.update()
    updated_label = label_repository.update_label(label)

    assert updated_label.updated_at > original_updated_at
```

**Integration Test via MCP:**
```python
# Test creating task with labels via MCP
response = mcp__agenthub_http__manage_task(
    action="create",
    git_branch_id="branch-uuid",
    title="Test Task with Labels",
    labels="documentation,api,frontend,backend",
    assignees="coding-agent"
)

# Should succeed without constraint violation
assert response["success"] == True
assert "labels" in response["data"]["task"]
```

**Success Criteria:**
- ✅ Label entity has default timestamps
- ✅ Label repository populates timestamps before insert
- ✅ Can create tasks with labels without errors
- ✅ All created labels have valid created_at and updated_at
- ✅ Unit tests pass
- ✅ Integration test via MCP succeeds
- ✅ Database constraint no longer violated
```

---

## Fix Prompt #3: Subtask Progress Calculation Inconsistency

### Issue Reference
**Issue ID**: #3
**Severity**: MEDIUM
**File**: `test-flow-issues-2025-10-22.md` - Issue #3

### Prompt for New Chat Session

```
I need to fix a subtask progress calculation bug where completed subtasks are not reflected in the parent task's progress summary.

**Context:**
When subtasks are marked as "done" (status="done" or progress_percentage=100), the parent task
progress still shows "completed: 0" instead of incrementing the completed count.

**Observed Behavior:**
```json
{
  "progress": {
    "total": 4,
    "completed": 0,  // Should be 1 or more if any subtasks are done
    "percentage": 0   // Should reflect actual completion
  }
}
```

**Files to Investigate and Modify:**

1. **Subtask Service:**
   - File: `agenthub_main/src/fastmcp/task_management/application/services/subtask_service.py`
   - Search for: update_subtask method, progress calculation
   - Lines: Around subtask update logic (estimate: 100-200)

2. **Task Progress Aggregation:**
   - File: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py`
   - Search for: calculate_subtask_progress, get_progress_summary
   - Look for: Method that aggregates subtask completion

3. **Subtask Entity:**
   - File: `agenthub_main/src/fastmcp/task_management/domain/entities/subtask.py`
   - Search for: is_completed property or method
   - Verify: Completion criteria logic

**Required Changes:**

1. Add/Update Subtask Completion Check (`subtask.py`):
```python
@dataclass
class Subtask:
    # ... existing fields ...

    @property
    def is_completed(self) -> bool:
        """Check if subtask is completed."""
        return (
            self.status == "done" or
            (self.progress_percentage is not None and self.progress_percentage >= 100)
        )

    @property
    def is_in_progress(self) -> bool:
        """Check if subtask is in progress."""
        return (
            self.status == "in_progress" or
            (self.progress_percentage is not None and
             0 < self.progress_percentage < 100)
        )
```

2. Update Progress Calculation (`task.py`):
```python
def calculate_subtask_progress(self) -> dict:
    """Calculate progress based on subtask completion."""
    if not self.subtasks:
        return {
            "total": 0,
            "completed": 0,
            "percentage": 0
        }

    total = len(self.subtasks)
    completed = sum(1 for subtask in self.subtasks if subtask.is_completed)
    percentage = (completed / total * 100) if total > 0 else 0

    return {
        "total": total,
        "completed": completed,
        "percentage": round(percentage, 2)
    }
```

3. Update Parent Task After Subtask Change (`subtask_service.py`):
```python
def update_subtask(self, task_id: str, subtask_id: str, **kwargs) -> Subtask:
    """Update subtask and refresh parent task progress."""
    # Update subtask
    subtask = self.subtask_repository.update(subtask_id, **kwargs)

    # Recalculate parent task progress
    task = self.task_repository.get(task_id)
    task_progress = task.calculate_subtask_progress()

    # Update parent task progress_percentage
    task.progress_percentage = task_progress["percentage"]
    self.task_repository.update(task)

    return subtask
```

**Test Verification:**

Create test file: `agenthub_main/src/tests/unit/test_subtask_progress.py`

```python
import pytest

def test_subtask_completion_by_status():
    """Test subtask marked complete by status='done'."""
    subtask = Subtask(
        title="Test",
        status="done",
        progress_percentage=0  # Even if 0, status takes precedence
    )
    assert subtask.is_completed == True

def test_subtask_completion_by_progress():
    """Test subtask marked complete by progress_percentage=100."""
    subtask = Subtask(
        title="Test",
        status="in_progress",  # Even if in_progress
        progress_percentage=100  # 100% means done
    )
    assert subtask.is_completed == True

def test_task_progress_with_completed_subtasks():
    """Test parent task progress reflects completed subtasks."""
    task = Task(title="Parent Task")

    # Add 4 subtasks
    task.add_subtask(Subtask(title="S1", status="todo"))
    task.add_subtask(Subtask(title="S2", status="in_progress", progress_percentage=50))
    task.add_subtask(Subtask(title="S3", status="done"))
    task.add_subtask(Subtask(title="S4", progress_percentage=100))

    progress = task.calculate_subtask_progress()

    assert progress["total"] == 4
    assert progress["completed"] == 2  # S3 and S4 are completed
    assert progress["percentage"] == 50  # 2/4 = 50%

def test_parent_task_updates_on_subtask_completion(subtask_service):
    """Test parent task progress updates when subtask is completed."""
    task = subtask_service.create_task(title="Parent")
    s1 = subtask_service.create_subtask(task.id, title="Sub 1")
    s2 = subtask_service.create_subtask(task.id, title="Sub 2")

    # Initially no completed subtasks
    task = subtask_service.get_task(task.id)
    progress = task.calculate_subtask_progress()
    assert progress["completed"] == 0
    assert progress["percentage"] == 0

    # Complete one subtask
    subtask_service.update_subtask(
        task.id,
        s1.id,
        status="done",
        progress_percentage=100
    )

    # Parent task should reflect completion
    task = subtask_service.get_task(task.id)
    progress = task.calculate_subtask_progress()
    assert progress["completed"] == 1
    assert progress["percentage"] == 50  # 1/2 = 50%
```

**Integration Test:**
```python
# Via MCP
response = manage_subtask(
    action="update",
    task_id="parent-task-id",
    subtask_id="subtask-id",
    status="done",
    progress_percentage=100
)

# Verify response shows updated progress
assert response["progress"]["completed"] > 0
assert response["progress"]["percentage"] > 0
```

**Success Criteria:**
- ✅ Subtask with status="done" counted as completed
- ✅ Subtask with progress_percentage=100 counted as completed
- ✅ Parent task progress accurately reflects subtask completion
- ✅ Progress percentage calculated correctly
- ✅ All unit tests pass
- ✅ Integration test via MCP shows correct progress
```

---

## Fix Prompt #4: Subtask Status Parameter Ignored During Creation

### Issue Reference
**Issue ID**: #4
**Severity**: LOW
**File**: `test-flow-issues-2025-10-22.md` - Issue #4

### Prompt for New Chat Session

```
I need to allow status and progress_percentage parameters during subtask creation instead of requiring a separate update call.

**Context:**
Currently, when creating a subtask with status="in_progress" or progress_percentage=45,
these parameters are ignored and the subtask is always created with status="todo" and
progress_percentage=0.

**Current Workaround (Inefficient):**
```python
# Create (status will be "todo")
subtask = manage_subtask(action="create", task_id=X, title=Y)

# Separate update call required
manage_subtask(
    action="update",
    task_id=X,
    subtask_id=subtask.id,
    status="in_progress",
    progress_percentage=45
)
```

**Desired Behavior:**
```python
# Create with initial state in one call
subtask = manage_subtask(
    action="create",
    task_id=X,
    title=Y,
    status="in_progress",
    progress_percentage=45
)
# Subtask created with status="in_progress", progress_percentage=45
```

**Files to Modify:**

1. **Subtask Service:**
   - File: `agenthub_main/src/fastmcp/task_management/application/services/subtask_service.py`
   - Search for: create_subtask method
   - Lines: Around subtask creation logic (estimate: 50-100)

2. **Subtask Entity:**
   - File: `agenthub_main/src/fastmcp/task_management/domain/entities/subtask.py`
   - Search for: Subtask __init__ or dataclass definition
   - Verify: Constructor accepts status and progress_percentage

3. **MCP Controller:**
   - File: `agenthub_main/src/fastmcp/controllers/subtask_controller.py`
   - Search for: handle create action
   - Ensure: Parameters passed through to service

**Required Changes:**

1. Update Subtask Creation (`subtask_service.py`):
```python
def create_subtask(
    self,
    task_id: str,
    title: str,
    description: str = "",
    status: str = "todo",  # Allow override
    progress_percentage: int = 0,  # Allow override
    assignees: list = None,
    **kwargs
) -> Subtask:
    """Create subtask with optional initial state."""

    # Validate and normalize status based on progress
    if progress_percentage >= 100:
        status = "done"
    elif progress_percentage > 0 and status == "todo":
        status = "in_progress"

    # Create subtask with provided state
    subtask = Subtask(
        id=generate_uuid(),
        parent_task_id=task_id,
        title=title,
        description=description,
        status=status,
        progress_percentage=progress_percentage,
        assignees=assignees or self._inherit_assignees(task_id),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        **kwargs
    )

    # Save and return
    return self.subtask_repository.create(subtask)
```

2. Update MCP Controller (`subtask_controller.py`):
```python
def handle_create(self, params: dict) -> dict:
    """Handle subtask creation with optional status and progress."""
    task_id = params.get("task_id")
    title = params.get("title")
    description = params.get("description", "")

    # Extract optional state parameters
    status = params.get("status", "todo")
    progress_percentage = params.get("progress_percentage", 0)
    progress_notes = params.get("progress_notes")
    assignees = params.get("assignees")

    # Create subtask with initial state
    subtask = self.subtask_service.create_subtask(
        task_id=task_id,
        title=title,
        description=description,
        status=status,
        progress_percentage=progress_percentage,
        progress_notes=progress_notes,
        assignees=assignees
    )

    return {"success": True, "subtask": subtask}
```

**Test Verification:**

Create test file: `agenthub_main/src/tests/unit/test_subtask_creation_state.py`

```python
import pytest

def test_create_subtask_with_status(subtask_service):
    """Test creating subtask with initial status."""
    task = create_test_task()

    subtask = subtask_service.create_subtask(
        task_id=task.id,
        title="Test Subtask",
        status="in_progress"
    )

    assert subtask.status == "in_progress"
    assert subtask.id is not None

def test_create_subtask_with_progress(subtask_service):
    """Test creating subtask with initial progress percentage."""
    task = create_test_task()

    subtask = subtask_service.create_subtask(
        task_id=task.id,
        title="Test Subtask",
        progress_percentage=45
    )

    assert subtask.progress_percentage == 45
    # Should auto-set status to in_progress
    assert subtask.status == "in_progress"

def test_create_subtask_100_percent_auto_done(subtask_service):
    """Test subtask with 100% progress auto-set to done status."""
    task = create_test_task()

    subtask = subtask_service.create_subtask(
        task_id=task.id,
        title="Test Subtask",
        progress_percentage=100
    )

    assert subtask.progress_percentage == 100
    assert subtask.status == "done"  # Auto-set to done

def test_create_subtask_default_state(subtask_service):
    """Test subtask creation without state uses defaults."""
    task = create_test_task()

    subtask = subtask_service.create_subtask(
        task_id=task.id,
        title="Test Subtask"
        # No status or progress specified
    )

    assert subtask.status == "todo"
    assert subtask.progress_percentage == 0
```

**Integration Test:**
```python
# Via MCP - Create subtask with initial state
response = manage_subtask(
    action="create",
    task_id="parent-task-id",
    title="Test Subtask",
    status="in_progress",
    progress_percentage=45,
    progress_notes="Starting with existing progress"
)

assert response["success"] == True
assert response["subtask"]["status"] == "in_progress"
assert response["subtask"]["progress_percentage"] == 45
```

**Success Criteria:**
- ✅ Can create subtask with status="in_progress"
- ✅ Can create subtask with progress_percentage during creation
- ✅ progress_percentage=100 auto-sets status="done"
- ✅ progress_percentage > 0 without status auto-sets status="in_progress"
- ✅ Default behavior (no params) still creates status="todo", progress=0
- ✅ All unit tests pass
- ✅ Integration test via MCP succeeds
- ✅ No need for separate update call after creation
```

---

## Summary

This document provides 4 detailed fix prompts for the issues discovered during comprehensive testing:

1. **Fix Prompt #1**: Datetime timezone handling (HIGH severity)
2. **Fix Prompt #2**: Label timestamp population (CRITICAL severity)
3. **Fix Prompt #3**: Subtask progress calculation (MEDIUM severity)
4. **Fix Prompt #4**: Subtask creation state parameters (LOW severity)

Each prompt includes:
- Full context and error details
- Exact file locations to modify
- Code examples for required changes
- Comprehensive test verification steps
- Clear success criteria

**Usage Instructions:**
1. Copy the entire prompt for the issue you want to fix
2. Start a new chat session with debugger-agent or coding-agent
3. Paste the prompt to initiate the fix
4. Follow the test verification steps to confirm the fix works
5. Update issue status in `test-flow-issues-2025-10-22.md` when resolved

---

**Document Generated**: 2025-10-22
**Test Orchestrator**: test-orchestrator-agent
**Related File**: `test-flow-issues-2025-10-22.md`
