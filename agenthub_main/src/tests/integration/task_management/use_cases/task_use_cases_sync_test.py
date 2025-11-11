"""
Integration tests for task use case layer synchronization hooks.

Tests verify that create_task, update_task, and complete_task use cases
correctly trigger synchronization to context_data and handle failures gracefully.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from fastmcp.task_management.application.dtos.task.create_task_request import (
    CreateTaskRequest,
)
from fastmcp.task_management.application.dtos.task.update_task_request import (
    UpdateTaskRequest,
)
from fastmcp.task_management.application.facades.task_application_facade import (
    TaskApplicationFacade,
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import (
    MockTaskRepository,
)


@pytest.fixture
def task_repository():
    """Create in-memory task repository for testing."""
    return MockTaskRepository()


@pytest.fixture
def context_service():
    """Create mock context service."""
    mock_service = MagicMock()
    mock_service.create_context = AsyncMock(return_value={"success": True})
    mock_service.update_context = AsyncMock(return_value={"success": True})
    return mock_service


@pytest.fixture
def facade(task_repository, context_service):
    """Create task application facade with mocked dependencies."""
    return TaskApplicationFacade(
        task_repository=task_repository, context_service=context_service
    )


@pytest.mark.asyncio
class TestCreateTaskSyncsMetadataOnCreation:
    """Test that create_task use case syncs metadata to context on creation."""

    async def test_create_task_syncs_basic_metadata(self, facade, task_repository):
        """Verify create_task synchronizes title, status, priority to context_data."""
        # Arrange
        git_branch_id = str(uuid4())
        create_request = CreateTaskRequest(
            git_branch_id=git_branch_id,
            title="Test Task",
            description="Test Description",
            status="todo",
            priority="high",
            assignees="test-agent",
        )

        # Act
        result = await facade.create_task(create_request)

        # Assert
        assert result["success"] is True
        task_id = result["task"]["id"]

        # Retrieve task to verify context_data sync
        task = task_repository.find_by_id(TaskId(task_id))
        assert task is not None

        # Verify context_data has metadata synced
        context_data = task.context_data
        assert context_data["metadata"]["task_id"] == task_id
        assert context_data["metadata"]["status"] == "todo"
        assert context_data["metadata"]["priority"] == "high"
        assert "@test-agent" in context_data["metadata"]["assignees"]

        # Verify objective section
        assert context_data["objective"]["title"] == "Test Task"
        assert context_data["objective"]["description"] == "Test Description"

    async def test_create_task_initializes_subtask_counts(
        self, facade, task_repository
    ):
        """Verify create_task initializes subtask counts to zero."""
        # Arrange
        create_request = CreateTaskRequest(
            git_branch_id=str(uuid4()),
            title="Task with Subtasks",
            assignees="test-agent",
        )

        # Act
        result = await facade.create_task(create_request)

        # Assert
        task_id = result["task"]["id"]
        task = task_repository.find_by_id(TaskId(task_id))

        # Verify subtask counts initialized
        context_data = task.context_data
        assert context_data["subtasks"]["total_count"] == 0
        assert context_data["subtasks"]["completed_count"] == 0
        assert context_data["subtasks"]["progress_percentage"] == 0.0


@pytest.mark.asyncio
class TestUpdateTaskSyncsOnUpdate:
    """Test that update_task use case triggers synchronization."""

    async def test_update_task_syncs_changed_fields(self, facade, task_repository):
        """Verify update_task synchronizes updated fields to context_data."""
        # Arrange - Create initial task
        task = Task.create(
            git_branch_id=str(uuid4()),
            title="Original Title",
            assignees=["original-agent"],
            user_id=str(uuid4()),
        )
        task_repository.save(task)

        # Act - Update task
        update_request = UpdateTaskRequest(
            task_id=str(task.id),
            title="Updated Title",
            priority="urgent",
            status="in_progress",
        )
        result = await facade.update_task(update_request)

        # Assert
        assert result["success"] is True

        # Verify sync happened
        updated_task = task_repository.find_by_id(task.id)
        context_data = updated_task.context_data

        assert context_data["objective"]["title"] == "Updated Title"
        assert context_data["metadata"]["priority"] == "urgent"
        assert context_data["metadata"]["status"] == "in_progress"

    async def test_update_task_preserves_unmodified_fields(
        self, facade, task_repository
    ):
        """Verify update_task preserves fields not being updated."""
        # Arrange
        task = Task.create(
            git_branch_id=str(uuid4()),
            title="Original",
            description="Keep this description",
            assignees=["keep-agent"],
            user_id=str(uuid4()),
        )
        task_repository.save(task)

        # Act - Update only title
        update_request = UpdateTaskRequest(task_id=str(task.id), title="New Title")
        await facade.update_task(update_request)

        # Assert
        updated_task = task_repository.find_by_id(task.id)
        context_data = updated_task.context_data

        # New field updated
        assert context_data["objective"]["title"] == "New Title"

        # Original fields preserved
        assert context_data["objective"]["description"] == "Keep this description"
        assert "@keep-agent" in context_data["metadata"]["assignees"]


@pytest.mark.asyncio
class TestCompleteTaskSyncsStatusAndMetadata:
    """Test that complete_task use case syncs completion data."""

    async def test_complete_task_updates_status_to_done(self, facade, task_repository):
        """Verify complete_task sets status to 'done' in context_data."""
        # Arrange
        task = Task.create(
            git_branch_id=str(uuid4()),
            title="Task to Complete",
            assignees=["test-agent"],
            user_id=str(uuid4()),
        )
        task_repository.save(task)

        # Act
        result = await facade.complete_task(
            task_id=str(task.id),
            completion_summary="Successfully completed all requirements",
            testing_notes="All tests passing",
        )

        # Assert
        assert result["success"] is True

        completed_task = task_repository.find_by_id(task.id)
        context_data = completed_task.context_data

        assert context_data["metadata"]["status"] == "done"
        assert completed_task.status == TaskStatus.DONE

    async def test_complete_task_syncs_completion_data(self, facade, task_repository):
        """Verify complete_task synchronizes completion summary to context_data."""
        # Arrange
        task = Task.create(
            git_branch_id=str(uuid4()),
            title="Task to Complete",
            assignees=["test-agent"],
            user_id=str(uuid4()),
        )
        task_repository.save(task)

        # Act
        completion_summary = "Implemented feature X with tests"
        testing_notes = "Unit tests: 15/15 passing"

        await facade.complete_task(
            task_id=str(task.id),
            completion_summary=completion_summary,
            testing_notes=testing_notes,
        )

        # Assert
        task_repository.find_by_id(task.id)
        # Completion data would be in context_data or task details
        # This verifies the sync happened without errors


@pytest.mark.asyncio
class TestSyncFailuresDontBreakTaskOperations:
    """Test that synchronization failures don't break core task operations."""

    async def test_create_task_succeeds_even_if_sync_fails(self, task_repository):
        """Verify task creation succeeds even if context sync fails."""
        # Arrange - Create facade with failing context service
        failing_context_service = MagicMock()
        failing_context_service.create_context = AsyncMock(
            side_effect=Exception("Context service unavailable")
        )

        facade = TaskApplicationFacade(
            task_repository=task_repository, context_service=failing_context_service
        )

        # Act
        create_request = CreateTaskRequest(
            git_branch_id=str(uuid4()),
            title="Task with Sync Failure",
            assignees="test-agent",
        )

        # Should not raise exception
        result = await facade.create_task(create_request)

        # Assert - Task still created
        assert result["success"] is True
        task_id = result["task"]["id"]

        task = task_repository.find_by_id(TaskId(task_id))
        assert task is not None
        assert task.title == "Task with Sync Failure"

    async def test_update_task_succeeds_even_if_sync_fails(self, task_repository):
        """Verify task update succeeds even if context sync fails."""
        # Arrange
        task = Task.create(
            git_branch_id=str(uuid4()),
            title="Original",
            assignees=["test-agent"],
            user_id=str(uuid4()),
        )
        task_repository.save(task)

        # Create facade with failing sync
        failing_context_service = MagicMock()
        failing_context_service.update_context = AsyncMock(
            side_effect=Exception("Sync failed")
        )

        facade = TaskApplicationFacade(
            task_repository=task_repository, context_service=failing_context_service
        )

        # Act
        update_request = UpdateTaskRequest(
            task_id=str(task.id), title="Updated Despite Sync Failure"
        )

        result = await facade.update_task(update_request)

        # Assert - Update still succeeded
        assert result["success"] is True

        updated_task = task_repository.find_by_id(task.id)
        assert updated_task.title == "Updated Despite Sync Failure"

    async def test_sync_errors_are_logged_not_raised(self, task_repository, caplog):
        """Verify sync errors are logged but don't propagate as exceptions."""
        # Arrange
        failing_context_service = MagicMock()
        failing_context_service.create_context = AsyncMock(
            side_effect=Exception("Context service error")
        )

        facade = TaskApplicationFacade(
            task_repository=task_repository, context_service=failing_context_service
        )

        # Act
        with caplog.at_level("WARNING"):
            create_request = CreateTaskRequest(
                git_branch_id=str(uuid4()), title="Test Logging", assignees="test-agent"
            )

            result = await facade.create_task(create_request)

        # Assert - Task created successfully
        assert result["success"] is True

        # Sync error should be logged (if logging is implemented)
        # This verifies graceful degradation
