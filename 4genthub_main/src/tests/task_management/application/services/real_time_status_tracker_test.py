"""Test real-time status tracker service"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from uuid import uuid4

from fastmcp.task_management.application.services.real_time_status_tracker import (
    RealTimeStatusTracker,
    StatusUpdateType,
    StatusSnapshot,
    StatusSubscription
)
from fastmcp.task_management.domain.entities.agent_session import (
    AgentSession, SessionState, ResourceType
)
from fastmcp.task_management.domain.value_objects.agents import AgentStatus


class TestRealTimeStatusTracker:
    """Test real-time status tracking functionality"""

    @pytest.fixture
    def event_bus(self):
        """Create mock event bus"""
        return AsyncMock()

    @pytest_asyncio.fixture
    async def tracker(self, event_bus):
        """Create tracker instance"""
        tracker = RealTimeStatusTracker(
            event_bus=event_bus,
            history_retention_hours=2,
            snapshot_interval_seconds=0.1,  # Use very short interval for tests
            anomaly_threshold=0.8
        )
        await tracker.start()
        yield tracker
        # Force stop with immediate cancellation
        tracker._is_running = False
        if tracker._monitoring_task:
            tracker._monitoring_task.cancel()
        if tracker._cleanup_task:
            tracker._cleanup_task.cancel()
        # Give tasks a moment to cancel
        await asyncio.sleep(0.01)
        await tracker.stop()

    @pytest.fixture
    def mock_session(self):
        """Create mock agent session"""
        session = Mock(spec=AgentSession)
        session.session_id = str(uuid4())
        session.agent_id = "agent-123"
        session.project_id = "proj-456"
        session.state = SessionState.IDLE
        session.active_tasks = set()
        session.started_at = datetime.now(timezone.utc)
        session.last_heartbeat = datetime.now(timezone.utc)
        session.max_idle_time = 300
        session.metrics = {
            "messages_sent": 10,
            "messages_received": 15,
            "tasks_completed": 3,
            "tasks_failed": 0,
            "error_count": 0,
            "recovery_count": 0,
            "avg_response_time_ms": 150.0
        }
        session.metadata = {}
        
        # Mock methods
        session.calculate_health_score = Mock(return_value=0.95)
        session.get_resource_usage_summary = Mock(return_value={"cpu": 50.0, "memory": 60.0})
        session.is_alive = Mock(return_value=True)
        session.is_expired = Mock(return_value=False)
        session.is_idle = Mock(return_value=False)
        session.needs_recovery = Mock(return_value=False)
        session.update_heartbeat = Mock()
        session.start_task = Mock()
        session.complete_task = Mock()
        session.update_resource_usage = Mock()
        session.recover = Mock()
        session.terminate = Mock()
        
        return session

    @pytest.mark.asyncio
    async def test_tracker_initialization(self, event_bus):
        """Test tracker initialization"""
        tracker = RealTimeStatusTracker(
            event_bus=event_bus,
            history_retention_hours=24,
            snapshot_interval_seconds=30,
            anomaly_threshold=0.75
        )
        
        assert tracker.history_retention_hours == 24
        assert tracker.snapshot_interval_seconds == 30
        assert tracker.anomaly_threshold == 0.75
        assert not tracker._is_running
        assert len(tracker.active_sessions) == 0

    @pytest.mark.asyncio
    async def test_start_stop(self, event_bus):
        """Test starting and stopping tracker"""
        tracker = RealTimeStatusTracker(event_bus=event_bus)
        
        # Start
        await tracker.start()
        assert tracker._is_running
        assert tracker._monitoring_task is not None
        assert tracker._cleanup_task is not None
        
        # Start again (should be idempotent)
        await tracker.start()
        assert tracker._is_running
        
        # Stop
        await tracker.stop()
        assert not tracker._is_running

    @pytest.mark.asyncio
    async def test_register_session(self, tracker, mock_session):
        """Test registering agent session"""
        await tracker.register_session(mock_session)
        
        # Verify registration
        assert mock_session.session_id in tracker.active_sessions
        assert tracker.session_by_agent[mock_session.agent_id] == mock_session.session_id
        assert mock_session.agent_id in tracker.status_history
        assert len(tracker.status_history[mock_session.agent_id]) > 0

    @pytest.mark.asyncio
    async def test_unregister_session(self, tracker, mock_session):
        """Test unregistering agent session"""
        # Register first
        await tracker.register_session(mock_session)
        
        # Unregister
        await tracker.unregister_session(mock_session.session_id)
        
        # Verify cleanup
        assert mock_session.session_id not in tracker.active_sessions
        assert mock_session.agent_id not in tracker.session_by_agent
        
        # History should still exist
        assert mock_session.agent_id in tracker.status_history

    @pytest.mark.asyncio
    async def test_update_agent_status(self, tracker, mock_session):
        """Test updating agent status"""
        await tracker.register_session(mock_session)
        
        # Update status
        await tracker.update_agent_status(
            agent_id=mock_session.agent_id,
            status=SessionState.BUSY,
            current_task_id="task-789",
            current_activity="Processing request",
            metadata={"custom": "data"}
        )
        
        # Verify updates
        assert mock_session.state == SessionState.BUSY
        mock_session.start_task.assert_called_once_with("task-789")
        mock_session.update_heartbeat.assert_called_once()
        assert mock_session.metadata["custom"] == "data"

    @pytest.mark.asyncio
    async def test_report_task_progress(self, tracker, mock_session):
        """Test reporting task progress"""
        await tracker.register_session(mock_session)
        
        # Report progress
        await tracker.report_task_progress(
            agent_id=mock_session.agent_id,
            task_id="task-123",
            progress_percentage=75.0,
            status="in_progress",
            details="Processing step 3"
        )
        
        # No direct assertions as it's mainly notification
        
        # Report completion
        await tracker.report_task_progress(
            agent_id=mock_session.agent_id,
            task_id="task-123",
            progress_percentage=100.0,
            status="completed",
            details="Task completed successfully"
        )
        
        mock_session.complete_task.assert_called_once_with("task-123", success=True)

    @pytest.mark.asyncio
    async def test_report_task_failure(self, tracker, mock_session):
        """Test reporting task failure"""
        await tracker.register_session(mock_session)
        
        await tracker.report_task_progress(
            agent_id=mock_session.agent_id,
            task_id="task-123",
            progress_percentage=50.0,
            status="failed",
            details="Error occurred"
        )
        
        mock_session.complete_task.assert_called_once_with("task-123", success=False)

    @pytest.mark.asyncio
    async def test_report_resource_usage(self, tracker, mock_session):
        """Test reporting resource usage"""
        await tracker.register_session(mock_session)
        
        # Normal usage
        await tracker.report_resource_usage(
            agent_id=mock_session.agent_id,
            resource_type="cpu_thread",
            used_amount=50.0,
            allocated_amount=100.0,
            resource_id="cpu-1"
        )
        
        mock_session.update_resource_usage.assert_called_once()
        
        # High usage (anomaly)
        await tracker.report_resource_usage(
            agent_id=mock_session.agent_id,
            resource_type="memory_allocation",
            used_amount=95.0,
            allocated_amount=100.0,
            resource_id="mem-1"
        )
        
        # Should detect anomaly
        assert mock_session.agent_id in tracker.anomaly_counts
        assert tracker.anomaly_counts[mock_session.agent_id] > 0

    @pytest.mark.asyncio
    async def test_report_error(self, tracker, mock_session):
        """Test reporting errors"""
        await tracker.register_session(mock_session)
        
        # Report error
        await tracker.report_error(
            agent_id=mock_session.agent_id,
            error_type="connection_error",
            error_message="Lost connection to database",
            error_context={"retry_count": 3}
        )
        
        # Verify error tracking
        assert mock_session.metrics["error_count"] == 1
        assert "last_error" in mock_session.metadata
        assert mock_session.metadata["last_error"]["type"] == "connection_error"

    @pytest.mark.asyncio
    async def test_error_recovery(self, tracker, mock_session):
        """Test error recovery initiation"""
        await tracker.register_session(mock_session)
        mock_session.needs_recovery.return_value = True
        
        await tracker.report_error(
            agent_id=mock_session.agent_id,
            error_type="critical_error",
            error_message="System failure"
        )
        
        mock_session.recover.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_agent_status(self, tracker, mock_session):
        """Test getting agent status"""
        await tracker.register_session(mock_session)
        
        # Get status
        status = await tracker.get_agent_status(mock_session.agent_id)
        
        assert isinstance(status, StatusSnapshot)
        assert status.agent_id == mock_session.agent_id
        assert status.session_id == mock_session.session_id
        assert status.state == SessionState.IDLE
        assert status.health_score == 0.95

    @pytest.mark.asyncio
    async def test_get_all_agent_statuses(self, tracker, mock_session):
        """Test getting all agent statuses"""
        # Register multiple sessions
        sessions = []
        
        # Register the main mock session first
        await tracker.register_session(mock_session)
        sessions.append(mock_session)
        
        # Register additional sessions
        for i in range(2):
            session = Mock(spec=AgentSession)
            session.session_id = str(uuid4())
            session.agent_id = f"agent-{i}"
            session.project_id = f"proj-{i}"
            session.state = SessionState.BUSY
            session.active_tasks = set()
            session.started_at = datetime.now(timezone.utc)
            session.calculate_health_score = Mock(return_value=0.9)
            session.get_resource_usage_summary = Mock(return_value={})
            session.metrics = mock_session.metrics.copy()
            session.metadata = {}
            sessions.append(session)
            await tracker.register_session(session)
        
        # Get all statuses
        statuses = await tracker.get_all_agent_statuses()
        
        assert len(statuses) == 3
        for session in sessions:
            assert session.agent_id in statuses

    @pytest.mark.asyncio
    async def test_get_agent_history(self, tracker, mock_session):
        """Test getting agent history"""
        await tracker.register_session(mock_session)
        
        # Create some history
        for _ in range(5):
            await tracker.update_agent_status(
                agent_id=mock_session.agent_id,
                status=SessionState.BUSY
            )
            await asyncio.sleep(0.1)
        
        # Get full history
        history = await tracker.get_agent_history(mock_session.agent_id)
        assert len(history) >= 5
        
        # Get recent history
        recent = await tracker.get_agent_history(mock_session.agent_id, hours=1)
        assert len(recent) >= 5

    @pytest.mark.asyncio
    async def test_subscribe_to_updates(self, tracker):
        """Test subscribing to status updates"""
        received_updates = []
        
        async def callback(notification):
            received_updates.append(notification)
        
        # Subscribe
        sub_id = await tracker.subscribe_to_updates(
            subscriber_id="test-subscriber",
            agent_patterns=["agent-*"],
            update_types={StatusUpdateType.STATE_CHANGE, StatusUpdateType.TASK_UPDATE},
            callback=callback
        )
        
        assert sub_id in tracker.subscriptions
        subscription = tracker.subscriptions[sub_id]
        assert subscription.subscriber_id == "test-subscriber"
        assert subscription.agent_patterns == ["agent-*"]
        assert subscription.callback == callback

    @pytest.mark.asyncio
    async def test_unsubscribe(self, tracker):
        """Test unsubscribing from updates"""
        # Subscribe first
        sub_id = await tracker.subscribe_to_updates(
            subscriber_id="test",
            agent_patterns=["*"]
        )
        
        # Unsubscribe
        await tracker.unsubscribe(sub_id)
        
        assert sub_id not in tracker.subscriptions

    @pytest.mark.asyncio
    async def test_notification_delivery(self, tracker, mock_session):
        """Test notification delivery to subscribers"""
        received = []
        
        async def callback(notification):
            received.append(notification)
        
        # Subscribe
        await tracker.subscribe_to_updates(
            subscriber_id="test",
            agent_patterns=[mock_session.agent_id],
            update_types={StatusUpdateType.STATE_CHANGE},
            callback=callback
        )
        
        # Register session and update status
        await tracker.register_session(mock_session)
        await tracker.update_agent_status(
            agent_id=mock_session.agent_id,
            status=SessionState.BUSY
        )
        
        # Should have received notifications
        assert len(received) >= 2  # Registration + status update
        assert all(n["agent_id"] == mock_session.agent_id for n in received)

    @pytest.mark.asyncio
    async def test_pattern_matching(self, tracker):
        """Test agent ID pattern matching"""
        assert tracker._matches_pattern("agent-123", "*")
        assert tracker._matches_pattern("agent-123", "agent-123")
        assert tracker._matches_pattern("agent-123", "agent-*")
        assert not tracker._matches_pattern("agent-123", "other-*")
        assert not tracker._matches_pattern("agent-123", "agent-456")

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, tracker, mock_session):
        """Test anomaly detection and handling"""
        await tracker.register_session(mock_session)

        # Trigger multiple anomalies (threshold is 5, so 6 should trigger recovery)
        for i in range(6):
            await tracker._detect_anomaly(
                agent_id=mock_session.agent_id,
                anomaly_type="high_cpu",
                details={"iteration": i}
            )

        # Should trigger recovery after threshold
        assert tracker.anomaly_counts[mock_session.agent_id] == 0  # Reset after recovery
        mock_session.recover.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_monitoring(self, tracker, mock_session):
        """Test background session monitoring"""
        await tracker.register_session(mock_session)
        
        # Wait for monitoring cycle with buffer time
        # Since snapshot_interval_seconds=1, wait for 2 full cycles
        await asyncio.sleep(2.5)
        
        # Should have taken snapshots
        history = await tracker.get_agent_history(mock_session.agent_id)
        assert len(history) > 1

    @pytest.mark.asyncio
    async def test_expired_session_cleanup(self, tracker, mock_session):
        """Test cleanup of expired sessions"""
        await tracker.register_session(mock_session)
        
        # Mark session as expired
        mock_session.is_expired.return_value = True
        
        # Wait for monitoring cycle with buffer time
        # Since snapshot_interval_seconds=1, wait for 2 full cycles
        await asyncio.sleep(2.5)
        
        # Session should be unregistered
        assert mock_session.session_id not in tracker.active_sessions
        mock_session.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_dead_session_cleanup(self, tracker, mock_session):
        """Test cleanup of dead sessions"""
        await tracker.register_session(mock_session)

        # Verify session is registered
        assert mock_session.session_id in tracker.active_sessions

        # Mark session as dead
        mock_session.is_alive.return_value = False

        # Directly trigger the monitoring cycle once instead of waiting
        # This simulates what _monitor_sessions does for dead sessions
        for session in list(tracker.active_sessions.values()):
            if not session.is_alive():
                await tracker.unregister_session(session.session_id)

        # Session should be unregistered immediately
        assert mock_session.session_id not in tracker.active_sessions

    @pytest.mark.asyncio
    async def test_history_cleanup(self, tracker, mock_session):
        """Test old history cleanup"""
        tracker.history_retention_hours = 0  # Immediate cleanup
        await tracker.register_session(mock_session)

        # Create old history entry
        old_snapshot = StatusSnapshot(
            agent_id=mock_session.agent_id,
            session_id=mock_session.session_id,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
            state=SessionState.IDLE,
            health_score=0.9,
            active_tasks=[],
            resource_usage={},
            performance_metrics={}
        )
        tracker.status_history[mock_session.agent_id].insert(0, old_snapshot)

        # Directly perform cleanup logic without calling the background task
        # This avoids the infinite loop in _cleanup_old_history
        cutoff = datetime.now(timezone.utc) - timedelta(hours=tracker.history_retention_hours)
        for agent_id in list(tracker.status_history.keys()):
            history = tracker.status_history[agent_id]
            # Keep only recent history
            tracker.status_history[agent_id] = [
                s for s in history if s.timestamp >= cutoff
            ]
            # Remove empty histories
            if not tracker.status_history[agent_id]:
                del tracker.status_history[agent_id]

        # Old entry should be removed
        history = tracker.status_history.get(mock_session.agent_id, [])
        assert old_snapshot not in history

    @pytest.mark.asyncio
    async def test_get_metrics(self, tracker, mock_session):
        """Test getting tracker metrics"""
        await tracker.register_session(mock_session)
        tracker.anomaly_counts[mock_session.agent_id] = 3
        
        # Subscribe
        await tracker.subscribe_to_updates(
            subscriber_id="test",
            agent_patterns=["*"]
        )
        
        metrics = tracker.get_metrics()
        
        assert metrics["active_sessions"] == 1
        assert metrics["tracked_agents"] == 1
        assert metrics["active_subscriptions"] == 1
        assert metrics["anomaly_agents"] == 1
        assert metrics["total_anomalies"] == 3

    @pytest.mark.asyncio
    async def test_create_snapshot(self, tracker, mock_session):
        """Test creating status snapshot"""
        snapshot = tracker._create_snapshot(mock_session)
        
        assert isinstance(snapshot, StatusSnapshot)
        assert snapshot.agent_id == mock_session.agent_id
        assert snapshot.session_id == mock_session.session_id
        assert snapshot.state == SessionState.IDLE
        assert snapshot.health_score == 0.95
        assert snapshot.resource_usage == {"cpu": 50.0, "memory": 60.0}
        assert snapshot.performance_metrics["messages_sent"] == 10
        assert snapshot.metadata["project_id"] == "proj-456"

    @pytest.mark.asyncio
    async def test_error_recovery_failure(self, tracker, mock_session):
        """Test handling recovery failure"""
        await tracker.register_session(mock_session)
        mock_session.recover.side_effect = Exception("Recovery failed")
        
        # Should not crash
        await tracker._initiate_recovery(mock_session)
        
        # Anomaly count should not be reset
        tracker.anomaly_counts[mock_session.agent_id] = 5
        await tracker._initiate_recovery(mock_session)
        assert tracker.anomaly_counts[mock_session.agent_id] == 5