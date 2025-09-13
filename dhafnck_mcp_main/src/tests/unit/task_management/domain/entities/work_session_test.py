"""
Unit tests for WorkSession domain entity.
Tests all methods, state transitions, edge cases, and business rules.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from fastmcp.task_management.domain.entities.work_session import (
    WorkSession,
    SessionStatus
)


class TestWorkSessionEntity:
    """Test suite for WorkSession domain entity"""
    
    @pytest.fixture
    def valid_session_data(self):
        """Provide valid test data for WorkSession creation"""
        return {
            'id': 'agent1_task1_1234567890',
            'agent_id': 'agent1',
            'task_id': 'task1',
            'git_branch_name': 'feature/test-branch',
            'started_at': datetime.now(timezone.utc)
        }
    
    @pytest.fixture
    def work_session(self, valid_session_data):
        """Create a WorkSession instance for testing"""
        return WorkSession(**valid_session_data)
    
    def test_create_work_session_with_required_fields_success(self, valid_session_data):
        """Test WorkSession creation with only required fields"""
        session = WorkSession(**valid_session_data)
        
        assert session.id == valid_session_data['id']
        assert session.agent_id == valid_session_data['agent_id']
        assert session.task_id == valid_session_data['task_id']
        assert session.git_branch_name == valid_session_data['git_branch_name']
        assert session.started_at == valid_session_data['started_at']
        assert session.status == SessionStatus.ACTIVE
        assert session.ended_at is None
        assert session.paused_at is None
        assert session.total_paused_duration == timedelta(0)
        assert session.session_notes == ""
        assert session.progress_updates == []
        assert session.resources_locked == []
        assert session.max_duration is None
        assert session.auto_save_interval == 300
    
    def test_create_work_session_with_optional_fields_success(self, valid_session_data):
        """Test WorkSession creation with optional fields"""
        max_duration = timedelta(hours=8)
        session_notes = "Initial notes"
        auto_save_interval = 600
        
        session = WorkSession(
            **valid_session_data,
            max_duration=max_duration,
            session_notes=session_notes,
            auto_save_interval=auto_save_interval
        )
        
        assert session.max_duration == max_duration
        assert session.session_notes == session_notes
        assert session.auto_save_interval == auto_save_interval
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_pause_session_from_active_state_success(self, mock_datetime, work_session):
        """Test successfully pausing an active session"""
        mock_now = datetime(2023, 1, 1, 10, 30, 0)
        mock_datetime.now.return_value = mock_now
        
        reason = "Taking a break"
        work_session.pause_session(reason)
        
        assert work_session.status == SessionStatus.PAUSED
        assert work_session.paused_at == mock_now
        assert work_session.last_activity == mock_now
        assert len(work_session.progress_updates) == 1
        assert work_session.progress_updates[0]['type'] == 'session_paused'
        assert reason in work_session.progress_updates[0]['message']
    
    def test_pause_session_from_non_active_state_raises_error(self, work_session):
        """Test pausing session from non-active state raises ValueError"""
        work_session.status = SessionStatus.COMPLETED
        
        with pytest.raises(ValueError, match="Cannot pause session in completed state"):
            work_session.pause_session("reason")
    
    def test_pause_session_without_reason_success(self, work_session):
        """Test pausing session without providing reason"""
        work_session.pause_session()
        
        assert work_session.status == SessionStatus.PAUSED
        # Should not have reason-specific progress update
        assert all('reason' not in update['message'] for update in work_session.progress_updates)
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_resume_session_from_paused_state_success(self, mock_datetime, work_session):
        """Test successfully resuming a paused session"""
        # First pause the session
        pause_time = datetime(2023, 1, 1, 10, 0, 0)
        mock_datetime.now.return_value = pause_time
        work_session.pause_session("break")
        
        # Then resume it
        resume_time = datetime(2023, 1, 1, 10, 30, 0)
        mock_datetime.now.return_value = resume_time
        work_session.resume_session()
        
        assert work_session.status == SessionStatus.ACTIVE
        assert work_session.paused_at is None
        assert work_session.last_activity == resume_time
        assert work_session.total_paused_duration == timedelta(minutes=30)
        assert len(work_session.progress_updates) == 2
        assert work_session.progress_updates[-1]['type'] == 'session_resumed'
    
    def test_resume_session_from_non_paused_state_raises_error(self, work_session):
        """Test resuming session from non-paused state raises ValueError"""
        with pytest.raises(ValueError, match="Cannot resume session in active state"):
            work_session.resume_session()
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_complete_session_successfully_success(self, mock_datetime, work_session):
        """Test successfully completing a session"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        notes = "Task completed successfully"
        work_session.complete_session(success=True, notes=notes)
        
        assert work_session.status == SessionStatus.COMPLETED
        assert work_session.ended_at == mock_now
        assert work_session.last_activity == mock_now
        assert notes in work_session.session_notes
        assert len(work_session.progress_updates) == 1
        assert work_session.progress_updates[0]['type'] == 'session_completed'
        assert 'successful' in work_session.progress_updates[0]['message']
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_complete_session_unsuccessfully_success(self, mock_datetime, work_session):
        """Test completing a session unsuccessfully"""
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        work_session.complete_session(success=False)
        
        assert work_session.status == SessionStatus.COMPLETED
        assert work_session.ended_at == mock_now
        assert 'unsuccessful' in work_session.progress_updates[0]['message']
    
    def test_complete_session_from_paused_state_success(self, work_session):
        """Test completing session from paused state"""
        work_session.status = SessionStatus.PAUSED
        
        work_session.complete_session()
        
        assert work_session.status == SessionStatus.COMPLETED
    
    def test_complete_session_from_invalid_state_raises_error(self, work_session):
        """Test completing session from invalid state raises ValueError"""
        work_session.status = SessionStatus.CANCELLED
        
        with pytest.raises(ValueError, match="Cannot complete session in cancelled state"):
            work_session.complete_session()
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_cancel_session_with_reason_success(self, mock_datetime, work_session):
        """Test cancelling session with reason"""
        mock_now = datetime(2023, 1, 1, 11, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        reason = "Higher priority task assigned"
        work_session.cancel_session(reason)
        
        assert work_session.status == SessionStatus.CANCELLED
        assert work_session.ended_at == mock_now
        assert work_session.last_activity == mock_now
        assert reason in work_session.session_notes
        assert len(work_session.progress_updates) == 1
        assert work_session.progress_updates[0]['type'] == 'session_cancelled'
        assert reason in work_session.progress_updates[0]['message']
    
    def test_cancel_session_without_reason_success(self, work_session):
        """Test cancelling session without reason"""
        work_session.cancel_session()
        
        assert work_session.status == SessionStatus.CANCELLED
        assert work_session.ended_at is not None
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_timeout_session_success(self, mock_datetime, work_session):
        """Test timing out a session"""
        mock_now = datetime(2023, 1, 1, 18, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        work_session.timeout_session()
        
        assert work_session.status == SessionStatus.TIMEOUT
        assert work_session.ended_at == mock_now
        assert len(work_session.progress_updates) == 1
        assert work_session.progress_updates[0]['type'] == 'session_timeout'
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_add_progress_update_success(self, mock_datetime, work_session):
        """Test adding progress update"""
        mock_now = datetime(2023, 1, 1, 10, 15, 0)
        mock_datetime.now.return_value = mock_now
        
        update_type = "task_progress"
        message = "Completed UI component"
        metadata = {"component": "LoginForm", "lines_changed": 50}
        
        work_session.add_progress_update(update_type, message, metadata)
        
        assert len(work_session.progress_updates) == 1
        update = work_session.progress_updates[0]
        assert update['type'] == update_type
        assert update['message'] == message
        assert update['metadata'] == metadata
        assert update['timestamp'] == mock_now.isoformat()
        assert work_session.last_activity == mock_now
    
    def test_add_progress_update_without_metadata_success(self, work_session):
        """Test adding progress update without metadata"""
        work_session.add_progress_update("test", "message")
        
        update = work_session.progress_updates[0]
        assert update['metadata'] == {}
    
    def test_lock_resource_new_resource_success(self, work_session):
        """Test locking a new resource"""
        resource_id = "database_connection_1"
        work_session.lock_resource(resource_id)
        
        assert resource_id in work_session.resources_locked
        assert len(work_session.progress_updates) == 1
        assert work_session.progress_updates[0]['type'] == 'resource_locked'
        assert resource_id in work_session.progress_updates[0]['message']
    
    def test_lock_resource_already_locked_no_duplicate(self, work_session):
        """Test locking already locked resource doesn't create duplicate"""
        resource_id = "database_connection_1"
        work_session.lock_resource(resource_id)
        work_session.lock_resource(resource_id)  # Lock again
        
        assert work_session.resources_locked.count(resource_id) == 1
        assert len(work_session.progress_updates) == 1  # Only one update
    
    def test_unlock_resource_locked_resource_success(self, work_session):
        """Test unlocking a locked resource"""
        resource_id = "database_connection_1"
        work_session.lock_resource(resource_id)
        work_session.unlock_resource(resource_id)
        
        assert resource_id not in work_session.resources_locked
        assert len(work_session.progress_updates) == 2
        assert work_session.progress_updates[-1]['type'] == 'resource_unlocked'
    
    def test_unlock_resource_not_locked_no_effect(self, work_session):
        """Test unlocking resource that isn't locked has no effect"""
        resource_id = "database_connection_1"
        initial_updates = len(work_session.progress_updates)
        
        work_session.unlock_resource(resource_id)
        
        assert resource_id not in work_session.resources_locked
        assert len(work_session.progress_updates) == initial_updates  # No new updates
    
    def test_unlock_all_resources_success(self, work_session):
        """Test unlocking all resources"""
        resources = ["db1", "file1", "cache1"]
        for resource in resources:
            work_session.lock_resource(resource)
        
        work_session.unlock_all_resources()
        
        assert len(work_session.resources_locked) == 0
        # Should have lock + unlock update for each resource
        assert len(work_session.progress_updates) == len(resources) * 2
    
    def test_get_active_duration_active_session_success(self, work_session):
        """Test getting active duration for active session"""
        # Set started_at to a specific time for predictable calculation
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 11, 0, 0)
            duration = work_session.get_active_duration()
        
        assert duration == timedelta(hours=2)
    
    def test_get_active_duration_with_paused_time_success(self, work_session):
        """Test getting active duration excluding paused time"""
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        work_session.total_paused_duration = timedelta(minutes=30)
        
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 11, 0, 0)
            duration = work_session.get_active_duration()
        
        assert duration == timedelta(hours=1, minutes=30)
    
    def test_get_active_duration_completed_session_success(self, work_session):
        """Test getting active duration for completed session"""
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        work_session.ended_at = datetime(2023, 1, 1, 12, 0, 0)
        work_session.status = SessionStatus.COMPLETED
        
        duration = work_session.get_active_duration()
        
        assert duration == timedelta(hours=3)
    
    def test_get_total_duration_active_session_success(self, work_session):
        """Test getting total duration for active session"""
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 13, 0, 0)
            duration = work_session.get_total_duration()
        
        assert duration == timedelta(hours=4)
    
    def test_get_total_duration_completed_session_success(self, work_session):
        """Test getting total duration for completed session"""
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        work_session.ended_at = datetime(2023, 1, 1, 14, 0, 0)
        work_session.status = SessionStatus.COMPLETED
        
        duration = work_session.get_total_duration()
        
        assert duration == timedelta(hours=5)
    
    def test_is_active_true_for_active_session(self, work_session):
        """Test is_active returns True for active session"""
        assert work_session.is_active() is True
    
    def test_is_active_false_for_non_active_session(self, work_session):
        """Test is_active returns False for non-active session"""
        work_session.status = SessionStatus.PAUSED
        assert work_session.is_active() is False
    
    def test_is_timeout_due_no_max_duration_returns_false(self, work_session):
        """Test is_timeout_due returns False when no max_duration set"""
        assert work_session.is_timeout_due() is False
    
    def test_is_timeout_due_within_limit_returns_false(self, work_session):
        """Test is_timeout_due returns False when within time limit"""
        work_session.max_duration = timedelta(hours=8)
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 15, 0, 0)  # 6 hours
            assert work_session.is_timeout_due() is False
    
    def test_is_timeout_due_exceeded_limit_returns_true(self, work_session):
        """Test is_timeout_due returns True when time limit exceeded"""
        work_session.max_duration = timedelta(hours=4)
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 15, 0, 0)  # 6 hours
            assert work_session.is_timeout_due() is True
    
    def test_get_session_summary_complete_data(self, work_session):
        """Test getting complete session summary"""
        # Setup session with some data
        work_session.add_progress_update("test", "Test update")
        work_session.lock_resource("resource1")
        work_session.session_notes = "Test notes"
        work_session.max_duration = timedelta(hours=8)
        
        summary = work_session.get_session_summary()
        
        assert summary['session_id'] == work_session.id
        assert summary['agent_id'] == work_session.agent_id
        assert summary['task_id'] == work_session.task_id
        assert summary['git_branch_name'] == work_session.git_branch_name
        assert summary['status'] == work_session.status.value
        
        # Check timing information
        timing = summary['timing']
        assert 'started_at' in timing
        assert 'active_duration' in timing
        assert 'total_duration' in timing
        
        # Check progress information
        progress = summary['progress']
        assert progress['total_updates'] == 2  # test update + resource lock
        assert progress['session_notes'] == "Test notes"
        
        # Check resources information
        resources = summary['resources']
        assert resources['locked_resources'] == ['resource1']
        assert resources['total_locked'] == 1
        
        # Check configuration
        config = summary['configuration']
        assert 'max_duration' in config
        assert config['auto_save_interval'] == 300
    
    def test_get_progress_timeline_chronological_order(self, work_session):
        """Test getting progress timeline in chronological order"""
        # Add updates with different timestamps
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            # First update
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 0, 0)
            work_session.add_progress_update("first", "First update")
            
            # Second update
            mock_datetime.now.return_value = datetime(2023, 1, 1, 9, 0, 0)  # Earlier time
            work_session.add_progress_update("second", "Second update")
            
            # Third update
            mock_datetime.now.return_value = datetime(2023, 1, 1, 11, 0, 0)  # Later time
            work_session.add_progress_update("third", "Third update")
        
        timeline = work_session.get_progress_timeline()
        
        assert len(timeline) == 3
        assert timeline[0]['type'] == 'second'  # Earliest timestamp
        assert timeline[1]['type'] == 'first'   # Middle timestamp
        assert timeline[2]['type'] == 'third'   # Latest timestamp
    
    def test_extend_session_existing_max_duration_success(self, work_session):
        """Test extending session with existing max duration"""
        initial_duration = timedelta(hours=4)
        extension = timedelta(hours=2)
        work_session.max_duration = initial_duration
        
        work_session.extend_session(extension)
        
        assert work_session.max_duration == timedelta(hours=6)
        assert len(work_session.progress_updates) == 1
        assert work_session.progress_updates[0]['type'] == 'session_extended'
        assert str(extension) in work_session.progress_updates[0]['message']
    
    def test_extend_session_no_existing_max_duration_success(self, work_session):
        """Test extending session without existing max duration"""
        extension = timedelta(hours=3)
        work_session.extend_session(extension)
        
        assert work_session.max_duration == extension
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_update_activity_success(self, mock_datetime, work_session):
        """Test updating last activity timestamp"""
        mock_now = datetime(2023, 1, 1, 15, 30, 0)
        mock_datetime.now.return_value = mock_now
        
        work_session.update_activity()
        
        assert work_session.last_activity == mock_now
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_create_session_factory_method_success(self, mock_datetime):
        """Test factory method for creating work session"""
        mock_now = datetime(2023, 1, 1, 9, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        agent_id = "agent123"
        task_id = "task456"
        git_branch_name = "feature/new-feature"
        max_duration_hours = 6.5
        
        session = WorkSession.create_session(
            agent_id=agent_id,
            task_id=task_id,
            git_branch_name=git_branch_name,
            max_duration_hours=max_duration_hours
        )
        
        assert session.agent_id == agent_id
        assert session.task_id == task_id
        assert session.git_branch_name == git_branch_name
        assert session.started_at == mock_now
        assert session.max_duration == timedelta(hours=6.5)
        assert session.status == SessionStatus.ACTIVE
        assert f"{agent_id}_{task_id}_" in session.id
        assert len(session.progress_updates) == 1
        assert session.progress_updates[0]['type'] == 'session_started'
    
    @patch('fastmcp.task_management.domain.entities.work_session.datetime')
    def test_create_session_without_max_duration_success(self, mock_datetime):
        """Test factory method without max duration"""
        mock_now = datetime(2023, 1, 1, 9, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        session = WorkSession.create_session(
            agent_id="agent1",
            task_id="task1",
            git_branch_name="main"
        )
        
        assert session.max_duration is None
    
    def test_session_status_enum_values(self):
        """Test SessionStatus enum values"""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.PAUSED.value == "paused"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.CANCELLED.value == "cancelled"
        assert SessionStatus.TIMEOUT.value == "timeout"


class TestWorkSessionBusinessRules:
    """Test suite for WorkSession business rules and constraints"""
    
    @pytest.fixture
    def work_session(self):
        """Create a WorkSession for business rule testing"""
        return WorkSession(
            id='test_session',
            agent_id='agent1',
            task_id='task1',
            git_branch_name='main',
            started_at=datetime.now(timezone.utc)
        )
    
    def test_session_state_transitions_valid(self, work_session):
        """Test valid state transitions"""
        # ACTIVE -> PAUSED
        work_session.pause_session()
        assert work_session.status == SessionStatus.PAUSED
        
        # PAUSED -> ACTIVE
        work_session.resume_session()
        assert work_session.status == SessionStatus.ACTIVE
        
        # ACTIVE -> COMPLETED
        work_session.complete_session()
        assert work_session.status == SessionStatus.COMPLETED
    
    def test_session_state_transitions_invalid(self, work_session):
        """Test invalid state transitions raise errors"""
        work_session.complete_session()  # Move to COMPLETED
        
        # Cannot pause completed session
        with pytest.raises(ValueError):
            work_session.pause_session()
        
        # Cannot resume completed session
        with pytest.raises(ValueError):
            work_session.resume_session()
        
        # Cannot complete completed session
        with pytest.raises(ValueError):
            work_session.complete_session()
    
    def test_resource_locking_prevents_duplicates(self, work_session):
        """Test resource locking business rule prevents duplicates"""
        resource_id = "shared_resource"
        
        work_session.lock_resource(resource_id)
        initial_count = len(work_session.resources_locked)
        
        work_session.lock_resource(resource_id)  # Try to lock again
        
        assert len(work_session.resources_locked) == initial_count
        assert work_session.resources_locked.count(resource_id) == 1
    
    def test_paused_duration_accumulates_correctly(self, work_session):
        """Test that paused duration accumulates correctly across multiple pauses"""
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            # First pause period: 30 minutes
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 0, 0)
            work_session.pause_session()
            
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 30, 0)
            work_session.resume_session()
            
            # Second pause period: 15 minutes
            mock_datetime.now.return_value = datetime(2023, 1, 1, 11, 0, 0)
            work_session.pause_session()
            
            mock_datetime.now.return_value = datetime(2023, 1, 1, 11, 15, 0)
            work_session.resume_session()
        
        assert work_session.total_paused_duration == timedelta(minutes=45)
    
    def test_timeout_logic_respects_max_duration(self, work_session):
        """Test timeout logic correctly respects max duration setting"""
        work_session.max_duration = timedelta(hours=2)
        work_session.started_at = datetime(2023, 1, 1, 9, 0, 0)
        
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            # Within time limit
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 30, 0)
            assert not work_session.is_timeout_due()
            
            # Exceeded time limit
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            assert work_session.is_timeout_due()
    
    def test_activity_tracking_updates_on_operations(self, work_session):
        """Test that last_activity updates on various operations"""
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            original_time = work_session.last_activity
            
            # Progress update should update activity
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 0, 0)
            work_session.add_progress_update("test", "message")
            assert work_session.last_activity != original_time
            
            # Pause should update activity
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 15, 0)
            work_session.pause_session()
            assert work_session.last_activity == datetime(2023, 1, 1, 10, 15, 0)
    
    def test_progress_updates_maintain_chronological_integrity(self, work_session):
        """Test that progress updates maintain chronological integrity"""
        with patch('fastmcp.task_management.domain.entities.work_session.datetime') as mock_datetime:
            timestamps = []
            
            for i in range(5):
                timestamp = datetime(2023, 1, 1, 10, i * 5, 0)
                mock_datetime.now.return_value = timestamp
                work_session.add_progress_update(f"update_{i}", f"Message {i}")
                timestamps.append(timestamp.isoformat())
            
            timeline = work_session.get_progress_timeline()
            timeline_timestamps = [update['timestamp'] for update in timeline]
            
            assert timeline_timestamps == sorted(timestamps)


