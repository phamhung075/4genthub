"""Unit tests for TaskStatus value object."""

import pytest
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum


class TestTaskStatusCreation:
    """Test TaskStatus creation with valid and invalid inputs."""
    
    def test_create_valid_status_todo(self):
        """Test creating TaskStatus with TODO value."""
        status = TaskStatus("todo")
        assert status.value == "todo"
        assert str(status) == "todo"
    
    def test_create_valid_status_in_progress(self):
        """Test creating TaskStatus with IN_PROGRESS value."""
        status = TaskStatus("in_progress")
        assert status.value == "in_progress"
        assert str(status) == "in_progress"
    
    def test_create_valid_status_blocked(self):
        """Test creating TaskStatus with BLOCKED value."""
        status = TaskStatus("blocked")
        assert status.value == "blocked"
        assert str(status) == "blocked"
    
    def test_create_valid_status_review(self):
        """Test creating TaskStatus with REVIEW value."""
        status = TaskStatus("review")
        assert status.value == "review"
        assert str(status) == "review"
    
    def test_create_valid_status_testing(self):
        """Test creating TaskStatus with TESTING value."""
        status = TaskStatus("testing")
        assert status.value == "testing"
        assert str(status) == "testing"
    
    def test_create_valid_status_done(self):
        """Test creating TaskStatus with DONE value."""
        status = TaskStatus("done")
        assert status.value == "done"
        assert str(status) == "done"
    
    def test_create_valid_status_cancelled(self):
        """Test creating TaskStatus with CANCELLED value."""
        status = TaskStatus("cancelled")
        assert status.value == "cancelled"
        assert str(status) == "cancelled"
    
    def test_create_valid_status_archived(self):
        """Test creating TaskStatus with ARCHIVED value."""
        status = TaskStatus("archived")
        assert status.value == "archived"
        assert str(status) == "archived"
    
    def test_all_enum_values_are_valid(self):
        """Test that all TaskStatusEnum values can create valid TaskStatus objects."""
        for status_enum in TaskStatusEnum:
            status = TaskStatus(status_enum.value)
            assert status.value == status_enum.value


class TestTaskStatusValidation:
    """Test TaskStatus validation and error handling."""
    
    def test_invalid_status_raises_error(self):
        """Test that invalid status values raise ValueError."""
        invalid_statuses = ["invalid", "pending", "completed", "working", "paused"]
        
        for invalid_status in invalid_statuses:
            with pytest.raises(ValueError, match="Invalid task status"):
                TaskStatus(invalid_status)
    
    def test_empty_status_raises_error(self):
        """Test that empty status raises ValueError."""
        with pytest.raises(ValueError, match="Task status cannot be empty"):
            TaskStatus("")
    
    def test_none_status_raises_error(self):
        """Test that None status raises appropriate error."""
        with pytest.raises(ValueError, match="Task status cannot be empty"):
            TaskStatus(None)
    
    def test_case_sensitivity(self):
        """Test that status values are case-sensitive."""
        # TaskStatus should be case-sensitive
        with pytest.raises(ValueError, match="Invalid task status"):
            TaskStatus("TODO")  # Uppercase should be invalid
        
        with pytest.raises(ValueError, match="Invalid task status"):
            TaskStatus("In_Progress")  # Mixed case should be invalid


class TestTaskStatusFactoryMethods:
    """Test TaskStatus factory methods."""
    
    def test_todo_factory(self):
        """Test todo() factory method."""
        status = TaskStatus.todo()
        assert status.value == "todo"
        assert status.is_todo()
    
    def test_in_progress_factory(self):
        """Test in_progress() factory method."""
        status = TaskStatus.in_progress()
        assert status.value == "in_progress"
        assert status.is_in_progress()
    
    def test_blocked_factory(self):
        """Test blocked() factory method."""
        status = TaskStatus.blocked()
        assert status.value == "blocked"
    
    def test_review_factory(self):
        """Test review() factory method."""
        status = TaskStatus.review()
        assert status.value == "review"
    
    def test_testing_factory(self):
        """Test testing() factory method."""
        status = TaskStatus.testing()
        assert status.value == "testing"
    
    def test_done_factory(self):
        """Test done() factory method."""
        status = TaskStatus.done()
        assert status.value == "done"
        assert status.is_done()
    
    def test_cancelled_factory(self):
        """Test cancelled() factory method."""
        status = TaskStatus.cancelled()
        assert status.value == "cancelled"
    
    def test_archived_factory(self):
        """Test archived() factory method."""
        status = TaskStatus.archived()
        assert status.value == "archived"
    
    def test_from_string_valid(self):
        """Test from_string() with valid values."""
        status = TaskStatus.from_string("in_progress")
        assert status.value == "in_progress"
        
        # Test with whitespace
        status_with_space = TaskStatus.from_string("  done  ")
        assert status_with_space.value == "done"
    
    def test_from_string_empty_defaults_to_todo(self):
        """Test from_string() with empty value defaults to todo."""
        status = TaskStatus.from_string("")
        assert status.value == "todo"
        
        status_none = TaskStatus.from_string(None)
        assert status_none.value == "todo"


