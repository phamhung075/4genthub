"""Unit tests for Get Server Status Use Case"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from fastmcp.connection_management.application.use_cases.get_server_status import (
    GetServerStatusUseCase
)
from fastmcp.connection_management.application.dtos.connection_dtos import (
    ServerStatusRequest,
    ServerStatusResponse
)
from fastmcp.connection_management.domain.entities.server import Server
from fastmcp.connection_management.domain.value_objects.server_capabilities import ServerCapabilities
from fastmcp.connection_management.domain.value_objects.server_status import ServerStatus


class TestGetServerStatusUseCase(unittest.TestCase):
    """Test suite for GetServerStatusUseCase following DDD patterns"""
    
    def setUp(self):
        """Set up test dependencies"""
        # Mock domain repositories
        self.mock_server_repository = Mock()
        self.mock_connection_repository = Mock()
        
        # Mock domain services
        self.mock_health_service = Mock()
        self.mock_diagnostics_service = Mock()
        
        # Create use case instance with mocked dependencies
        self.use_case = GetServerStatusUseCase(
            server_repository=self.mock_server_repository,
            connection_repository=self.mock_connection_repository,
            health_service=self.mock_health_service,
            diagnostics_service=self.mock_diagnostics_service
        )
        
        # Set up default mock server
        self.mock_server = Mock(spec=Server)
        self.mock_server.name = "4genthub Server"
        self.mock_server.version = "2.1.0"
        self.mock_server.restart_count = 0
        self.mock_server.get_uptime_seconds.return_value = 3600
        
        # Set up default mock health status
        mock_health_status = Mock(spec=ServerStatus)
        mock_health_status.to_dict.return_value = {
            "status": "healthy",
            "cpu_usage": 15.5,
            "memory_usage": 45.2,
            "active_connections": 5
        }
        self.mock_server.check_health.return_value = mock_health_status
        
        # Set up default mock capabilities
        self.mock_capabilities = Mock(spec=ServerCapabilities)
        self.mock_capabilities.core_features = ["Task Management", "Agent Orchestration"]
        self.mock_capabilities.get_total_actions_count.return_value = 25
        self.mock_capabilities.authentication_enabled = True
        self.mock_server.get_capabilities.return_value = self.mock_capabilities
        
        # Set up default diagnostics response
        self.mock_diagnostics_service.get_connection_statistics.return_value = {
            "total_connections": 10,
            "active_connections": 5,
            "total_requests": 1000,
            "error_rate": 0.01
        }
    
    def test_execute_with_existing_server(self):
        """Test getting status from an existing server"""
        # Arrange
        request = ServerStatusRequest()
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ServerStatusResponse)
        self.assertTrue(response.success)
        
        # Verify server info
        self.assertEqual(response.server_info["name"], "4genthub Server")
        self.assertEqual(response.server_info["version"], "2.1.0")
        self.assertEqual(response.server_info["uptime_seconds"], 3600)
        self.assertEqual(response.server_info["restart_count"], 0)
        
        # Verify connection stats
        self.assertEqual(response.connection_stats["total_connections"], 10)
        self.assertEqual(response.connection_stats["active_connections"], 5)
        
        # Verify health status
        self.assertEqual(response.health_status["status"], "healthy")
        self.assertEqual(response.health_status["cpu_usage"], 15.5)
        
        # Verify capabilities summary
        self.assertEqual(response.capabilities_summary["total_features"], 2)
        self.assertEqual(response.capabilities_summary["total_actions"], 25)
        self.assertTrue(response.capabilities_summary["authentication_enabled"])
        
        # Verify interactions
        self.mock_server_repository.get_current_server.assert_called_once()
        self.mock_server.check_health.assert_called_once()
        self.mock_server.get_capabilities.assert_called_once()
        self.mock_diagnostics_service.get_connection_statistics.assert_called_once()
    
    def test_execute_creates_server_when_none_exists(self):
        """Test creating a new server when none exists"""
        # Arrange
        request = ServerStatusRequest()
        
        # Configure no existing server
        self.mock_server_repository.get_current_server.return_value = None
        
        # Configure health service responses
        self.mock_health_service.get_environment_info.return_value = {
            "platform": "linux",
            "python_version": "3.11.0",
            "memory_total": "16GB"
        }
        self.mock_health_service.get_authentication_status.return_value = {
            "enabled": True,
            "type": "JWT",
            "provider": "Supabase"
        }
        self.mock_health_service.get_task_management_info.return_value = {
            "total_tasks": 50,
            "active_projects": 3,
            "completed_tasks": 30
        }
        
        # Configure created server
        self.mock_server_repository.create_server.return_value = self.mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        
        # Verify server creation
        self.mock_server_repository.create_server.assert_called_once_with(
            name="4genthub - Task Management & Agent Orchestration",
            version="2.1.0",
            environment={
                "platform": "linux",
                "python_version": "3.11.0",
                "memory_total": "16GB"
            },
            authentication={
                "enabled": True,
                "type": "JWT",
                "provider": "Supabase"
            },
            task_management={
                "total_tasks": 50,
                "active_projects": 3,
                "completed_tasks": 30
            }
        )
        
        # Verify health service calls
        self.mock_health_service.get_environment_info.assert_called_once()
        self.mock_health_service.get_authentication_status.assert_called_once()
        self.mock_health_service.get_task_management_info.assert_called_once()
    
    def test_execute_handles_repository_exception(self):
        """Test error handling when repository raises exception"""
        # Arrange
        request = ServerStatusRequest()
        self.mock_server_repository.get_current_server.side_effect = Exception(
            "Database unavailable"
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ServerStatusResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.server_info, {})
        self.assertEqual(response.connection_stats, {})
        self.assertEqual(response.health_status, {})
        self.assertEqual(response.capabilities_summary, {})
        self.assertEqual(response.error, "Database unavailable")
    
    def test_execute_handles_health_check_exception(self):
        """Test error handling when health check fails"""
        # Arrange
        request = ServerStatusRequest()
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        self.mock_server.check_health.side_effect = Exception("Health check failed")
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Health check failed")
    
    def test_execute_handles_diagnostics_exception(self):
        """Test error handling when diagnostics service fails"""
        # Arrange
        request = ServerStatusRequest()
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        self.mock_diagnostics_service.get_connection_statistics.side_effect = Exception(
            "Diagnostics unavailable"
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Diagnostics unavailable")
    
    @patch('fastmcp.connection_management.application.use_cases.get_server_status.logger')
    def test_execute_logs_errors(self, mock_logger):
        """Test that errors are properly logged"""
        # Arrange
        request = ServerStatusRequest()
        error_message = "Critical failure"
        self.mock_server_repository.get_current_server.side_effect = Exception(error_message)
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        self.assertIn("Error getting server status", error_call_args)
        self.assertIn(error_message, error_call_args)
    
    def test_execute_with_high_uptime(self):
        """Test server status with high uptime"""
        # Arrange
        request = ServerStatusRequest()
        self.mock_server.get_uptime_seconds.return_value = 86400  # 24 hours
        self.mock_server.restart_count = 5
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.server_info["uptime_seconds"], 86400)
        self.assertEqual(response.server_info["restart_count"], 5)
    
    def test_execute_with_unhealthy_server(self):
        """Test status when server is unhealthy"""
        # Arrange
        request = ServerStatusRequest()
        
        # Configure unhealthy status
        mock_unhealthy_status = Mock(spec=ServerStatus)
        mock_unhealthy_status.to_dict.return_value = {
            "status": "unhealthy",
            "cpu_usage": 95.0,
            "memory_usage": 98.5,
            "active_connections": 0,
            "errors": ["High CPU usage", "Memory threshold exceeded"]
        }
        self.mock_server.check_health.return_value = mock_unhealthy_status
        
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.health_status["status"], "unhealthy")
        self.assertEqual(response.health_status["cpu_usage"], 95.0)
        self.assertEqual(response.health_status["memory_usage"], 98.5)
        self.assertIn("High CPU usage", response.health_status["errors"])
    
    def test_execute_with_no_active_connections(self):
        """Test status when there are no active connections"""
        # Arrange
        request = ServerStatusRequest()
        
        # Configure no active connections
        self.mock_diagnostics_service.get_connection_statistics.return_value = {
            "total_connections": 0,
            "active_connections": 0,
            "total_requests": 0,
            "error_rate": 0.0
        }
        
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.connection_stats["active_connections"], 0)
        self.assertEqual(response.connection_stats["total_connections"], 0)
    
    def test_execute_with_disabled_authentication(self):
        """Test status when authentication is disabled"""
        # Arrange
        request = ServerStatusRequest()
        
        # Configure disabled authentication
        self.mock_capabilities.authentication_enabled = False
        
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertFalse(response.capabilities_summary["authentication_enabled"])
    
    def test_execute_validates_response_structure(self):
        """Test that response structure adheres to DTO specification"""
        # Arrange
        request = ServerStatusRequest()
        self.mock_server_repository.get_current_server.return_value = self.mock_server
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert - Validate response structure
        self.assertIsInstance(response, ServerStatusResponse)
        self.assertIsInstance(response.success, bool)
        self.assertIsInstance(response.server_info, dict)
        self.assertIsInstance(response.connection_stats, dict)
        self.assertIsInstance(response.health_status, dict)
        self.assertIsInstance(response.capabilities_summary, dict)
        
        # Validate server_info structure
        self.assertIn("name", response.server_info)
        self.assertIn("version", response.server_info)
        self.assertIn("uptime_seconds", response.server_info)
        self.assertIn("restart_count", response.server_info)
        
        # Validate capabilities_summary structure
        self.assertIn("total_features", response.capabilities_summary)
        self.assertIn("total_actions", response.capabilities_summary)
        self.assertIn("authentication_enabled", response.capabilities_summary)
    
    def test_execute_with_server_creation_failure(self):
        """Test handling when server creation fails"""
        # Arrange
        request = ServerStatusRequest()
        
        # Configure no existing server and creation failure
        self.mock_server_repository.get_current_server.return_value = None
        self.mock_health_service.get_environment_info.return_value = {}
        self.mock_health_service.get_authentication_status.return_value = {}
        self.mock_health_service.get_task_management_info.return_value = {}
        
        self.mock_server_repository.create_server.side_effect = Exception(
            "Server creation failed"
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Server creation failed")


if __name__ == '__main__':
    unittest.main()