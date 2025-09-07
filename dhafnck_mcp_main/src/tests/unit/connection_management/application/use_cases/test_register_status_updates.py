"""Unit tests for Register Status Updates Use Case"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from fastmcp.connection_management.application.use_cases.register_status_updates import (
    RegisterStatusUpdatesUseCase
)
from fastmcp.connection_management.application.dtos.connection_dtos import (
    RegisterUpdatesRequest,
    RegisterUpdatesResponse
)
from fastmcp.connection_management.domain.value_objects.status_update import StatusUpdate


class TestRegisterStatusUpdatesUseCase(unittest.TestCase):
    """Test suite for RegisterStatusUpdatesUseCase following DDD patterns"""
    
    def setUp(self):
        """Set up test dependencies"""
        # Mock domain services
        self.mock_broadcasting_service = Mock()
        
        # Create use case instance with mocked dependencies
        self.use_case = RegisterStatusUpdatesUseCase(
            broadcasting_service=self.mock_broadcasting_service
        )
        
        # Set up default mock status update
        self.mock_status_update = Mock(spec=StatusUpdate)
        self.mock_status_update.timestamp = datetime.now()
        self.mock_status_update.event_type = "client_registered"
        self.mock_status_update.session_id = None
        self.mock_status_update.data = {}
        
        # Set up default service responses
        self.mock_broadcasting_service.register_client_for_updates.return_value = (
            self.mock_status_update
        )
        self.mock_broadcasting_service.get_registered_clients_count.return_value = 5
        self.mock_broadcasting_service.get_last_broadcast_info.return_value = {
            "timestamp": "2025-08-29T10:00:00",
            "event_type": "health_check",
            "recipients": 4
        }
    
    def test_execute_successful_registration(self):
        """Test successful client registration for status updates"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, RegisterUpdatesResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.session_id, session_id)
        self.assertTrue(response.registered)
        
        # Verify update info
        self.assertEqual(response.update_info["registered_clients"], 5)
        self.assertEqual(response.update_info["event_type"], "client_registered")
        self.assertIn("registration_time", response.update_info)
        self.assertIn("last_broadcast", response.update_info)
        
        # Verify service interactions
        self.mock_broadcasting_service.register_client_for_updates.assert_called_once()
        call_args = self.mock_broadcasting_service.register_client_for_updates.call_args
        self.assertEqual(call_args[0][0], session_id)
        self.assertIn("session_id", call_args[0][1])
        self.assertIn("registered_at", call_args[0][1])
        
        self.mock_broadcasting_service.get_registered_clients_count.assert_called_once()
        self.mock_broadcasting_service.get_last_broadcast_info.assert_called_once()
    
    def test_execute_with_client_info(self):
        """Test registration with additional client information"""
        # Arrange
        session_id = str(uuid4())
        client_info = {
            "user_agent": "Test Client v1.0",
            "ip_address": "192.168.1.100",
            "client_version": "1.2.3"
        }
        request = RegisterUpdatesRequest(
            session_id=session_id,
            client_info=client_info
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertTrue(response.registered)
        
        # Verify client info was passed to service
        call_args = self.mock_broadcasting_service.register_client_for_updates.call_args
        passed_client_info = call_args[0][1]
        
        self.assertEqual(passed_client_info["user_agent"], "Test Client v1.0")
        self.assertEqual(passed_client_info["ip_address"], "192.168.1.100")
        self.assertEqual(passed_client_info["client_version"], "1.2.3")
        self.assertEqual(passed_client_info["session_id"], session_id)
        self.assertIn("registered_at", passed_client_info)
    
    def test_execute_with_empty_client_info(self):
        """Test registration with no client info provided"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(
            session_id=session_id,
            client_info=None
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        
        # Verify minimal client info was created
        call_args = self.mock_broadcasting_service.register_client_for_updates.call_args
        passed_client_info = call_args[0][1]
        
        self.assertEqual(passed_client_info["session_id"], session_id)
        self.assertIn("registered_at", passed_client_info)
    
    def test_execute_handles_service_exception(self):
        """Test error handling when broadcasting service raises exception"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        
        self.mock_broadcasting_service.register_client_for_updates.side_effect = Exception(
            "Broadcasting service unavailable"
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertIsInstance(response, RegisterUpdatesResponse)
        self.assertFalse(response.success)
        self.assertEqual(response.session_id, session_id)
        self.assertFalse(response.registered)
        self.assertEqual(response.update_info, {})
        self.assertEqual(response.error, "Broadcasting service unavailable")
    
    @patch('fastmcp.connection_management.application.use_cases.register_status_updates.logger')
    def test_execute_logs_errors(self, mock_logger):
        """Test that errors are properly logged"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        error_message = "Registration failed"
        
        self.mock_broadcasting_service.register_client_for_updates.side_effect = Exception(
            error_message
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        self.assertIn("Error registering for status updates", error_call_args)
        self.assertIn(error_message, error_call_args)
    
    def test_execute_with_no_registered_clients(self):
        """Test registration when this is the first client"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        
        # Configure as first client
        self.mock_broadcasting_service.get_registered_clients_count.return_value = 1
        self.mock_broadcasting_service.get_last_broadcast_info.return_value = None
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.update_info["registered_clients"], 1)
        self.assertIsNone(response.update_info["last_broadcast"])
    
    def test_execute_with_multiple_registrations(self):
        """Test handling multiple registration attempts"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        
        # First registration
        response1 = self.use_case.execute(request)
        
        # Configure for second registration
        self.mock_broadcasting_service.get_registered_clients_count.return_value = 5
        
        # Second registration (same session)
        response2 = self.use_case.execute(request)
        
        # Assert both registrations successful
        self.assertTrue(response1.success)
        self.assertTrue(response2.success)
        self.assertEqual(response1.session_id, response2.session_id)
        
        # Verify service was called twice
        self.assertEqual(
            self.mock_broadcasting_service.register_client_for_updates.call_count, 2
        )
    
    def test_execute_with_special_characters_in_session_id(self):
        """Test registration with special characters in session ID"""
        # Arrange
        session_id = "test-session_123!@#$%"
        request = RegisterUpdatesRequest(session_id=session_id)
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertEqual(response.session_id, session_id)
    
    def test_execute_validates_response_structure(self):
        """Test that response structure adheres to DTO specification"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert - Validate response structure
        self.assertIsInstance(response, RegisterUpdatesResponse)
        self.assertIsInstance(response.success, bool)
        self.assertIsInstance(response.session_id, str)
        self.assertIsInstance(response.registered, bool)
        self.assertIsInstance(response.update_info, dict)
        
        # Validate update_info structure
        self.assertIn("registered_clients", response.update_info)
        self.assertIn("last_broadcast", response.update_info)
        self.assertIn("registration_time", response.update_info)
        self.assertIn("event_type", response.update_info)
        
        # Verify types
        self.assertIsInstance(response.update_info["registered_clients"], int)
        self.assertIsInstance(response.update_info["event_type"], str)
        self.assertIsInstance(response.update_info["registration_time"], str)
    
    @patch('fastmcp.connection_management.application.use_cases.register_status_updates.datetime')
    def test_execute_uses_current_timestamp(self, mock_datetime):
        """Test that registration uses current timestamp"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        
        # Configure mock datetime
        mock_now = datetime(2025, 8, 29, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        mock_datetime.now.assert_called()
        
        # Verify timestamp was used in client_info
        call_args = self.mock_broadcasting_service.register_client_for_updates.call_args
        passed_client_info = call_args[0][1]
        self.assertEqual(passed_client_info["registered_at"], mock_now.isoformat())
    
    def test_execute_handles_none_last_broadcast(self):
        """Test handling when there's no last broadcast information"""
        # Arrange
        session_id = str(uuid4())
        request = RegisterUpdatesRequest(session_id=session_id)
        
        # Configure no last broadcast
        self.mock_broadcasting_service.get_last_broadcast_info.return_value = None
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        self.assertIsNone(response.update_info["last_broadcast"])
    
    def test_execute_with_large_client_info(self):
        """Test registration with large client info payload"""
        # Arrange
        session_id = str(uuid4())
        large_client_info = {
            f"field_{i}": f"value_{i}" * 100 for i in range(100)
        }
        request = RegisterUpdatesRequest(
            session_id=session_id,
            client_info=large_client_info
        )
        
        # Act
        response = self.use_case.execute(request)
        
        # Assert
        self.assertTrue(response.success)
        
        # Verify all fields were passed
        call_args = self.mock_broadcasting_service.register_client_for_updates.call_args
        passed_client_info = call_args[0][1]
        
        for i in range(100):
            self.assertIn(f"field_{i}", passed_client_info)


if __name__ == '__main__':
    unittest.main()