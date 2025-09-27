"""Unit tests for TaskCompletionService - Domain Service for Task Completion Business Rules"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any, Optional

from fastmcp.task_management.domain.services.task_completion_service import (
    TaskCompletionService,
    TaskContextRepositoryProtocol
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskCompletionError


# Fixtures at module level
@pytest.fixture
def mock_subtask_repository():
    """Mock subtask repository."""
    return Mock(spec=SubtaskRepository)


@pytest.fixture
def mock_task_context_repository():
    """Mock task context repository."""
    return Mock(spec=TaskContextRepositoryProtocol)


@pytest.fixture
def service(mock_subtask_repository, mock_task_context_repository):
    """Create TaskCompletionService instance with mocks."""
    return TaskCompletionService(
        subtask_repository=mock_subtask_repository,
        task_context_repository=mock_task_context_repository
    )


@pytest.fixture
def service_without_context(mock_subtask_repository):
    """Create TaskCompletionService instance without context repository."""
    return TaskCompletionService(
        subtask_repository=mock_subtask_repository,
        task_context_repository=None
    )


@pytest.fixture
def valid_task():
    """Create a valid task for testing."""
    task = Mock(spec=Task)
    task.id = TaskId("550e8400-e29b-41d4-a716-446655440001")
    task.title = "Complete authentication feature"
    task.status = TaskStatus.IN_PROGRESS
    task.context_id = "550e8400-e29b-41d4-a716-446655440001"
    return task


@pytest.fixture
def completed_subtask():
    """Create a completed subtask."""
    subtask = Mock(spec=Subtask)
    subtask.id = TaskId("550e8400-e29b-41d4-a716-446655440002")
    subtask.title = "Implement login UI"
    subtask.status = TaskStatus.DONE
    subtask.is_completed = True
    return subtask


@pytest.fixture
def incomplete_subtask():
    """Create an incomplete subtask."""
    subtask = Mock(spec=Subtask)
    subtask.id = TaskId("550e8400-e29b-41d4-a716-446655440003")
    subtask.title = "Add session management"
    subtask.status = TaskStatus.IN_PROGRESS
    subtask.is_completed = False
    return subtask


class TestCanCompleteTask:
    """Test the can_complete_task method."""

    def test_can_complete_task_with_no_subtasks(self, service, valid_task, mock_subtask_repository, mock_task_context_repository):
        """Test task can be completed when it has no subtasks."""
        mock_subtask_repository.find_by_parent_task_id.return_value = []
        mock_task_context_repository.get.return_value = {"id": "context-1"}

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is True
        assert error_msg is None
        mock_subtask_repository.find_by_parent_task_id.assert_called_once_with(valid_task.id)

    def test_can_complete_task_with_all_subtasks_completed(self, service, valid_task, completed_subtask, mock_subtask_repository):
        """Test task can be completed when all subtasks are done."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [completed_subtask, completed_subtask]

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is True
        assert error_msg is None

    def test_cannot_complete_task_with_incomplete_subtasks(self, service, valid_task, completed_subtask, incomplete_subtask, mock_subtask_repository):
        """Test task cannot be completed when some subtasks are incomplete."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [completed_subtask, incomplete_subtask]

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is False
        assert "Cannot complete task: 1 of 2 subtasks are not done" in error_msg

    def test_task_without_context_id_but_has_context_in_repository(self, service, valid_task, mock_subtask_repository, mock_task_context_repository):
        """Test task without context_id but context exists in repository."""
        valid_task.context_id = None
        mock_task_context_repository.get.return_value = {"id": "context-1"}
        mock_subtask_repository.find_by_parent_task_id.return_value = []

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is True
        assert error_msg is None
        mock_task_context_repository.get.assert_called_once_with(valid_task.id.value)

    def test_task_without_context_logs_info(self, service, valid_task, mock_subtask_repository, mock_task_context_repository, caplog):
        """Test task without context logs info message."""
        import logging
        caplog.set_level(logging.INFO)
        
        valid_task.context_id = None
        mock_task_context_repository.get.return_value = None
        mock_subtask_repository.find_by_parent_task_id.return_value = []

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is True
        assert error_msg is None
        assert "Context will be auto-created during completion" in caplog.text

    def test_exception_handling_in_can_complete_task(self, service, valid_task, mock_subtask_repository):
        """Test exception handling in can_complete_task."""
        mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("Database error")

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is False
        assert "Internal error validating task completion" in error_msg

    def test_multiple_incomplete_subtasks(self, service, valid_task, incomplete_subtask, mock_subtask_repository):
        """Test task with multiple incomplete subtasks."""
        # Create multiple incomplete subtasks with proper attributes
        incomplete_subtasks = []
        for i in range(3):
            subtask = Mock(spec=Subtask)
            subtask.id = TaskId(f"550e8400-e29b-41d4-a716-44665544000{i}")
            subtask.title = f"Incomplete task {i}"
            subtask.status = TaskStatus.TODO
            subtask.is_completed = False
            incomplete_subtasks.append(subtask)

        mock_subtask_repository.find_by_parent_task_id.return_value = incomplete_subtasks

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is False
        assert "Cannot complete task: 3 of 3 subtasks are not done" in error_msg
        
        # Check that incomplete subtask details were stored
        assert hasattr(service, '_incomplete_subtasks')
        assert len(service._incomplete_subtasks) == 3
        assert service._incomplete_count == 3
        assert service._total_count == 3


class TestValidateTaskCompletion:
    """Test the validate_task_completion method."""

    def test_validate_task_completion_success(self, service, valid_task, mock_subtask_repository):
        """Test successful task completion validation."""
        mock_subtask_repository.find_by_parent_task_id.return_value = []

        # Should not raise exception
        service.validate_task_completion(valid_task)

    def test_validate_task_completion_raises_exception(self, service, valid_task, incomplete_subtask, mock_subtask_repository):
        """Test validation raises exception for incomplete subtasks."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [incomplete_subtask]

        with pytest.raises(TaskCompletionError) as exc_info:
            service.validate_task_completion(valid_task)

        exception = exc_info.value
        assert "Cannot complete task" in str(exception)
        assert exception.context.get("incomplete_subtasks") is not None
        assert len(exception.context["incomplete_subtasks"]) == 1
        assert exception.context["incomplete_subtasks"][0]["title"] == "Add session management"

    def test_validate_task_completion_with_context_data(self, service, valid_task, incomplete_subtask, completed_subtask, mock_subtask_repository):
        """Test validation exception includes proper context data."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [completed_subtask, incomplete_subtask]

        with pytest.raises(TaskCompletionError) as exc_info:
            service.validate_task_completion(valid_task)

        exception = exc_info.value
        assert exception.context.get("incomplete_subtasks") is not None
        assert exception.context.get("total_count") == 2
        assert len(exception.context["incomplete_subtasks"]) == 1


class TestGetCompletionBlockers:
    """Test the get_completion_blockers method."""

    def test_no_blockers_when_completable(self, service, valid_task, mock_subtask_repository, mock_task_context_repository):
        """Test empty list when task can be completed."""
        mock_subtask_repository.find_by_parent_task_id.return_value = []
        mock_task_context_repository.get.return_value = {"id": "context-1"}

        blockers = service.get_completion_blockers(valid_task)
        
        assert blockers == []

    def test_blocker_for_incomplete_subtasks(self, service, valid_task, incomplete_subtask, completed_subtask, mock_subtask_repository):
        """Test blocker message for incomplete subtasks."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [completed_subtask, incomplete_subtask]

        blockers = service.get_completion_blockers(valid_task)
        
        assert len(blockers) == 1
        assert "1 of 2 subtasks are incomplete" in blockers[0]
        assert "Add session management" in blockers[0]
        assert "Complete all subtasks first" in blockers[0]

    def test_blocker_with_many_incomplete_subtasks(self, service, valid_task, mock_subtask_repository):
        """Test blocker message truncates when many subtasks are incomplete."""
        # Create many incomplete subtasks
        incomplete_subtasks = []
        for i in range(5):
            subtask = Mock(spec=Subtask)
            subtask.title = f"Task {i}"
            subtask.is_completed = False
            incomplete_subtasks.append(subtask)

        mock_subtask_repository.find_by_parent_task_id.return_value = incomplete_subtasks

        blockers = service.get_completion_blockers(valid_task)
        
        assert len(blockers) == 1
        assert "5 of 5 subtasks are incomplete" in blockers[0]
        assert "Task 0, Task 1, Task 2" in blockers[0]
        assert "and 2 more" in blockers[0]

    def test_blocker_exception_handling(self, service, valid_task, mock_subtask_repository):
        """Test exception handling in get_completion_blockers."""
        mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("Database error")

        blockers = service.get_completion_blockers(valid_task)
        
        assert len(blockers) == 1
        assert "Error checking completion status" in blockers[0]


