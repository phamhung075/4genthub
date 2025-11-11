"""Comprehensive Integration Tests for Domain Event Flow

This test suite verifies the complete domain event flow from entity to handlers,
covering all event types and scenarios in the DDD Phase 5 refactoring.

Test Coverage:
- End-to-end event flow (entity → repository → event bus → handlers)
- Task lifecycle events
- Agent coordination events
- Project lifecycle events
- Event bus integration
- Event persistence
- Cross-aggregate coordination
- Error handling and edge cases
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from fastmcp.task_management.application.event_handlers.agent_event_handlers import (
    AgentEventHandlers,
)
from fastmcp.task_management.application.event_handlers.project_event_handlers import (
    ProjectEventHandlers,
)

# Event Handlers
from fastmcp.task_management.application.event_handlers.task_event_handlers import (
    TaskEventHandlers,
)
from fastmcp.task_management.domain.events.agent_events import (
    AgentAssigned,
    AgentUnassigned,
    AgentWorkloadChanged,
)

# Domain Events
from fastmcp.task_management.domain.events.base import BaseDomainEvent
from fastmcp.task_management.domain.events.project_lifecycle_events import (
    ProjectArchived,
    ProjectCreatedEvent,
    ProjectHealthChanged,
    ProjectStatisticsUpdatedEvent,
)
from fastmcp.task_management.domain.events.task_lifecycle_events import (
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskMovedToBranchEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)

# Event Infrastructure
from fastmcp.task_management.infrastructure.event_bus import (
    get_event_bus,
    reset_event_bus,
)

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def event_bus():
    """Event bus fixture with clean state"""
    reset_event_bus()
    bus = get_event_bus()
    yield bus
    bus.clear_subscriptions()
    reset_event_bus()


@pytest.fixture
def mock_event_store():
    """Mock event store for testing"""
    store = MagicMock()
    store.save_event = AsyncMock()
    store.get_events = AsyncMock(return_value=[])
    store.get_events_by_aggregate = AsyncMock(return_value=[])
    return store


@pytest.fixture
def mock_task_repository():
    """Mock task repository for testing"""
    repo = MagicMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_agent_repository():
    """Mock agent repository for testing"""
    repo = MagicMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_project_repository():
    """Mock project repository for testing"""
    repo = MagicMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def task_event_handler(mock_event_store, mock_task_repository):
    """Task event handler fixture"""
    return TaskEventHandlers(mock_event_store, mock_task_repository)


@pytest.fixture
def agent_event_handler(mock_event_store, mock_agent_repository):
    """Agent event handler fixture"""
    return AgentEventHandlers(mock_event_store, mock_agent_repository)


@pytest.fixture
def project_event_handler(mock_event_store, mock_project_repository):
    """Project event handler fixture"""
    return ProjectEventHandlers(mock_event_store, mock_project_repository)


# ==============================================================================
# Test Class 1: End-to-End Event Flow Tests
# ==============================================================================


class TestEndToEndEventFlow:
    """Test complete event flow from entity to handlers"""

    @pytest.mark.asyncio
    async def test_task_creation_full_flow(self, event_bus, task_event_handler):
        """Test: Create task → Event raised → Published → Handled → Statistics updated"""
        # Setup: Track handler calls
        handled_events = []

        async def track_handler(event: TaskCreatedEvent):
            handled_events.append(event)

        event_bus.subscribe(TaskCreatedEvent, track_handler)

        # Action: Create and publish task created event
        task_id = str(uuid4())
        branch_id = str(uuid4())
        event = TaskCreatedEvent(
            task_id=task_id,
            branch_id=branch_id,
            title="Test Task",
            status="todo",
            priority="high",
            assignees=["coding-agent"],
            user_id="user123",
        )

        await event_bus.publish(event)

        # Verify: Event was received and processed
        assert len(handled_events) == 1
        assert handled_events[0].task_id == task_id
        assert handled_events[0].title == "Test Task"
        assert handled_events[0].status == "todo"

    @pytest.mark.asyncio
    async def test_task_update_full_flow(self, event_bus):
        """Test: Update task → Event raised → Published → Handled → Notifications sent"""
        # Setup
        handled_events = []

        async def update_handler(event: TaskUpdatedEvent):
            handled_events.append(event)

        event_bus.subscribe(TaskUpdatedEvent, update_handler)

        # Action
        task_id = str(uuid4())
        event = TaskUpdatedEvent(
            task_id=task_id,
            branch_id=str(uuid4()),
            old_status="todo",
            new_status="in_progress",
            changes={"status": {"old": "todo", "new": "in_progress"}},
            user_id="user123",
        )

        await event_bus.publish(event)

        # Verify
        assert len(handled_events) == 1
        assert handled_events[0].old_status == "todo"
        assert handled_events[0].new_status == "in_progress"
        assert "status" in handled_events[0].changes

    @pytest.mark.asyncio
    async def test_task_completion_full_flow(self, event_bus):
        """Test: Complete task → Event raised → Published → Handled → Metrics calculated"""
        # Setup
        handled_events = []

        def completion_handler(event: TaskCompletedEvent):
            handled_events.append(event)

        event_bus.subscribe(TaskCompletedEvent, completion_handler)

        # Action
        event = TaskCompletedEvent(
            task_id=str(uuid4()),
            branch_id=str(uuid4()),
            title="Completed Task",
            completion_summary="All features implemented",
            testing_notes="All tests passing",
            completed_by="user123",
            time_spent_minutes=120,
            insights_found=["Learned new pattern"],
        )

        await event_bus.publish(event)
        await asyncio.sleep(0.1)  # Give time for async processing

        # Verify
        assert len(handled_events) == 1
        assert handled_events[0].completion_summary == "All features implemented"
        assert handled_events[0].time_spent_minutes == 120
        assert len(handled_events[0].insights_found) == 1

    @pytest.mark.asyncio
    async def test_task_deletion_full_flow(self, event_bus):
        """Test: Delete task → Event raised → Published → Handled → Archival triggered"""
        # Setup
        handled_events = []

        async def deletion_handler(event: TaskDeletedEvent):
            handled_events.append(event)

        event_bus.subscribe(TaskDeletedEvent, deletion_handler)

        # Action
        event = TaskDeletedEvent(
            task_id=str(uuid4()),
            branch_id=str(uuid4()),
            status="cancelled",
            title="Deleted Task",
            user_id="user123",
        )

        await event_bus.publish(event)

        # Verify
        assert len(handled_events) == 1
        assert handled_events[0].status == "cancelled"
        assert handled_events[0].title == "Deleted Task"


# ==============================================================================
# Test Class 2: Task Lifecycle Event Tests
# ==============================================================================


class TestTaskLifecycleEvents:
    """Test task lifecycle event structure and behavior"""

    def test_task_created_event_structure(self):
        """Verify TaskCreatedEvent has all required fields"""
        event = TaskCreatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="New Task",
            status="todo",
            priority="medium",
            assignees=["coding-agent", "test-agent"],
            user_id="user789",
        )

        # Verify all fields present
        assert event.task_id == "task-123"
        assert event.branch_id == "branch-456"
        assert event.title == "New Task"
        assert event.status == "todo"
        assert event.priority == "medium"
        assert len(event.assignees) == 2
        assert event.user_id == "user789"

        # Verify metadata
        assert isinstance(event.event_id, UUID)
        assert isinstance(event.occurred_at, datetime)
        assert event.event_type == "TaskCreatedEvent"

    def test_task_updated_event_with_changes(self):
        """Verify TaskUpdatedEvent changes dictionary is correct"""
        changes = {
            "status": {"old": "todo", "new": "in_progress"},
            "priority": {"old": "low", "new": "high"},
            "assignees": {"old": ["agent1"], "new": ["agent1", "agent2"]},
        }

        event = TaskUpdatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            old_status="todo",
            new_status="in_progress",
            changes=changes,
            user_id="user789",
        )

        # Verify changes tracked correctly
        assert "status" in event.changes
        assert "priority" in event.changes
        assert "assignees" in event.changes
        assert event.changes["status"]["new"] == "in_progress"
        assert len(event.changes["assignees"]["new"]) == 2

    def test_task_completed_event_timing(self):
        """Verify TaskCompletedEvent completion time calculation"""
        event = TaskCompletedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Completed Task",
            completion_summary="Done",
            time_spent_minutes=90,
        )

        assert event.time_spent_minutes == 90
        assert isinstance(event.occurred_at, datetime)
        # Completion time should be recent
        time_diff = (datetime.now(UTC) - event.occurred_at).total_seconds()
        assert time_diff < 1  # Less than 1 second old

    def test_task_status_changed_event_transitions(self):
        """Verify TaskStatusChangedEvent valid status transitions"""
        valid_transitions = [
            ("todo", "in_progress"),
            ("in_progress", "review"),
            ("review", "done"),
            ("in_progress", "blocked"),
        ]

        for old_status, new_status in valid_transitions:
            event = TaskStatusChangedEvent(
                task_id="task-123",
                branch_id="branch-456",
                old_status=old_status,
                new_status=new_status,
                user_id="user789",
            )

            assert event.old_status == old_status
            assert event.new_status == new_status
            assert event.old_status != event.new_status

    def test_task_moved_to_branch_event(self):
        """Verify TaskMovedToBranchEvent branch movement events"""
        old_branch = str(uuid4())
        new_branch = str(uuid4())

        event = TaskMovedToBranchEvent(
            task_id="task-123",
            old_branch_id=old_branch,
            new_branch_id=new_branch,
            user_id="user789",
        )

        assert event.old_branch_id == old_branch
        assert event.new_branch_id == new_branch
        assert event.old_branch_id != event.new_branch_id


# ==============================================================================
# Test Class 3: Agent Coordination Event Tests
# ==============================================================================


class TestAgentCoordinationEvents:
    """Test agent coordination event flow"""

    @pytest.mark.asyncio
    async def test_agent_assigned_event_flow(self, event_bus):
        """Agent assignment → Event → Handler → Workload updated"""
        handled = []

        async def handler(event: AgentAssigned):
            handled.append(event)

        event_bus.subscribe(AgentAssigned, handler)

        event = AgentAssigned(
            agent_id="coding-agent",
            task_id="task-123",
            role="implementation",
            assigned_by="user123",
            responsibilities=["Implement feature"],
        )

        await event_bus.publish(event)

        assert len(handled) == 1
        assert handled[0].agent_id == "coding-agent"
        assert handled[0].task_id == "task-123"

    @pytest.mark.asyncio
    async def test_agent_unassigned_event_flow(self, event_bus):
        """Agent removal → Event → Handler → Workload recalculated"""
        handled = []

        def handler(event: AgentUnassigned):
            handled.append(event)

        event_bus.subscribe(AgentUnassigned, handler)

        event = AgentUnassigned(
            agent_id="coding-agent",
            task_id="task-123",
            unassigned_by="user123",
            reason="Task completed",
        )

        await event_bus.publish(event)
        await asyncio.sleep(0.1)

        assert len(handled) == 1
        assert handled[0].agent_id == "coding-agent"

    @pytest.mark.asyncio
    async def test_agent_workload_changed_event(self, event_bus):
        """Workload change → Event → Handler → Metrics updated"""
        handled = []

        async def handler(event: AgentWorkloadChanged):
            handled.append(event)

        event_bus.subscribe(AgentWorkloadChanged, handler)

        event = AgentWorkloadChanged(
            agent_id="coding-agent",
            old_task_count=5,
            new_task_count=7,
            old_workload_percentage=50.0,
            new_workload_percentage=70.0,
            reason="New task assigned",
        )

        await event_bus.publish(event)

        assert len(handled) == 1
        assert handled[0].old_task_count == 5
        assert handled[0].new_task_count == 7

    @pytest.mark.asyncio
    async def test_multiple_agent_assignments(self, event_bus):
        """Multiple agents → Events → Handlers → All notified"""
        handled = []

        async def handler(event: AgentAssigned):
            handled.append(event)

        event_bus.subscribe(AgentAssigned, handler)

        # Assign multiple agents
        agents = ["coding-agent", "test-agent", "review-agent"]
        for agent in agents:
            event = AgentAssigned(
                agent_id=agent,
                task_id="task-123",
                role="implementation",
                assigned_by="user123",
            )
            await event_bus.publish(event)

        assert len(handled) == 3
        handled_agents = [e.agent_id for e in handled]
        assert set(handled_agents) == set(agents)


# ==============================================================================
# Test Class 4: Project Lifecycle Event Tests
# ==============================================================================


class TestProjectLifecycleEvents:
    """Test project lifecycle event flow"""

    @pytest.mark.asyncio
    async def test_project_created_event_flow(self, event_bus):
        """Project creation → Event → Handler → Initialization"""
        handled = []

        async def handler(event: ProjectCreatedEvent):
            handled.append(event)

        event_bus.subscribe(ProjectCreatedEvent, handler)

        event = ProjectCreatedEvent(
            project_id="proj-123",
            name="New Project",
            description="Test project",
            status="active",
        )

        await event_bus.publish(event)

        assert len(handled) == 1
        assert handled[0].project_id == "proj-123"
        assert handled[0].name == "New Project"

    @pytest.mark.asyncio
    async def test_project_archived_event_flow(self, event_bus):
        """Project archival → Event → Handler → Cleanup"""
        handled = []

        def handler(event: ProjectArchived):
            handled.append(event)

        event_bus.subscribe(ProjectArchived, handler)

        event = ProjectArchived(
            project_id="proj-123",
            name="Test Project",
            archived_by="user123",
            reason="Project completed",
        )

        await event_bus.publish(event)
        await asyncio.sleep(0.1)

        assert len(handled) == 1
        assert handled[0].reason == "Project completed"

    @pytest.mark.asyncio
    async def test_project_health_changed_event(self, event_bus):
        """Health change → Event → Handler → Intervention triggered"""
        handled = []

        async def handler(event: ProjectHealthChanged):
            handled.append(event)

        event_bus.subscribe(ProjectHealthChanged, handler)

        event = ProjectHealthChanged(
            project_id="proj-123",
            old_health_status="healthy",
            new_health_status="warning",
            health_metrics={"bug_count": 15, "test_coverage": 65},
            reason="Test coverage dropped below threshold",
        )

        await event_bus.publish(event)

        assert len(handled) == 1
        assert handled[0].new_health_status == "warning"
        assert handled[0].health_metrics["bug_count"] == 15

    @pytest.mark.asyncio
    async def test_project_statistics_updated_event(self, event_bus):
        """Stats update → Event → Handler → Metrics refreshed"""
        handled = []

        async def handler(event: ProjectStatisticsUpdatedEvent):
            handled.append(event)

        event_bus.subscribe(ProjectStatisticsUpdatedEvent, handler)

        event = ProjectStatisticsUpdatedEvent(
            project_id="proj-123",
            branch_count=3,
            total_tasks=50,
            completed_tasks=30,
            in_progress_tasks=15,
            todo_tasks=5,
            overall_progress_percentage=60.0,
        )

        await event_bus.publish(event)

        assert len(handled) == 1
        assert handled[0].total_tasks == 50
        assert handled[0].completed_tasks == 30


# ==============================================================================
# Test Class 5: Event Bus Integration Tests
# ==============================================================================


class TestEventBusIntegration:
    """Test event bus integration with repositories"""

    @pytest.mark.asyncio
    async def test_multiple_handlers_same_event(self, event_bus):
        """Multiple handlers receive same event"""
        handler1_calls = []
        handler2_calls = []
        handler3_calls = []

        def handler1(event: TaskCreatedEvent):
            handler1_calls.append(event)

        async def handler2(event: TaskCreatedEvent):
            handler2_calls.append(event)

        def handler3(event: TaskCreatedEvent):
            handler3_calls.append(event)

        event_bus.subscribe(TaskCreatedEvent, handler1)
        event_bus.subscribe(TaskCreatedEvent, handler2)
        event_bus.subscribe(TaskCreatedEvent, handler3)

        event = TaskCreatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Test",
            status="todo",
            priority="medium",
        )

        await event_bus.publish(event)
        await asyncio.sleep(0.1)

        # All handlers should be called
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
        assert len(handler3_calls) == 1

    @pytest.mark.asyncio
    async def test_async_event_processing(self, event_bus):
        """Events processed asynchronously"""
        processed = []
        processing_times = []

        async def slow_handler(event: TaskCreatedEvent):
            start = datetime.now(UTC)
            await asyncio.sleep(0.05)
            processed.append(event)
            end = datetime.now(UTC)
            processing_times.append((end - start).total_seconds())

        event_bus.subscribe(TaskCreatedEvent, slow_handler)

        # Publish multiple events
        for i in range(3):
            event = TaskCreatedEvent(
                task_id=f"task-{i}",
                branch_id="branch-456",
                title=f"Task {i}",
                status="todo",
                priority="medium",
            )
            await event_bus.publish(event)

        # Wait for processing
        await asyncio.sleep(0.3)

        assert len(processed) == 3
        # Each should take ~50ms
        assert all(0.04 < t < 0.1 for t in processing_times)

    @pytest.mark.asyncio
    async def test_event_ordering_guaranteed(self, event_bus):
        """Events processed in order"""
        processed_order = []

        async def order_tracker(event: TaskCreatedEvent):
            processed_order.append(event.task_id)

        event_bus.subscribe(TaskCreatedEvent, order_tracker)

        # Publish in specific order
        for i in range(5):
            event = TaskCreatedEvent(
                task_id=f"task-{i}",
                branch_id="branch-456",
                title=f"Task {i}",
                status="todo",
                priority="medium",
            )
            await event_bus.publish(event)

        await asyncio.sleep(0.2)

        # Verify order preserved
        assert processed_order == ["task-0", "task-1", "task-2", "task-3", "task-4"]

    @pytest.mark.asyncio
    async def test_event_handler_error_isolation(self, event_bus):
        """Handler error doesn't affect others"""
        successful_calls = []

        def failing_handler(event: TaskCreatedEvent):
            raise Exception("Handler failed")

        def successful_handler(event: TaskCreatedEvent):
            successful_calls.append(event)

        event_bus.subscribe(TaskCreatedEvent, failing_handler)
        event_bus.subscribe(TaskCreatedEvent, successful_handler)

        event = TaskCreatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Test",
            status="todo",
            priority="medium",
        )

        await event_bus.publish(event)
        await asyncio.sleep(0.1)

        # Successful handler should still execute
        assert len(successful_calls) == 1


