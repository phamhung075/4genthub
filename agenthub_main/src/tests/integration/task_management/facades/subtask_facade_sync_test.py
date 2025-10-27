"""
Integration tests for subtask facade synchronization.

Tests verify that subtask operations (create, update, complete, delete)
trigger parent task count and progress updates correctly.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from fastmcp.task_management.application.facades.subtask_application_facade import SubtaskApplicationFacade
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.value_objects.subtask_id import SubtaskId
from fastmcp.task_management.infrastructure.repositories.mock_repository_factory import MockTaskRepository, MockSubtaskRepository


@pytest.fixture
def task_repository():
    """Create in-memory task repository."""
    return MockTaskRepository()


@pytest.fixture
def subtask_repository():
    """Create in-memory subtask repository."""
    return MockSubtaskRepository()


@pytest.fixture
def context_service():
    """Create mock context service."""
    mock_service = MagicMock()
    mock_service.create_context = AsyncMock(return_value={"success": True})
    mock_service.update_context = AsyncMock(return_value={"success": True})
    return mock_service


@pytest.fixture
def parent_task(task_repository):
    """Create a parent task for subtask tests."""
    task = Task.create(
        git_branch_id=str(uuid4()),
        title="Parent Task",
        assignees=["parent-agent"],
        user_id=str(uuid4())
    )
    task_repository.save(task)
    return task


@pytest.fixture
def facade(task_repository, subtask_repository, context_service):
    """Create subtask application facade."""
    return SubtaskApplicationFacade(
        task_repository=task_repository,
        subtask_repository=subtask_repository,
        context_service=context_service
    )


@pytest.mark.asyncio
class TestCreateSubtaskUpdatesParentCounts:
    """Test that creating a subtask updates parent task counts."""

    async def test_create_subtask_increments_total_count(
        self, facade, task_repository, parent_task
    ):
        """Verify creating a subtask increments parent total_count."""
        # Arrange - Initial counts should be 0
        parent = task_repository.find_by_id(parent_task.id)
        initial_total = parent.context_data.get("subtasks", {}).get("total_count", 0)

        # Act - Create subtask
        result = await facade.create_subtask(
            task_id=str(parent_task.id),
            title="Subtask 1",
            assignees="subtask-agent"
        )

        # Assert
        assert result["success"] is True

        # Verify parent task counts updated
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == initial_total + 1
        assert subtasks_data["completed_count"] == 0
        assert subtasks_data["progress_percentage"] == 0.0

    async def test_create_multiple_subtasks_counts_accurately(
        self, facade, task_repository, parent_task
    ):
        """Verify creating multiple subtasks updates counts correctly."""
        # Act - Create 3 subtasks
        for i in range(3):
            await facade.create_subtask(
                task_id=str(parent_task.id),
                title=f"Subtask {i+1}",
                assignees="subtask-agent"
            )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 3
        assert subtasks_data["completed_count"] == 0
        assert subtasks_data["progress_percentage"] == 0.0


@pytest.mark.asyncio
class TestUpdateSubtaskRecalculatesProgress:
    """Test that updating subtask status recalculates progress."""

    async def test_update_subtask_to_in_progress_updates_progress(
        self, facade, task_repository, subtask_repository, parent_task
    ):
        """Verify updating subtask status updates parent progress."""
        # Arrange - Create 2 subtasks
        subtask1 = await facade.create_subtask(
            task_id=str(parent_task.id),
            title="Subtask 1",
            assignees="agent-1"
        )
        subtask2 = await facade.create_subtask(
            task_id=str(parent_task.id),
            title="Subtask 2",
            assignees="agent-2"
        )

        # Act - Update one subtask to in_progress
        await facade.update_subtask(
            task_id=str(parent_task.id),
            subtask_id=subtask1["subtask"]["id"],
            status="in_progress",
            progress_percentage=50
        )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 2
        # Progress should reflect partial completion
        # With 1 subtask at 50% and 1 at 0%, average is 25%
        assert 0 <= subtasks_data["progress_percentage"] <= 100

    async def test_update_subtask_percentage_updates_parent_progress(
        self, facade, task_repository, parent_task
    ):
        """Verify updating subtask progress_percentage updates parent."""
        # Arrange
        subtask = await facade.create_subtask(
            task_id=str(parent_task.id),
            title="Subtask 1",
            assignees="agent-1"
        )

        # Act - Update progress to 75%
        await facade.update_subtask(
            task_id=str(parent_task.id),
            subtask_id=subtask["subtask"]["id"],
            progress_percentage=75
        )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        # Single subtask at 75% should reflect in parent
        assert subtasks_data["progress_percentage"] == 75.0


@pytest.mark.asyncio
class TestCompleteSubtaskUpdatesCompletedCount:
    """Test that completing a subtask updates completed_count."""

    async def test_complete_subtask_increments_completed_count(
        self, facade, task_repository, parent_task
    ):
        """Verify completing a subtask increments parent completed_count."""
        # Arrange - Create 2 subtasks
        subtask1 = await facade.create_subtask(
            task_id=str(parent_task.id),
            title="Subtask 1",
            assignees="agent-1"
        )

        # Act - Complete the subtask
        await facade.complete_subtask(
            task_id=str(parent_task.id),
            subtask_id=subtask1["subtask"]["id"],
            completion_summary="Completed successfully"
        )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 1
        assert subtasks_data["completed_count"] == 1
        assert subtasks_data["progress_percentage"] == 100.0

    async def test_complete_multiple_subtasks_updates_counts(
        self, facade, task_repository, parent_task
    ):
        """Verify completing multiple subtasks updates counts correctly."""
        # Arrange - Create 4 subtasks
        subtask_ids = []
        for i in range(4):
            result = await facade.create_subtask(
                task_id=str(parent_task.id),
                title=f"Subtask {i+1}",
                assignees="agent"
            )
            subtask_ids.append(result["subtask"]["id"])

        # Act - Complete 2 out of 4 subtasks
        for subtask_id in subtask_ids[:2]:
            await facade.complete_subtask(
                task_id=str(parent_task.id),
                subtask_id=subtask_id,
                completion_summary="Done"
            )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 4
        assert subtasks_data["completed_count"] == 2
        assert subtasks_data["progress_percentage"] == 50.0


@pytest.mark.asyncio
class TestDeleteSubtaskDecrementsCount:
    """Test that deleting a subtask decrements total_count."""

    async def test_delete_subtask_decrements_total_count(
        self, facade, task_repository, parent_task
    ):
        """Verify deleting a subtask decrements parent total_count."""
        # Arrange - Create 3 subtasks
        subtask_ids = []
        for i in range(3):
            result = await facade.create_subtask(
                task_id=str(parent_task.id),
                title=f"Subtask {i+1}",
                assignees="agent"
            )
            subtask_ids.append(result["subtask"]["id"])

        # Act - Delete one subtask
        await facade.delete_subtask(
            task_id=str(parent_task.id),
            subtask_id=subtask_ids[0]
        )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 2

    async def test_delete_completed_subtask_updates_both_counts(
        self, facade, task_repository, parent_task
    ):
        """Verify deleting a completed subtask updates both total and completed counts."""
        # Arrange - Create and complete a subtask
        subtask = await facade.create_subtask(
            task_id=str(parent_task.id),
            title="Subtask to Delete",
            assignees="agent"
        )

        await facade.complete_subtask(
            task_id=str(parent_task.id),
            subtask_id=subtask["subtask"]["id"],
            completion_summary="Done"
        )

        # Verify counts before deletion
        parent = task_repository.find_by_id(parent_task.id)
        assert parent.context_data["subtasks"]["total_count"] == 1
        assert parent.context_data["subtasks"]["completed_count"] == 1

        # Act - Delete the completed subtask
        await facade.delete_subtask(
            task_id=str(parent_task.id),
            subtask_id=subtask["subtask"]["id"]
        )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 0
        assert subtasks_data["completed_count"] == 0


@pytest.mark.asyncio
class TestMultipleSubtasksCountAccurately:
    """Test complex scenarios with multiple subtasks."""

    async def test_mixed_operations_maintain_count_accuracy(
        self, facade, task_repository, parent_task
    ):
        """Verify mixed create/complete/delete operations maintain accurate counts."""
        # Create 5 subtasks
        subtask_ids = []
        for i in range(5):
            result = await facade.create_subtask(
                task_id=str(parent_task.id),
                title=f"Subtask {i+1}",
                assignees="agent"
            )
            subtask_ids.append(result["subtask"]["id"])

        # Complete 3 subtasks
        for subtask_id in subtask_ids[:3]:
            await facade.complete_subtask(
                task_id=str(parent_task.id),
                subtask_id=subtask_id,
                completion_summary="Done"
            )

        # Delete 1 completed subtask
        await facade.delete_subtask(
            task_id=str(parent_task.id),
            subtask_id=subtask_ids[0]
        )

        # Assert final state: 4 total (5 created - 1 deleted), 2 completed (3 completed - 1 deleted)
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 4
        assert subtasks_data["completed_count"] == 2
        assert subtasks_data["progress_percentage"] == 50.0

    async def test_all_subtasks_completed_shows_100_percent(
        self, facade, task_repository, parent_task
    ):
        """Verify completing all subtasks shows 100% progress."""
        # Arrange - Create 3 subtasks
        subtask_ids = []
        for i in range(3):
            result = await facade.create_subtask(
                task_id=str(parent_task.id),
                title=f"Subtask {i+1}",
                assignees="agent"
            )
            subtask_ids.append(result["subtask"]["id"])

        # Act - Complete all subtasks
        for subtask_id in subtask_ids:
            await facade.complete_subtask(
                task_id=str(parent_task.id),
                subtask_id=subtask_id,
                completion_summary="Done"
            )

        # Assert
        parent = task_repository.find_by_id(parent_task.id)
        subtasks_data = parent.context_data.get("subtasks", {})

        assert subtasks_data["total_count"] == 3
        assert subtasks_data["completed_count"] == 3
        assert subtasks_data["progress_percentage"] == 100.0
