"""Unit tests for Check Connection Health Use Case"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from fastmcp.connection_management.application.use_cases.check_connection_health import (
    CheckConnectionHealthUseCase
)
from fastmcp.connection_management.application.dtos.connection_dtos import (
    ConnectionHealthRequest,
    ConnectionHealthResponse
)
from fastmcp.connection_management.domain.entities.connection import Connection
from fastmcp.connection_management.domain.value_objects.connection_health import ConnectionHealth


class TestCheckConnectionHealthUseCase(unittest.TestCase):
    """Test suite for CheckConnectionHealthUseCase following DDD patterns"""
    
    def setUp(self):
        """Set up test dependencies"""
        # Mock domain repositories
        self.mock_connection_repository = Mock()
        
        # Mock domain services
        self.mock_diagnostics_service = Mock()
        
        # Create use case instance with mocked dependencies
        self.use_case = CheckConnectionHealthUseCase(
            connection_repository=self.mock_connection_repository,
            diagnostics_service=self.mock_diagnostics_service
        )
        
        # Set up default mock responses
        self.mock_diagnostics_service.get_connection_statistics.return_value = {
            "active_connections": 5,
            "total_requests": 100,
            "error_rate": 0.02
        }
        
        self.mock_diagnostics_service.get_reconnection_recommendations.return_value = {
            "recommendations": ["Optimize connection pooling", "Reduce timeout values"]
        }
    
    def test_execute_with_specific_connection_id_found(self):
        """Test checking health of a specific connection that exists"""
        # Arrange
        connection_id = str(uuid4())
        request = ConnectionHealthRequest(connection_id=connection_id)
        
        # Create mock connection entity
        mock_connection = Mock(spec=Connection)
        mock_health = Mock(spec=ConnectionHealth)
        mock_health.to_dict.return_value = {
            "status": "healthy",
            "latency": 50,
            "uptime": 3600,
            "error_count": 0
        }
        mock_connection.diagnose_health.return_value = mock_health
        
        self.mock_connection_repository.find_by_id.return_value = mock_connection
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ConnectionHealthResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.status, "healthy")
        self.assertEqual(response.connection_info["status"], "healthy")
        self.assertEqual(response.connection_info["latency"], 50)
        self.assertIn("Optimize connection pooling", response.recommendations)
        
        # Verify interactions
        self.mock_connection_repository.find_by_id.assert_called_once_with(connection_id)
        mock_connection.diagnose_health.assert_called_once()
        self.mock_diagnostics_service.get_connection_statistics.assert_called_once()
        self.mock_diagnostics_service.get_reconnection_recommendations.assert_called_once()
    
    def test_execute_with_specific_connection_id_not_found(self):
        """Test checking health when specific connection does not exist"""
        # Arrange
        connection_id = str(uuid4())
        request = ConnectionHealthRequest(connection_id=connection_id)
        
        self.mock_connection_repository.find_by_id.return_value = None
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ConnectionHealthResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.status, "healthy")
        self.assertIn("error", response.connection_info)
        self.assertIn(f"Connection {connection_id} not found", response.connection_info["error"])
        
        # Verify interactions
        self.mock_connection_repository.find_by_id.assert_called_once_with(connection_id)
    
    def test_execute_without_connection_id_general_health(self):
        """Test checking general connection health without specific ID"""
        # Arrange
        request = ConnectionHealthRequest(connection_id=None)
        
        # Create mock active connections
        mock_connections = [Mock(spec=Connection) for _ in range(3)]
        self.mock_connection_repository.find_all_active.return_value = mock_connections
        self.mock_connection_repository.get_connection_count.return_value = 10
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ConnectionHealthResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.status, "healthy")
        self.assertEqual(response.connection_info["active_connections"], 3)
        self.assertEqual(response.connection_info["total_connections"], 10)
        
        # Verify interactions
        self.mock_connection_repository.find_all_active.assert_called_once()
        self.mock_connection_repository.get_connection_count.assert_called_once()
    
    def test_execute_with_no_active_connections(self):
        """Test status when no active connections exist"""
        # Arrange
        request = ConnectionHealthRequest(connection_id=None)
        
        # Configure no active connections
        self.mock_diagnostics_service.get_connection_statistics.return_value = {
            "active_connections": 0,
            "total_requests": 0,
            "error_rate": 0.0
        }
        
        self.mock_connection_repository.find_all_active.return_value = []
        self.mock_connection_repository.get_connection_count.return_value = 0
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ConnectionHealthResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.status, "no_clients")
        self.assertEqual(response.connection_info["active_connections"], 0)
    
    def test_execute_handles_repository_exception(self):
        """Test error handling when repository raises exception"""
        # Arrange
        request = ConnectionHealthRequest(connection_id=str(uuid4()))
        
        self.mock_connection_repository.find_by_id.side_effect = Exception("Database error")
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ConnectionHealthResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.status, "error")
        self.assertEqual(response.error, "Database error")
        self.assertEqual(response.connection_info, {})
        self.assertEqual(response.diagnostics, {})
        self.assertEqual(response.recommendations, [])
    
    def test_execute_handles_diagnostics_service_exception(self):
        """Test error handling when diagnostics service raises exception"""
        # Arrange
        request = ConnectionHealthRequest(connection_id=None)
        
        self.mock_diagnostics_service.get_connection_statistics.side_effect = Exception(
            "Diagnostics unavailable"
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, ConnectionHealthResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.status, "error")
        self.assertEqual(response.error, "Diagnostics unavailable")
    
    @patch('fastmcp.connection_management.application.use_cases.check_connection_health.logger')
    def test_execute_logs_errors(self, mock_logger):
        """Test that errors are properly logged"""
        # Arrange
        request = ConnectionHealthRequest(connection_id=str(uuid4()))
        error_message = "Critical system failure"
        
        self.mock_connection_repository.find_by_id.side_effect = Exception(error_message)
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        self.assertIn("Error checking connection health", error_call_args)
        self.assertIn(error_message, error_call_args)
    
    def test_execute_with_include_details_parameter(self):
        """Test execution with optional include_details parameter"""
        # Arrange
        request = ConnectionHealthRequest(
            connection_id=None,
            include_details=True  # Optional parameter if supported
        )
        
        mock_connections = [Mock(spec=Connection) for _ in range(2)]
        self.mock_connection_repository.find_all_active.return_value = mock_connections
        self.mock_connection_repository.get_connection_count.return_value = 5
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertIsNotNone(response.diagnostics)
        self.assertIsNotNone(response.recommendations)
    
    def test_execute_with_empty_recommendations(self):
        """Test handling of empty recommendations from diagnostics service"""
        # Arrange
        request = ConnectionHealthRequest(connection_id=None)
        
        # Configure empty recommendations
        self.mock_diagnostics_service.get_reconnection_recommendations.return_value = {}
        
        mock_connections = [Mock(spec=Connection)]
        self.mock_connection_repository.find_all_active.return_value = mock_connections
        self.mock_connection_repository.get_connection_count.return_value = 1
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.recommendations, [])
    
    def test_execute_validates_connection_health_response_structure(self):
        """Test that response structure adheres to DTO specification"""
        # Arrange
        request = ConnectionHealthRequest(connection_id=None)
        
        mock_connections = []
        self.mock_connection_repository.find_all_active.return_value = mock_connections
        self.mock_connection_repository.get_connection_count.return_value = 0
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert - Validate response structure
        self.assertIsInstance(response, ConnectionHealthResponse)
        self.assertIsInstance(response.success, bool)
        self.assertIsInstance(response.status, str)
        self.assertIsInstance(response.connection_info, dict)
        self.assertIsInstance(response.diagnostics, dict)
        self.assertIsInstance(response.recommendations, list)
        
        # Verify optional error field is None when successful
        if response.success:
            self.assertIsNone(getattr(response, 'error', None))


if __name__ == '__main__':
    unittest.main()