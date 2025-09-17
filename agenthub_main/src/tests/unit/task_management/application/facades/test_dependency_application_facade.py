"""
Tests for DependencyApplicationFacade - Comprehensive dependency facade testing
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from fastmcp.task_management.application.facades.dependency_application_facade import DependencyApplicationFacade
from fastmcp.task_management.application.dtos.dependency.add_dependency_request import AddDependencyRequest
from fastmcp.task_management.application.services.dependencie_application_service import DependencieApplicationService
from fastmcp.task_management.domain.repositories.task_repository import TaskRepository
from fastmcp.task_management.domain.exceptions import TaskNotFoundError


class MockDependencyResponse:
    """Mock response for dependency operations"""
    def __init__(self, success=True, task_id="", dependencies=None, message=""):
        self.success = success
        self.task_id = task_id
        self.dependencies = dependencies or []
        self.message = message


class TestDependencyApplicationFacade:
    """Test cases for DependencyApplicationFacade"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Mock task repository"""
        return Mock(spec=TaskRepository)
    
    @pytest.fixture
    def mock_dependency_app_service(self):
        """Mock dependency application service"""
        return Mock(spec=DependencieApplicationService)
    
    @pytest.fixture
    def facade(self, mock_task_repository):
        """Create facade instance for testing"""
        return DependencyApplicationFacade(task_repository=mock_task_repository)
    
    @pytest.fixture
    def facade_with_mocked_service(self, mock_task_repository, mock_dependency_app_service):
        """Create facade with mocked service"""
        facade = DependencyApplicationFacade(task_repository=mock_task_repository)
        facade._dependency_app_service = mock_dependency_app_service
        return facade
    
    def test_facade_initialization(self, mock_task_repository):
        """Test facade initialization"""
        facade = DependencyApplicationFacade(task_repository=mock_task_repository)
        
        assert facade._task_repository == mock_task_repository
        assert isinstance(facade._dependency_app_service, DependencieApplicationService)
    
    def test_add_dependency_success(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test successful dependency addition"""
        mock_response = MockDependencyResponse(
            success=True,
            task_id="task-123",
            dependencies=["dep-456"],
            message="Dependency added successfully"
        )
        mock_dependency_app_service.add_dependency.return_value = mock_response
        
        result = facade_with_mocked_service.manage_dependencies(
            action="add_dependency",
            task_id="task-123",
            dependency_data={"dependency_id": "dep-456"}
        )
        
        assert result["success"] is True
        assert result["action"] == "add_dependency"
        assert result["task_id"] == "task-123"
        assert result["dependencies"] == ["dep-456"]
        assert result["message"] == "Dependency added successfully"
        
        # Verify service was called correctly
        mock_dependency_app_service.add_dependency.assert_called_once()
        call_args = mock_dependency_app_service.add_dependency.call_args[0][0]
        assert isinstance(call_args, AddDependencyRequest)
        assert call_args.task_id == "task-123"
        assert call_args.depends_on_task_id == "dep-456"
    
    def test_add_dependency_missing_task_id(self, facade_with_mocked_service):
        """Test add_dependency with missing task_id"""
        result = facade_with_mocked_service.manage_dependencies(
            action="add_dependency",
            task_id="",
            dependency_data={"dependency_id": "dep-456"}
        )
        
        assert result["success"] is False
        assert "Task ID is required" in result["error"]
    
    def test_add_dependency_missing_dependency_data(self, facade_with_mocked_service):
        """Test add_dependency with missing dependency_data"""
        result = facade_with_mocked_service.manage_dependencies(
            action="add_dependency",
            task_id="task-123",
            dependency_data=None
        )
        
        assert result["success"] is False
        assert "dependency_data with dependency_id is required" in result["error"]
    
    def test_add_dependency_missing_dependency_id(self, facade_with_mocked_service):
        """Test add_dependency with missing dependency_id in data"""
        result = facade_with_mocked_service.manage_dependencies(
            action="add_dependency",
            task_id="task-123",
            dependency_data={"other_field": "value"}
        )
        
        assert result["success"] is False
        assert "dependency_data with dependency_id is required" in result["error"]
    
    def test_remove_dependency_success(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test successful dependency removal"""
        mock_response = MockDependencyResponse(
            success=True,
            task_id="task-123",
            dependencies=[],
            message="Dependency removed successfully"
        )
        mock_dependency_app_service.remove_dependency.return_value = mock_response
        
        result = facade_with_mocked_service.manage_dependencies(
            action="remove_dependency",
            task_id="task-123",
            dependency_data={"dependency_id": "dep-456"}
        )
        
        assert result["success"] is True
        assert result["action"] == "remove_dependency"
        assert result["task_id"] == "task-123"
        assert result["dependencies"] == []
        assert result["message"] == "Dependency removed successfully"
        
        mock_dependency_app_service.remove_dependency.assert_called_once_with("task-123", "dep-456")
    
    def test_remove_dependency_missing_dependency_data(self, facade_with_mocked_service):
        """Test remove_dependency with missing dependency_data"""
        result = facade_with_mocked_service.manage_dependencies(
            action="remove_dependency",
            task_id="task-123",
            dependency_data=None
        )
        
        assert result["success"] is False
        assert "dependency_data with dependency_id is required" in result["error"]
    
    def test_get_dependencies_success(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test successful dependency retrieval"""
        mock_dependency_app_service.get_dependencies.return_value = {
            "dependencies": ["dep-1", "dep-2"],
            "dependency_count": 2,
            "can_start": True
        }
        
        result = facade_with_mocked_service.manage_dependencies(
            action="get_dependencies",
            task_id="task-123"
        )
        
        assert result["success"] is True
        assert result["action"] == "get_dependencies"
        assert result["dependencies"] == ["dep-1", "dep-2"]
        assert result["dependency_count"] == 2
        assert result["can_start"] is True
        
        mock_dependency_app_service.get_dependencies.assert_called_once_with("task-123")
    
    def test_clear_dependencies_success(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test successful dependency clearing"""
        mock_response = MockDependencyResponse(
            success=True,
            task_id="task-123",
            dependencies=[],
            message="All dependencies cleared"
        )
        mock_dependency_app_service.clear_dependencies.return_value = mock_response
        
        result = facade_with_mocked_service.manage_dependencies(
            action="clear_dependencies",
            task_id="task-123"
        )
        
        assert result["success"] is True
        assert result["action"] == "clear_dependencies"
        assert result["task_id"] == "task-123"
        assert result["dependencies"] == []
        assert result["message"] == "All dependencies cleared"
        
        mock_dependency_app_service.clear_dependencies.assert_called_once_with("task-123")
    
    def test_get_blocking_tasks_success(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test successful blocking tasks retrieval"""
        mock_dependency_app_service.get_blocking_tasks.return_value = {
            "blocking_tasks": ["task-456", "task-789"],
            "blocking_count": 2,
            "is_blocking_others": True
        }
        
        result = facade_with_mocked_service.manage_dependencies(
            action="get_blocking_tasks",
            task_id="task-123"
        )
        
        assert result["success"] is True
        assert result["action"] == "get_blocking_tasks"
        assert result["blocking_tasks"] == ["task-456", "task-789"]
        assert result["blocking_count"] == 2
        assert result["is_blocking_others"] is True
        
        mock_dependency_app_service.get_blocking_tasks.assert_called_once_with("task-123")
    
    def test_unknown_action(self, facade_with_mocked_service):
        """Test handling of unknown action"""
        result = facade_with_mocked_service.manage_dependencies(
            action="unknown_action",
            task_id="task-123"
        )
        
        assert result["success"] is False
        assert "Unknown dependency action: unknown_action" in result["error"]
    
    def test_task_not_found_error(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test handling of TaskNotFoundError"""
        mock_dependency_app_service.get_dependencies.side_effect = TaskNotFoundError("Task not found")
        
        result = facade_with_mocked_service.manage_dependencies(
            action="get_dependencies",
            task_id="nonexistent-task"
        )
        
        assert result["success"] is False
        assert "Task not found" in result["error"]
    
    def test_value_error_handling(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test handling of ValueError from service"""
        mock_dependency_app_service.add_dependency.side_effect = ValueError("Invalid dependency")
        
        result = facade_with_mocked_service.manage_dependencies(
            action="add_dependency",
            task_id="task-123",
            dependency_data={"dependency_id": "invalid-dep"}
        )
        
        assert result["success"] is False
        assert "Invalid dependency" in result["error"]
    
    def test_unexpected_exception_handling(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test handling of unexpected exceptions"""
        mock_dependency_app_service.get_dependencies.side_effect = Exception("Unexpected error")
        
        with patch('fastmcp.task_management.application.facades.dependency_application_facade.logger') as mock_logger:
            result = facade_with_mocked_service.manage_dependencies(
                action="get_dependencies",
                task_id="task-123"
            )
            
            assert result["success"] is False
            assert "Dependency operation failed" in result["error"]
            assert "Unexpected error" in result["error"]
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
    
    def test_whitespace_task_id_validation(self, facade_with_mocked_service):
        """Test that whitespace-only task_id is rejected"""
        result = facade_with_mocked_service.manage_dependencies(
            action="get_dependencies",
            task_id="   "  # Whitespace only
        )
        
        assert result["success"] is False
        assert "Task ID is required" in result["error"]
    
    def test_all_actions_with_valid_data(self, facade_with_mocked_service, mock_dependency_app_service):
        """Test all actions with valid data to ensure coverage"""
        # Configure mock responses
        mock_add_response = MockDependencyResponse(True, "task-123", ["dep-1"], "Added")
        mock_remove_response = MockDependencyResponse(True, "task-123", [], "Removed")
        mock_clear_response = MockDependencyResponse(True, "task-123", [], "Cleared")
        
        mock_dependency_app_service.add_dependency.return_value = mock_add_response
        mock_dependency_app_service.remove_dependency.return_value = mock_remove_response
        mock_dependency_app_service.clear_dependencies.return_value = mock_clear_response
        mock_dependency_app_service.get_dependencies.return_value = {"dependencies": ["dep-1"]}
        mock_dependency_app_service.get_blocking_tasks.return_value = {"blocking_tasks": ["task-2"]}
        
        actions_and_data = [
            ("add_dependency", {"dependency_id": "dep-1"}),
            ("remove_dependency", {"dependency_id": "dep-1"}),
            ("clear_dependencies", None),
            ("get_dependencies", None),
            ("get_blocking_tasks", None)
        ]
        
        for action, dependency_data in actions_and_data:
            result = facade_with_mocked_service.manage_dependencies(
                action=action,
                task_id="task-123",
                dependency_data=dependency_data
            )
            
            assert result["success"] is True, f"Action {action} failed: {result}"
            assert result["action"] == action


class TestDependencyApplicationFacadeIntegration:
    """Integration-style tests for DependencyApplicationFacade"""
    
    def test_dependency_lifecycle(self):
        """Test complete dependency lifecycle"""
        mock_repository = Mock(spec=TaskRepository)
        facade = DependencyApplicationFacade(task_repository=mock_repository)
        
        # Mock the service responses for a complete workflow
        with patch.object(facade._dependency_app_service, 'add_dependency') as mock_add, \
             patch.object(facade._dependency_app_service, 'get_dependencies') as mock_get, \
             patch.object(facade._dependency_app_service, 'remove_dependency') as mock_remove:
            
            # Configure responses
            mock_add.return_value = MockDependencyResponse(True, "task-1", ["dep-1"], "Added")
            mock_get.return_value = {"dependencies": ["dep-1"], "dependency_count": 1}
            mock_remove.return_value = MockDependencyResponse(True, "task-1", [], "Removed")
            
            # Add dependency
            add_result = facade.manage_dependencies(
                action="add_dependency",
                task_id="task-1",
                dependency_data={"dependency_id": "dep-1"}
            )
            assert add_result["success"] is True
            
            # Get dependencies
            get_result = facade.manage_dependencies(
                action="get_dependencies",
                task_id="task-1"
            )
            assert get_result["success"] is True
            assert get_result["dependency_count"] == 1
            
            # Remove dependency
            remove_result = facade.manage_dependencies(
                action="remove_dependency",
                task_id="task-1",
                dependency_data={"dependency_id": "dep-1"}
            )
            assert remove_result["success"] is True
            
            # Verify all service methods were called
            mock_add.assert_called_once()
            mock_get.assert_called_once()
            mock_remove.assert_called_once()
    
    def test_error_recovery_and_resilience(self):
        """Test that facade recovers gracefully from errors"""
        mock_repository = Mock(spec=TaskRepository)
        facade = DependencyApplicationFacade(task_repository=mock_repository)
        
        with patch.object(facade._dependency_app_service, 'get_dependencies') as mock_get:
            # First call fails
            mock_get.side_effect = Exception("Temporary error")
            
            result1 = facade.manage_dependencies(
                action="get_dependencies",
                task_id="task-1"
            )
            assert result1["success"] is False
            
            # Second call succeeds
            mock_get.side_effect = None
            mock_get.return_value = {"dependencies": [], "dependency_count": 0}
            
            result2 = facade.manage_dependencies(
                action="get_dependencies",
                task_id="task-1"
            )
            assert result2["success"] is True