class TestGetSubtaskCompletionSummary:
    """Test the get_subtask_completion_summary method."""

    def test_summary_with_no_subtasks(self, service, valid_task, mock_subtask_repository):
        """Test summary when task has no subtasks."""
        mock_subtask_repository.find_by_parent_task_id.return_value = []

        summary = service.get_subtask_completion_summary(valid_task)
        
        assert summary["total"] == 0
        assert summary["completed"] == 0
        assert summary["incomplete"] == 0
        assert summary["completion_percentage"] == 100
        assert summary["can_complete_parent"] is True

    def test_summary_with_all_completed(self, service, valid_task, completed_subtask, mock_subtask_repository):
        """Test summary when all subtasks are completed."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [completed_subtask, completed_subtask]

        summary = service.get_subtask_completion_summary(valid_task)
        
        assert summary["total"] == 2
        assert summary["completed"] == 2
        assert summary["incomplete"] == 0
        assert summary["completion_percentage"] == 100
        assert summary["can_complete_parent"] is True

    def test_summary_with_partial_completion(self, service, valid_task, completed_subtask, incomplete_subtask, mock_subtask_repository):
        """Test summary with partially completed subtasks."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [completed_subtask, incomplete_subtask]

        summary = service.get_subtask_completion_summary(valid_task)
        
        assert summary["total"] == 2
        assert summary["completed"] == 1
        assert summary["incomplete"] == 1
        assert summary["completion_percentage"] == 50.0
        assert summary["can_complete_parent"] is False

    def test_summary_with_exception(self, service, valid_task, mock_subtask_repository):
        """Test summary when exception occurs."""
        mock_subtask_repository.find_by_parent_task_id.side_effect = Exception("Database error")

        summary = service.get_subtask_completion_summary(valid_task)
        
        assert summary["total"] == 0
        assert summary["completed"] == 0
        assert summary["incomplete"] == 0
        assert summary["completion_percentage"] == 0
        assert summary["can_complete_parent"] is False
        assert summary["error"] == "Database error"


