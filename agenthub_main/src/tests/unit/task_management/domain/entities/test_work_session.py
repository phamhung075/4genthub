"""Unit tests for WorkSession entity."""

import pytest
from datetime import datetime, timedelta, timezone
import time
from unittest.mock import patch

from fastmcp.task_management.domain.entities.work_session import (
    WorkSession, SessionStatus
)


class TestWorkSessionCreation:
    """Test WorkSession entity creation."""
    
    def test_create_work_session_minimal(self):
        """Test creating work session with minimal parameters."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="feature-branch",
            started_at=datetime.now(timezone.utc)
        )
        
        assert session.id == "session-1"
        assert session.agent_id == "agent-1"
        assert session.task_id == "task-1"
        assert session.git_branch_name == "feature-branch"
        assert session.status == SessionStatus.ACTIVE
        assert session.ended_at is None
        assert session.paused_at is None
        assert session.total_paused_duration == timedelta(0)
        assert session.session_notes == ""
        assert session.progress_updates == []
        assert session.resources_locked == []
        assert session.auto_save_interval == 300
    
    def test_create_work_session_with_configuration(self):
        """Test creating work session with custom configuration."""
        max_duration = timedelta(hours=2)
        session = WorkSession(
            id="session-2",
            agent_id="agent-2",
            task_id="task-2",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc),
            max_duration=max_duration,
            auto_save_interval=600,
            session_notes="Initial notes"
        )
        
        assert session.max_duration == max_duration
        assert session.auto_save_interval == 600
        assert session.session_notes == "Initial notes"
    
    def test_create_work_session_with_initial_resources(self):
        """Test creating work session with initial locked resources."""
        resources = ["file-1", "db-connection-1"]
        session = WorkSession(
            id="session-3",
            agent_id="agent-3",
            task_id="task-3",
            git_branch_name="dev",
            started_at=datetime.now(timezone.utc),
            resources_locked=resources
        )
        
        assert session.resources_locked == resources


class TestWorkSessionStatusTransitions:
    """Test WorkSession status transitions."""
    
    def test_pause_active_session(self):
        """Test pausing an active session."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.pause_session("Taking a break")
        
        assert session.status == SessionStatus.PAUSED
        assert session.paused_at is not None
        assert len(session.progress_updates) == 1
        assert session.progress_updates[0]["type"] == "session_paused"
        assert "Taking a break" in session.progress_updates[0]["message"]
    
    def test_pause_non_active_session_fails(self):
        """Test that pausing non-active session raises error."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        session.status = SessionStatus.COMPLETED
        
        with pytest.raises(ValueError, match="Cannot pause session in completed state"):
            session.pause_session()
    
    def test_resume_paused_session(self):
        """Test resuming a paused session."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        # Pause then resume
        session.pause_session("Taking a break")  # Add reason to create progress update
        paused_at = session.paused_at
        
        # Wait a bit to ensure pause duration
        time.sleep(0.1)
        
        session.resume_session()
        
        assert session.status == SessionStatus.ACTIVE
        assert session.paused_at is None
        assert session.total_paused_duration > timedelta(0)
        assert len(session.progress_updates) == 2
        assert session.progress_updates[0]["type"] == "session_paused"
        assert session.progress_updates[1]["type"] == "session_resumed"
    
    def test_resume_non_paused_session_fails(self):
        """Test that resuming non-paused session raises error."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="Cannot resume session in active state"):
            session.resume_session()
    
    def test_complete_session_successfully(self):
        """Test completing a session successfully."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.complete_session(success=True, notes="Task completed")
        
        assert session.status == SessionStatus.COMPLETED
        assert session.ended_at is not None
        assert "Task completed" in session.session_notes
        assert len(session.progress_updates) == 1
        assert "successful" in session.progress_updates[0]["message"]
    
    def test_complete_session_unsuccessfully(self):
        """Test completing a session unsuccessfully."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.complete_session(success=False, notes="Encountered error")
        
        assert session.status == SessionStatus.COMPLETED
        assert "unsuccessful" in session.progress_updates[0]["message"]
    
    def test_complete_paused_session(self):
        """Test completing a paused session."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.pause_session()
        session.complete_session()
        
        assert session.status == SessionStatus.COMPLETED
        assert session.ended_at is not None
    
    def test_complete_already_completed_session_fails(self):
        """Test that completing already completed session raises error."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        session.status = SessionStatus.COMPLETED
        
        with pytest.raises(ValueError, match="Cannot complete session in completed state"):
            session.complete_session()
    
    def test_cancel_session(self):
        """Test cancelling a session."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.cancel_session("User requested cancellation")
        
        assert session.status == SessionStatus.CANCELLED
        assert session.ended_at is not None
        assert "User requested cancellation" in session.session_notes
        assert len(session.progress_updates) == 1
        assert session.progress_updates[0]["type"] == "session_cancelled"
    
    def test_timeout_session(self):
        """Test timing out a session."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.timeout_session()
        
        assert session.status == SessionStatus.TIMEOUT
        assert session.ended_at is not None
        assert len(session.progress_updates) == 1
        assert session.progress_updates[0]["type"] == "session_timeout"


class TestWorkSessionProgressTracking:
    """Test WorkSession progress tracking."""
    
    def test_add_progress_update(self):
        """Test adding progress update."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.add_progress_update(
            update_type="code_written",
            message="Implemented user authentication",
            metadata={"lines_added": 150, "files_modified": 3}
        )
        
        assert len(session.progress_updates) == 1
        update = session.progress_updates[0]
        assert update["type"] == "code_written"
        assert update["message"] == "Implemented user authentication"
        assert update["metadata"]["lines_added"] == 150
        assert update["metadata"]["files_modified"] == 3
        assert "timestamp" in update
    
    def test_multiple_progress_updates(self):
        """Test adding multiple progress updates."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.add_progress_update("started", "Beginning work")
        session.add_progress_update("analysis", "Analyzed requirements")
        session.add_progress_update("implementation", "Started coding")
        
        assert len(session.progress_updates) == 3
        assert [u["type"] for u in session.progress_updates] == ["started", "analysis", "implementation"]
    
    def test_progress_update_updates_last_activity(self):
        """Test that progress updates update last activity timestamp."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )

        initial_activity = session.last_activity
        time.sleep(0.01)  # Small delay

        session.add_progress_update("test", "Test update")

        assert session.last_activity > initial_activity


