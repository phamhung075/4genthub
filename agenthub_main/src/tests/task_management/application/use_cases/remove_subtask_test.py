"""Test suite for RemoveSubtask use case."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from datetime import datetime

from fastmcp.task_management.application.use_cases.remove_subtask import RemoveSubtaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.shared.domain.value_objects import UUID


class TestRemoveSubtaskUseCase:
    """Test cases for RemoveSubtask use case."""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository."""
        return Mock()
    
    @pytest.fixture
    def mock_subtask_repository(self):
        """Create mock subtask repository."""
        return Mock()
    
    @pytest.fixture
    def use_case(self, mock_task_repository, mock_subtask_repository):
        """Create RemoveSubtaskUseCase instance."""
        return RemoveSubtaskUseCase(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository
        )
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task with subtasks."""
        subtask_ids = [UUID.generate(), UUID.generate(), UUID.generate()]
        return Task(
            id=UUID.generate(),
            title="Parent Task",
            description="Parent task description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            details=None,
            assignees=["user1", "user2"],
            labels=[],
            estimated_effort=None,
            due_date=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            parent_task_id=None,
            dependencies=[],
            blocking_tasks=[],
            subtask_ids=subtask_ids,
            subtask_count=3,
            context_id=None,
            completion_summary=None
        )
    
    @pytest.fixture
    def sample_subtask(self):
        """Create a sample subtask."""
        return Subtask(
            id=UUID.generate(),
            title="Subtask to Remove",
            description="This will be removed",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assignees=["user1"],
            progress_notes="Some progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_execute_remove_subtask_success(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task
    ):
        """Test successful removal of subtask from task."""
        user_id = str(uuid4())
        subtask_to_remove = sample_task.subtask_ids[1]  # Remove middle subtask
        
        # Setup mocks
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.delete = AsyncMock(return_value=True)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        result = await use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=subtask_to_remove.value,
            user_id=user_id
        )
        
        # Verify
        assert result is True
        
        # Check task was fetched
        mock_task_repository.find_by_id.assert_called_once_with(
            UUID(sample_task.id.value),
            user_id=user_id
        )
        
        # Check subtask was deleted
        mock_subtask_repository.delete.assert_called_once_with(
            subtask_to_remove,
            user_id=user_id
        )
        
        # Check task was updated
        mock_task_repository.save.assert_called_once()
        updated_task = mock_task_repository.save.call_args[0][0]
        assert subtask_to_remove not in updated_task.subtask_ids
        assert len(updated_task.subtask_ids) == 2
        assert updated_task.subtask_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_remove_last_subtask(
        self, use_case, mock_task_repository, mock_subtask_repository
    ):
        """Test removing the last subtask from a task."""
        # Task with only one subtask
        single_subtask_id = UUID.generate()
        task_with_one_subtask = Task(
            id=UUID.generate(),
            title="Task with one subtask",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            details=None,
            assignees=["user1"],
            labels=[],
            estimated_effort=None,
            due_date=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            git_branch_id=UUID.generate(),
            project_id=UUID.generate(),
            parent_task_id=None,
            dependencies=[],
            blocking_tasks=[],
            subtask_ids=[single_subtask_id],
            subtask_count=1,
            context_id=None,
            completion_summary=None
        )
        
        mock_task_repository.find_by_id = AsyncMock(return_value=task_with_one_subtask)
        mock_subtask_repository.delete = AsyncMock(return_value=True)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await use_case.execute(
            task_id=task_with_one_subtask.id.value,
            subtask_id=single_subtask_id.value,
            user_id=str(uuid4())
        )
        
        # Verify task now has no subtasks
        updated_task = mock_task_repository.save.call_args[0][0]
        assert len(updated_task.subtask_ids) == 0
        assert updated_task.subtask_count == 0
    
    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, use_case, mock_task_repository):
        """Test removing subtask when task doesn't exist."""
        task_id = str(uuid4())
        subtask_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_task_repository.find_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="Task not found"):
            await use_case.execute(
                task_id=task_id,
                subtask_id=subtask_id,
                user_id=user_id
            )
        
        mock_task_repository.find_by_id.assert_called_once_with(
            UUID(task_id),
            user_id=user_id
        )
    
    @pytest.mark.asyncio
    async def test_execute_subtask_not_in_task(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task
    ):
        """Test removing subtask that doesn't belong to the task."""
        user_id = str(uuid4())
        unrelated_subtask_id = str(uuid4())  # Not in task's subtask_ids
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.delete = AsyncMock(return_value=True)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        result = await use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=unrelated_subtask_id,
            user_id=user_id
        )
        
        # Should still succeed but task remains unchanged
        assert result is True
        
        # Verify task wasn't modified
        updated_task = mock_task_repository.save.call_args[0][0]
        assert len(updated_task.subtask_ids) == 3  # No change
        assert updated_task.subtask_count == 3  # No change
    
    @pytest.mark.asyncio
    async def test_execute_subtask_deletion_fails(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task
    ):
        """Test when subtask deletion fails."""
        user_id = str(uuid4())
        subtask_id = sample_task.subtask_ids[0].value
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.delete = AsyncMock(return_value=False)
        
        # Execute
        result = await use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=subtask_id,
            user_id=user_id
        )
        
        # Should return False
        assert result is False
        
        # Task should not be saved when deletion fails
        mock_task_repository.save.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_updates_task_timestamp(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task
    ):
        """Test that removing subtask updates task's updated_at timestamp."""
        original_updated_at = sample_task.updated_at
        subtask_id = sample_task.subtask_ids[0].value
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.delete = AsyncMock(return_value=True)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=subtask_id,
            user_id=str(uuid4())
        )
        
        # Verify timestamp was updated
        updated_task = mock_task_repository.save.call_args[0][0]
        assert updated_task.updated_at > original_updated_at
    
    @pytest.mark.asyncio
    async def test_execute_maintains_subtask_order(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task
    ):
        """Test that removing subtask maintains order of remaining subtasks."""
        original_ids = [sid.value for sid in sample_task.subtask_ids]
        subtask_to_remove = sample_task.subtask_ids[1]  # Remove middle one
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.delete = AsyncMock(return_value=True)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await use_case.execute(
            task_id=sample_task.id.value,
            subtask_id=subtask_to_remove.value,
            user_id=str(uuid4())
        )
        
        # Verify order is maintained
        updated_task = mock_task_repository.save.call_args[0][0]
        remaining_ids = [sid.value for sid in updated_task.subtask_ids]
        
        assert remaining_ids == [original_ids[0], original_ids[2]]