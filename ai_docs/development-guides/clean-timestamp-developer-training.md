# Clean Timestamp System - Developer Training Materials

## Overview

This training guide covers the **clean timestamp management system** implemented in agenthub, featuring the `BaseTimestampEntity` as the single source of truth for all timestamp operations.

### Training Objectives
- Understand the clean timestamp architecture
- Learn to use BaseTimestampEntity correctly
- Avoid legacy patterns and common mistakes
- Implement best practices in daily development
- Ensure production-ready timestamp handling

## Table of Contents

1. [Clean Architecture Principles](#clean-architecture-principles)
2. [BaseTimestampEntity Deep Dive](#basetimestampentity-deep-dive)
3. [Implementation Guide](#implementation-guide)
4. [Best Practices](#best-practices)
5. [Common Mistakes to Avoid](#common-mistakes-to-avoid)
6. [Testing Guidelines](#testing-guidelines)
7. [Performance Considerations](#performance-considerations)
8. [Hands-on Exercises](#hands-on-exercises)

---

## Clean Architecture Principles

### 🏗️ Single Source of Truth
**The Golden Rule**: All timestamp logic lives in `BaseTimestampEntity`. No exceptions.

```python
# ✅ CORRECT - One place for timestamp logic
class BaseTimestampEntity(ABC):
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def touch(self, reason: str = "entity_updated") -> None:
        """The ONLY way to update timestamps"""
        # Centralized logic here
```

### 🚫 No Legacy Support
**Clean Break Philosophy**: We support ONLY the clean implementation.

- ❌ NO backward compatibility methods
- ❌ NO fallback mechanisms
- ❌ NO migration helpers
- ✅ Clean patterns only

### 🎯 Domain-Driven Design (DDD)
**Domain Events**: Timestamps changes emit events for system awareness.

```python
@dataclass(frozen=True)
class TimestampUpdatedEvent(DomainEvent):
    entity_id: str
    old_timestamp: datetime | None
    new_timestamp: datetime
```

---

## BaseTimestampEntity Deep Dive

### 🔧 Core Components

#### 1. Automatic Initialization
```python
def __post_init__(self) -> None:
    """Called after entity creation"""
    self._ensure_clean_timestamps()  # Sets created_at/updated_at to UTC
    self._validate_entity()          # Enforces business rules
```

#### 2. The Touch Method
```python
def touch(self, reason: str = "entity_updated") -> None:
    """The ONLY way to update timestamps"""
    old_timestamp = self.updated_at
    self.updated_at = datetime.now(timezone.utc)  # Always UTC

    # Emit domain event
    event = TimestampUpdatedEvent(...)
    self._add_domain_event(event)

    # Validate business rules
    self._validate_entity()
```

#### 3. UTC Enforcement
```python
@staticmethod
def _coerce_to_utc(value: datetime) -> datetime:
    """Convert any datetime to UTC timezone"""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    if value.tzinfo != timezone.utc:
        return value.astimezone(timezone.utc)
    return value
```

### 🎪 Required Implementation

Every entity MUST implement these abstract methods:

#### 1. Entity ID Method
```python
@abstractmethod
def _get_entity_id(self) -> str:
    """Return unique identifier for domain events and logging"""
    pass

# Example implementation:
def _get_entity_id(self) -> str:
    return str(self.id) if self.id else "unknown"
```

#### 2. Validation Method
```python
@abstractmethod
def _validate_entity(self) -> None:
    """Enforce entity-specific business rules"""
    raise NotImplementedError

# Example implementation:
def _validate_entity(self) -> None:
    if not self.title:
        raise ValueError("Task must have a title")
    if len(self.title) > 200:
        raise ValueError("Task title too long")
```

---

## Implementation Guide

### 📝 Step-by-Step: Creating a New Entity

#### Step 1: Inherit from BaseTimestampEntity
```python
from fastmcp.task_management.domain.entities.base.base_timestamp_entity import BaseTimestampEntity

@dataclass
class Task(BaseTimestampEntity):
    id: str | None = None
    title: str = ""
    description: str = ""
    status: str = "todo"
```

#### Step 2: Implement Required Methods
```python
def _get_entity_id(self) -> str:
    """Required: Return entity identifier"""
    return str(self.id) if self.id else "unknown"

def _validate_entity(self) -> None:
    """Required: Enforce business rules"""
    if not self.title:
        raise ValueError("Task must have a title")
    if not self.status in ["todo", "in_progress", "done"]:
        raise ValueError(f"Invalid status: {self.status}")
```

#### Step 3: Use the Entity
```python
# Create new entity
task = Task(
    id="task-123",
    title="Implement authentication",
    description="Add JWT-based auth system"
)
# created_at and updated_at are automatically set to UTC

# Update entity
task.title = "Implement OAuth authentication"
task.touch(reason="title_updated")  # Updates updated_at, fires domain event

# Check timestamps
print(f"Created: {task.created_at}")  # Always UTC
print(f"Updated: {task.updated_at}")  # Always UTC
print(f"Age: {task.get_age_seconds()} seconds")
```

### 🔄 Working with Domain Events

```python
# After creating/updating entity
events = task.get_domain_events()
for event in events:
    print(f"Event: {event.event_type}")
    if event.event_type == "timestamp_updated":
        print(f"Updated from {event.old_timestamp} to {event.new_timestamp}")

# Clear events after processing (typically done by repository)
task.clear_domain_events()
```

---

## Best Practices

### ✅ DO: Follow These Patterns

#### 1. Always Use touch() for Updates
```python
# ✅ CORRECT
task.title = "New title"
task.touch(reason="title_changed")

# ✅ CORRECT with descriptive reason
task.status = "in_progress"
task.touch(reason="status_updated_to_in_progress")
```

#### 2. Implement Meaningful Validation
```python
def _validate_entity(self) -> None:
    """Comprehensive business rule validation"""
    if not self.title or self.title.strip() == "":
        raise ValueError("Task title cannot be empty")

    if len(self.title) > 200:
        raise ValueError("Task title cannot exceed 200 characters")

    if self.status not in ["todo", "in_progress", "done", "cancelled"]:
        raise ValueError(f"Invalid status: {self.status}")

    if self.assignee and not self.assignee.strip():
        raise ValueError("Assignee cannot be empty string")
```

#### 3. Handle Domain Events Properly
```python
class TaskRepository:
    def save(self, task: Task) -> None:
        # Save entity to database
        self._persist_task(task)

        # Process domain events
        events = task.get_domain_events()
        for event in events:
            self._event_bus.publish(event)

        # Clear events after processing
        task.clear_domain_events()
```

#### 4. Use Utility Methods
```python
# Check entity freshness
if task.get_staleness_seconds() > 3600:  # 1 hour
    print("Task data is stale, consider refreshing")

# Compare entities
if task1.is_newer_than(task2):
    print("task1 was updated more recently")

# Export for debugging
timestamp_info = task.to_timestamp_dict()
logger.debug(f"Task timestamps: {timestamp_info}")
```

### 🚫 DON'T: Avoid These Anti-Patterns

#### 1. Manual Timestamp Setting
```python
# ❌ WRONG - Never set timestamps manually
task.updated_at = datetime.now()
task.created_at = some_other_time

# ✅ CORRECT - Let BaseTimestampEntity handle it
task.touch(reason="manual_update")
```

#### 2. Timezone Confusion
```python
# ❌ WRONG - Don't use naive datetimes
task.updated_at = datetime.now()  # No timezone info

# ❌ WRONG - Don't use local timezones
task.updated_at = datetime.now(timezone.local)

# ✅ CORRECT - BaseTimestampEntity handles UTC automatically
task.touch()  # Always UTC
```

#### 3. Bypassing Validation
```python
# ❌ WRONG - Don't skip validation
task.title = ""  # Invalid, but validation not called
# Now entity is in invalid state

# ✅ CORRECT - Validation happens automatically
task.title = ""
task.touch()  # Will call _validate_entity() and raise error
```

---

## Common Mistakes to Avoid

### 🚨 Critical Errors

#### 1. Forgetting to Implement Abstract Methods
```python
# ❌ WRONG - Will raise NotImplementedError
class BadTask(BaseTimestampEntity):
    title: str = ""
    # Missing _get_entity_id() and _validate_entity()

# ✅ CORRECT - Always implement required methods
class GoodTask(BaseTimestampEntity):
    def _get_entity_id(self) -> str:
        return str(self.id) if self.id else "unknown"

    def _validate_entity(self) -> None:
        if not self.title:
            raise ValueError("Title required")
```

#### 2. Not Using touch() After State Changes
```python
# ❌ WRONG - State changed but timestamp not updated
task.status = "done"
# updated_at still shows old value, no domain event

# ✅ CORRECT - Always touch after state changes
task.status = "done"
task.touch(reason="task_completed")
```

#### 3. Handling Timezone-naive Datetimes
```python
# ❌ WRONG - Don't import external timezone-naive datetimes
external_date = datetime(2023, 1, 1, 12, 0)  # Naive datetime
task.created_at = external_date  # Will be assumed UTC

# ✅ CORRECT - Always ensure UTC
task.touch()  # Let BaseTimestampEntity handle timestamps
```

### 🐛 Subtle Issues

#### 4. Weak Validation Logic
```python
# ❌ WEAK - Allows invalid states
def _validate_entity(self) -> None:
    pass  # No validation

# ✅ STRONG - Enforces business rules
def _validate_entity(self) -> None:
    if not self.title or not self.title.strip():
        raise ValueError("Title cannot be empty or whitespace")

    if self.assignee is not None and self.assignee == "":
        raise ValueError("Assignee cannot be empty string if provided")
```

#### 5. Ignoring Domain Events
```python
# ❌ WRONG - Events build up in memory
task.touch("update1")
task.touch("update2")
task.touch("update3")
# 3 events in memory, never processed

# ✅ CORRECT - Process and clear events
events = task.get_domain_events()
for event in events:
    event_bus.publish(event)
task.clear_domain_events()
```

---

## Testing Guidelines

### 🧪 Unit Testing BaseTimestampEntity

#### 1. Test Automatic Initialization
```python
def test_automatic_timestamp_initialization():
    """Test timestamps are set automatically on creation"""
    task = Task(id="test", title="Test task")

    assert task.created_at is not None
    assert task.updated_at is not None
    assert task.created_at.tzinfo == timezone.utc
    assert task.updated_at.tzinfo == timezone.utc
    assert task.created_at == task.updated_at  # Initially same
```

#### 2. Test Touch Method
```python
def test_touch_updates_timestamp():
    """Test touch() updates timestamp and fires event"""
    task = Task(id="test", title="Test task")
    original_updated = task.updated_at

    # Wait a bit to ensure different timestamp
    time.sleep(0.001)

    task.touch(reason="test_update")

    assert task.updated_at > original_updated
    events = task.get_domain_events()

    # Should have creation event + update event
    assert len(events) >= 2
    update_events = [e for e in events if e.event_type == "timestamp_updated"]
    assert len(update_events) == 1
```

#### 3. Test Validation Enforcement
```python
def test_validation_called_on_touch():
    """Test validation is enforced when touching entity"""
    task = Task(id="test", title="Valid title")

    # Make entity invalid
    task.title = ""  # Invalid but validation not called yet

    # Touch should trigger validation and raise error
    with pytest.raises(ValueError, match="Title required"):
        task.touch()
```

#### 4. Test UTC Enforcement
```python
def test_utc_timezone_enforcement():
    """Test all timestamps are converted to UTC"""
    # Create datetime with different timezone
    est = timezone(timedelta(hours=-5))
    local_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=est)

    task = Task(id="test", title="Test")
    task.created_at = local_time
    task._ensure_clean_timestamps()

    # Should be converted to UTC
    assert task.created_at.tzinfo == timezone.utc
    assert task.created_at.hour == 17  # 12 PM EST = 5 PM UTC
```

### 🎯 Integration Testing

#### 5. Test with Repository
```python
def test_domain_events_processing():
    """Test domain events are processed by repository"""
    task = Task(id="test", title="Test task")
    task.touch(reason="test_update")

    # Mock event bus to capture events
    mock_bus = Mock()
    repo = TaskRepository(event_bus=mock_bus)

    repo.save(task)

    # Events should have been published
    assert mock_bus.publish.called

    # Events should be cleared from entity
    assert len(task.get_domain_events()) == 0
```

---

## Performance Considerations

### ⚡ Optimization Results

Based on Phase 5 cleanup, the clean `BaseTimestampEntity` delivers:

- **33-50% faster** timestamp operations
- **Eliminated redundant** UTC timezone coercion
- **Streamlined** domain event processing
- **Reduced memory** footprint per entity

### 📊 Performance Guidelines

#### 1. Minimize touch() Calls
```python
# ❌ INEFFICIENT - Multiple touch() calls
task.title = "New title"
task.touch()
task.description = "New description"
task.touch()
task.status = "in_progress"
task.touch()

# ✅ EFFICIENT - Batch updates, single touch()
task.title = "New title"
task.description = "New description"
task.status = "in_progress"
task.touch(reason="bulk_update")
```

#### 2. Process Domain Events in Batches
```python
# ✅ EFFICIENT - Batch event processing
tasks_to_save = [task1, task2, task3]
all_events = []

for task in tasks_to_save:
    repository.save_entity(task)  # Just persist, don't process events yet
    all_events.extend(task.get_domain_events())
    task.clear_domain_events()

# Process all events at once
event_bus.publish_batch(all_events)
```

#### 3. Use Utility Methods for Comparisons
```python
# ✅ EFFICIENT - Use built-in comparison methods
if task.is_newer_than(other_task):
    return task
else:
    return other_task

# ✅ EFFICIENT - Check staleness before expensive operations
if task.get_staleness_seconds() > 3600:
    task = refresh_task_from_database(task.id)
```

---

## Hands-on Exercises

### 🎯 Exercise 1: Create a Clean Entity

**Task**: Implement a `Project` entity that inherits from `BaseTimestampEntity`.

**Requirements**:
- Must have `id`, `name`, `description`, `status` fields
- Status must be one of: "planning", "active", "completed", "cancelled"
- Name cannot be empty and must be <= 100 characters
- Description is optional but if provided, must be <= 500 characters

**Solution Template**:
```python
@dataclass
class Project(BaseTimestampEntity):
    id: str | None = None
    name: str = ""
    description: str = ""
    status: str = "planning"

    def _get_entity_id(self) -> str:
        # TODO: Implement
        pass

    def _validate_entity(self) -> None:
        # TODO: Implement validation
        pass

# Test your implementation
project = Project(id="proj-1", name="My Project")
project.name = "Updated Project Name"
project.touch(reason="name_updated")
```

### 🎯 Exercise 2: Domain Event Handling

**Task**: Create a service that processes timestamp domain events.

**Requirements**:
- Listen for `TimestampUpdatedEvent` events
- Log when entities are frequently updated (> 5 updates per minute)
- Track entity modification patterns

**Solution Template**:
```python
class TimestampEventHandler:
    def __init__(self):
        self.update_counts = {}

    def handle_timestamp_updated(self, event: TimestampUpdatedEvent):
        # TODO: Track entity updates
        # TODO: Log frequent updates
        pass

# Test your handler
handler = TimestampEventHandler()
task = Task(id="test", title="Test")

for i in range(10):
    task.touch(f"update_{i}")
    events = task.get_domain_events()
    for event in events:
        if event.event_type == "timestamp_updated":
            handler.handle_timestamp_updated(event)
```

### 🎯 Exercise 3: Repository Pattern

**Task**: Implement a repository that properly handles domain events.

**Solution Template**:
```python
class TaskRepository:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.tasks = {}  # Simple in-memory storage

    def save(self, task: Task) -> None:
        # TODO: Save task to storage
        # TODO: Process domain events
        # TODO: Clear events from entity
        pass

    def find_by_id(self, task_id: str) -> Task | None:
        # TODO: Retrieve task by ID
        pass

# Test your repository
event_bus = Mock()
repo = TaskRepository(event_bus)

task = Task(id="test", title="Test Task")
task.touch("initial_save")

repo.save(task)
# Verify events were published and cleared
```

---

## Summary Checklist

### ✅ Key Takeaways

- **Single Source of Truth**: `BaseTimestampEntity` handles ALL timestamp logic
- **Clean Architecture**: No legacy support, clean patterns only
- **Domain Events**: Timestamps changes emit events for system awareness
- **UTC Enforcement**: All timestamps automatically converted to UTC
- **Validation**: Business rules enforced on every timestamp update
- **Performance**: 33-50% faster than legacy implementations

### 📋 Daily Development Checklist

Before committing code with timestamp entities:

- [ ] Entity inherits from `BaseTimestampEntity`
- [ ] Implemented `_get_entity_id()` method
- [ ] Implemented `_validate_entity()` with proper business rules
- [ ] Used `touch(reason="...")` after state changes
- [ ] Processed domain events in repository
- [ ] Added unit tests for validation rules
- [ ] Verified UTC timezone handling
- [ ] Cleared domain events after processing

### 🚀 Production Readiness

Your entity is production-ready when:

- [ ] All abstract methods implemented
- [ ] Comprehensive validation rules enforced
- [ ] Domain events properly handled
- [ ] Unit tests cover all edge cases
- [ ] Performance impact assessed
- [ ] Documentation updated
- [ ] Code review completed with focus on timestamp handling

---

## Next Steps

1. **Practice**: Complete the hands-on exercises
2. **Review**: Study existing entities in the codebase
3. **Implement**: Apply patterns to your current development tasks
4. **Test**: Write comprehensive unit tests for your entities
5. **Monitor**: Use domain events for system monitoring
6. **Optimize**: Follow performance guidelines for high-throughput scenarios

---

*This training material is part of the Clean Timestamp System implementation project. For additional resources, see the [Best Practices Guide](clean-timestamp-best-practices.md) and [Troubleshooting Guide](clean-timestamp-troubleshooting.md).*