"""Test suite for AutomatedContextSyncService.

Tests for automated context synchronization across task and subtask operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any, List

from fastmcp.task_management.application.services.automated_context_sync_service import AutomatedContextSyncService
from fastmcp.task_management.application.services.task_context_sync_service import TaskContextSyncService
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId


class TestAutomatedContextSyncServiceInit:
    """Test AutomatedContextSyncService initialization."""

    def test_initialization_with_minimal_dependencies(self):
        """Test service initialization with minimal dependencies."""
        mock_task_repo = Mock(spec=TaskRepository)
        
        service = AutomatedContextSyncService(mock_task_repo)
        
        assert service._task_repository == mock_task_repo
        assert service._subtask_repository is None
        assert service._user_id is None
        assert service._context_sync_service is not None

    def test_initialization_with_all_dependencies(self):
        """Test service initialization with all dependencies."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        user_id = "test_user_123"
        
        service = AutomatedContextSyncService(
            mock_task_repo, 
            mock_subtask_repo, 
            user_id
        )
        
        assert service._task_repository == mock_task_repo
        assert service._subtask_repository == mock_subtask_repo
        assert service._user_id == user_id

    def test_with_user_method(self):
        """Test with_user method creates new instance with user context."""
        mock_task_repo = Mock(spec=TaskRepository)
        original_service = AutomatedContextSyncService(mock_task_repo)
        user_id = "test_user_456"
        
        user_scoped_service = original_service.with_user(user_id)
        
        assert user_scoped_service._user_id == user_id
        assert user_scoped_service is not original_service
        assert isinstance(user_scoped_service, AutomatedContextSyncService)

    def test_get_user_scoped_repository_with_with_user_method(self):
        """Test _get_user_scoped_repository with repository that has with_user method."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, user_id="test_user")
        
        mock_repo = Mock()
        mock_user_scoped_repo = Mock()
        mock_repo.with_user.return_value = mock_user_scoped_repo
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_user_scoped_repo
        mock_repo.with_user.assert_called_once_with("test_user")


    def test_get_user_scoped_repository_no_user_context(self):
        """Test _get_user_scoped_repository returns original repo when no user context."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)  # No user_id
        mock_repo = Mock()
        
        result = service._get_user_scoped_repository(mock_repo)
        
        assert result == mock_repo


