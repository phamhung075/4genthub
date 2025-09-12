"""Test agent session entity"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import uuid

from fastmcp.task_management.domain.entities.agent_session import (
    AgentSession,
    SessionState,
    ResourceType,
    ResourceUsage,
    CommunicationChannel
)
from fastmcp.task_management.domain.value_objects.coordination import CoordinationMessage
from fastmcp.task_management.domain.exceptions.base import DomainException


class TestResourceUsage:
    """Test resource usage tracking"""

    def test_usage_percentage(self):
        """Test calculating usage percentage"""
        resource = ResourceUsage(
            resource_type=ResourceType.CPU_THREAD,
            allocated_amount=100.0,
            used_amount=75.0,
            allocation_time=datetime.utcnow()
        )
        
        assert resource.usage_percentage == 75.0
        
        # Test zero allocation
        resource.allocated_amount = 0
        assert resource.usage_percentage == 0.0

    def test_is_overutilized(self):
        """Test checking if resource is overutilized"""
        resource = ResourceUsage(
            resource_type=ResourceType.MEMORY_ALLOCATION,
            allocated_amount=1000.0,
            used_amount=950.0,
            allocation_time=datetime.utcnow()
        )
        
        assert resource.is_overutilized()  # Default 90% threshold
        assert resource.is_overutilized(threshold=90.0)
        assert not resource.is_overutilized(threshold=96.0)


class TestAgentSession:
    """Test agent session entity"""

    @pytest.fixture
    def session(self):
        """Create test session"""
        return AgentSession(
            agent_id="agent-123",
            user_id="user-456",
            project_id="proj-789",
            heartbeat_interval=30,
            max_idle_time=300,
            max_session_duration=3600
        )

    def test_session_initialization(self, session):
        """Test session initialization"""
        assert session.agent_id == "agent-123"
        assert session.user_id == "user-456"
        assert session.project_id == "proj-789"
        assert session.state == SessionState.INITIALIZING
        assert session.heartbeat_interval == 30
        assert session.max_idle_time == 300
        assert session.max_session_duration == 3600
        assert len(session.active_tasks) == 0
        assert len(session.resources) == 0
        assert len(session.channels) == 0

    def test_activate_session(self, session):
        """Test session activation"""
        session.activate()
        assert session.state == SessionState.ACTIVE
        assert session.last_heartbeat is not None

    def test_activate_session_invalid_state(self, session):
        """Test activation from invalid state"""
        session.state = SessionState.TERMINATED
        
        with pytest.raises(DomainException) as exc:
            session.activate()
        assert "Cannot activate session" in str(exc.value)

    def test_update_heartbeat(self, session):
        """Test updating heartbeat"""
        old_heartbeat = session.last_heartbeat
        session.state = SessionState.IDLE
        
        session.update_heartbeat()
        
        assert session.last_heartbeat > old_heartbeat
        assert session.state == SessionState.ACTIVE

    def test_is_alive(self, session):
        """Test checking if session is alive"""
        session.activate()
        assert session.is_alive()
        
        # Simulate old heartbeat
        session.last_heartbeat = datetime.utcnow() - timedelta(seconds=70)
        assert not session.is_alive()
        
        # Disconnected state
        session.last_heartbeat = datetime.utcnow()
        session.state = SessionState.DISCONNECTED
        assert not session.is_alive()

    def test_is_expired(self, session):
        """Test checking if session is expired"""
        assert not session.is_expired()
        
        # Simulate old session
        session.started_at = datetime.utcnow() - timedelta(seconds=3700)
        assert session.is_expired()
        
        # No max duration
        session.max_session_duration = None
        assert not session.is_expired()

    def test_is_idle(self, session):
        """Test checking if session is idle"""
        # Active tasks - not idle
        session.active_tasks.add("task-1")
        assert not session.is_idle()
        
        # No tasks, recent heartbeat - not idle
        session.active_tasks.clear()
        session.last_heartbeat = datetime.utcnow()
        assert not session.is_idle()
        
        # No tasks, old heartbeat - idle
        session.last_heartbeat = datetime.utcnow() - timedelta(seconds=400)
        assert session.is_idle()

    def test_start_task(self, session):
        """Test starting a task"""
        session.activate()
        session.start_task("task-123")
        
        assert "task-123" in session.active_tasks
        assert session.state == SessionState.BUSY

    def test_complete_task_success(self, session):
        """Test completing task successfully"""
        session.activate()
        session.start_task("task-123")
        
        session.complete_task("task-123", success=True)
        
        assert "task-123" not in session.active_tasks
        assert "task-123" in session.completed_tasks
        assert session.metrics["tasks_completed"] == 1
        assert session.state == SessionState.IDLE

    def test_complete_task_failure(self, session):
        """Test completing task with failure"""
        session.activate()
        session.start_task("task-123")
        
        session.complete_task("task-123", success=False)
        
        assert "task-123" not in session.active_tasks
        assert "task-123" in session.failed_tasks
        assert session.metrics["tasks_failed"] == 1

    def test_multiple_active_tasks(self, session):
        """Test handling multiple active tasks"""
        session.activate()
        session.start_task("task-1")
        session.start_task("task-2")
        
        # Complete one task - should stay busy
        session.complete_task("task-1")
        assert session.state == SessionState.BUSY
        
        # Complete all tasks - should go idle
        session.complete_task("task-2")
        assert session.state == SessionState.IDLE

    def test_allocate_resource(self, session):
        """Test resource allocation"""
        resource = session.allocate_resource(
            resource_type=ResourceType.MEMORY_ALLOCATION,
            amount=1024.0,
            resource_id="mem-123"
        )
        
        assert resource.resource_type == ResourceType.MEMORY_ALLOCATION
        assert resource.allocated_amount == 1024.0
        assert resource.used_amount == 0
        assert resource.resource_id == "mem-123"
        
        key = "memory_allocation_mem-123"
        assert key in session.resources
        assert "mem-123" in session.resource_locks

    def test_update_resource_usage(self, session):
        """Test updating resource usage"""
        session.allocate_resource(
            resource_type=ResourceType.CPU_THREAD,
            amount=4.0,
            resource_id="cpu-1"
        )
        
        session.update_resource_usage(
            resource_type=ResourceType.CPU_THREAD,
            used_amount=3.0,
            resource_id="cpu-1"
        )
        
        key = "cpu_thread_cpu-1"
        assert session.resources[key].used_amount == 3.0

    def test_release_resource(self, session):
        """Test releasing resource"""
        session.allocate_resource(
            resource_type=ResourceType.FILE_LOCK,
            amount=1.0,
            resource_id="file-123"
        )
        
        session.release_resource(
            resource_type=ResourceType.FILE_LOCK,
            resource_id="file-123"
        )
        
        key = "file_lock_file-123"
        assert key not in session.resources
        assert "file-123" not in session.resource_locks

    def test_get_resource_usage_summary(self, session):
        """Test getting resource usage summary"""
        # Allocate multiple resources
        session.allocate_resource(ResourceType.CPU_THREAD, 4.0)
        session.update_resource_usage(ResourceType.CPU_THREAD, 3.0)
        
        session.allocate_resource(ResourceType.MEMORY_ALLOCATION, 1000.0)
        session.update_resource_usage(ResourceType.MEMORY_ALLOCATION, 800.0)
        
        summary = session.get_resource_usage_summary()
        
        assert ResourceType.CPU_THREAD.value in summary
        assert summary[ResourceType.CPU_THREAD.value] == 75.0  # 3/4 * 100
        assert summary[ResourceType.MEMORY_ALLOCATION.value] == 80.0  # 800/1000 * 100

    def test_open_channel(self, session):
        """Test opening communication channel"""
        channel = session.open_channel(
            channel_id="ch-123",
            channel_type="websocket",
            participants=["agent-123", "agent-456"]
        )
        
        assert channel.channel_id == "ch-123"
        assert channel.channel_type == "websocket"
        assert channel.participants == ["agent-123", "agent-456"]
        assert channel.is_active
        assert "ch-123" in session.channels

    def test_close_channel(self, session):
        """Test closing communication channel"""
        session.open_channel("ch-123", "websocket", ["agent-123"])
        
        session.close_channel("ch-123")
        
        assert not session.channels["ch-123"].is_active

    def test_add_message(self, session):
        """Test adding messages"""
        message = Mock(spec=CoordinationMessage)
        
        # Outgoing message
        session.add_message(message, is_outgoing=True)
        assert session.metrics["messages_sent"] == 1
        assert len(session.message_history) == 1
        
        # Incoming message
        session.add_message(message, is_outgoing=False)
        assert session.metrics["messages_received"] == 1
        assert len(session.message_history) == 2

    def test_message_history_limit(self, session):
        """Test message history size limit"""
        # Add many messages
        for i in range(1100):
            message = Mock(spec=CoordinationMessage)
            session.add_message(message)
        
        # Should keep only last 500
        assert len(session.message_history) == 500

    def test_get_active_channels(self, session):
        """Test getting active channels"""
        session.open_channel("ch-1", "websocket", ["agent-1"])
        session.open_channel("ch-2", "direct", ["agent-2"])
        session.close_channel("ch-1")
        
        active = session.get_active_channels()
        assert len(active) == 1
        assert active[0].channel_id == "ch-2"

    def test_calculate_health_score_perfect(self, session):
        """Test calculating perfect health score"""
        session.metrics["tasks_completed"] = 10
        session.metrics["tasks_failed"] = 0
        session.metrics["error_count"] = 0
        
        score = session.calculate_health_score()
        assert score == 100.0

    def test_calculate_health_score_with_issues(self, session):
        """Test calculating health score with issues"""
        # High resource usage
        session.allocate_resource(ResourceType.CPU_THREAD, 4.0)
        session.update_resource_usage(ResourceType.CPU_THREAD, 3.8)  # 95% usage
        
        # Some errors
        session.metrics["tasks_completed"] = 8
        session.metrics["tasks_failed"] = 2
        session.metrics["error_count"] = 5
        session.metrics["messages_sent"] = 10
        
        score = session.calculate_health_score()
        assert score < 100.0
        assert score > 0.0

    def test_needs_recovery(self, session):
        """Test checking if recovery is needed"""
        # Healthy session
        assert not session.needs_recovery()
        
        # Low health score
        session.metrics["error_count"] = 50
        session.metrics["messages_sent"] = 100
        assert session.needs_recovery()
        
        # High error count
        session.metrics["error_count"] = 11
        assert session.needs_recovery()

    def test_recover(self, session):
        """Test session recovery"""
        # Set up problematic state
        session.metrics["error_count"] = 15
        session.state = SessionState.DISCONNECTED
        session.pending_messages = [Mock() for _ in range(5)]
        
        # Allocate overutilized resource
        session.allocate_resource(ResourceType.MEMORY_ALLOCATION, 1000.0)
        session.update_resource_usage(ResourceType.MEMORY_ALLOCATION, 950.0)
        
        # Recover
        session.recover()
        
        assert session.metrics["recovery_count"] == 1
        assert session.metrics["error_count"] == 0
        assert session.state == SessionState.ACTIVE
        assert len(session.pending_messages) == 0
        
        # Resource usage should be reduced
        resource = session.resources["memory_allocation_default"]
        assert resource.used_amount == 500.0  # 50% of allocated

    def test_terminate(self, session):
        """Test session termination"""
        # Set up active session
        session.activate()
        session.start_task("task-1")
        session.allocate_resource(ResourceType.FILE_LOCK, 1.0, "file-1")
        session.open_channel("ch-1", "websocket", ["agent-1"])
        
        # Terminate
        session.terminate("User requested")
        
        assert session.state == SessionState.TERMINATED
        assert len(session.channels) == 1  # Still there but inactive
        assert not session.channels["ch-1"].is_active
        assert len(session.resources) == 0
        assert len(session.resource_locks) == 0
        assert session.metadata["termination_reason"] == "User requested"
        assert "terminated_at" in session.metadata

    def test_to_dict(self, session):
        """Test converting session to dictionary"""
        session.activate()
        session.start_task("task-1")
        session.complete_task("task-1")
        
        data = session.to_dict()
        
        assert data["session_id"] == session.session_id
        assert data["agent_id"] == "agent-123"
        assert data["user_id"] == "user-456"
        assert data["project_id"] == "proj-789"
        assert data["state"] == "active"
        assert data["completed_tasks_count"] == 1
        assert data["failed_tasks_count"] == 0
        assert data["health_score"] == 100.0
        assert data["is_alive"] is True
        assert data["is_expired"] is False

    def test_session_with_no_max_duration(self):
        """Test session without maximum duration"""
        session = AgentSession(
            agent_id="agent-1",
            max_session_duration=None
        )
        
        # Should never expire
        session.started_at = datetime.utcnow() - timedelta(days=7)
        assert not session.is_expired()

    def test_default_resource_allocation(self, session):
        """Test allocating resource without ID"""
        resource = session.allocate_resource(
            resource_type=ResourceType.API_QUOTA,
            amount=100.0
        )
        
        assert resource.resource_id is None
        key = "api_quota_default"
        assert key in session.resources
        assert len(session.resource_locks) == 0  # No lock for default resource