class TestHelperMethods:
    """Test helper methods."""

    def test_create_context_required_error(self, service, valid_task):
        """Test _create_context_required_error helper method."""
        error_info = service._create_context_required_error(valid_task)
        
        assert error_info["error"] == "Task completion requires context to be created first."
        assert "explanation" in error_info
        assert "recovery_instructions" in error_info
        assert len(error_info["recovery_instructions"]) == 3
        assert "step_by_step_fix" in error_info
        assert len(error_info["step_by_step_fix"]) == 3
        assert str(valid_task.id.value) in error_info["step_by_step_fix"][0]["command"]

    def test_create_incomplete_subtasks_error(self, service, valid_task, incomplete_subtask, mock_subtask_repository):
        """Test _create_incomplete_subtasks_error helper method."""
        mock_subtask_repository.find_by_parent_task_id.return_value = [incomplete_subtask]
        
        error_info = service._create_incomplete_subtasks_error(valid_task, [incomplete_subtask])
        
        assert error_info["error"] == "Cannot complete task while subtasks remain incomplete."
        assert error_info["details"]["incomplete_count"] == 1
        assert error_info["details"]["total_subtasks"] == 1
        assert len(error_info["details"]["incomplete_subtask_titles"]) == 1
        assert error_info["details"]["incomplete_subtask_titles"][0] == "Add session management"
        assert len(error_info["recovery_instructions"]) == 3
        assert len(error_info["step_by_step_fix"]) == 3


class TestServiceWithoutContextRepository:
    """Test service behavior without context repository."""

    def test_can_complete_without_context_repository(self, service_without_context, valid_task, mock_subtask_repository):
        """Test task can be completed without context repository."""
        valid_task.context_id = None
        mock_subtask_repository.find_by_parent_task_id.return_value = []

        can_complete, error_msg = service_without_context.can_complete_task(valid_task)
        
        assert can_complete is True
        assert error_msg is None

    def test_blockers_without_context_repository(self, service_without_context, valid_task, mock_subtask_repository):
        """Test blockers don't include context when repository not available."""
        valid_task.context_id = None
        mock_subtask_repository.find_by_parent_task_id.return_value = []

        blockers = service_without_context.get_completion_blockers(valid_task)
        
        assert blockers == []


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_subtask_with_non_value_object_id(self, service, valid_task, mock_subtask_repository):
        """Test handling of subtasks with plain string IDs."""
        # Create subtask with plain string ID (not TaskId object)
        subtask = Mock(spec=Subtask)
        subtask.id = "plain-string-id"
        subtask.title = "Plain ID subtask"
        subtask.status = "in_progress"
        subtask.is_completed = False

        mock_subtask_repository.find_by_parent_task_id.return_value = [subtask]

        can_complete, error_msg = service.can_complete_task(valid_task)
        
        assert can_complete is False
        assert "Cannot complete task: 1 of 1 subtasks are not done" in error_msg

    def test_completion_percentage_rounding(self, service, valid_task, mock_subtask_repository):
        """Test completion percentage is properly rounded."""
        # Create 3 subtasks, 1 completed
        subtasks = []
        for i in range(3):
            subtask = Mock(spec=Subtask)
            subtask.is_completed = (i == 0)  # Only first is completed
            subtasks.append(subtask)

        mock_subtask_repository.find_by_parent_task_id.return_value = subtasks

        summary = service.get_subtask_completion_summary(valid_task)
        
        assert summary["completion_percentage"] == 33.3  # 1/3 = 33.333... rounded to 33.3

    def test_empty_subtask_titles_in_blockers(self, service, valid_task, mock_subtask_repository):
        """Test handling of subtasks with empty titles."""
        subtask = Mock(spec=Subtask)
        subtask.title = ""
        subtask.is_completed = False

        mock_subtask_repository.find_by_parent_task_id.return_value = [subtask]

        blockers = service.get_completion_blockers(valid_task)
        
        assert len(blockers) == 1
        assert "1 of 1 subtasks are incomplete" in blockers[0]
        # Empty title should still be included
        assert "(including: )" in blockers[0]