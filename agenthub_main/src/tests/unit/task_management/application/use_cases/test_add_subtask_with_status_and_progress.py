"""Test Add Subtask with Status and Progress Percentage Parameters

This test verifies the fix for Issue #4: Allow Status and Progress Parameters in Subtask Creation
"""

from unittest.mock import Mock

import pytest

from fastmcp.task_management.application.dtos.subtask.add_subtask_request import (
    AddSubtaskRequest,
)
from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId


@pytest.fixture
def mock_task_repository():
    """Mock task repository."""
    repository = Mock()

    # Create a mock task
    task = Task(title="Parent Task", description="Test parent task", assignees=[])
    task.id = TaskId.from_string("test-task-id")
    task.subtasks = []
    # subtask_count is now a computed property from len(subtasks), no need to set it

    repository.find_by_id = Mock(return_value=task)
    repository.save = Mock()

    return repository


@pytest.fixture
def mock_subtask_repository():
    """Mock subtask repository."""
    repository = Mock()
    repository.get_next_id = Mock(return_value=TaskId.from_string("test-subtask-id"))
    repository.save = Mock()
    return repository


@pytest.fixture
def add_subtask_use_case(mock_task_repository, mock_subtask_repository):
    """Create AddSubtaskUseCase instance with mocked dependencies."""
    return AddSubtaskUseCase(
        task_repository=mock_task_repository, subtask_repository=mock_subtask_repository
    )


class TestAddSubtaskWithStatusAndProgress:
    """Test subtask creation with status and progress_percentage parameters."""

    def test_create_subtask_with_status_in_progress(self, add_subtask_use_case):
        """Test creating subtask with status='in_progress'."""
        request = AddSubtaskRequest(
            task_id="test-task-id",
            title="Test Subtask",
            description="Test description",
            status="in_progress",
        )

        response = add_subtask_use_case.execute(request)

        assert response.subtask is not None
        assert response.subtask["status"] == "in_progress"
        assert response.subtask["title"] == "Test Subtask"

    def test_create_subtask_with_progress_percentage_45(self, add_subtask_use_case):
        """Test creating subtask with progress_percentage=45."""
        request = AddSubtaskRequest(
            task_id="test-task-id",
            title="Test Subtask",
            description="Test description",
            progress_percentage=45,
        )

        response = add_subtask_use_case.execute(request)

        assert response.subtask is not None
        assert response.subtask["progress_percentage"] == 45
        # Should auto-set status to in_progress
        assert response.subtask["status"] == "in_progress"

    def test_create_subtask_with_progress_percentage_100_auto_sets_done(
        self, add_subtask_use_case
    ):
        """Test creating subtask with progress_percentage=100 auto-sets status to 'done'."""
        request = AddSubtaskRequest(
            task_id="test-task-id",
            title="Test Subtask",
            description="Test description",
            progress_percentage=100,
        )

        response = add_subtask_use_case.execute(request)

        assert response.subtask is not None
        assert response.subtask["progress_percentage"] == 100
        # Should auto-set status to done
        assert response.subtask["status"] == "done"

    def test_create_subtask_with_both_status_and_progress(self, add_subtask_use_case):
        """Test creating subtask with both status and progress_percentage."""
        request = AddSubtaskRequest(
            task_id="test-task-id",
            title="Test Subtask",
            description="Test description",
            status="in_progress",
            progress_percentage=75,
        )

        response = add_subtask_use_case.execute(request)

        assert response.subtask is not None
        assert response.subtask["status"] == "in_progress"
        assert response.subtask["progress_percentage"] == 75

    def test_create_subtask_without_status_defaults_to_todo(self, add_subtask_use_case):
        """Test creating subtask without status defaults to 'todo'."""
        request = AddSubtaskRequest(
            task_id="test-task-id", title="Test Subtask", description="Test description"
        )

        response = add_subtask_use_case.execute(request)

        assert response.subtask is not None
        assert response.subtask["status"] == "todo"
        assert response.subtask["progress_percentage"] == 0

    def test_create_subtask_with_progress_0_keeps_todo_status(
        self, add_subtask_use_case
    ):
        """Test creating subtask with progress_percentage=0 keeps status as 'todo'."""
        request = AddSubtaskRequest(
            task_id="test-task-id",
            title="Test Subtask",
            description="Test description",
            progress_percentage=0,
        )

        response = add_subtask_use_case.execute(request)

        assert response.subtask is not None
        assert response.subtask["status"] == "todo"
        assert response.subtask["progress_percentage"] == 0

    def test_create_subtask_with_invalid_status_raises_error(
        self, add_subtask_use_case
    ):
        """Test creating subtask with invalid status raises an error."""
        request = AddSubtaskRequest(
            task_id="test-task-id",
            title="Test Subtask",
            description="Test description",
            status="invalid_status",
        )

        with pytest.raises(ValueError):
            add_subtask_use_case.execute(request)

    def test_create_subtask_with_all_parameters(self, add_subtask_use_case):
        """Test creating subtask with all parameters including status and progress."""
        request = AddSubtaskRequest(
            task_id="test-task-id",
            title="Complete Subtask",
            description="Full test",
            status="in_progress",
            progress_percentage=50,
            priority="high",
            assignees=["coding-agent"],
        )

        response = add_subtask_use_case.execute(request)

        assert response.subtask is not None
        assert response.subtask["status"] == "in_progress"
        assert response.subtask["progress_percentage"] == 50
        assert response.subtask["priority"] == "high"
        assert len(response.subtask["assignees"]) == 1