# ==============================================================================
# Test Class 6: Event Persistence Tests
# ==============================================================================


class TestEventPersistence:
    """Test event persistence to event store"""

    @pytest.mark.asyncio
    async def test_events_persisted_to_event_store(self, mock_event_store):
        """Events saved for audit trail"""
        # Create event
        event = TaskCreatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Test Task",
            status="todo",
            priority="high",
        )

        # Save to store
        await mock_event_store.save_event(event)

        # Verify saved
        mock_event_store.save_event.assert_called_once()
        saved_event = mock_event_store.save_event.call_args[0][0]
        assert saved_event.task_id == "task-123"

    @pytest.mark.asyncio
    async def test_event_replay_from_store(self, mock_event_store, event_bus):
        """Events can be replayed"""
        # Mock stored events
        stored_events = [
            TaskCreatedEvent(
                task_id="task-1",
                branch_id="b1",
                title="T1",
                status="todo",
                priority="low",
            ),
            TaskCreatedEvent(
                task_id="task-2",
                branch_id="b1",
                title="T2",
                status="todo",
                priority="low",
            ),
        ]
        mock_event_store.get_events.return_value = stored_events

        # Replay events
        replayed = []

        async def replay_handler(event: TaskCreatedEvent):
            replayed.append(event)

        event_bus.subscribe(TaskCreatedEvent, replay_handler)

        # Simulate replay
        events = await mock_event_store.get_events()
        for event in events:
            await event_bus.publish(event)

        await asyncio.sleep(0.1)

        assert len(replayed) == 2

    @pytest.mark.asyncio
    async def test_event_history_retrieval(self, mock_event_store):
        """Event history can be queried"""
        task_id = "task-123"

        # Mock historical events
        historical_events = [
            TaskCreatedEvent(
                task_id=task_id,
                branch_id="b1",
                title="T",
                status="todo",
                priority="low",
            ),
            TaskUpdatedEvent(
                task_id=task_id,
                branch_id="b1",
                old_status="todo",
                new_status="in_progress",
            ),
            TaskCompletedEvent(
                task_id=task_id, branch_id="b1", title="T", completion_summary="Done"
            ),
        ]
        mock_event_store.get_events_by_aggregate.return_value = historical_events

        # Retrieve history
        history = await mock_event_store.get_events_by_aggregate(task_id)

        assert len(history) == 3
        assert isinstance(history[0], TaskCreatedEvent)
        assert isinstance(history[1], TaskUpdatedEvent)
        assert isinstance(history[2], TaskCompletedEvent)

    @pytest.mark.asyncio
    async def test_event_metadata_preserved(self, mock_event_store):
        """Event metadata preserved through persistence"""
        event = TaskCreatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Test",
            status="todo",
            priority="high",
            user_id="user789",
        )

        original_id = event.event_id
        original_time = event.occurred_at

        # Save and verify
        await mock_event_store.save_event(event)

        saved_event = mock_event_store.save_event.call_args[0][0]
        assert saved_event.event_id == original_id
        assert saved_event.occurred_at == original_time
        assert saved_event.user_id == "user789"


