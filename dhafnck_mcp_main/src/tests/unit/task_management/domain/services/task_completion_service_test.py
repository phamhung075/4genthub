"""
Unit tests for TaskCompletionService domain service.
Tests all business rules, validation logic, error handling, and edge cases.
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
from typing import Optional, Dict, Any

from fastmcp.task_management.domain.services.task_completion_service import (
    TaskCompletionService,
    TaskContextRepositoryProtocol
)
from fastmcp.task_management.domain.entities.task import Task
from fastmcp.task_management.domain.entities.subtask import Subtask
from fastmcp.task_management.domain.repositories.subtask_repository import SubtaskRepository
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskCompletionError


class MockTaskContextRepository:
    """Mock implementation of TaskContextRepositoryProtocol for testing"""
    
    def __init__(self):
        self.contexts = {}
    
    def get(self, context_id: str) -> Optional[Dict[str, Any]]:
        return self.contexts.get(context_id)
    
    def add_context(self, context_id: str, context: Dict[str, Any]):
        self.contexts[context_id] = context


class TestTaskCompletionServiceInitialization:
    """Test suite for TaskCompletionService initialization"""
    
    def test_init_with_subtask_repository_only_success(self):
        """Test initialization with only subtask repository"""
        subtask_repo = Mock(spec=SubtaskRepository)
        
        service = TaskCompletionService(subtask_repo)
        
        assert service._subtask_repository == subtask_repo
        assert service._task_context_repository is None
    
    def test_init_with_both_repositories_success(self):
        """Test initialization with both repositories"""
        subtask_repo = Mock(spec=SubtaskRepository)
        context_repo = MockTaskContextRepository()
        
        service = TaskCompletionService(subtask_repo, context_repo)
        
        assert service._subtask_repository == subtask_repo
        assert service._task_context_repository == context_repo


class TestTaskCompletionServiceCanCompleteTask:
    """Test suite for can_complete_task method"""
    
    @pytest.fixture
    def mock_subtask_repo(self):
        """Create mock subtask repository"""
        return Mock(spec=SubtaskRepository)
    
    @pytest.fixture
    def mock_context_repo(self):
        """Create mock context repository"""
        return MockTaskContextRepository()
    
    @pytest.fixture
    def service_with_context(self, mock_subtask_repo, mock_context_repo):
        """Create service with context repository"""
        return TaskCompletionService(mock_subtask_repo, mock_context_repo)
    
    @pytest.fixture
    def service_without_context(self, mock_subtask_repo):
        """Create service without context repository"""
        return TaskCompletionService(mock_subtask_repo)
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id=TaskId.generate(),
            title="Test Task",
            description="Test Description",
            git_branch_id="branch_123",
            context_id="context_123"
        )
    
    @pytest.fixture
    def sample_task_no_context(self):
        """Create sample task without context for testing"""
        return Task(
            id=TaskId.generate(),
            title="Test Task No Context",
            description="Test Description",
            git_branch_id="branch_123",
            context_id=None
        )
    
    def test_can_complete_task_no_subtasks_success(self, service_without_context, mock_subtask_repo, sample_task):
        """Test can complete task with no subtasks returns True"""
        mock_subtask_repo.find_by_parent_task_id.return_value = []
        
        can_complete, error_msg = service_without_context.can_complete_task(sample_task)
        
        assert can_complete is True
        assert error_msg is None
        mock_subtask_repo.find_by_parent_task_id.assert_called_once_with(sample_task.id)
    
    def test_can_complete_task_all_subtasks_completed_success(self, service_without_context, mock_subtask_repo, sample_task):
        """Test can complete task when all subtasks are completed"""
        completed_subtask1 = Mock()
        completed_subtask1.is_completed = True
        completed_subtask1.title = "Completed Subtask 1"
        
        completed_subtask2 = Mock()
        completed_subtask2.is_completed = True
        completed_subtask2.title = "Completed Subtask 2"
        
        mock_subtask_repo.find_by_parent_task_id.return_value = [completed_subtask1, completed_subtask2]
        
        can_complete, error_msg = service_without_context.can_complete_task(sample_task)
        
        assert can_complete is True
        assert error_msg is None
    
    def test_can_complete_task_has_incomplete_subtasks_returns_false(self, service_without_context, mock_subtask_repo, sample_task):
        """Test can complete task returns False when subtasks are incomplete"""
        completed_subtask = Mock()
        completed_subtask.is_completed = True
        completed_subtask.title = "Completed Subtask"
        
        incomplete_subtask1 = Mock()
        incomplete_subtask1.is_completed = False
        incomplete_subtask1.title = "Incomplete Subtask 1"
        
        incomplete_subtask2 = Mock()
        incomplete_subtask2.is_completed = False
        incomplete_subtask2.title = "Incomplete Subtask 2"
        
        mock_subtask_repo.find_by_parent_task_id.return_value = [
            completed_subtask, incomplete_subtask1, incomplete_subtask2
        ]
        
        can_complete, error_msg = service_without_context.can_complete_task(sample_task)
        
        assert can_complete is False
        assert error_msg is not None
        assert "2 of 3 subtasks are incomplete" in error_msg
        assert "Incomplete Subtask 1" in error_msg
        assert "Incomplete Subtask 2" in error_msg
        assert "Complete all subtasks first" in error_msg
    
    def test_can_complete_task_many_incomplete_subtasks_truncates_list(self, service_without_context, mock_subtask_repo, sample_task):
        """Test can complete task truncates long list of incomplete subtasks"""
        incomplete_subtasks = []
        for i in range(5):
            subtask = Mock()
            subtask.is_completed = False
            subtask.title = f"Incomplete Subtask {i+1}"
            incomplete_subtasks.append(subtask)
        
        mock_subtask_repo.find_by_parent_task_id.return_value = incomplete_subtasks
        
        can_complete, error_msg = service_without_context.can_complete_task(sample_task)
        
        assert can_complete is False
        assert "5 of 5 subtasks are incomplete" in error_msg
        assert "Incomplete Subtask 1" in error_msg
        assert "Incomplete Subtask 2" in error_msg
        assert "Incomplete Subtask 3" in error_msg
        assert "and 2 more" in error_msg


class TestTaskCompletionServiceValidateTaskCompletion:
    """Test suite for validate_task_completion method"""
    
    @pytest.fixture
    def service(self):
        """Create service for testing"""
        mock_repo = Mock(spec=SubtaskRepository)
        return TaskCompletionService(mock_repo)
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id=TaskId.generate(),
            title="Test Task",
            description="Test Description",
            git_branch_id="branch_123"
        )
    
    def test_validate_task_completion_can_complete_success(self, service, sample_task):
        """Test validate_task_completion succeeds when task can be completed"""
        service._subtask_repository.find_by_parent_task_id.return_value = []
        
        # Should not raise exception
        service.validate_task_completion(sample_task)
    
    def test_validate_task_completion_cannot_complete_raises_exception(self, service, sample_task):
        """Test validate_task_completion raises exception when task cannot be completed"""
        incomplete_subtask = Mock()
        incomplete_subtask.is_completed = False
        incomplete_subtask.title = "Incomplete Subtask"
        
        service._subtask_repository.find_by_parent_task_id.return_value = [incomplete_subtask]
        
        with pytest.raises(TaskCompletionError, match="Cannot complete task"):
            service.validate_task_completion(sample_task)
    
    def test_validate_task_completion_raises_exception_with_custom_message(self, service, sample_task):
        """Test validate_task_completion raises exception with custom error message"""
        service._subtask_repository.find_by_parent_task_id.side_effect = Exception("Custom error")
        
        with pytest.raises(TaskCompletionError, match="Internal error validating task completion"):
            service.validate_task_completion(sample_task)


class TestTaskCompletionServiceGetSubtaskCompletionSummary:
    """Test suite for get_subtask_completion_summary method"""
    
    @pytest.fixture
    def service(self):
        """Create service for testing"""
        mock_repo = Mock(spec=SubtaskRepository)
        return TaskCompletionService(mock_repo)
    
    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id=TaskId.generate(),
            title="Test Task",
            description="Test Description",
            git_branch_id="branch_123"
        )
    
    def test_get_subtask_completion_summary_no_subtasks(self, service, sample_task):
        """Test get_subtask_completion_summary with no subtasks"""
        service._subtask_repository.find_by_parent_task_id.return_value = []
        
        summary = service.get_subtask_completion_summary(sample_task)
        
        assert summary['total'] == 0
        assert summary['completed'] == 0
        assert summary['incomplete'] == 0
        assert summary['completion_percentage'] == 100
        assert summary['can_complete_parent'] is True
    
    def test_get_subtask_completion_summary_all_completed(self, service, sample_task):
        """Test get_subtask_completion_summary with all subtasks completed"""
        completed_subtask1 = Mock()
        completed_subtask1.is_completed = True
        
        completed_subtask2 = Mock()
        completed_subtask2.is_completed = True
        
        service._subtask_repository.find_by_parent_task_id.return_value = [
            completed_subtask1, completed_subtask2
        ]
        
        summary = service.get_subtask_completion_summary(sample_task)
        
        assert summary['total'] == 2
        assert summary['completed'] == 2
        assert summary['incomplete'] == 0
        assert summary['completion_percentage'] == 100.0
        assert summary['can_complete_parent'] is True
    
    def test_get_subtask_completion_summary_partially_completed(self, service, sample_task):
        """Test get_subtask_completion_summary with partially completed subtasks"""
        completed_subtask = Mock()
        completed_subtask.is_completed = True
        
        incomplete_subtask1 = Mock()
        incomplete_subtask1.is_completed = False
        
        incomplete_subtask2 = Mock()
        incomplete_subtask2.is_completed = False
        
        service._subtask_repository.find_by_parent_task_id.return_value = [
            completed_subtask, incomplete_subtask1, incomplete_subtask2
        ]
        
        summary = service.get_subtask_completion_summary(sample_task)
        
        assert summary['total'] == 3
        assert summary['completed'] == 1
        assert summary['incomplete'] == 2
        assert summary['completion_percentage'] == 33.3
        assert summary['can_complete_parent'] is False