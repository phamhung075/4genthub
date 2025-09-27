"""Unit tests for Branch Statistics Service"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Optional

from fastmcp.task_management.domain.services.branch_statistics_service import (
    BranchStatisticsService,
    BranchStatistics
)


class MockTask:
    """Mock task entity for testing"""
    def __init__(self, id: str, status: str):
        self.id = id
        self.status = status


class MockBranch:
    """Mock branch entity for testing"""
    def __init__(self, id: str, task_count: int = 0, completed_task_count: int = 0, progress_percentage: float = 0.0):
        self.id = id
        self.task_count = task_count
        self.completed_task_count = completed_task_count
        self.progress_percentage = progress_percentage


class TestBranchStatisticsService:
    """Test cases for BranchStatisticsService"""

    @pytest.fixture
    def mock_task_repository(self):
        """Mock task repository"""
        return Mock()

    @pytest.fixture
    def mock_git_branch_repository(self):
        """Mock git branch repository"""
        return Mock()

    @pytest.fixture
    def service(self, mock_task_repository, mock_git_branch_repository):
        """Create service instance with mocks"""
        return BranchStatisticsService(
            task_repository=mock_task_repository,
            git_branch_repository=mock_git_branch_repository
        )

    def test_on_task_created_updates_statistics(self, service, mock_task_repository, mock_git_branch_repository):
        """Test that task creation triggers statistics update"""
        # Arrange
        branch_id = "branch123"
        task_id = "task456"
        status = "todo"
        
        mock_tasks = [
            MockTask("task1", "done"),
            MockTask("task2", "in_progress"),
            MockTask("task3", "todo"),
            MockTask(task_id, status)  # New task
        ]
        mock_task_repository.find_by_git_branch_id.return_value = mock_tasks
        
        mock_branch = MockBranch(branch_id)
        mock_git_branch_repository.get.return_value = mock_branch

        # Act
        service.on_task_created(task_id, branch_id, status)

        # Assert
        mock_task_repository.find_by_git_branch_id.assert_called_once_with(branch_id)
        mock_git_branch_repository.get.assert_called_once_with(branch_id)
        mock_git_branch_repository.update.assert_called_once_with(
            branch_id,
            {
                'task_count': 4,
                'completed_task_count': 1,
                'progress_percentage': 25.0
            }
        )

    def test_on_task_created_without_branch_id_does_nothing(self, service, mock_task_repository):
        """Test that task creation without branch_id is ignored"""
        # Act
        service.on_task_created("task123", None, "todo")

        # Assert
        mock_task_repository.find_by_git_branch_id.assert_not_called()

    def test_on_task_updated_same_branch_status_change(self, service, mock_task_repository, mock_git_branch_repository):
        """Test task status update on same branch"""
        # Arrange
        branch_id = "branch123"
        task_id = "task456"
        
        mock_tasks = [
            MockTask("task1", "done"),
            MockTask(task_id, "done"),  # Updated task
            MockTask("task3", "blocked")
        ]
        mock_task_repository.find_by_git_branch_id.return_value = mock_tasks
        
        mock_branch = MockBranch(branch_id)
        mock_git_branch_repository.get.return_value = mock_branch

        # Act
        service.on_task_updated(
            task_id,
            old_branch_id=branch_id,
            new_branch_id=branch_id,
            old_status="in_progress",
            new_status="done"
        )

        # Assert
        mock_git_branch_repository.update.assert_called_once_with(
            branch_id,
            {
                'task_count': 3,
                'completed_task_count': 2,
                'progress_percentage': 66.66666666666666
            }
        )

    def test_on_task_updated_branch_change(self, service, mock_task_repository, mock_git_branch_repository):
        """Test task moved between branches"""
        # Arrange
        old_branch_id = "branch123"
        new_branch_id = "branch456"
        task_id = "task789"
        
        # Define tasks after the move - task has been moved from old to new branch
        # Old branch no longer has the moved task
        old_branch_tasks = [
            MockTask("task1", "done"),
            MockTask("task2", "todo")
        ]
        
        # New branch now has the moved task  
        new_branch_tasks = [
            MockTask("task3", "done"),
            MockTask("task4", "in_progress"),
            MockTask(task_id, "todo")  # Moved task
        ]
        
        # Setup mock to return different results based on branch_id parameter
        def find_tasks_side_effect(branch_id):
            if branch_id == old_branch_id:
                return old_branch_tasks
            elif branch_id == new_branch_id:
                return new_branch_tasks
            else:
                return []
        
        mock_task_repository.find_by_git_branch_id.side_effect = find_tasks_side_effect
        
        mock_branch = MockBranch("dummy")
        mock_git_branch_repository.get.return_value = mock_branch

        # Act
        service.on_task_updated(
            task_id,
            old_branch_id=old_branch_id,
            new_branch_id=new_branch_id,
            old_status="todo",
            new_status="todo"
        )

        # Assert - both branches should be updated
        assert mock_git_branch_repository.update.call_count == 2
        
        # Since branches are processed in a set, order is not guaranteed
        # Check that both branches were updated with correct values
        update_calls = {
            call[0][0]: call[0][1]  # branch_id: updates dict
            for call in mock_git_branch_repository.update.call_args_list
        }
        
        # Check old branch update (task removed, so only 2 tasks remain)
        assert old_branch_id in update_calls
        assert update_calls[old_branch_id]['task_count'] == 2
        assert update_calls[old_branch_id]['completed_task_count'] == 1
        assert update_calls[old_branch_id]['progress_percentage'] == 50.0
        
        # Check new branch update (task added, so 3 tasks total)
        assert new_branch_id in update_calls
        assert update_calls[new_branch_id]['task_count'] == 3
        assert update_calls[new_branch_id]['completed_task_count'] == 1
        assert update_calls[new_branch_id]['progress_percentage'] == 33.33333333333333

    def test_on_task_deleted(self, service, mock_task_repository, mock_git_branch_repository):
        """Test task deletion updates statistics"""
        # Arrange
        branch_id = "branch123"
        deleted_task_id = "task456"
        
        # Remaining tasks after deletion
        mock_tasks = [
            MockTask("task1", "done"),
            MockTask("task3", "blocked")
        ]
        mock_task_repository.find_by_git_branch_id.return_value = mock_tasks
        
        mock_branch = MockBranch(branch_id)
        mock_git_branch_repository.get.return_value = mock_branch

        # Act
        service.on_task_deleted(deleted_task_id, branch_id, "todo")

        # Assert
        mock_git_branch_repository.update.assert_called_once_with(
            branch_id,
            {
                'task_count': 2,
                'completed_task_count': 1,
                'progress_percentage': 50.0
            }
        )

    def test_recalculate_branch_statistics(self, service, mock_task_repository, mock_git_branch_repository):
        """Test direct recalculation of branch statistics"""
        # Arrange
        branch_id = "branch123"
        
        mock_tasks = [
            MockTask("task1", "done"),
            MockTask("task2", "done"),
            MockTask("task3", "in_progress"),
            MockTask("task4", "blocked"),
            MockTask("task5", "todo")
        ]
        mock_task_repository.find_by_git_branch_id.return_value = mock_tasks
        
        mock_branch = MockBranch(branch_id)
        mock_git_branch_repository.get.return_value = mock_branch

        # Act
        stats = service._recalculate_branch_statistics(branch_id)

        # Assert
        assert stats.branch_id == branch_id
        assert stats.task_count == 5
        assert stats.completed_task_count == 2
        assert stats.in_progress_count == 1
        assert stats.blocked_count == 1
        assert stats.progress_percentage == 40.0

    def test_recalculate_branch_statistics_empty_branch(self, service, mock_task_repository, mock_git_branch_repository):
        """Test statistics for branch with no tasks"""
        # Arrange
        branch_id = "branch123"
        mock_task_repository.find_by_git_branch_id.return_value = []
        
        mock_branch = MockBranch(branch_id)
        mock_git_branch_repository.get.return_value = mock_branch

        # Act
        stats = service._recalculate_branch_statistics(branch_id)

        # Assert
        assert stats.task_count == 0
        assert stats.completed_task_count == 0
        assert stats.progress_percentage == 0.0

    def test_recalculate_branch_statistics_branch_not_found(self, service, mock_task_repository, mock_git_branch_repository):
        """Test statistics calculation when branch not found"""
        # Arrange
        branch_id = "nonexistent"
        mock_task_repository.find_by_git_branch_id.return_value = []
        mock_git_branch_repository.get.return_value = None

        # Act
        stats = service._recalculate_branch_statistics(branch_id)

        # Assert
        mock_git_branch_repository.update.assert_not_called()
        assert stats.branch_id == branch_id
        assert stats.task_count == 0

    def test_recalculate_all_branches_with_project_id(self, service, mock_task_repository, mock_git_branch_repository):
        """Test recalculating statistics for all branches in a project"""
        # Arrange
        project_id = "project123"
        
        mock_branches = [
            MockBranch("branch1"),
            MockBranch("branch2")
        ]
        mock_git_branch_repository.find_by_project_id.return_value = mock_branches
        
        # Mock tasks for each branch
        branch1_tasks = [MockTask("task1", "done")]
        branch2_tasks = [MockTask("task2", "in_progress"), MockTask("task3", "done")]
        
        mock_task_repository.find_by_git_branch_id.side_effect = [
            branch1_tasks,
            branch2_tasks
        ]
        
        mock_git_branch_repository.get.return_value = MockBranch("dummy")

        # Act
        results = service.recalculate_all_branches(project_id)

        # Assert
        assert len(results) == 2
        assert results["branch1"].task_count == 1
        assert results["branch1"].completed_task_count == 1
        assert results["branch1"].progress_percentage == 100.0
        
        assert results["branch2"].task_count == 2
        assert results["branch2"].completed_task_count == 1
        assert results["branch2"].progress_percentage == 50.0

    def test_recalculate_all_branches_without_project_id(self, service, mock_task_repository, mock_git_branch_repository):
        """Test recalculating statistics for all branches globally"""
        # Arrange
        mock_branches = [
            MockBranch("branch1"),
            MockBranch("branch2"),
            MockBranch("branch3")
        ]
        mock_git_branch_repository.get_all.return_value = mock_branches
        
        # Mock same tasks for simplicity
        mock_tasks = [MockTask("task1", "done")]
        mock_task_repository.find_by_git_branch_id.return_value = mock_tasks
        mock_git_branch_repository.get.return_value = MockBranch("dummy")

        # Act
        results = service.recalculate_all_branches()

        # Assert
        assert len(results) == 3
        mock_git_branch_repository.find_by_project_id.assert_not_called()
        mock_git_branch_repository.get_all.assert_called_once()

    def test_recalculate_all_branches_handles_exceptions(self, service, mock_task_repository, mock_git_branch_repository):
        """Test that exceptions in one branch don't stop processing others"""
        # Arrange
        mock_branches = [
            MockBranch("branch1"),
            MockBranch("branch2"),
            MockBranch("branch3")
        ]
        mock_git_branch_repository.get_all.return_value = mock_branches
        
        # First branch fails, others succeed
        mock_task_repository.find_by_git_branch_id.side_effect = [
            Exception("Database error"),
            [MockTask("task2", "done")],
            [MockTask("task3", "todo")]
        ]
        
        mock_git_branch_repository.get.return_value = MockBranch("dummy")

        # Act
        results = service.recalculate_all_branches()

        # Assert
        assert len(results) == 2  # Only successful branches
        assert "branch1" not in results
        assert "branch2" in results
        assert "branch3" in results

    def test_get_branch_statistics(self, service, mock_task_repository, mock_git_branch_repository):
        """Test getting current statistics for a branch"""
        # Arrange
        branch_id = "branch123"
        
        mock_branch = MockBranch(branch_id)
        mock_git_branch_repository.get.return_value = mock_branch
        
        mock_tasks = [
            MockTask("task1", "done"),
            MockTask("task2", "done"),
            MockTask("task3", "in_progress"),
            MockTask("task4", "blocked"),
            MockTask("task5", "todo")
        ]
        mock_task_repository.find_by_git_branch_id.return_value = mock_tasks

        # Act
        stats = service.get_branch_statistics(branch_id)

        # Assert
        assert stats is not None
        assert stats.branch_id == branch_id
        assert stats.task_count == 5
        assert stats.completed_task_count == 2
        assert stats.in_progress_count == 1
        assert stats.blocked_count == 1
        assert stats.progress_percentage == 40.0

    def test_get_branch_statistics_branch_not_found(self, service, mock_git_branch_repository):
        """Test getting statistics for non-existent branch"""
        # Arrange
        mock_git_branch_repository.get.return_value = None

        # Act
        stats = service.get_branch_statistics("nonexistent")

        # Assert
        assert stats is None

    @patch('fastmcp.task_management.domain.services.branch_statistics_service.logger')
    def test_error_logging_on_task_created(self, mock_logger, service, mock_task_repository):
        """Test that errors are logged when task creation handler fails"""
        # Arrange
        branch_id = "branch123"
        mock_task_repository.find_by_git_branch_id.side_effect = Exception("DB Error")

        # Act
        service.on_task_created("task123", branch_id, "todo")

        # Assert
        mock_logger.error.assert_called_once()
        assert "Failed to update branch statistics on task creation" in mock_logger.error.call_args[0][0]

    @patch('fastmcp.task_management.domain.services.branch_statistics_service.logger')
    def test_error_logging_on_task_updated(self, mock_logger, service, mock_task_repository):
        """Test that errors are logged when task update handler fails"""
        # Arrange
        branch_id = "branch123"
        mock_task_repository.find_by_git_branch_id.side_effect = Exception("DB Error")

        # Act
        service.on_task_updated("task123", branch_id, branch_id, "todo", "done")

        # Assert
        mock_logger.error.assert_called()
        error_msg = mock_logger.error.call_args[0][0]
        assert "Failed to update branch" in error_msg
        assert "statistics" in error_msg

    @patch('fastmcp.task_management.domain.services.branch_statistics_service.logger')
    def test_warning_when_branch_not_found_during_update(self, mock_logger, service, mock_task_repository, mock_git_branch_repository):
        """Test that warning is logged when branch not found during statistics update"""
        # Arrange
        branch_id = "nonexistent"
        mock_task_repository.find_by_git_branch_id.return_value = []
        mock_git_branch_repository.get.return_value = None

        # Act
        service._recalculate_branch_statistics(branch_id)

        # Assert
        mock_logger.warning.assert_called_once()
        assert f"Branch {branch_id} not found for statistics update" in mock_logger.warning.call_args[0][0]