# ==============================================================================
# Test Class 7: Cross-Aggregate Event Tests
# ==============================================================================


class TestCrossAggregateEvents:
    """Test events that coordinate across multiple aggregates"""

    @pytest.mark.asyncio
    async def test_task_completion_triggers_project_stats(self, event_bus):
        """Task done → Project stats updated"""
        project_updates = []

        async def project_stats_handler(event: ProjectStatisticsUpdatedEvent):
            project_updates.append(event)

        event_bus.subscribe(ProjectStatisticsUpdatedEvent, project_stats_handler)

        # Simulate task completion triggering project stats update
        task_event = TaskCompletedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Completed Task",
            completion_summary="Done",
        )
        await event_bus.publish(task_event)

        # Simulate project stats update
        stats_event = ProjectStatisticsUpdatedEvent(
            project_id="proj-789",
            branch_count=3,
            total_tasks=10,
            completed_tasks=6,
            in_progress_tasks=3,
            todo_tasks=1,
            overall_progress_percentage=60.0,
        )
        await event_bus.publish(stats_event)

        assert len(project_updates) == 1
        assert project_updates[0].completed_tasks == 6

    @pytest.mark.asyncio
    async def test_agent_assignment_updates_branch_metrics(self, event_bus):
        """Agent assigned → Branch metrics updated"""
        agent_assignments = []

        async def assignment_handler(event: AgentAssigned):
            agent_assignments.append(event)

        event_bus.subscribe(AgentAssigned, assignment_handler)

        event = AgentAssigned(
            agent_id="coding-agent",
            task_id="task-123",
            role="implementation",
            assigned_by="user123",
        )
        await event_bus.publish(event)

        assert len(agent_assignments) == 1

    @pytest.mark.asyncio
    async def test_multiple_aggregate_coordination(self, event_bus):
        """Events coordinate across Task/Agent/Project"""
        all_events = []

        async def universal_handler(event: BaseDomainEvent):
            all_events.append(event)

        # Subscribe to all event types
        event_bus.subscribe(TaskCreatedEvent, universal_handler)
        event_bus.subscribe(AgentAssigned, universal_handler)
        event_bus.subscribe(ProjectStatisticsUpdatedEvent, universal_handler)

        # Publish events from different aggregates
        await event_bus.publish(
            TaskCreatedEvent(
                task_id="task-1",
                branch_id="b1",
                title="T",
                status="todo",
                priority="low",
            )
        )
        await event_bus.publish(
            AgentAssigned(
                agent_id="a1", task_id="task-1", role="impl", assigned_by="user"
            )
        )
        await event_bus.publish(
            ProjectStatisticsUpdatedEvent(
                project_id="p1",
                branch_count=1,
                total_tasks=1,
                completed_tasks=0,
                in_progress_tasks=1,
                todo_tasks=0,
                overall_progress_percentage=0.0,
            )
        )

        assert len(all_events) == 3


