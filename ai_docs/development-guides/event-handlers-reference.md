# Event Handlers Reference

**Document Version**: 1.0
**Last Updated**: 2025-10-09
**Phase**: Phase 5 - Domain Events Pattern
**Audience**: Developers implementing and maintaining event handlers

## Table of Contents

1. [Overview](#overview)
2. [Handler Architecture](#handler-architecture)
3. [TaskEventHandlers](#taskeventhandlers)
4. [AgentEventHandlers](#agenteventhandlers)
5. [ProjectEventHandlers](#projecteventhandlers)
6. [HintEventHandlers](#hinteventhandlers)
7. [ProgressEventHandlers](#progresseventhandlers)
8. [Handler Registration](#handler-registration)
9. [Handler Lifecycle](#handler-lifecycle)
10. [Testing Handlers](#testing-handlers)
11. [Best Practices](#best-practices)

## Overview

Event handlers process domain events to maintain system state, trigger workflows, and coordinate actions across the application. The agenthub system includes 5 handler classes with a total of 1,392 lines of handler code.

### Handler Statistics

| Handler Class | Events Handled | Lines of Code | Primary Responsibility |
|---------------|----------------|---------------|------------------------|
| TaskEventHandlers | 7 | 374 | Task lifecycle tracking |
| AgentEventHandlers | 17 | 521 | Multi-agent coordination |
| ProjectEventHandlers | 6 | 497 | Project management |
| HintEventHandlers | 2 | ~150 | Workflow guidance |
| ProgressEventHandlers | 2 | ~150 | Progress tracking |

## Handler Architecture

### Base Handler Pattern

All handlers follow a consistent pattern:

```python
class YourEventHandlers:
    """Handler for domain events."""

    def __init__(
        self,
        event_store: EventStore,
        required_dependency: Service,
        optional_dependency: Optional[Service] = None
    ):
        """Initialize with required dependencies."""
        self.event_store = event_store
        self.required_dependency = required_dependency
        self.optional_dependency = optional_dependency

        # Internal state for tracking
        self.statistics = {}

    async def handle_event_name(self, event: EventType) -> None:
        """
        Handle specific event.

        Actions:
        - What this handler does
        - Key responsibilities
        - Side effects
        """
        # 1. Log event
        logger.info(f"Handling {event.event_type}: {event.event_id}")

        # 2. Validate/process
        await self._process_event(event)

        # 3. Update statistics
        self._update_stats(event)

        # 4. Trigger follow-up actions
        if self.optional_dependency:
            await self.optional_dependency.notify(event)

    async def process_event(self, event: BaseDomainEvent) -> None:
        """Route events to appropriate handlers."""
        handlers = {
            "EventType1": self.handle_event_name,
            "EventType2": self.handle_another_event,
        }

        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)
```

### Key Design Principles

1. **Dependency Injection**: All dependencies injected via constructor
2. **Async/Await**: All handlers are async for non-blocking I/O
3. **Error Handling**: Graceful degradation when optional services unavailable
4. **Statistics Tracking**: Internal state for metrics and analytics
5. **Routing Pattern**: Single `process_event` method routes to specific handlers

## TaskEventHandlers

**Location**: `application/event_handlers/task_event_handlers.py`
**Size**: 374 lines
**Events**: 7 task lifecycle events

### Class Overview

```python
class TaskEventHandlers:
    """
    Handles task-related domain events.

    Processes events to maintain statistics, update metrics,
    track task lifecycle, and trigger workflow actions.
    """

    def __init__(
        self,
        event_store: EventStore,
        task_repository: Optional[Any] = None,
        notification_service: Optional[Any] = None
    ):
        self.event_store = event_store
        self.task_repository = task_repository
        self.notification_service = notification_service

        # Statistics tracking by project
        self.task_stats: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {
                "created": 0,
                "updated": 0,
                "completed": 0,
                "deleted": 0,
                "status_changes": 0,
                "moved": 0
            }
        )

        # Status transition tracking
        self.status_transitions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Completion time tracking
        self.completion_times: List[float] = []
```

### Handler Methods

#### 1. handle_task_created

**Event**: `TaskCreatedEvent`

**Actions**:
- Updates project statistics (increments created count)
- Sends notifications to assigned agents
- Initializes task tracking in repository
- Logs task creation for audit trail

**Code Example**:
```python
async def handle_task_created(self, event: TaskCreatedEvent) -> None:
    """
    Handle task created event.

    Updates statistics, notifies stakeholders, and initializes tracking.
    """
    logger.info(
        f"Task created: {event.task_id} - '{event.title}' "
        f"(priority: {event.priority}, status: {event.status})"
    )

    # Update statistics by project
    project_key = str(event.project_id) if hasattr(event, 'project_id') else 'unknown'
    self.task_stats[project_key]["created"] += 1

    # Send notifications to assignees
    if self.notification_service and hasattr(event, 'assignees'):
        for assignee in event.assignees:
            await self.notification_service.notify_task_assignment(
                assignee=assignee,
                task_id=event.task_id,
                title=event.title,
                priority=event.priority
            )

    # Initialize task tracking
    if self.task_repository:
        await self.task_repository.track_task_creation(event)
```

#### 2. handle_task_updated

**Event**: `TaskUpdatedEvent`

**Actions**:
- Increments update statistics
- Identifies significant changes (status, priority, assignees, due_date)
- Sends notifications for significant updates
- Tracks change history

#### 3. handle_task_deleted

**Event**: `TaskDeletedEvent`

**Actions**:
- Updates deletion statistics
- Archives task data with timestamp
- Notifies stakeholders of deletion
- Logs deletion for audit trail

#### 4. handle_task_status_changed

**Event**: `TaskStatusChangedEvent`

**Actions**:
- Tracks status transition (from → to)
- Records transition timestamp and user
- Triggers workflow actions based on new status:
  - `in_progress` → calls `_handle_task_started`
  - `blocked` → calls `_handle_task_blocked`
  - `review` → calls `_handle_task_needs_review`

**Code Example**:
```python
async def handle_task_status_changed(self, event: TaskStatusChangedEvent) -> None:
    """
    Handle task status changed event.

    Tracks status transitions, calculates metrics, and triggers workflows.
    """
    logger.info(
        f"Task status changed: {event.task_id} - "
        f"{event.previous_status} → {event.new_status}"
    )

    # Track status transition
    transition = {
        "task_id": str(event.task_id),
        "from": event.previous_status,
        "to": event.new_status,
        "timestamp": event.occurred_at.isoformat(),
        "user": event.user_id
    }
    self.status_transitions[str(event.task_id)].append(transition)

    # Trigger workflow actions based on new status
    if event.new_status == "in_progress":
        await self._handle_task_started(event)
    elif event.new_status == "blocked":
        await self._handle_task_blocked(event)
    elif event.new_status == "review":
        await self._handle_task_needs_review(event)
```

#### 5. handle_task_completed

**Event**: `TaskCompletedEvent`

**Actions**:
- Updates completion statistics
- Tracks completion time metrics
- Calculates average completion time (rolling 10-task window)
- Notifies stakeholders of completion
- Checks for dependent tasks that can now start
- Triggers dependency notifications

**Code Example**:
```python
async def handle_task_completed(self, event: TaskCompletedEvent) -> None:
    """
    Handle task completed event.

    Calculates completion time, updates metrics, and triggers celebrations.
    """
    logger.info(
        f"Task completed: {event.task_id} - '{event.title}' "
        f"(completion time: {event.completion_time_seconds}s)"
    )

    # Track completion time
    if event.completion_time_seconds:
        self.completion_times.append(event.completion_time_seconds)

    # Calculate completion metrics
    if len(self.completion_times) >= 5:
        avg_completion = sum(self.completion_times[-10:]) / min(len(self.completion_times), 10)
        logger.info(f"Average completion time (last 10): {avg_completion:.2f}s")

    # Check for dependent tasks that can now start
    if self.task_repository:
        dependent_tasks = await self.task_repository.get_dependent_tasks(event.task_id)
        for dep_task in dependent_tasks:
            await self._check_dependencies_and_notify(dep_task)
```

#### 6. handle_task_retrieved

**Event**: `TaskRetrievedEvent`

**Actions**:
- Tracks access patterns for analytics
- Records task access timestamp
- Logs access for audit trail (debug level)

#### 7. handle_task_moved_to_branch

**Event**: `TaskMovedToBranchEvent`

**Actions**:
- Updates move statistics
- Notifies affected branch members
- Updates branch metrics in both source and target branches

### Helper Methods

#### _handle_task_started

```python
async def _handle_task_started(self, event: TaskStatusChangedEvent) -> None:
    """Handle workflow when task is started."""
    logger.info(f"Task started workflow triggered for {event.task_id}")

    if self.notification_service:
        await self.notification_service.notify_task_started(
            task_id=event.task_id,
            started_by=event.user_id
        )
```

#### _handle_task_blocked

```python
async def _handle_task_blocked(self, event: TaskStatusChangedEvent) -> None:
    """Handle workflow when task is blocked."""
    logger.warning(f"Task blocked workflow triggered for {event.task_id}")

    if self.notification_service:
        await self.notification_service.notify_task_blocked(
            task_id=event.task_id,
            blocked_by=event.user_id,
            urgent=True
        )
```

#### _handle_task_needs_review

```python
async def _handle_task_needs_review(self, event: TaskStatusChangedEvent) -> None:
    """Handle workflow when task needs review."""
    logger.info(f"Task review workflow triggered for {event.task_id}")

    if self.notification_service:
        await self.notification_service.notify_task_needs_review(
            task_id=event.task_id,
            submitted_by=event.user_id
        )
```

#### _check_dependencies_and_notify

```python
async def _check_dependencies_and_notify(self, task_id: UUID) -> None:
    """Check if all dependencies are complete and notify if ready."""
    if not self.task_repository:
        return

    dependencies = await self.task_repository.get_task_dependencies(task_id)
    all_complete = all(dep.status == "done" for dep in dependencies)

    if all_complete and self.notification_service:
        await self.notification_service.notify_task_ready(
            task_id=task_id,
            message="All dependencies completed, task is ready to start"
        )
```

### Statistics Methods

#### get_task_statistics

```python
async def get_task_statistics(self, project_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Get task statistics for a project or all projects.

    Args:
        project_id: Optional project ID to filter statistics

    Returns:
        Dictionary containing task statistics including:
        - created, updated, completed, deleted counts
        - status_changes, moved counts
        - completion_rate (completed/created)
        - avg_completion_time_seconds
    """
    if project_id:
        project_key = str(project_id)
        return {
            "project_id": project_key,
            "statistics": dict(self.task_stats.get(project_key, {}))
        }

    # Aggregate across all projects
    total_stats = {
        "created": sum(s.get("created", 0) for s in self.task_stats.values()),
        "updated": sum(s.get("updated", 0) for s in self.task_stats.values()),
        "completed": sum(s.get("completed", 0) for s in self.task_stats.values()),
        # ... other metrics
    }

    # Calculate completion rate
    if total_stats["created"] > 0:
        total_stats["completion_rate"] = (
            total_stats["completed"] / total_stats["created"]
        )

    return {
        "summary": total_stats,
        "by_project": {k: dict(v) for k, v in self.task_stats.items()}
    }
```

## AgentEventHandlers

**Location**: `application/event_handlers/agent_event_handlers.py`
**Size**: 521 lines
**Events**: 17 agent coordination events

### Class Overview

```python
class AgentEventHandlers:
    """
    Handles agent coordination domain events.

    Processes events related to agent assignments, workload, collaboration,
    conflicts, escalations, and performance evaluation.
    """

    def __init__(
        self,
        event_store: EventStore,
        agent_repository: Optional[Any] = None,
        notification_service: Optional[Any] = None,
        workload_service: Optional[Any] = None
    ):
        self.event_store = event_store
        self.agent_repository = agent_repository
        self.notification_service = notification_service
        self.workload_service = workload_service

        # Agent statistics tracking
        self.agent_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "assignments": 0,
                "unassignments": 0,
                "workload_changes": 0,
                "handoffs_initiated": 0,
                "handoffs_completed": 0,
                "conflicts_detected": 0,
                "conflicts_resolved": 0,
                "collaborations": 0,
                "escalations": 0,
                "evaluations": 0
            }
        )

        # Workload tracking
        self.agent_workloads: Dict[str, float] = {}

        # Active handoffs
        self.active_handoffs: Dict[str, Dict[str, Any]] = {}

        # Active collaborations
        self.active_collaborations: Dict[str, Dict[str, Any]] = {}
```

### Key Handler Methods

#### Assignment & Workload

1. **handle_agent_assigned** - Processes agent assignment to tasks
2. **handle_agent_unassigned** - Processes agent removal from tasks
3. **handle_agent_workload_changed** - Tracks workload changes and triggers rebalancing

#### Work Handoff

4. **handle_work_handoff_requested** - Initiates handoff workflow
5. **handle_work_handoff_accepted** - Completes successful handoff
6. **handle_work_handoff_rejected** - Handles rejected handoffs
7. **handle_work_handoff_completed** - Finalizes handoff and archives

#### Conflict Management

8. **handle_conflict_detected** - Alerts and initiates conflict resolution
9. **handle_conflict_resolved** - Closes conflict and documents resolution

#### Collaboration

10. **handle_agent_collaboration_started** - Initializes collaboration context
11. **handle_agent_collaboration_ended** - Documents outcomes and follow-ups

#### Communication & Status

12. **handle_agent_status_broadcast** - Updates agent availability dashboard
13. **handle_agent_workload_rebalanced** - Executes task reassignments
14. **handle_agent_communication_sent** - Delivers messages and tracks delivery

#### Escalation

15. **handle_agent_escalation_raised** - Alerts escalation target and tracks response
16. **handle_agent_escalation_resolved** - Notifies original agent and documents resolution

#### Performance

17. **handle_agent_performance_evaluated** - Updates agent profile and identifies trends

### Example Handler Implementation

```python
async def handle_agent_workload_changed(self, event: AgentWorkloadChanged) -> None:
    """
    Handle agent workload changed event.

    Monitors workload changes and triggers rebalancing if thresholds exceeded.
    """
    logger.info(
        f"Agent workload changed: {event.agent_id} - "
        f"{event.old_workload_percentage:.1f}% → {event.new_workload_percentage:.1f}%"
    )

    # Update statistics
    self.agent_stats[event.agent_id]["workload_changes"] += 1

    # Track current workload
    self.agent_workloads[event.agent_id] = event.new_workload_percentage

    # Check for overload condition (>80%)
    if event.new_workload_percentage > 80.0:
        logger.warning(f"Agent {event.agent_id} overloaded at {event.new_workload_percentage:.1f}%")

        # Trigger workload rebalancing
        if self.workload_service:
            await self.workload_service.trigger_rebalancing(
                overloaded_agent=event.agent_id,
                reason="workload_threshold_exceeded"
            )

        # Alert via notification service
        if self.notification_service:
            await self.notification_service.alert_agent_overload(
                agent_id=event.agent_id,
                workload_percentage=event.new_workload_percentage
            )

    # Update agent availability status
    if self.agent_repository:
        await self.agent_repository.update_workload(
            agent_id=event.agent_id,
            workload_percentage=event.new_workload_percentage
        )
```

## ProjectEventHandlers

**Location**: `application/event_handlers/project_event_handlers.py`
**Size**: 497 lines
**Events**: 6 project lifecycle events

### Class Overview

```python
class ProjectEventHandlers:
    """
    Handles project lifecycle domain events.

    Processes events related to project creation, updates, deletion,
    statistics updates, health monitoring, and archival.
    """

    def __init__(
        self,
        event_store: EventStore,
        project_repository: Optional[Any] = None,
        notification_service: Optional[Any] = None,
        health_monitor: Optional[Any] = None
    ):
        self.event_store = event_store
        self.project_repository = project_repository
        self.notification_service = notification_service
        self.health_monitor = health_monitor

        # Project statistics tracking
        self.project_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "created_at": None,
                "updates": 0,
                "health_changes": 0,
                "last_health_status": "unknown"
            }
        )

        # Health history
        self.health_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
```

### Key Handler Methods

1. **handle_project_created** - Initializes project structure and default branches
2. **handle_project_updated** - Reindexes and notifies of changes
3. **handle_project_deleted** - Archives and cleans up resources
4. **handle_project_statistics_updated** - Updates dashboards and checks thresholds
5. **handle_project_health_changed** - Alerts stakeholders and triggers interventions
6. **handle_project_archived** - Moves to archive storage and preserves audit trail

### Example Handler Implementation

```python
async def handle_project_health_changed(self, event: ProjectHealthChanged) -> None:
    """
    Handle project health changed event.

    Monitors health transitions and triggers interventions for degraded health.
    """
    logger.info(
        f"Project health changed: {event.project_id} - "
        f"{event.old_health_status} → {event.new_health_status}"
    )

    # Update statistics
    self.project_stats[event.project_id]["health_changes"] += 1
    self.project_stats[event.project_id]["last_health_status"] = event.new_health_status

    # Record health history
    health_record = {
        "timestamp": event.occurred_at.isoformat(),
        "old_status": event.old_health_status,
        "new_status": event.new_health_status,
        "metrics": event.health_metrics,
        "reason": event.reason
    }
    self.health_history[event.project_id].append(health_record)

    # Alert stakeholders for degraded health
    if event.new_health_status in ["at_risk", "critical"]:
        logger.warning(
            f"Project {event.project_id} health degraded to {event.new_health_status}"
        )

        if self.notification_service:
            await self.notification_service.alert_project_health_degraded(
                project_id=event.project_id,
                health_status=event.new_health_status,
                metrics=event.health_metrics,
                reason=event.reason
            )

    # Trigger health interventions
    if self.health_monitor and event.new_health_status == "critical":
        await self.health_monitor.trigger_intervention(
            project_id=event.project_id,
            health_metrics=event.health_metrics
        )

    # Update project repository
    if self.project_repository:
        await self.project_repository.update_health_status(
            project_id=event.project_id,
            health_status=event.new_health_status,
            metrics=event.health_metrics
        )
```

## HintEventHandlers

**Location**: `application/event_handlers/hint_event_handlers.py`
**Events**: 2 hint-related events

Processes hint generation and delivery events for workflow guidance.

## ProgressEventHandlers

**Location**: `application/event_handlers/progress_event_handlers.py`
**Events**: 2 progress-related events

Processes progress tracking and milestone events for task completion monitoring.

## Handler Registration

### Registration Pattern

```python
from fastmcp.task_management.infrastructure.event_bus import event_bus
from fastmcp.task_management.application.event_handlers import (
    TaskEventHandlers,
    AgentEventHandlers,
    ProjectEventHandlers,
    HintEventHandlers,
    ProgressEventHandlers
)

def register_all_handlers(dependencies):
    """Register all event handlers with the event bus."""

    # Initialize handlers
    task_handlers = TaskEventHandlers(
        event_store=dependencies.event_store,
        task_repository=dependencies.task_repository,
        notification_service=dependencies.notification_service
    )

    agent_handlers = AgentEventHandlers(
        event_store=dependencies.event_store,
        agent_repository=dependencies.agent_repository,
        notification_service=dependencies.notification_service,
        workload_service=dependencies.workload_service
    )

    project_handlers = ProjectEventHandlers(
        event_store=dependencies.event_store,
        project_repository=dependencies.project_repository,
        notification_service=dependencies.notification_service,
        health_monitor=dependencies.health_monitor
    )

    # Register task handlers
    event_bus.subscribe(TaskCreatedEvent, task_handlers.handle_task_created)
    event_bus.subscribe(TaskUpdatedEvent, task_handlers.handle_task_updated)
    event_bus.subscribe(TaskDeletedEvent, task_handlers.handle_task_deleted)
    event_bus.subscribe(TaskStatusChangedEvent, task_handlers.handle_task_status_changed)
    event_bus.subscribe(TaskCompletedEvent, task_handlers.handle_task_completed)
    event_bus.subscribe(TaskRetrievedEvent, task_handlers.handle_task_retrieved)
    event_bus.subscribe(TaskMovedToBranchEvent, task_handlers.handle_task_moved_to_branch)

    # Register agent handlers (17 subscriptions)
    event_bus.subscribe(AgentAssigned, agent_handlers.handle_agent_assigned)
    event_bus.subscribe(AgentUnassigned, agent_handlers.handle_agent_unassigned)
    event_bus.subscribe(AgentWorkloadChanged, agent_handlers.handle_agent_workload_changed)
    # ... (14 more agent event subscriptions)

    # Register project handlers (6 subscriptions)
    event_bus.subscribe(ProjectCreatedEvent, project_handlers.handle_project_created)
    event_bus.subscribe(ProjectUpdatedEvent, project_handlers.handle_project_updated)
    event_bus.subscribe(ProjectDeletedEvent, project_handlers.handle_project_deleted)
    event_bus.subscribe(ProjectStatisticsUpdatedEvent, project_handlers.handle_project_statistics_updated)
    event_bus.subscribe(ProjectHealthChanged, project_handlers.handle_project_health_changed)
    event_bus.subscribe(ProjectArchived, project_handlers.handle_project_archived)

    return {
        "task": task_handlers,
        "agent": agent_handlers,
        "project": project_handlers
    }
```

### Application Startup

```python
# In your application initialization (e.g., main.py or app.py)
from fastmcp.task_management.application.event_handlers.registration import register_all_handlers

async def startup():
    """Initialize application and register handlers."""
    # Create dependencies
    dependencies = ApplicationDependencies(
        event_store=EventStore(),
        task_repository=TaskRepository(),
        agent_repository=AgentRepository(),
        project_repository=ProjectRepository(),
        notification_service=NotificationService(),
        workload_service=WorkloadService(),
        health_monitor=HealthMonitor()
    )

    # Register all handlers
    handlers = register_all_handlers(dependencies)

    logger.info("All event handlers registered successfully")

    return handlers
```

## Handler Lifecycle

### Initialization Phase

1. **Create Dependencies**: Initialize all required services
2. **Instantiate Handlers**: Create handler instances with dependencies
3. **Register Subscriptions**: Subscribe handlers to event types
4. **Verify Registration**: Optionally verify all subscriptions active

### Runtime Phase

1. **Event Published**: Event bus receives published event
2. **Dispatch to Handlers**: Event bus calls all registered handlers
3. **Handler Execution**: Each handler processes event asynchronously
4. **Error Handling**: Errors logged but don't stop other handlers
5. **Statistics Update**: Handlers update internal statistics

### Shutdown Phase

1. **Unsubscribe Handlers**: Remove all event subscriptions
2. **Flush Statistics**: Persist any pending statistics
3. **Close Connections**: Clean up database/service connections
4. **Log Summary**: Output final statistics and metrics

## Testing Handlers

### Unit Testing Handlers

```python
import pytest
from unittest.mock import Mock, AsyncMock
from fastmcp.task_management.application.event_handlers import TaskEventHandlers
from fastmcp.task_management.domain.events.task_lifecycle_events import TaskCreatedEvent

@pytest.mark.asyncio
async def test_task_created_handler():
    """Test TaskCreatedEvent handler processes event correctly."""
    # Arrange
    mock_event_store = Mock()
    mock_task_repo = AsyncMock()
    mock_notification = AsyncMock()

    handler = TaskEventHandlers(
        event_store=mock_event_store,
        task_repository=mock_task_repo,
        notification_service=mock_notification
    )

    event = TaskCreatedEvent(
        task_id="task-123",
        branch_id="branch-456",
        title="Test Task",
        status="todo",
        priority="high",
        assignees=["agent-1", "agent-2"]
    )

    # Act
    await handler.handle_task_created(event)

    # Assert
    assert handler.task_stats["unknown"]["created"] == 1
    mock_task_repo.track_task_creation.assert_called_once_with(event)
    assert mock_notification.notify_task_assignment.call_count == 2
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_handler_integration_with_event_bus():
    """Test handler integration with event bus."""
    # Arrange
    event_bus = EventBus (with EventQueue and EventWorker)()
    dependencies = create_test_dependencies()
    handlers = register_all_handlers(dependencies)

    event = TaskCreatedEvent(...)

    # Act
    await event_bus.publish_async(event)

    # Assert - verify handler was called and side effects occurred
    stats = await handlers["task"].get_task_statistics()
    assert stats["summary"]["created"] == 1
```

### Testing Error Handling

```python
@pytest.mark.asyncio
async def test_handler_error_handling():
    """Test handler handles errors gracefully."""
    # Arrange
    mock_notification = AsyncMock(side_effect=Exception("Service unavailable"))
    handler = TaskEventHandlers(
        event_store=Mock(),
        notification_service=mock_notification
    )

    event = TaskCreatedEvent(...)

    # Act - should not raise exception
    await handler.handle_task_created(event)

    # Assert - statistics still updated despite notification failure
    assert handler.task_stats["unknown"]["created"] == 1
```

## Best Practices

### 1. Idempotency

**Rule**: Handlers should be safe to call multiple times with same event

```python
async def handle_task_completed(self, event: TaskCompletedEvent) -> None:
    """Handle task completion (idempotent)."""
    # Check if already processed
    if await self.event_store.has_processed(event.event_id):
        logger.debug(f"Event {event.event_id} already processed")
        return

    # Process event
    await self._update_statistics(event)

    # Mark as processed
    await self.event_store.mark_processed(event.event_id)
```

### 2. Error Isolation

**Rule**: Errors in one handler shouldn't affect others

```python
async def handle_event(self, event: BaseDomainEvent) -> None:
    """Handle event with isolated error handling."""
    try:
        # Critical operation
        await self._update_required_state(event)
    except Exception as e:
        logger.error(f"Critical error in handler: {e}", exc_info=True)
        raise  # Re-raise for critical operations

    try:
        # Non-critical operation
        await self._send_notification(event)
    except Exception as e:
        logger.warning(f"Notification failed: {e}")
        # Don't re-raise for non-critical operations
```

### 3. Performance

**Rule**: Handlers should be fast and non-blocking

```python
async def handle_event(self, event: BaseDomainEvent) -> None:
    """Handle event efficiently."""
    # Good: Async I/O operations
    await asyncio.gather(
        self._update_stats(event),
        self._send_notification(event),
        self._trigger_workflow(event)
    )

    # Avoid: Blocking operations
    # time.sleep(5)  # Bad!
    # requests.get(url)  # Bad! Use aiohttp instead
```

### 4. Testing

**Rule**: Test handlers with mocked dependencies

```python
@pytest.fixture
def task_handler():
    """Create TaskEventHandlers with mocked dependencies."""
    return TaskEventHandlers(
        event_store=Mock(),
        task_repository=AsyncMock(),
        notification_service=AsyncMock()
    )

@pytest.mark.asyncio
async def test_with_mocks(task_handler):
    """Test handler behavior with mocked dependencies."""
    event = TaskCreatedEvent(...)
    await task_handler.handle_task_created(event)

    # Verify mock calls
    task_handler.task_repository.track_task_creation.assert_called_once()
```

### 5. Logging

**Rule**: Log at appropriate levels with context

```python
async def handle_event(self, event: BaseDomainEvent) -> None:
    """Handle event with proper logging."""
    # INFO: Normal operations
    logger.info(f"Processing {event.event_type}: {event.event_id}")

    # WARNING: Degraded conditions
    if workload > 80:
        logger.warning(f"Agent {agent_id} overloaded: {workload}%")

    # ERROR: Failures that need attention
    try:
        await self._critical_operation()
    except Exception as e:
        logger.error(f"Critical failure: {e}", exc_info=True)

    # DEBUG: Detailed troubleshooting info
    logger.debug(f"Event details: {event.to_dict()}")
```

## Related Documentation

- [Domain Events Catalog](../core-architecture/domain-events-catalog.md) - Complete event reference
- [Domain Events Usage Guide](./domain-events-usage-guide.md) - How to create and use events
- [DDD Refactoring Task Roadmap](./ddd-refactoring-task-roadmap.md) - Phase 5 context
- [Testing Guide](../testing-qa/testing-guide.md) - Testing patterns and best practices

---

**Document Status**: Complete ✅
**Total Handlers Documented**: 5 handler classes covering 30+ events
**Next Steps**: Implement handlers in your domain following these patterns