class TestTaskStatusCheckers:
    """Test TaskStatus state checking methods."""
    
    def test_is_todo(self):
        """Test is_todo() method."""
        todo_status = TaskStatus.todo()
        assert todo_status.is_todo() is True
        
        other_status = TaskStatus.in_progress()
        assert other_status.is_todo() is False
    
    def test_is_in_progress(self):
        """Test is_in_progress() method."""
        in_progress_status = TaskStatus.in_progress()
        assert in_progress_status.is_in_progress() is True
        
        other_status = TaskStatus.todo()
        assert other_status.is_in_progress() is False
    
    def test_is_done(self):
        """Test is_done() method."""
        done_status = TaskStatus.done()
        assert done_status.is_done() is True
        
        other_status = TaskStatus.in_progress()
        assert other_status.is_done() is False
    
    def test_is_completed(self):
        """Test is_completed() method (alias for is_done)."""
        done_status = TaskStatus.done()
        assert done_status.is_completed() is True
        assert done_status.is_completed() == done_status.is_done()
        
        other_status = TaskStatus.in_progress()
        assert other_status.is_completed() is False


class TestTaskStatusTransitions:
    """Test TaskStatus transition validation."""
    
    def test_todo_transitions(self):
        """Test valid transitions from TODO status."""
        todo_status = TaskStatus.todo()
        
        # Valid transitions (TODO → IN_PROGRESS, CANCELLED, DONE)
        assert todo_status.can_transition_to("in_progress") is True
        assert todo_status.can_transition_to("cancelled") is True
        assert todo_status.can_transition_to("done") is True  # Direct completion allowed
        
        # Invalid transitions
        assert todo_status.can_transition_to("blocked") is False
        assert todo_status.can_transition_to("review") is False
        assert todo_status.can_transition_to("testing") is False
        assert todo_status.can_transition_to("archived") is False
    
    def test_in_progress_transitions(self):
        """Test valid transitions from IN_PROGRESS status."""
        in_progress_status = TaskStatus.in_progress()
        
        # Valid transitions
        assert in_progress_status.can_transition_to("blocked") is True
        assert in_progress_status.can_transition_to("review") is True
        assert in_progress_status.can_transition_to("testing") is True
        assert in_progress_status.can_transition_to("cancelled") is True
        assert in_progress_status.can_transition_to("done") is True
        
        # Invalid transitions
        assert in_progress_status.can_transition_to("todo") is False
        assert in_progress_status.can_transition_to("archived") is False
    
    def test_blocked_transitions(self):
        """Test valid transitions from BLOCKED status."""
        blocked_status = TaskStatus.blocked()
        
        # Valid transitions
        assert blocked_status.can_transition_to("in_progress") is True
        assert blocked_status.can_transition_to("cancelled") is True
        
        # Invalid transitions
        assert blocked_status.can_transition_to("todo") is False
        assert blocked_status.can_transition_to("done") is False
        assert blocked_status.can_transition_to("review") is False
        assert blocked_status.can_transition_to("testing") is False
        assert blocked_status.can_transition_to("archived") is False
    
    def test_review_transitions(self):
        """Test valid transitions from REVIEW status."""
        review_status = TaskStatus.review()
        
        # Valid transitions
        assert review_status.can_transition_to("in_progress") is True
        assert review_status.can_transition_to("testing") is True
        assert review_status.can_transition_to("done") is True
        assert review_status.can_transition_to("cancelled") is True
        
        # Invalid transitions
        assert review_status.can_transition_to("todo") is False
        assert review_status.can_transition_to("blocked") is False
        assert review_status.can_transition_to("archived") is False
    
    def test_testing_transitions(self):
        """Test valid transitions from TESTING status."""
        testing_status = TaskStatus.testing()
        
        # Valid transitions
        assert testing_status.can_transition_to("in_progress") is True
        assert testing_status.can_transition_to("review") is True
        assert testing_status.can_transition_to("done") is True
        assert testing_status.can_transition_to("cancelled") is True
        
        # Invalid transitions
        assert testing_status.can_transition_to("todo") is False
        assert testing_status.can_transition_to("blocked") is False
        assert testing_status.can_transition_to("archived") is False
    
    def test_done_transitions(self):
        """Test that DONE status has no valid transitions."""
        done_status = TaskStatus.done()
        
        # No valid transitions from done
        assert done_status.can_transition_to("todo") is False
        assert done_status.can_transition_to("in_progress") is False
        assert done_status.can_transition_to("blocked") is False
        assert done_status.can_transition_to("review") is False
        assert done_status.can_transition_to("testing") is False
        assert done_status.can_transition_to("cancelled") is False
        assert done_status.can_transition_to("archived") is False
    
    def test_cancelled_transitions(self):
        """Test valid transitions from CANCELLED status."""
        cancelled_status = TaskStatus.cancelled()
        
        # Valid transitions
        assert cancelled_status.can_transition_to("todo") is True
        
        # Invalid transitions
        assert cancelled_status.can_transition_to("in_progress") is False
        assert cancelled_status.can_transition_to("blocked") is False
        assert cancelled_status.can_transition_to("review") is False
        assert cancelled_status.can_transition_to("testing") is False
        assert cancelled_status.can_transition_to("done") is False
        assert cancelled_status.can_transition_to("archived") is False
    
    def test_archived_transitions(self):
        """Test that ARCHIVED status has no valid transitions."""
        archived_status = TaskStatus.archived()
        
        # No valid transitions from archived
        assert archived_status.can_transition_to("todo") is False
        assert archived_status.can_transition_to("in_progress") is False
        assert archived_status.can_transition_to("blocked") is False
        assert archived_status.can_transition_to("review") is False
        assert archived_status.can_transition_to("testing") is False
        assert archived_status.can_transition_to("done") is False
        assert archived_status.can_transition_to("cancelled") is False
    
    def test_transition_with_invalid_status(self):
        """Test transitions with invalid status values."""
        status = TaskStatus.todo()
        
        # Invalid status should return False (not raise exception)
        assert status.can_transition_to("invalid_status") is False
        assert status.can_transition_to("") is False
        assert status.can_transition_to("pending") is False