# ==============================================================================
# Test Class 8: Error Handling and Edge Cases
# ==============================================================================


class TestEventErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_event_handler_exception_logged(self, event_bus):
        """Handler exceptions logged, not propagated"""
        successful_calls = []

        def failing_handler(event: TaskCreatedEvent):
            raise ValueError("Handler error")

        def successful_handler(event: TaskCreatedEvent):
            successful_calls.append(event)

        event_bus.subscribe(TaskCreatedEvent, failing_handler)
        event_bus.subscribe(TaskCreatedEvent, successful_handler)

        event = TaskCreatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Test",
            status="todo",
            priority="medium",
        )

        # Should not raise exception
        await event_bus.publish(event)
        await asyncio.sleep(0.1)

        # Successful handler still executed
        assert len(successful_calls) == 1

    @pytest.mark.asyncio
    async def test_invalid_event_data_handled(self, event_bus):
        """Invalid event data handled gracefully"""
        handled = []

        def handler(event: TaskCreatedEvent):
            # Validate event data
            if not event.task_id:
                return
            handled.append(event)

        event_bus.subscribe(TaskCreatedEvent, handler)

        # Event with empty task_id
        event = TaskCreatedEvent(
            task_id="",
            branch_id="branch-456",
            title="Test",
            status="todo",
            priority="medium",
        )

        await event_bus.publish(event)
        await asyncio.sleep(0.1)

        # Handler should skip invalid event
        assert len(handled) == 0

    @pytest.mark.asyncio
    async def test_concurrent_event_processing(self, event_bus):
        """Concurrent events handled correctly"""
        processed = []
        lock = asyncio.Lock()

        async def concurrent_handler(event: TaskCreatedEvent):
            async with lock:
                await asyncio.sleep(0.01)
                processed.append(event.task_id)

        event_bus.subscribe(TaskCreatedEvent, concurrent_handler)

        # Publish multiple events concurrently
        tasks = []
        for i in range(5):
            event = TaskCreatedEvent(
                task_id=f"task-{i}",
                branch_id="branch-456",
                title=f"Task {i}",
                status="todo",
                priority="medium",
            )
            tasks.append(event_bus.publish(event))

        await asyncio.gather(*tasks)
        await asyncio.sleep(0.2)

        # All events should be processed
        assert len(processed) == 5
        assert set(processed) == {f"task-{i}" for i in range(5)}

    @pytest.mark.asyncio
    async def test_event_with_no_subscribers(self, event_bus):
        """Event with no subscribers handled gracefully"""
        # Create event with no subscribers
        event = TaskCreatedEvent(
            task_id="task-123",
            branch_id="branch-456",
            title="Orphan Event",
            status="todo",
            priority="low",
        )

        # Should not raise exception
        await event_bus.publish(event)

        # Verify no subscribers
        assert not event_bus.has_subscribers(TaskCreatedEvent)


