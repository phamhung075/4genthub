"""Test suite for AddSubtask use case."""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from datetime import datetime

from fastmcp.task_management.application.use_cases.add_subtask import AddSubtaskUseCase
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.value_objects.task_status import TaskStatus
from fastmcp.task_management.domain.value_objects.priority import Priority
from fastmcp.shared.domain.value_objects import UUID


class TestAddSubtaskUseCase:
    """Test cases for AddSubtask use case."""
    
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
        """Create AddSubtaskUseCase instance."""
        return AddSubtaskUseCase(
            task_repository=mock_task_repository,
            subtask_repository=mock_subtask_repository
        )
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task."""
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
            subtask_ids=[],
            subtask_count=0,
            context_id=None,
            completion_summary=None
        )
    
    @pytest.fixture
    def sample_subtask(self):
        """Create a sample subtask."""
        return Subtask(
            id=UUID.generate(),
            title="New Subtask",
            description="Subtask description",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assignees=["user1"],
            progress_notes="Initial progress",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_execute_add_subtask_success(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task, sample_subtask
    ):
        """Test successful addition of subtask to task."""
        task_id = sample_task.id.value
        user_id = str(uuid4())
        
        # Setup mocks
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.save = AsyncMock(return_value=sample_subtask)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        result = await use_case.execute(
            task_id=task_id,
            subtask=sample_subtask,
            user_id=user_id
        )
        
        # Verify
        assert result == sample_subtask
        
        # Check task was fetched
        mock_task_repository.find_by_id.assert_called_once_with(
            UUID(task_id),
            user_id=user_id
        )
        
        # Check subtask was saved
        mock_subtask_repository.save.assert_called_once()
        saved_subtask = mock_subtask_repository.save.call_args[0][0]
        assert saved_subtask.task_id.value == task_id
        
        # Check task was updated
        mock_task_repository.save.assert_called_once()
        updated_task = mock_task_repository.save.call_args[0][0]
        assert sample_subtask.id.value in [sid.value for sid in updated_task.subtask_ids]
        assert updated_task.subtask_count == 1
    
    @pytest.mark.asyncio
    async def test_execute_add_multiple_subtasks(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task
    ):
        """Test adding multiple subtasks updates count correctly."""
        # Start with task having 2 subtasks
        existing_subtask_ids = [UUID.generate(), UUID.generate()]
        sample_task.subtask_ids = existing_subtask_ids
        sample_task.subtask_count = 2
        
        new_subtask = Subtask(
            id=UUID.generate(),
            title="Third Subtask",
            description="Another subtask",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            assignees=["user3"],
            progress_notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.save = AsyncMock(return_value=new_subtask)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await use_case.execute(
            task_id=sample_task.id.value,
            subtask=new_subtask,
            user_id=str(uuid4())
        )
        
        # Verify task now has 3 subtasks
        updated_task = mock_task_repository.save.call_args[0][0]
        assert len(updated_task.subtask_ids) == 3
        assert updated_task.subtask_count == 3
        assert new_subtask.id in updated_task.subtask_ids
    
    @pytest.mark.asyncio
    async def test_execute_task_not_found(self, use_case, mock_task_repository, sample_subtask):
        """Test adding subtask when task doesn't exist."""
        task_id = str(uuid4())
        user_id = str(uuid4())
        
        mock_task_repository.find_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="Task not found"):
            await use_case.execute(
                task_id=task_id,
                subtask=sample_subtask,
                user_id=user_id
            )
        
        mock_task_repository.find_by_id.assert_called_once_with(
            UUID(task_id),
            user_id=user_id
        )
    
    @pytest.mark.asyncio
    async def test_execute_subtask_inherits_task_assignees(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task
    ):
        """Test that subtask inherits parent task assignees if not specified."""
        # Subtask with empty assignees
        subtask_no_assignees = Subtask(
            id=UUID.generate(),
            title="Subtask without assignees",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assignees=[],
            progress_notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.save = AsyncMock(return_value=subtask_no_assignees)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await use_case.execute(
            task_id=sample_task.id.value,
            subtask=subtask_no_assignees,
            user_id=str(uuid4())
        )
        
        # Verify subtask was saved with parent's assignees
        saved_subtask = mock_subtask_repository.save.call_args[0][0]
        assert saved_subtask.assignees == sample_task.assignees
    
    @pytest.mark.asyncio
    async def test_execute_duplicate_subtask_prevention(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task, sample_subtask
    ):
        """Test that duplicate subtask IDs are not added."""
        # Task already has the subtask
        sample_task.subtask_ids = [sample_subtask.id]
        sample_task.subtask_count = 1
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.save = AsyncMock(return_value=sample_subtask)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await use_case.execute(
            task_id=sample_task.id.value,
            subtask=sample_subtask,
            user_id=str(uuid4())
        )
        
        # Verify count didn't increase
        updated_task = mock_task_repository.save.call_args[0][0]
        assert len(updated_task.subtask_ids) == 1
        assert updated_task.subtask_count == 1
    
    @pytest.mark.asyncio
    async def test_execute_updates_task_timestamp(
        self, use_case, mock_task_repository, mock_subtask_repository, sample_task, sample_subtask
    ):
        """Test that adding subtask updates task's updated_at timestamp."""
        original_updated_at = sample_task.updated_at
        
        mock_task_repository.find_by_id = AsyncMock(return_value=sample_task)
        mock_subtask_repository.save = AsyncMock(return_value=sample_subtask)
        mock_task_repository.save = AsyncMock()
        
        # Execute
        await use_case.execute(
            task_id=sample_task.id.value,
            subtask=sample_subtask,
            user_id=str(uuid4())
        )
        
        # Verify timestamp was updated
        updated_task = mock_task_repository.save.call_args[0][0]
        assert updated_task.updated_at > original_updated_at