class TestWorkSessionResourceManagement:
    """Test WorkSession resource management."""
    
    def test_lock_resource(self):
        """Test locking a resource."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.lock_resource("database-1")
        
        assert "database-1" in session.resources_locked
        assert len(session.progress_updates) == 1
        assert session.progress_updates[0]["type"] == "resource_locked"
    
    def test_lock_duplicate_resource(self):
        """Test locking already locked resource."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.lock_resource("file-1")
        session.lock_resource("file-1")  # Try to lock again
        
        assert session.resources_locked.count("file-1") == 1
        assert len(session.progress_updates) == 1  # Only one lock event
    
    def test_unlock_resource(self):
        """Test unlocking a resource."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.lock_resource("cache-1")
        session.unlock_resource("cache-1")
        
        assert "cache-1" not in session.resources_locked
        assert len(session.progress_updates) == 2
        assert session.progress_updates[1]["type"] == "resource_unlocked"
    
    def test_unlock_non_locked_resource(self):
        """Test unlocking resource that wasn't locked."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        session.unlock_resource("not-locked")
        
        assert len(session.progress_updates) == 0  # No unlock event
    
    def test_unlock_all_resources(self):
        """Test unlocking all resources."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        # Lock multiple resources
        session.lock_resource("db-1")
        session.lock_resource("file-1")
        session.lock_resource("api-1")
        
        session.unlock_all_resources()
        
        assert len(session.resources_locked) == 0
        assert len(session.progress_updates) == 6  # 3 locks + 3 unlocks


class TestWorkSessionDuration:
    """Test WorkSession duration calculations."""
    
    def test_get_active_duration_for_active_session(self):
        """Test getting active duration for active session."""
        started = datetime.now(timezone.utc) - timedelta(minutes=30)
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=started
        )
        
        duration = session.get_active_duration()
        
        # Should be approximately 30 minutes
        assert duration >= timedelta(minutes=29, seconds=50)
        assert duration <= timedelta(minutes=30, seconds=10)
    
    def test_get_active_duration_with_pauses(self):
        """Test getting active duration excluding pauses."""
        started = datetime.now(timezone.utc) - timedelta(hours=1)
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=started
        )
        
        # Add 15 minutes of pause time
        session.total_paused_duration = timedelta(minutes=15)
        
        duration = session.get_active_duration()
        
        # Should be approximately 45 minutes (60 - 15)
        assert duration >= timedelta(minutes=44, seconds=50)
        assert duration <= timedelta(minutes=45, seconds=10)
    
    def test_get_active_duration_for_completed_session(self):
        """Test getting active duration for completed session."""
        started = datetime.now(timezone.utc) - timedelta(hours=2)
        ended = started + timedelta(hours=1, minutes=30)
        
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=started
        )
        session.status = SessionStatus.COMPLETED
        session.ended_at = ended
        
        duration = session.get_active_duration()
        
        assert duration == timedelta(hours=1, minutes=30)
    
    def test_get_total_duration(self):
        """Test getting total duration including pauses."""
        started = datetime.now(timezone.utc) - timedelta(hours=2)
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=started
        )
        
        # Add pause time (doesn't affect total duration)
        session.total_paused_duration = timedelta(minutes=30)
        
        duration = session.get_total_duration()
        
        # Should be approximately 2 hours
        assert duration >= timedelta(hours=1, minutes=59, seconds=50)
        assert duration <= timedelta(hours=2, seconds=10)
    
    def test_get_total_duration_for_ended_session(self):
        """Test getting total duration for ended session."""
        started = datetime.now(timezone.utc) - timedelta(hours=3)
        ended = started + timedelta(hours=2)
        
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=started
        )
        session.status = SessionStatus.COMPLETED
        session.ended_at = ended
        
        duration = session.get_total_duration()
        
        assert duration == timedelta(hours=2)


class TestWorkSessionScenarios:
    """Test complex WorkSession scenarios."""
    
    def test_pause_resume_cycle(self):
        """Test multiple pause/resume cycles."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        # First pause/resume
        session.pause_session("Break 1")
        time.sleep(0.05)
        session.resume_session()
        pause1_duration = session.total_paused_duration
        
        # Second pause/resume
        session.pause_session("Break 2")
        time.sleep(0.05)
        session.resume_session()
        pause2_duration = session.total_paused_duration
        
        assert pause2_duration > pause1_duration
        assert len(session.progress_updates) == 4  # 2 pauses + 2 resumes
    
    def test_session_with_resources_and_completion(self):
        """Test session lifecycle with resource management."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc)
        )
        
        # Lock resources
        session.lock_resource("db-conn-1")
        session.lock_resource("file-handle-1")
        
        # Do some work
        session.add_progress_update("work", "Processing data")
        
        # Complete session (resources should remain locked for cleanup)
        session.complete_session(notes="Finished processing")
        
        assert session.status == SessionStatus.COMPLETED
        assert len(session.resources_locked) == 2  # Still locked
        assert len(session.progress_updates) >= 3
    
    def test_max_duration_check(self):
        """Test session with max duration configuration."""
        started = datetime.now(timezone.utc) - timedelta(hours=3)
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=started,
            max_duration=timedelta(hours=2)
        )
        
        # Check if session should timeout
        current_duration = session.get_total_duration()
        should_timeout = current_duration > session.max_duration
        
        assert should_timeout is True
        
        # Timeout the session
        session.timeout_session()
        assert session.status == SessionStatus.TIMEOUT
    
    def test_session_notes_accumulation(self):
        """Test that session notes accumulate properly."""
        session = WorkSession(
            id="session-1",
            agent_id="agent-1",
            task_id="task-1",
            git_branch_name="main",
            started_at=datetime.now(timezone.utc),
            session_notes="Initial setup"
        )
        
        # Add notes through various operations
        session.pause_session("Coffee break")
        session.resume_session()
        session.cancel_session("Emergency came up")
        
        assert "Initial setup" in session.session_notes
        assert "Emergency came up" in session.session_notes