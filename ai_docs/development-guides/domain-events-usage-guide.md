# Domain Events Usage Guide

**Document Version**: 1.0
**Last Updated**: 2025-10-09
**Phase**: Phase 5 - Domain Events Pattern
**Audience**: Developers implementing event-driven features

## Table of Contents

1. [Quick Start](#quick-start)
2. [Creating Domain Events](#creating-domain-events)
3. [Raising Events from Entities](#raising-events-from-entities)
4. [Handling Events](#handling-events)
5. [Event Bus Integration](#event-bus-integration)
6. [Best Practices](#best-practices)
7. [Common Patterns](#common-patterns)
8. [Testing Events](#testing-events)
9. [Troubleshooting](#troubleshooting)

## Quick Start

### 5-Minute Example

```python
# 1. Import the base class
from fastmcp.task_management.domain.events.base import BaseDomainEvent

# 2. Create an event class
from dataclasses import dataclass

@dataclass(frozen=True)
class UserRegisteredEvent(BaseDomainEvent):
    user_id: str
    email: str
    registration_source: str

# 3. Raise the event from your entity
class User:
    def register(self, email: str, source: str):
        # ... perform registration logic ...

        # Raise event
        event = UserRegisteredEvent(
            user_id=self.id,
            email=email,
            registration_source=source,
            aggregate_id=self.id,
            aggregate_type="User"
        )
        # Publish via event bus (see Event Bus Integration section)
```

## Creating Domain Events

### Step 1: Define Your Event Class

All events must inherit from `BaseDomainEvent` and use the `frozen=True` dataclass decorator for immutability:

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from fastmcp.task_management.domain.events.base import BaseDomainEvent

@dataclass(frozen=True)
class YourEventName(BaseDomainEvent):
    """
    Event raised when [describe when this event occurs].

    This event captures [describe what state change occurred].
    """
    # Required fields specific to this event
    entity_id: str
    some_value: str

    # Optional fields with defaults
    optional_field: Optional[str] = None
    list_field: List[str] = field(default_factory=list)
    dict_field: Dict[str, Any] = field(default_factory=dict)
```

### Step 2: Add Event-Specific Properties

**Rules**:
- Use `frozen=True` for immutability
- Use clear, descriptive field names
- Provide type hints for all fields
- Use `Optional[]` for nullable fields
- Use `field(default_factory=...)` for mutable defaults (lists, dicts)
- Add docstring explaining when and why event is raised

**Example with Rich Context**:

```python
@dataclass(frozen=True)
class FeatureDeployedEvent(BaseDomainEvent):
    """
    Event raised when a feature is successfully deployed to production.

    This event captures deployment metadata, affected systems,
    and rollback information for audit and monitoring purposes.
    """
    feature_id: str
    feature_name: str
    deployed_by: str
    deployment_environment: str  # staging, production, etc.
    version: str
    affected_services: List[str] = field(default_factory=list)
    deployment_duration_seconds: int = 0
    rollback_available: bool = True
    rollback_instructions: Optional[str] = None
    health_check_url: Optional[str] = None
```

### Step 3: Use the Factory Function (Optional)

For convenience, use the `create_domain_event` helper:

```python
from fastmcp.task_management.domain.events.base import create_domain_event

# Instead of manually creating the event:
event = FeatureDeployedEvent(
    feature_id="feat-123",
    feature_name="Dark Mode",
    deployed_by="user-456",
    deployment_environment="production",
    version="2.1.0",
    aggregate_id="feat-123",
    aggregate_type="Feature",
    user_id="user-456"
)

# Use the factory function:
event = create_domain_event(
    FeatureDeployedEvent,
    aggregate_id="feat-123",
    aggregate_type="Feature",
    user_id="user-456",
    # Event-specific fields:
    feature_id="feat-123",
    feature_name="Dark Mode",
    deployed_by="user-456",
    deployment_environment="production",
    version="2.1.0"
)
```

## Raising Events from Entities

### Pattern 1: Direct Event Publishing

```python
from fastmcp.task_management.infrastructure.event_bus import event_bus

class Task:
    def complete(
        self,
        completed_by: str,
        completion_summary: str,
        testing_notes: Optional[str] = None
    ):
        """Complete this task and raise completion event."""
        # 1. Validate state
        if self.status == "done":
            raise ValueError("Task already completed")

        # 2. Update state
        old_status = self.status
        self.status = "done"
        self.completed_by = completed_by
        self.completed_at = datetime.now(timezone.utc)

        # 3. Create and publish event
        event = TaskCompletedEvent(
            task_id=self.id,
            branch_id=self.branch_id,
            title=self.title,
            completion_summary=completion_summary,
            testing_notes=testing_notes,
            completed_by=completed_by,
            aggregate_id=self.id,
            aggregate_type="Task",
            user_id=completed_by
        )

        # 4. Publish via event bus
        event_bus.publish(event)

        return self
```

### Pattern 2: Collecting Events for Batch Publishing

```python
class Project:
    def __init__(self):
        self._pending_events: List[BaseDomainEvent] = []

    def archive(self, archived_by: str, reason: Optional[str] = None):
        """Archive this project."""
        # Update state
        self.status = "archived"
        self.archived_at = datetime.now(timezone.utc)

        # Collect event (don't publish yet)
        event = ProjectArchived(
            project_id=self.id,
            name=self.name,
            archived_by=archived_by,
            reason=reason,
            aggregate_id=self.id,
            aggregate_type="Project"
        )
        self._pending_events.append(event)

    def get_pending_events(self) -> List[BaseDomainEvent]:
        """Return and clear pending events."""
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events

# In your application service or repository:
from fastmcp.task_management.infrastructure.event_bus import event_bus

# After saving entity
project.archive(archived_by="user-123", reason="Project completed")
repository.save(project)

# Publish collected events
for event in project.get_pending_events():
    event_bus.publish(event)
```

### Pattern 3: Event Mixin for Entities

```python
class EventSourcedEntity:
    """Mixin for entities that raise domain events."""

    def __init__(self):
        self._domain_events: List[BaseDomainEvent] = []

    def _raise_event(self, event: BaseDomainEvent):
        """Add event to pending events."""
        self._domain_events.append(event)

    def get_domain_events(self) -> List[BaseDomainEvent]:
        """Return and clear domain events."""
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    def clear_domain_events(self):
        """Clear all pending events."""
        self._domain_events.clear()

# Usage in entity
class Agent(EventSourcedEntity):
    def assign_to_task(self, task_id: str, role: str, assigned_by: str):
        """Assign this agent to a task."""
        # Update state
        self.current_tasks.append(task_id)
        self.workload_percentage = self._calculate_workload()

        # Raise event
        self._raise_event(AgentAssigned(
            agent_id=self.id,
            task_id=task_id,
            role=role,
            assigned_by=assigned_by,
            aggregate_id=self.id,
            aggregate_type="Agent"
        ))
```

## Handling Events

### Creating an Event Handler

```python
from typing import Any

class YourEventHandlers:
    """Handler for your domain events."""

    def __init__(self, dependencies):
        """Initialize with required dependencies."""
        self.notification_service = dependencies.notification_service
        self.statistics_service = dependencies.statistics_service

    async def handle_feature_deployed(self, event: FeatureDeployedEvent) -> None:
        """
        Handle FeatureDeployedEvent.

        Actions:
        - Send deployment notifications
        - Update deployment metrics
        - Schedule health checks
        - Log deployment for audit
        """
        # 1. Send notifications
        await self.notification_service.notify_deployment(
            feature_name=event.feature_name,
            environment=event.deployment_environment,
            deployed_by=event.deployed_by
        )

        # 2. Update statistics
        await self.statistics_service.record_deployment(
            feature_id=event.feature_id,
            duration_seconds=event.deployment_duration_seconds,
            environment=event.deployment_environment
        )

        # 3. Schedule health checks
        if event.health_check_url:
            await self._schedule_health_check(event.health_check_url)

        # 4. Log for audit trail
        logger.info(
            f"Feature '{event.feature_name}' deployed to {event.deployment_environment}",
            extra={
                "feature_id": event.feature_id,
                "version": event.version,
                "deployed_by": event.deployed_by,
                "event_id": str(event.event_id)
            }
        )

    async def _schedule_health_check(self, url: str) -> None:
        """Schedule health check monitoring."""
        # Implementation details...
```

### Registering Handlers

```python
from fastmcp.task_management.infrastructure.event_bus import event_bus

# Create handler instance
feature_handlers = FeatureEventHandlers(dependencies)

# Register handler for specific event type
event_bus.subscribe(FeatureDeployedEvent, feature_handlers.handle_feature_deployed)

# Register multiple handlers
event_bus.subscribe(FeatureDeployedEvent, feature_handlers.handle_feature_deployed)
event_bus.subscribe(FeatureRolledBackEvent, feature_handlers.handle_feature_rolled_back)
event_bus.subscribe(FeatureHealthCheckFailedEvent, feature_handlers.handle_health_check_failed)
```

### Handler Best Practices

**1. Idempotency**: Handlers should be idempotent (safe to call multiple times)

```python
async def handle_task_completed(self, event: TaskCompletedEvent) -> None:
    """Handle task completion event (idempotent)."""
    # Check if already processed
    if await self.completion_log.exists(event.event_id):
        logger.info(f"Event {event.event_id} already processed, skipping")
        return

    # Process event
    await self._update_statistics(event)

    # Mark as processed
    await self.completion_log.record(event.event_id)
```

**2. Error Handling**: Always handle errors gracefully

```python
async def handle_agent_assigned(self, event: AgentAssigned) -> None:
    """Handle agent assignment event with error handling."""
    try:
        await self._send_notification(event.agent_id, event.task_id)
    except NotificationError as e:
        logger.error(f"Failed to send notification: {e}")
        # Don't propagate - notification failure shouldn't break event flow

    try:
        await self._update_workload(event.agent_id)
    except Exception as e:
        logger.error(f"Failed to update workload: {e}", exc_info=True)
        # Re-raise - workload tracking is critical
        raise
```

**3. Async/Await**: Use async handlers for I/O operations

```python
async def handle_project_created(self, event: ProjectCreatedEvent) -> None:
    """Handle project creation (async I/O)."""
    # Multiple async operations can run concurrently
    await asyncio.gather(
        self._create_default_branches(event.project_id),
        self._initialize_context(event.project_id),
        self._send_welcome_email(event.project_id)
    )
```

## Event Bus Integration

### Publishing Events

```python
from fastmcp.task_management.infrastructure.event_bus import event_bus

# Synchronous publish
event_bus.publish(event)

# Async publish
await event_bus.publish_async(event)

# Batch publish
events = [event1, event2, event3]
event_bus.publish_batch(events)
```

### Subscribing to Events

```python
from fastmcp.task_management.infrastructure.event_bus import event_bus

# Subscribe single handler
event_bus.subscribe(TaskCreatedEvent, handler.handle_task_created)

# Subscribe multiple handlers to same event
event_bus.subscribe(TaskCreatedEvent, statistics_handler.handle_task_created)
event_bus.subscribe(TaskCreatedEvent, notification_handler.handle_task_created)
event_bus.subscribe(TaskCreatedEvent, workflow_handler.handle_task_created)

# Unsubscribe
event_bus.unsubscribe(TaskCreatedEvent, handler.handle_task_created)
```

### Event Bus Configuration

```python
# In your application startup
from fastmcp.task_management.infrastructure.event_bus import EventBus (with EventQueue and EventWorker)

# Create event bus instance
event_bus = EventBus (with EventQueue and EventWorker)()

# Register all handlers
def register_event_handlers(event_bus: EventBus (with EventQueue and EventWorker), dependencies):
    """Register all domain event handlers."""
    # Task handlers
    task_handlers = TaskEventHandlers(dependencies)
    event_bus.subscribe(TaskCreatedEvent, task_handlers.handle_created)
    event_bus.subscribe(TaskUpdatedEvent, task_handlers.handle_updated)
    event_bus.subscribe(TaskCompletedEvent, task_handlers.handle_completed)

    # Agent handlers
    agent_handlers = AgentEventHandlers(dependencies)
    event_bus.subscribe(AgentAssigned, agent_handlers.handle_assigned)
    event_bus.subscribe(AgentWorkloadChanged, agent_handlers.handle_workload_changed)

    # Project handlers
    project_handlers = ProjectEventHandlers(dependencies)
    event_bus.subscribe(ProjectCreatedEvent, project_handlers.handle_created)
    event_bus.subscribe(ProjectHealthChanged, project_handlers.handle_health_changed)

# Call during initialization
register_event_handlers(event_bus, application_dependencies)
```

## Best Practices

### 1. Event Naming

✅ **Good**:
```python
@dataclass(frozen=True)
class OrderPlacedEvent(BaseDomainEvent):
    """Event raised when a customer places an order."""
    order_id: str
    customer_id: str
    total_amount: float
```

❌ **Bad**:
```python
@dataclass(frozen=True)
class PlaceOrder(BaseDomainEvent):  # Imperative, not past tense
    """Place an order."""  # Should describe the event, not command
```

### 2. Event Granularity

**Rule**: One event per meaningful state change

✅ **Good** (Specific events):
```python
TaskCreatedEvent(...)      # Task was created
TaskStatusChangedEvent(...) # Status changed
TaskCompletedEvent(...)    # Task was completed (rich context)
```

❌ **Bad** (Too generic):
```python
TaskEvent(action="created", ...)  # Don't use action flags
TaskModifiedEvent(...)            # Too vague
```

### 3. Event Data Completeness

**Rule**: Events should be self-contained

✅ **Good** (Complete context):
```python
@dataclass(frozen=True)
class TaskCompletedEvent(BaseDomainEvent):
    task_id: str
    branch_id: str
    title: str                      # Include for handlers
    completion_summary: str
    testing_notes: Optional[str]
    completed_by: Optional[str]
    time_spent_minutes: Optional[int]
    insights_found: List[str]       # Rich context
```

❌ **Bad** (Missing context):
```python
@dataclass(frozen=True)
class TaskCompletedEvent(BaseDomainEvent):
    task_id: str  # Handlers must look up everything else
```

### 4. Avoiding Event Chains

**Rule**: Events shouldn't directly trigger other events (handlers can raise new events if needed)

✅ **Good**:
```python
# In handler
async def handle_task_completed(self, event: TaskCompletedEvent):
    """Handle completion and trigger downstream work."""
    # Update statistics
    await self._update_stats(event)

    # If this was final task, mark project complete
    if await self._is_project_complete(event.branch_id):
        # Raise new event through proper channels
        project_event = ProjectCompletedEvent(...)
        event_bus.publish(project_event)
```

❌ **Bad**:
```python
# In entity
def complete_task(self):
    event1 = TaskCompletedEvent(...)
    event_bus.publish(event1)

    # Don't raise cascading events here
    event2 = ProjectUpdatedEvent(...)
    event_bus.publish(event2)  # Bad: cascading events
```

### 5. Event Versioning

**Rule**: Plan for event evolution

```python
@dataclass(frozen=True)
class TaskCreatedEvent(BaseDomainEvent):
    """
    Event raised when a task is created.

    Version History:
    - v1: Initial version (task_id, title, status)
    - v2: Added assignees field (2025-10-09)
    - v3: Added priority field (2025-10-09)
    """
    task_id: str
    title: str
    status: str
    assignees: List[str] = field(default_factory=list)  # v2
    priority: str = "medium"  # v3 with default for compatibility
```

### 6. Testing Events

**Rule**: Test event creation and handling separately

```python
# Test event creation
def test_task_completed_event_creation():
    """Test TaskCompletedEvent can be created with valid data."""
    event = TaskCompletedEvent(
        task_id="task-123",
        branch_id="branch-456",
        title="Test task",
        completion_summary="Task completed successfully",
        completed_by="user-789"
    )

    assert event.task_id == "task-123"
    assert event.event_type == "TaskCompletedEvent"
    assert event.event_id is not None
    assert event.occurred_at is not None

# Test event handling
@pytest.mark.asyncio
async def test_handle_task_completed():
    """Test handler processes TaskCompletedEvent correctly."""
    # Arrange
    mock_stats_service = Mock()
    handler = TaskEventHandlers(stats_service=mock_stats_service)
    event = TaskCompletedEvent(...)

    # Act
    await handler.handle_completed(event)

    # Assert
    mock_stats_service.update_completion_stats.assert_called_once()
```

## Common Patterns

### Pattern 1: Audit Trail

```python
@dataclass(frozen=True)
class AuditEventMixin:
    """Mixin for events that need audit trail."""
    user_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

@dataclass(frozen=True)
class SensitiveDataAccessedEvent(BaseDomainEvent, AuditEventMixin):
    """Event raised when sensitive data is accessed."""
    data_id: str
    data_type: str
    access_reason: str
    user_id: str
    ip_address: Optional[str] = None
```

### Pattern 2: Workflow Orchestration

```python
class WorkflowOrchestrator:
    """Orchestrate multi-step workflows via events."""

    async def handle_task_completed(self, event: TaskCompletedEvent):
        """Complete task and trigger next workflow step."""
        # Check if all prerequisite tasks done
        prerequisites_done = await self._check_prerequisites(event.task_id)

        if prerequisites_done:
            # Trigger next phase
            next_event = WorkflowPhaseCompletedEvent(
                workflow_id=event.workflow_id,
                phase="implementation",
                next_phase="testing"
            )
            event_bus.publish(next_event)
```

### Pattern 3: Event Aggregation

```python
class MetricsAggregator:
    """Aggregate events for analytics."""

    def __init__(self):
        self.hourly_buffer = []

    async def handle_task_created(self, event: TaskCreatedEvent):
        """Buffer task creation for hourly aggregation."""
        self.hourly_buffer.append({
            'timestamp': event.occurred_at,
            'type': 'task_created',
            'project_id': event.branch_id
        })

        # Flush if buffer full
        if len(self.hourly_buffer) >= 1000:
            await self._flush_metrics()
```

### Pattern 4: Event Replay

```python
class EventStore:
    """Store events for replay and debugging."""

    async def store_event(self, event: BaseDomainEvent):
        """Persist event to event store."""
        await self.db.insert('events', {
            'event_id': str(event.event_id),
            'event_type': event.event_type,
            'aggregate_id': event.aggregate_id,
            'occurred_at': event.occurred_at,
            'payload': event.to_dict()
        })

    async def replay_events(self, aggregate_id: str):
        """Replay all events for an aggregate."""
        events = await self.db.query(
            'SELECT * FROM events WHERE aggregate_id = ? ORDER BY occurred_at',
            [aggregate_id]
        )

        for event_data in events:
            # Reconstruct and republish event
            event_class = self._get_event_class(event_data['event_type'])
            event = event_class(**event_data['payload'])
            event_bus.publish(event)
```

## Testing Events

### Unit Testing Events

```python
import pytest
from datetime import datetime, timezone

def test_event_immutability():
    """Test that events cannot be modified after creation."""
    event = TaskCreatedEvent(
        task_id="task-123",
        branch_id="branch-456",
        title="Test",
        status="todo",
        priority="medium"
    )

    # Should raise error when trying to modify
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.title = "Modified"

def test_event_serialization():
    """Test event serialization to dict."""
    event = TaskCreatedEvent(
        task_id="task-123",
        branch_id="branch-456",
        title="Test",
        status="todo",
        priority="medium"
    )

    event_dict = event.to_dict()

    assert event_dict['task_id'] == "task-123"
    assert event_dict['event_type'] == "TaskCreatedEvent"
    assert 'event_id' in event_dict
    assert 'occurred_at' in event_dict
```

### Integration Testing Handlers

```python
@pytest.mark.asyncio
async def test_task_completed_handler_integration():
    """Test TaskCompletedEvent handler with real dependencies."""
    # Arrange
    db = await create_test_database()
    stats_service = StatisticsService(db)
    handler = TaskEventHandlers(stats_service)

    event = TaskCompletedEvent(
        task_id="task-123",
        branch_id="branch-456",
        title="Test task",
        completion_summary="Done",
        completed_by="user-789"
    )

    # Act
    await handler.handle_completed(event)

    # Assert
    stats = await stats_service.get_branch_stats("branch-456")
    assert stats['completed_tasks'] == 1
```

### Testing Event Bus

```python
@pytest.mark.asyncio
async def test_event_bus_publishes_to_all_subscribers():
    """Test event bus delivers events to all subscribers."""
    # Arrange
    handler1_called = False
    handler2_called = False

    async def handler1(event):
        nonlocal handler1_called
        handler1_called = True

    async def handler2(event):
        nonlocal handler2_called
        handler2_called = True

    event_bus.subscribe(TaskCreatedEvent, handler1)
    event_bus.subscribe(TaskCreatedEvent, handler2)

    # Act
    event = TaskCreatedEvent(...)
    await event_bus.publish_async(event)

    # Assert
    assert handler1_called
    assert handler2_called
```

## Troubleshooting

### Problem: Events Not Being Received

**Symptoms**: Handler not called when event published

**Solutions**:
1. Check handler is registered:
```python
# Verify subscription
assert event_bus.has_subscription(TaskCreatedEvent, handler.handle_created)
```

2. Check event type matches:
```python
# Ensure using exact class, not subclass
event_bus.subscribe(TaskCreatedEvent, handler)  # Correct
event_bus.subscribe(BaseDomainEvent, handler)   # Won't match TaskCreatedEvent
```

3. Check handler signature:
```python
# Correct signature
async def handle_created(self, event: TaskCreatedEvent) -> None:

# Wrong signature (missing event parameter)
async def handle_created(self) -> None:  # Won't work
```

### Problem: Event Handler Errors

**Symptoms**: Exceptions in event handlers breaking flow

**Solutions**:
1. Add try-catch in handlers:
```python
async def handle_event(self, event):
    try:
        await self._process(event)
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)
        # Don't re-raise unless critical
```

2. Use error handler pattern:
```python
class ResilientEventHandler:
    async def handle(self, event):
        try:
            await self._do_work(event)
        except Exception as e:
            await self._handle_error(event, e)

    async def _handle_error(self, event, error):
        # Log, alert, retry, or dead letter queue
        logger.error(f"Failed to handle {event.event_type}: {error}")
        await self.error_queue.enqueue(event, error)
```

### Problem: Event Ordering Issues

**Symptoms**: Events processed out of order

**Solutions**:
1. Add sequence numbers:
```python
@dataclass(frozen=True)
class OrderedEvent(BaseDomainEvent):
    sequence_number: int
    aggregate_version: int
```

2. Use event streams per aggregate:
```python
class AggregateEventStream:
    async def publish_ordered(self, events: List[BaseDomainEvent]):
        """Publish events in order for same aggregate."""
        for event in sorted(events, key=lambda e: e.sequence_number):
            await event_bus.publish_async(event)
```

### Problem: Event Data Too Large

**Symptoms**: Events cause memory/network issues

**Solutions**:
1. Reference large data instead of including it:
```python
@dataclass(frozen=True)
class FileUploadedEvent(BaseDomainEvent):
    file_id: str
    file_size_bytes: int
    storage_url: str  # Reference, not file content
    checksum: str
```

2. Split into multiple events:
```python
# Instead of one huge event
@dataclass(frozen=True)
class BatchProcessedEvent(BaseDomainEvent):
    batch_id: str
    item_count: int
    # Don't include all items!

# Emit per-item events
@dataclass(frozen=True)
class ItemProcessedEvent(BaseDomainEvent):
    batch_id: str
    item_id: str
    item_data: Dict[str, Any]
```

## Related Documentation

- [Domain Events Catalog](../core-architecture/domain-events-catalog.md) - Complete event reference
- [Event Handlers Reference](./event-handlers-reference.md) - Handler implementation details
- [DDD Refactoring Task Roadmap](./ddd-refactoring-task-roadmap.md) - Phase 5 context
- [Testing Guide](../testing-qa/testing-guide.md) - Comprehensive testing patterns

---

**Document Status**: Complete ✅
**Next Steps**: See [Event Handlers Reference](./event-handlers-reference.md) for handler implementation details