class TestWorkSessionEdgeCases:
    """Test suite for WorkSession edge cases and error conditions"""
    
    def test_empty_string_parameters_handled_correctly(self):
        """Test handling of empty string parameters"""
        session = WorkSession(
            id='',
            agent_id='',
            task_id='',
            git_branch_name='',
            started_at=datetime.now(timezone.utc)
        )
        
        assert session.id == ''
        assert session.agent_id == ''
        assert session.task_id == ''
        assert session.git_branch_name == ''
    
    def test_extreme_duration_values(self):
        """Test handling of extreme duration values"""
        session = WorkSession(
            id='test',
            agent_id='agent1',
            task_id='task1',
            git_branch_name='main',
            started_at=datetime.now(timezone.utc),
            max_duration=timedelta(days=365)  # Very long duration
        )
        
        assert session.max_duration == timedelta(days=365)
    
    def test_session_notes_concatenation_behavior(self):
        """Test session notes concatenation behavior"""
        session = WorkSession(
            id='test',
            agent_id='agent1',
            task_id='task1',
            git_branch_name='main',
            started_at=datetime.now(timezone.utc),
            session_notes="Initial notes"
        )
        
        session.complete_session(notes="Completion notes")
        session.cancel_session("Cancel reason")
        
        notes = session.session_notes
        assert "Initial notes" in notes
        assert "Completion notes" in notes
        assert "Cancel reason" in notes
    
    def test_large_number_of_progress_updates(self):
        """Test handling large number of progress updates"""
        session = WorkSession(
            id='test',
            agent_id='agent1',
            task_id='task1',
            git_branch_name='main',
            started_at=datetime.now(timezone.utc)
        )
        
        # Add many progress updates
        for i in range(1000):
            session.add_progress_update(f"type_{i}", f"Message {i}")
        
        assert len(session.progress_updates) == 1000
        timeline = session.get_progress_timeline()
        assert len(timeline) == 1000
    
    def test_large_number_of_resources(self):
        """Test handling large number of locked resources"""
        session = WorkSession(
            id='test',
            agent_id='agent1',
            task_id='task1',
            git_branch_name='main',
            started_at=datetime.now(timezone.utc)
        )
        
        # Lock many resources
        for i in range(100):
            session.lock_resource(f"resource_{i}")
        
        assert len(session.resources_locked) == 100
        
        # Unlock all
        session.unlock_all_resources()
        assert len(session.resources_locked) == 0
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters"""
        session = WorkSession(
            id='test_🔧',
            agent_id='agent_μ',
            task_id='task_∑',
            git_branch_name='feature/测试-branch',
            started_at=datetime.now(timezone.utc)
        )
        
        session.add_progress_update("test_💻", "Message with émojis and ñ characters")
        session.session_notes = "Notes with üñíçødé characters"
        
        summary = session.get_session_summary()
        assert '🔧' in summary['session_id']
        assert 'μ' in summary['agent_id']
        assert '∑' in summary['task_id']
        assert '测试' in summary['git_branch_name']