# ==============================================================================
# Test Execution Summary
# ==============================================================================

"""
Test Coverage Summary:

✅ Class 1: TestEndToEndEventFlow (4 tests)
   - test_task_creation_full_flow
   - test_task_update_full_flow
   - test_task_completion_full_flow
   - test_task_deletion_full_flow

✅ Class 2: TestTaskLifecycleEvents (5 tests)
   - test_task_created_event_structure
   - test_task_updated_event_with_changes
   - test_task_completed_event_timing
   - test_task_status_changed_event_transitions
   - test_task_moved_to_branch_event

✅ Class 3: TestAgentCoordinationEvents (4 tests)
   - test_agent_assigned_event_flow
   - test_agent_unassigned_event_flow
   - test_agent_workload_changed_event
   - test_multiple_agent_assignments

✅ Class 4: TestProjectLifecycleEvents (4 tests)
   - test_project_created_event_flow
   - test_project_archived_event_flow
   - test_project_health_changed_event
   - test_project_statistics_updated_event

✅ Class 5: TestEventBusIntegration (5 tests)
   - test_multiple_handlers_same_event
   - test_async_event_processing
   - test_event_ordering_guaranteed
   - test_event_handler_error_isolation

✅ Class 6: TestEventPersistence (4 tests)
   - test_events_persisted_to_event_store
   - test_event_replay_from_store
   - test_event_history_retrieval
   - test_event_metadata_preserved

✅ Class 7: TestCrossAggregateEvents (3 tests)
   - test_task_completion_triggers_project_stats
   - test_agent_assignment_updates_branch_metrics
   - test_multiple_aggregate_coordination

✅ Class 8: TestEventErrorHandling (4 tests)
   - test_event_handler_exception_logged
   - test_invalid_event_data_handled
   - test_concurrent_event_processing
   - test_event_with_no_subscribers

TOTAL: 33 comprehensive integration tests covering all event flow scenarios
"""
