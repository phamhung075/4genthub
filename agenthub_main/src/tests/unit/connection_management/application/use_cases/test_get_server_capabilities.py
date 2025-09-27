"""Unit tests for Get Server Capabilities Use Case"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from fastmcp.connection_management.application.use_cases.get_server_capabilities import (
    GetServerCapabilitiesUseCase
)
from fastmcp.connection_management.application.dtos.connection_dtos import (
    ServerCapabilitiesRequest,
    ServerCapabilitiesResponse
)
from fastmcp.connection_management.domain.entities.server import Server
from fastmcp.connection_management.domain.value_objects.server_capabilities import ServerCapabilities


class TestGetServerCapabilitiesUseCase(unittest.TestCase):
    """Test suite for GetServerCapabilitiesUseCase following DDD patterns"""
    
    def setUp(self):
        """Set up test dependencies"""
        # Mock domain repositories
        self.mock_server_repository = Mock()
        
        # Mock domain services
        self.mock_health_service = Mock()
        
        # Create use case instance with mocked dependencies
        self.use_case = GetServerCapabilitiesUseCase(
            server_repository=self.mock_server_repository,
            health_service=self.mock_health_service
        )
        
        # Set up default mock capabilities
        self.mock_capabilities = Mock(spec=ServerCapabilities)
        self.mock_capabilities.core_features = [
            "Task Management",
            "Agent Orchestration",
            "Context Hierarchy",
            "Authentication"
        ]
        self.mock_capabilities.available_actions = {
            "task": ["create", "update", "delete", "complete"],
            "project": ["create", "list", "health_check"],
            "agent": ["register", "assign", "unassign"]
        }
        self.mock_capabilities.authentication_enabled = True
        self.mock_capabilities.mvp_mode = False
        self.mock_capabilities.version = "2.1.0"
        self.mock_capabilities.get_total_actions_count.return_value = 11
    
    def test_execute_with_existing_server(self):
        """Test getting capabilities from an existing server"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        # Create mock server entity
        mock_server = Mock(spec=Server)
        mock_server.get_capabilities.return_value = self.mock_capabilities
        
        self.mock_server_repository.get_current_server.return_value = mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ServerCapabilitiesResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.core_features, self.mock_capabilities.core_features)
        self.assertEqual(response.available_actions, self.mock_capabilities.available_actions)
        self.assertTrue(response.authentication_enabled)
        self.assertFalse(response.mvp_mode)
        self.assertEqual(response.version, "2.1.0")
        self.assertEqual(response.total_actions, 11)
        
        # Verify interactions
        self.mock_server_repository.get_current_server.assert_called_once()
        mock_server.get_capabilities.assert_called_once()
        self.mock_server_repository.save_server.assert_not_called()
    
    def test_execute_creates_server_when_none_exists(self):
        """Test creating a new server when none exists"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        # Configure no existing server
        self.mock_server_repository.get_current_server.return_value = None
        
        # Configure health service responses
        self.mock_health_service.get_environment_info.return_value = {
            "platform": "linux",
            "python_version": "3.11.0"
        }
        self.mock_health_service.get_authentication_status.return_value = {
            "enabled": True,
            "type": "JWT"
        }
        self.mock_health_service.get_task_management_info.return_value = {
            "total_tasks": 0,
            "active_projects": 0
        }
        
        # Create mock new server
        mock_new_server = Mock(spec=Server)
        mock_new_server.get_capabilities.return_value = self.mock_capabilities
        
        self.mock_server_repository.create_server.return_value = mock_new_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ServerCapabilitiesResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.version, "2.1.0")
        
        # Verify server creation
        self.mock_server_repository.create_server.assert_called_once_with(
            name="agenthub - Task Management & Agent Orchestration",
            version="2.1.0",
            environment={"platform": "linux", "python_version": "3.11.0"},
            authentication={"enabled": True, "type": "JWT"},
            task_management={"total_tasks": 0, "active_projects": 0}
        )
        self.mock_server_repository.save_server.assert_called_once_with(mock_new_server)
        
        # Verify health service calls
        self.mock_health_service.get_environment_info.assert_called_once()
        self.mock_health_service.get_authentication_status.assert_called_once()
        self.mock_health_service.get_task_management_info.assert_called_once()
    
    def test_execute_handles_repository_exception(self):
        """Test error handling when repository raises exception"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        self.mock_server_repository.get_current_server.side_effect = Exception(
            "Database connection failed"
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ServerCapabilitiesResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.core_features, [])
        self.assertEqual(response.available_actions, {})
        self.assertFalse(response.authentication_enabled)
        self.assertFalse(response.mvp_mode)
        self.assertEqual(response.version, "Unknown")
        self.assertEqual(response.total_actions, 0)
        self.assertEqual(response.error, "Database connection failed")
    
    def test_execute_handles_capabilities_exception(self):
        """Test error handling when getting capabilities fails"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        # Create mock server that raises exception on get_capabilities
        mock_server = Mock(spec=Server)
        mock_server.get_capabilities.side_effect = Exception("Capabilities unavailable")
        
        self.mock_server_repository.get_current_server.return_value = mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ServerCapabilitiesResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Capabilities unavailable")
    
    @patch('fastmcp.connection_management.application.use_cases.get_server_capabilities.logger')
    def test_execute_logs_errors(self, mock_logger):
        """Test that errors are properly logged"""
        # Arrange
        request = ServerCapabilitiesRequest()
        error_message = "Critical system error"
        
        self.mock_server_repository.get_current_server.side_effect = Exception(error_message)
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        self.assertIn("Error getting server capabilities", error_call_args)
        self.assertIn(error_message, error_call_args)
    
    def test_execute_with_mvp_mode_enabled(self):
        """Test getting capabilities when MVP mode is enabled"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        # Configure MVP mode capabilities
        mock_mvp_capabilities = Mock(spec=ServerCapabilities)
        mock_mvp_capabilities.core_features = ["Basic Task Management"]
        mock_mvp_capabilities.available_actions = {
            "task": ["create", "list"]
        }
        mock_mvp_capabilities.authentication_enabled = False
        mock_mvp_capabilities.mvp_mode = True
        mock_mvp_capabilities.version = "2.1.0-mvp"
        mock_mvp_capabilities.get_total_actions_count.return_value = 2
        
        mock_server = Mock(spec=Server)
        mock_server.get_capabilities.return_value = mock_mvp_capabilities
        
        self.mock_server_repository.get_current_server.return_value = mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertTrue(response.mvp_mode)
        self.assertFalse(response.authentication_enabled)
        self.assertEqual(response.total_actions, 2)
        self.assertEqual(response.version, "2.1.0-mvp")
    
    def test_execute_with_empty_capabilities(self):
        """Test handling server with empty capabilities"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        # Configure empty capabilities
        mock_empty_capabilities = Mock(spec=ServerCapabilities)
        mock_empty_capabilities.core_features = []
        mock_empty_capabilities.available_actions = {}
        mock_empty_capabilities.authentication_enabled = False
        mock_empty_capabilities.mvp_mode = False
        mock_empty_capabilities.version = "0.0.0"
        mock_empty_capabilities.get_total_actions_count.return_value = 0
        
        mock_server = Mock(spec=Server)
        mock_server.get_capabilities.return_value = mock_empty_capabilities
        
        self.mock_server_repository.get_current_server.return_value = mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.core_features, [])
        self.assertEqual(response.available_actions, {})
        self.assertEqual(response.total_actions, 0)
    
    def test_execute_validates_response_structure(self):
        """Test that response structure adheres to DTO specification"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        mock_server = Mock(spec=Server)
        mock_server.get_capabilities.return_value = self.mock_capabilities
        
        self.mock_server_repository.get_current_server.return_value = mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert - Validate response structure
        self.assertIsInstance(response, ServerCapabilitiesResponse)
        self.assertIsInstance(response.success, bool)
        self.assertIsInstance(response.core_features, list)
        self.assertIsInstance(response.available_actions, dict)
        self.assertIsInstance(response.authentication_enabled, bool)
        self.assertIsInstance(response.mvp_mode, bool)
        self.assertIsInstance(response.version, str)
        self.assertIsInstance(response.total_actions, int)
        
        # Verify all core features are strings
        for feature in response.core_features:
            self.assertIsInstance(feature, str)
        
        # Verify available_actions structure
        for category, actions in response.available_actions.items():
            self.assertIsInstance(category, str)
            self.assertIsInstance(actions, list)
            for action in actions:
                self.assertIsInstance(action, str)
    
    def test_execute_server_creation_failure(self):
        """Test handling failure during server creation"""
        # Arrange
        request = ServerCapabilitiesRequest()
        
        # Configure no existing server
        self.mock_server_repository.get_current_server.return_value = None
        
        # Configure health service
        self.mock_health_service.get_environment_info.return_value = {}
        self.mock_health_service.get_authentication_status.return_value = {}
        self.mock_health_service.get_task_management_info.return_value = {}
        
        # Simulate server creation failure
        self.mock_server_repository.create_server.side_effect = Exception(
            "Failed to create server"
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Failed to create server")
        self.mock_server_repository.save_server.assert_not_called()


if __name__ == '__main__':
    unittest.main()