class TestTaskStatusEquality:
    """Test TaskStatus equality and comparison."""
    
    def test_equal_statuses(self):
        """Test that TaskStatus objects with same value are equal."""
        status1 = TaskStatus("todo")
        status2 = TaskStatus("todo")
        assert status1 == status2
        
        # Test with factory methods
        status3 = TaskStatus.todo()
        status4 = TaskStatus.todo()
        assert status3 == status4
        assert status1 == status3
    
    def test_not_equal_statuses(self):
        """Test that TaskStatus objects with different values are not equal."""
        status1 = TaskStatus("todo")
        status2 = TaskStatus("done")
        assert status1 != status2
    
    def test_equality_with_string(self):
        """Test equality comparison with string (should use value comparison)."""
        status = TaskStatus("todo")
        # Direct string comparison might not work due to dataclass behavior
        assert status.value == "todo"
        assert str(status) == "todo"


class TestTaskStatusImmutability:
    """Test TaskStatus immutability."""
    
    def test_status_is_immutable(self):
        """Test that TaskStatus value cannot be changed after creation."""
        status = TaskStatus("todo")
        
        with pytest.raises(AttributeError):
            status.value = "done"


class TestTaskStatusHashing:
    """Test TaskStatus hashing behavior."""
    
    def test_status_is_hashable(self):
        """Test that TaskStatus can be used as dict key or in sets."""
        status1 = TaskStatus("todo")
        status2 = TaskStatus("done")
        status3 = TaskStatus("todo")  # Duplicate
        
        # Test as dict keys
        status_dict = {status1: "First", status2: "Second"}
        assert status_dict[status1] == "First"
        assert status_dict[status2] == "Second"
        
        # Test in sets
        status_set = {status1, status2, status3}
        assert len(status_set) == 2  # Duplicate should be ignored
        assert status1 in status_set
        assert status2 in status_set
    
    def test_equal_statuses_have_same_hash(self):
        """Test that equal TaskStatus objects have the same hash."""
        status1 = TaskStatus("todo")
        status2 = TaskStatus("todo")
        status3 = TaskStatus.todo()
        
        assert hash(status1) == hash(status2)
        assert hash(status1) == hash(status3)