class TestTaskContextSynchronization:
    """Test task-level context synchronization."""

    @pytest.mark.asyncio
    async def test_sync_task_context_after_update_success(self):
        """Test successful task context synchronization."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        # Mock the context sync service
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.return_value = {"success": True}
        
        # Create mock task
        mock_task = Mock(spec=Task)
        mock_task.id = TaskId.generate_new()
        mock_task.git_branch_id = "branch_123"
        mock_task.project_id = "project_456"
        
        result = await service.sync_task_context_after_update(mock_task, "update")
        
        assert result is True
        service._context_sync_service.sync_context_and_get_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_task_context_after_update_with_task_id_value_object(self):
        """Test sync with task ID that has value attribute."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.return_value = {"success": True}
        
        # Create mock task with value object ID
        mock_task = Mock(spec=Task)
        mock_task_id = Mock()
        mock_task_id.value = "task_uuid_123"
        mock_task.id = mock_task_id
        mock_task.git_branch_id = "branch_123"
        mock_task.project_id = "project_456"
        
        result = await service.sync_task_context_after_update(mock_task, "create")
        
        assert result is True
        # Verify the call was made with string version of ID
        call_args = service._context_sync_service.sync_context_and_get_task.call_args
        assert call_args[1]["task_id"] == "task_uuid_123"

    @pytest.mark.asyncio
    async def test_sync_task_context_after_update_failure(self):
        """Test task context synchronization failure."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.return_value = None
        
        mock_task = Mock(spec=Task)
        mock_task.id = "task_123"
        mock_task.git_branch_id = "branch_123"
        mock_task.project_id = "project_456"
        
        with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
            result = await service.sync_task_context_after_update(mock_task, "update")
            
            assert result is False
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_sync_task_context_after_update_exception(self):
        """Test task context synchronization with exception."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.side_effect = Exception("Sync failed")
        
        mock_task = Mock(spec=Task)
        mock_task.id = "task_123"
        
        with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
            result = await service.sync_task_context_after_update(mock_task, "update")
            
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_sync_task_context_with_defaults(self):
        """Test sync with default values when task attributes are missing."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.return_value = {"success": True}
        
        # Create mock task with project_id but without git_branch_id
        mock_task = Mock(spec=Task)
        mock_task.id = "task_123"
        mock_task.project_id = "project_456"  # project_id is now required
        # Don't set git_branch_id attribute
        
        result = await service.sync_task_context_after_update(mock_task, "update")
        
        assert result is True
        call_args = service._context_sync_service.sync_context_and_get_task.call_args[1]
        assert call_args["project_id"] == "project_456"
        assert call_args["git_branch_name"] == "main"

    @pytest.mark.asyncio
    async def test_sync_task_context_without_project_id_fails(self):
        """Test sync fails when project_id is missing."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        
        # Create mock task without project_id
        mock_task = Mock(spec=Task)
        mock_task.id = "task_123"
        # Don't set project_id attribute - this should cause failure
        
        with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
            result = await service.sync_task_context_after_update(mock_task, "update")
            
            assert result is False
            mock_logger.error.assert_called()
            # Verify the error message mentions project_id requirement
            error_call = mock_logger.error.call_args[0][0]
            assert "project_id is required" in error_call

    def test_sync_task_context_after_update_sync_wrapper_in_async_context(self):
        """Test synchronous wrapper when already in async context."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        mock_task = Mock(spec=Task)
        mock_task.id = "task_123"
        
        # Mock the running event loop check
        with patch('asyncio.get_running_loop'):
            with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
                result = service.sync_task_context_after_update_sync(mock_task, "update")
                
                assert result is True
                mock_logger.info.assert_called()

    def test_sync_task_context_after_update_sync_wrapper_no_loop(self):
        """Test synchronous wrapper when no event loop exists."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        mock_task = Mock(spec=Task)
        mock_task.id = "task_123"
        
        # Mock no running event loop
        with patch('asyncio.get_running_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = True
                
                result = service.sync_task_context_after_update_sync(mock_task, "update")
                
                assert result is True
                mock_run.assert_called_once()

    def test_sync_task_context_after_update_sync_wrapper_exception(self):
        """Test synchronous wrapper exception handling."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        mock_task = Mock(spec=Task)
        mock_task.id = "task_123"
        
        with patch('asyncio.get_running_loop', side_effect=Exception("Unexpected error")):
            with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
                result = service.sync_task_context_after_update_sync(mock_task, "update")
                
                assert result is False
                mock_logger.warning.assert_called()


class TestSubtaskContextSynchronization:
    """Test subtask-level context synchronization."""

    @pytest.mark.asyncio
    async def test_sync_parent_context_after_subtask_update_success(self):
        """Test successful parent context sync after subtask update."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, mock_subtask_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.return_value = {"success": True}
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        mock_parent_task.project_id = "project_456"  # Add required project_id
        mock_subtask = Mock(spec=Subtask)
        
        # Mock progress calculation
        with patch.object(service, '_calculate_subtask_progress') as mock_calc:
            mock_calc.return_value = {"progress_percentage": 50}
            
            result = await service.sync_parent_context_after_subtask_update(
                mock_parent_task, mock_subtask, "subtask_update"
            )
            
            assert result is True
            mock_calc.assert_called_once_with(mock_parent_task)

    @pytest.mark.asyncio
    async def test_sync_parent_context_after_subtask_update_no_subtask_repo(self):
        """Test parent context sync when no subtask repository available."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)  # No subtask repo
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.return_value = {"success": True}
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        mock_parent_task.project_id = "project_456"  # Add required project_id
        
        result = await service.sync_parent_context_after_subtask_update(mock_parent_task)
        
        assert result is True
        # Should still sync parent context even without subtask progress

    @pytest.mark.asyncio
    async def test_sync_parent_context_after_subtask_update_exception(self):
        """Test parent context sync exception handling."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.side_effect = Exception("Sync failed")
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        mock_parent_task.project_id = "project_456"  # Add required project_id
        
        with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
            result = await service.sync_parent_context_after_subtask_update(mock_parent_task)
            
            assert result is False
            mock_logger.error.assert_called()

    def test_sync_parent_context_after_subtask_update_sync_wrapper(self):
        """Test synchronous wrapper for parent context sync."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        
        # Mock no running event loop
        with patch('asyncio.get_running_loop', side_effect=RuntimeError("No loop")):
            with patch('asyncio.run') as mock_run:
                mock_run.return_value = True
                
                result = service.sync_parent_context_after_subtask_update_sync(mock_parent_task)
                
                assert result is True
                mock_run.assert_called_once()


class TestProgressCalculation:
    """Test subtask progress calculation and aggregation."""

    @pytest.mark.asyncio
    async def test_calculate_subtask_progress_no_repository(self):
        """Test progress calculation when no subtask repository available."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)  # No subtask repo
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        
        result = await service._calculate_subtask_progress(mock_parent_task)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_calculate_subtask_progress_no_subtasks(self):
        """Test progress calculation when no subtasks exist."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, mock_subtask_repo)
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        mock_subtask_repo.find_by_parent_task_id.return_value = []
        
        result = await service._calculate_subtask_progress(mock_parent_task)
        
        expected = {
            "total_subtasks": 0,
            "completed_subtasks": 0,
            "progress_percentage": 100,
            "can_complete_parent": True
        }
        
        assert result == expected

    @pytest.mark.asyncio
    async def test_calculate_subtask_progress_with_subtasks(self):
        """Test progress calculation with mixed subtask completion."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, mock_subtask_repo)
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        
        # Create mock subtasks - 2 completed, 3 incomplete
        mock_subtasks = []
        for i in range(5):
            subtask = Mock(spec=Subtask)
            subtask.is_completed = i < 2  # First 2 are completed
            mock_subtasks.append(subtask)
        
        mock_subtask_repo.find_by_parent_task_id.return_value = mock_subtasks
        
        result = await service._calculate_subtask_progress(mock_parent_task)
        
        assert result["total_subtasks"] == 5
        assert result["completed_subtasks"] == 2
        assert result["incomplete_subtasks"] == 3
        assert result["progress_percentage"] == 40.0  # 2/5 = 40%
        assert result["can_complete_parent"] is False
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_calculate_subtask_progress_all_completed(self):
        """Test progress calculation when all subtasks are completed."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, mock_subtask_repo)
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        
        # Create mock subtasks - all completed
        mock_subtasks = []
        for i in range(3):
            subtask = Mock(spec=Subtask)
            subtask.is_completed = True
            mock_subtasks.append(subtask)
        
        mock_subtask_repo.find_by_parent_task_id.return_value = mock_subtasks
        
        result = await service._calculate_subtask_progress(mock_parent_task)
        
        assert result["total_subtasks"] == 3
        assert result["completed_subtasks"] == 3
        assert result["progress_percentage"] == 100.0
        assert result["can_complete_parent"] is True

    @pytest.mark.asyncio
    async def test_calculate_subtask_progress_exception(self):
        """Test progress calculation exception handling."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, mock_subtask_repo)
        
        mock_parent_task = Mock(spec=Task)
        mock_parent_task.id = "parent_task_123"
        mock_subtask_repo.find_by_parent_task_id.side_effect = Exception("Database error")
        
        with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
            result = await service._calculate_subtask_progress(mock_parent_task)
            
            assert result is None
            mock_logger.error.assert_called()


class TestBatchOperations:
    """Test batch synchronization operations."""

    @pytest.mark.asyncio
    async def test_sync_multiple_tasks_success(self):
        """Test successful batch synchronization of multiple tasks."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
        service._context_sync_service.sync_context_and_get_task.return_value = {"success": True}
        
        # Mock tasks
        mock_tasks = []
        task_ids = ["task_1", "task_2", "task_3"]
        for task_id in task_ids:
            mock_task = Mock(spec=Task)
            mock_task.id = task_id
            mock_task.project_id = "project_456"  # Add required project_id
            mock_tasks.append(mock_task)
        
        # Mock repository responses
        with patch('fastmcp.task_management.domain.value_objects.task_id.TaskId') as mock_task_id:
            mock_task_repo.find_by_id.side_effect = mock_tasks
            
            results = await service.sync_multiple_tasks(task_ids)
            
            assert len(results) == 3
            assert all(results[task_id] for task_id in task_ids)

    @pytest.mark.asyncio
    async def test_sync_multiple_tasks_some_not_found(self):
        """Test batch sync with some tasks not found."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        task_ids = ["task_1", "task_2", "task_3"]
        
        # Mock repository responses - task_2 not found
        def mock_find_by_id(task_id):
            if str(task_id) == "task_2":
                return None
            mock_task = Mock(spec=Task)
            mock_task.id = str(task_id)
            mock_task.project_id = "project_456"  # Add required project_id
            return mock_task
        
        with patch('fastmcp.task_management.domain.value_objects.task_id.TaskId') as mock_task_id:
            mock_task_id.from_string.side_effect = lambda x: x  # Return task_id as-is
            mock_task_repo.find_by_id.side_effect = mock_find_by_id
            
            service._context_sync_service = AsyncMock(spec=TaskContextSyncService)
            service._context_sync_service.sync_context_and_get_task.return_value = {"success": True}
            
            with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
                results = await service.sync_multiple_tasks(task_ids)
                
                assert results["task_1"] is True
                assert results["task_2"] is False
                assert results["task_3"] is True
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_sync_multiple_tasks_with_exceptions(self):
        """Test batch sync with some tasks throwing exceptions."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        task_ids = ["task_1", "task_2"]
        
        with patch('fastmcp.task_management.domain.value_objects.task_id.TaskId') as mock_task_id:
            mock_task_id.from_string.side_effect = Exception("Invalid task ID")
            
            with patch('fastmcp.task_management.application.services.automated_context_sync_service.logger') as mock_logger:
                results = await service.sync_multiple_tasks(task_ids)
                
                assert all(not result for result in results.values())
                assert mock_logger.error.call_count == 2


class TestServiceHealthAndMonitoring:
    """Test service health and monitoring functionality."""

    def test_get_sync_statistics(self):
        """Test getting synchronization statistics."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, mock_subtask_repo)
        
        stats = service.get_sync_statistics()
        
        assert stats["service_status"] == "active"
        assert stats["sync_service_available"] is True
        assert stats["subtask_repository_available"] is True
        assert "last_health_check" in stats
        assert stats["features"]["task_context_sync"] is True
        assert stats["features"]["subtask_parent_sync"] is True
        assert stats["features"]["batch_operations"] is True
        assert stats["features"]["progress_calculation"] is True

    def test_get_sync_statistics_minimal_setup(self):
        """Test statistics with minimal service setup."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)  # No subtask repo
        
        stats = service.get_sync_statistics()
        
        assert stats["subtask_repository_available"] is False
        assert stats["features"]["subtask_parent_sync"] is False
        assert stats["features"]["progress_calculation"] is False

    def test_validate_sync_configuration_valid(self):
        """Test configuration validation with valid setup."""
        mock_task_repo = Mock(spec=TaskRepository)
        mock_subtask_repo = Mock(spec=SubtaskRepository)
        service = AutomatedContextSyncService(mock_task_repo, mock_subtask_repo)
        
        with patch('asyncio.get_event_loop'):
            validation = service.validate_sync_configuration()
            
            assert validation["is_valid"] is True
            assert len(validation["issues"]) == 0
            assert validation["async_support"] is True
            assert "validation_timestamp" in validation

    def test_validate_sync_configuration_missing_task_repo(self):
        """Test configuration validation with missing task repository."""
        service = AutomatedContextSyncService(None)
        
        validation = service.validate_sync_configuration()
        
        assert validation["is_valid"] is False
        assert "Task repository not configured" in validation["issues"]
        assert len(validation["recommendations"]) > 0

    def test_validate_sync_configuration_no_async_support(self):
        """Test configuration validation without async support."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        
        with patch('asyncio.get_event_loop', side_effect=Exception("No event loop")):
            validation = service.validate_sync_configuration()
            
            assert "Asyncio event loop not available" in validation["issues"]
            assert validation["async_support"] is False

    def test_validate_sync_configuration_no_context_sync_service(self):
        """Test configuration validation without context sync service."""
        mock_task_repo = Mock(spec=TaskRepository)
        service = AutomatedContextSyncService(mock_task_repo)
        service._context_sync_service = None
        
        validation = service.validate_sync_configuration()
        
        assert validation["is_valid"] is False
        assert "Context sync service not available" in validation["issues"]