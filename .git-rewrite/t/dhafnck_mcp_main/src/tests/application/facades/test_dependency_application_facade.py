"""Tests for DependencyApplicationFacade"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from fastmcp.task_management.application.facades.dependency_application_facade import DependencyApplicationFacade
from fastmcp.task_management.application.dtos.dependency.add_dependency_request import AddDependencyRequest
from fastmcp.task_management.domain.exceptions import TaskNotFoundError


class TestDependencyApplicationFacade:
    """Test cases for DependencyApplicationFacade"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_task_repository = Mock()
        self.facade = DependencyApplicationFacade(self.mock_task_repository)

    def test_init(self):
        """Test facade initialization"""
        assert self.facade._task_repository == self.mock_task_repository
        assert hasattr(self.facade, '_dependency_app_service')

    def test_manage_dependencies_add_success(self):
        """Test successful add dependency operation"""
        # Setup
        task_id = "task-123"
        dependency_data = {"dependency_id": "dep-456"}
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.task_id = task_id
        mock_response.dependencies = ["dep-456"]
        mock_response.message = "Dependency added successfully"
        
        self.facade._dependency_app_service.add_dependency = Mock(return_value=mock_response)
        
        # Execute
        result = self.facade.manage_dependencies("add_dependency", task_id, dependency_data)
        
        # Assert
        assert result == {
            "success": True,
            "action": "add_dependency",
            "task_id": task_id,
            "dependencies": ["dep-456"],
            "message": "Dependency added successfully"
        }
        
        # Verify correct request was created
        call_args = self.facade._dependency_app_service.add_dependency.call_args[0]
        assert isinstance(call_args[0], AddDependencyRequest)
        assert call_args[0].task_id == task_id
        assert call_args[0].depends_on_task_id == "dep-456"

    def test_manage_dependencies_add_missing_dependency_data(self):
        """Test add dependency with missing dependency data"""
        task_id = "task-123"
        
        result = self.facade.manage_dependencies("add_dependency", task_id)
        
        assert result == {
            "success": False,
            "error": "dependency_data with dependency_id is required"
        }

    def test_manage_dependencies_add_missing_dependency_id(self):
        """Test add dependency with missing dependency_id"""
        task_id = "task-123"
        dependency_data = {"other_field": "value"}
        
        result = self.facade.manage_dependencies("add_dependency", task_id, dependency_data)
        
        assert result == {
            "success": False,
            "error": "dependency_data with dependency_id is required"
        }

    def test_manage_dependencies_remove_success(self):
        """Test successful remove dependency operation"""
        task_id = "task-123"
        dependency_data = {"dependency_id": "dep-456"}
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.task_id = task_id
        mock_response.dependencies = []
        mock_response.message = "Dependency removed successfully"
        
        self.facade._dependency_app_service.remove_dependency = Mock(return_value=mock_response)
        
        result = self.facade.manage_dependencies("remove_dependency", task_id, dependency_data)
        
        assert result == {
            "success": True,
            "action": "remove_dependency",
            "task_id": task_id,
            "dependencies": [],
            "message": "Dependency removed successfully"
        }
        
        self.facade._dependency_app_service.remove_dependency.assert_called_once_with(
            task_id, "dep-456"
        )

    def test_manage_dependencies_remove_missing_dependency_data(self):
        """Test remove dependency with missing dependency data"""
        task_id = "task-123"
        
        result = self.facade.manage_dependencies("remove_dependency", task_id)
        
        assert result == {
            "success": False,
            "error": "dependency_data with dependency_id is required"
        }

    def test_manage_dependencies_get_dependencies_success(self):
        """Test successful get dependencies operation"""
        task_id = "task-123"
        
        mock_response = {
            "task_id": task_id,
            "dependencies": ["dep-456", "dep-789"],
            "blocking_tasks": ["block-111"]
        }
        
        self.facade._dependency_app_service.get_dependencies = Mock(return_value=mock_response)
        
        result = self.facade.manage_dependencies("get_dependencies", task_id)
        
        assert result == {
            "success": True,
            "action": "get_dependencies",
            "task_id": task_id,
            "dependencies": ["dep-456", "dep-789"],
            "blocking_tasks": ["block-111"]
        }

    def test_manage_dependencies_clear_dependencies_success(self):
        """Test successful clear dependencies operation"""
        task_id = "task-123"
        
        mock_response = Mock()
        mock_response.success = True
        mock_response.task_id = task_id
        mock_response.dependencies = []
        mock_response.message = "All dependencies cleared"
        
        self.facade._dependency_app_service.clear_dependencies = Mock(return_value=mock_response)
        
        result = self.facade.manage_dependencies("clear_dependencies", task_id)
        
        assert result == {
            "success": True,
            "action": "clear_dependencies",
            "task_id": task_id,
            "dependencies": [],
            "message": "All dependencies cleared"
        }

    def test_manage_dependencies_get_blocking_tasks_success(self):
        """Test successful get blocking tasks operation"""
        task_id = "task-123"
        
        mock_response = {
            "task_id": task_id,
            "blocking_tasks": ["block-111", "block-222"],
            "dependents": ["dep-333"]
        }
        
        self.facade._dependency_app_service.get_blocking_tasks = Mock(return_value=mock_response)
        
        result = self.facade.manage_dependencies("get_blocking_tasks", task_id)
        
        assert result == {
            "success": True,
            "action": "get_blocking_tasks",
            "task_id": task_id,
            "blocking_tasks": ["block-111", "block-222"],
            "dependents": ["dep-333"]
        }

    def test_manage_dependencies_unknown_action(self):
        """Test unknown action"""
        task_id = "task-123"
        
        result = self.facade.manage_dependencies("unknown_action", task_id)
        
        assert result == {
            "success": False,
            "error": "Unknown dependency action: unknown_action"
        }

    def test_manage_dependencies_empty_task_id(self):
        """Test with empty task ID"""
        result = self.facade.manage_dependencies("add_dependency", "")
        
        assert result == {
            "success": False,
            "error": "Task ID is required for dependency operations"
        }

    def test_manage_dependencies_none_task_id(self):
        """Test with None task ID"""
        result = self.facade.manage_dependencies("add_dependency", None)
        
        assert result == {
            "success": False,
            "error": "Task ID is required for dependency operations"
        }

    def test_manage_dependencies_whitespace_task_id(self):
        """Test with whitespace-only task ID"""
        result = self.facade.manage_dependencies("add_dependency", "   ")
        
        assert result == {
            "success": False,
            "error": "Task ID is required for dependency operations"
        }

    def test_manage_dependencies_task_not_found_error(self):
        """Test handling of TaskNotFoundError"""
        task_id = "task-123"
        dependency_data = {"dependency_id": "dep-456"}
        
        self.facade._dependency_app_service.add_dependency = Mock(
            side_effect=TaskNotFoundError("Task not found")
        )
        
        result = self.facade.manage_dependencies("add_dependency", task_id, dependency_data)
        
        assert result == {
            "success": False,
            "error": "Task not found"
        }

    def test_manage_dependencies_value_error(self):
        """Test handling of ValueError"""
        task_id = "task-123"
        dependency_data = {"dependency_id": "dep-456"}
        
        self.facade._dependency_app_service.add_dependency = Mock(
            side_effect=ValueError("Invalid dependency")
        )
        
        result = self.facade.manage_dependencies("add_dependency", task_id, dependency_data)
        
        assert result == {
            "success": False,
            "error": "Invalid dependency"
        }

    @patch('fastmcp.task_management.application.facades.dependency_application_facade.logger')
    def test_manage_dependencies_unexpected_error(self, mock_logger):
        """Test handling of unexpected error"""
        task_id = "task-123"
        dependency_data = {"dependency_id": "dep-456"}
        
        self.facade._dependency_app_service.add_dependency = Mock(
            side_effect=Exception("Unexpected error")
        )
        
        result = self.facade.manage_dependencies("add_dependency", task_id, dependency_data)
        
        assert result == {
            "success": False,
            "error": "Dependency operation failed: Unexpected error"
        }
        
        mock_logger.error.assert_called_once()
        assert "Unexpected error in manage_dependencies" in str(mock_logger.error.call_args)

    def test_manage_dependencies_all_actions_coverage(self):
        """Test that all supported actions are handled"""
        supported_actions = [
            "add_dependency",
            "remove_dependency", 
            "get_dependencies",
            "clear_dependencies",
            "get_blocking_tasks"
        ]
        
        task_id = "task-123"
        
        for action in supported_actions:
            # Mock appropriate service method
            if action in ["add_dependency", "remove_dependency", "clear_dependencies"]:
                mock_response = Mock()
                mock_response.success = True
                mock_response.task_id = task_id
                mock_response.dependencies = []
                mock_response.message = f"{action} success"
                
                service_method = getattr(self.facade._dependency_app_service, action)
                service_method.return_value = mock_response
            else:
                service_method = getattr(self.facade._dependency_app_service, action)
                service_method.return_value = {"task_id": task_id}
            
            # Execute based on action requirements
            if action in ["add_dependency", "remove_dependency"]:
                dependency_data = {"dependency_id": "dep-456"}
                result = self.facade.manage_dependencies(action, task_id, dependency_data)
            else:
                result = self.facade.manage_dependencies(action, task_id)
            
            # All actions should succeed with proper mocking
            assert result["success"] is True
            assert result["action"] == action

    def test_service_integration(self):
        """Test that facade properly initializes dependency service"""
        # Verify service is created with correct repository
        assert hasattr(self.facade, '_dependency_app_service')
        assert self.facade._dependency_app_service is not None
        
        # Test that service methods are callable
        service_methods = [
            'add_dependency',
            'remove_dependency',
            'get_dependencies', 
            'clear_dependencies',
            'get_blocking_tasks'
        ]
        
        for method_name in service_methods:
            assert hasattr(self.facade._dependency_app_service, method_name)
            assert callable(getattr(self.facade._dependency_app_service, method_name))