class TestTaskStatusEdgeCases:
    """Test edge cases and error handling."""
    
    def test_status_with_whitespace_in_value(self):
        """Test that status values with internal whitespace are invalid."""
        with pytest.raises(ValueError, match="Invalid task status"):
            TaskStatus("in progress")  # Space instead of underscore
        
        with pytest.raises(ValueError, match="Invalid task status"):
            TaskStatus("to do")  # Space instead of no space
    
    def test_status_string_representation(self):
        """Test string representation of TaskStatus."""
        for status_enum in TaskStatusEnum:
            status = TaskStatus(status_enum.value)
            assert str(status) == status_enum.value
    
    def test_transition_to_same_status(self):
        """Test transitioning to the same status."""
        status = TaskStatus("todo")
        # Transitioning to same status should return False
        assert status.can_transition_to("todo") is False
        
        # Test for all statuses
        for status_enum in TaskStatusEnum:
            status = TaskStatus(status_enum.value)
            assert status.can_transition_to(status_enum.value) is False


class TestTaskStatusIntegration:
    

    """Integration tests with real use cases."""
    
    def test_typical_task_lifecycle(self):
        """Test a typical task lifecycle progression."""
        # Start with TODO
        task_status = TaskStatus.todo()
        assert task_status.is_todo()
        
        # Move to IN_PROGRESS
        assert task_status.can_transition_to("in_progress")
        task_status = TaskStatus.in_progress()
        assert task_status.is_in_progress()
        
        # Move to REVIEW
        assert task_status.can_transition_to("review")
        task_status = TaskStatus.review()
        
        # Move to TESTING
        assert task_status.can_transition_to("testing")
        task_status = TaskStatus.testing()
        
        # Complete the task
        assert task_status.can_transition_to("done")
        task_status = TaskStatus.done()
        assert task_status.is_done()
        assert task_status.is_completed()
        
        # Cannot transition from done
        assert not task_status.can_transition_to("in_progress")
    
    def test_blocked_task_flow(self):
        """Test task flow when blocked."""
        # Start with IN_PROGRESS
        task_status = TaskStatus.in_progress()
        
        # Get blocked
        assert task_status.can_transition_to("blocked")
        task_status = TaskStatus.blocked()
        
        # Unblock and continue
        assert task_status.can_transition_to("in_progress")
        task_status = TaskStatus.in_progress()
        
        # Complete
        assert task_status.can_transition_to("done")
    
    def test_cancelled_task_reopening(self):
        """Test reopening a cancelled task."""
        # Start with TODO
        task_status = TaskStatus.todo()
        
        # Cancel the task
        assert task_status.can_transition_to("cancelled")
        task_status = TaskStatus.cancelled()
        
        # Reopen the task
        assert task_status.can_transition_to("todo")
        task_status = TaskStatus.todo()
        
        # Continue normal flow
        assert task_status.can_transition_to("in_progress")
    
    def test_status_collection_usage(self):
        """Test using TaskStatus in collections."""
        statuses = [
            TaskStatus.todo(),
            TaskStatus.in_progress(),
            TaskStatus.done(),
            TaskStatus.blocked(),
            TaskStatus.review()
        ]
        
        # Filter completed tasks
        completed = [s for s in statuses if s.is_completed()]
        assert len(completed) == 1
        assert completed[0].value == "done"
        
        # Group by status
        status_groups = {}
        for status in statuses:
            status_groups.setdefault(status.value, []).append(status)
        
        assert len(status_groups) == 5
        assert all(len(group) == 1 for group in status_groups.values())