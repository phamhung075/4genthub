"""Unit tests for TaskStatus value object."""
import pytest
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus, TaskStatusEnum


class TestTaskStatus:
    """Test cases for TaskStatus value object"""
    
    def test_create_task_status_with_valid_status(self):
        """Test creating TaskStatus with valid status string"""
        status = TaskStatus("todo")
        assert status.value == "todo"
        assert str(status) == "todo"
    
    def test_create_task_status_with_all_valid_statuses(self):
        """Test creating TaskStatus with all valid enum values"""
        valid_statuses = ["todo", "in_progress", "blocked", "review", "testing", "done", "cancelled", "archived"]
        
        for status_value in valid_statuses:
            status = TaskStatus(status_value)
            assert status.value == status_value
    
    def test_task_status_is_immutable(self):
        """Test that TaskStatus is immutable (frozen dataclass)"""
        status = TaskStatus("todo")
        
        with pytest.raises(AttributeError):
            status.value = "done"
    
    def test_task_status_with_empty_string(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError, match="Task status cannot be empty"):
            TaskStatus("")
    
    def test_task_status_with_invalid_status(self):
        """Test that invalid status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid task status: invalid"):
            TaskStatus("invalid")
        
        with pytest.raises(ValueError, match="Invalid task status: completed"):
            TaskStatus("completed")  # Should be 'done'
    
    def test_class_attributes_for_backward_compatibility(self):
        """Test that class attributes exist for backward compatibility"""
        assert TaskStatus.TODO == "todo"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.BLOCKED == "blocked"
        assert TaskStatus.REVIEW == "review"
        assert TaskStatus.TESTING == "testing"
        assert TaskStatus.DONE == "done"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.ARCHIVED == "archived"
    
    def test_factory_methods(self):
        """Test factory methods for creating TaskStatus instances"""
        assert TaskStatus.todo().value == "todo"
        assert TaskStatus.in_progress().value == "in_progress"
        assert TaskStatus.blocked().value == "blocked"
        assert TaskStatus.review().value == "review"
        assert TaskStatus.testing().value == "testing"
        assert TaskStatus.done().value == "done"
        assert TaskStatus.cancelled().value == "cancelled"
        assert TaskStatus.archived().value == "archived"
    
    def test_from_string_method(self):
        """Test creating TaskStatus from string"""
        status = TaskStatus.from_string("in_progress")
        assert status.value == "in_progress"
        
        # Test with whitespace
        status_with_spaces = TaskStatus.from_string("  done  ")
        assert status_with_spaces.value == "done"
        
        # Test with None defaults to "todo"
        status_none = TaskStatus.from_string(None)
        assert status_none.value == "todo"
        
        # Test with empty string defaults to "todo"
        status_empty = TaskStatus.from_string("")
        assert status_empty.value == "todo"
    
    def test_is_methods(self):
        """Test status checking methods"""
        todo_status = TaskStatus("todo")
        assert todo_status.is_todo() is True
        assert todo_status.is_in_progress() is False
        assert todo_status.is_done() is False
        assert todo_status.is_completed() is False  # Alias for is_done
        
        in_progress_status = TaskStatus("in_progress")
        assert in_progress_status.is_todo() is False
        assert in_progress_status.is_in_progress() is True
        assert in_progress_status.is_done() is False
        assert in_progress_status.is_completed() is False
        
        done_status = TaskStatus("done")
        assert done_status.is_todo() is False
        assert done_status.is_in_progress() is False
        assert done_status.is_done() is True
        assert done_status.is_completed() is True  # Alias for is_done
    
    def test_can_transition_to_from_todo(self):
        """Test valid transitions from TODO status"""
        todo = TaskStatus("todo")
        
        assert todo.can_transition_to("in_progress") is True
        assert todo.can_transition_to("cancelled") is True
        assert todo.can_transition_to("done") is True  # Direct completion allowed per business rules
        assert todo.can_transition_to("blocked") is False
        assert todo.can_transition_to("review") is False
        assert todo.can_transition_to("testing") is False
    
    def test_can_transition_to_from_in_progress(self):
        """Test valid transitions from IN_PROGRESS status"""
        in_progress = TaskStatus("in_progress")
        
        assert in_progress.can_transition_to("blocked") is True
        assert in_progress.can_transition_to("review") is True
        assert in_progress.can_transition_to("testing") is True
        assert in_progress.can_transition_to("cancelled") is True
        assert in_progress.can_transition_to("done") is True
        assert in_progress.can_transition_to("todo") is False
    
    def test_can_transition_to_from_blocked(self):
        """Test valid transitions from BLOCKED status"""
        blocked = TaskStatus("blocked")
        
        assert blocked.can_transition_to("in_progress") is True
        assert blocked.can_transition_to("cancelled") is True
        assert blocked.can_transition_to("done") is False  # Cannot skip directly from blocked to done
        assert blocked.can_transition_to("todo") is False
    
    def test_can_transition_to_from_review(self):
        """Test valid transitions from REVIEW status"""
        review = TaskStatus("review")
        
        assert review.can_transition_to("in_progress") is True
        assert review.can_transition_to("testing") is True
        assert review.can_transition_to("done") is True
        assert review.can_transition_to("cancelled") is True
        assert review.can_transition_to("blocked") is False
    
    def test_can_transition_to_from_testing(self):
        """Test valid transitions from TESTING status"""
        testing = TaskStatus("testing")
        
        assert testing.can_transition_to("in_progress") is True
        assert testing.can_transition_to("review") is True
        assert testing.can_transition_to("done") is True
        assert testing.can_transition_to("cancelled") is True
        assert testing.can_transition_to("blocked") is False
    
    def test_can_transition_to_from_done(self):
        """Test that no transitions are allowed from DONE status"""
        done = TaskStatus("done")
        
        assert done.can_transition_to("todo") is False
        assert done.can_transition_to("in_progress") is False
        assert done.can_transition_to("blocked") is False
        assert done.can_transition_to("cancelled") is False
    
    def test_can_transition_to_from_cancelled(self):
        """Test valid transitions from CANCELLED status"""
        cancelled = TaskStatus("cancelled")
        
        assert cancelled.can_transition_to("todo") is True  # Can reopen
        assert cancelled.can_transition_to("in_progress") is False
        assert cancelled.can_transition_to("done") is False
    
    def test_can_transition_to_from_archived(self):
        """Test that no transitions are allowed from ARCHIVED status"""
        archived = TaskStatus("archived")
        
        assert archived.can_transition_to("todo") is False
        assert archived.can_transition_to("in_progress") is False
        assert archived.can_transition_to("done") is False
        assert archived.can_transition_to("cancelled") is False
    
    def test_task_status_equality(self):
        """Test TaskStatus equality comparison"""
        status1 = TaskStatus("todo")
        status2 = TaskStatus("todo")
        status3 = TaskStatus("done")
        
        assert status1 == status2
        assert status1 != status3
        assert status1 != "todo"  # Not equal to string
    
    def test_task_status_hash(self):
        """Test TaskStatus hashing for use in sets/dicts"""
        status1 = TaskStatus("todo")
        status2 = TaskStatus("todo")
        status3 = TaskStatus("done")
        
        assert hash(status1) == hash(status2)
        assert hash(status1) != hash(status3)
        
        # Can be used in sets
        statuses = {status1, status2, status3}
        assert len(statuses) == 2  # status1 and status2 are equal
    
    def test_task_status_enum_values(self):
        """Test TaskStatusEnum has expected values"""
        expected_statuses = {
            TaskStatusEnum.TODO: "todo",
            TaskStatusEnum.IN_PROGRESS: "in_progress",
            TaskStatusEnum.BLOCKED: "blocked",
            TaskStatusEnum.REVIEW: "review",
            TaskStatusEnum.TESTING: "testing",
            TaskStatusEnum.DONE: "done",
            TaskStatusEnum.CANCELLED: "cancelled",
            TaskStatusEnum.ARCHIVED: "archived"
        }
        
        for enum_member, expected_value in expected_statuses.items():
            assert enum_member.value == expected_value