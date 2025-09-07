"""Tests for ConnectionMCPController"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, Union

from fastmcp.connection_management.interface.controllers.connection_mcp_controller import ConnectionMCPController
from fastmcp.connection_management.application.dtos.connection_dtos import (
    HealthCheckResponse, ServerCapabilitiesResponse, ConnectionHealthResponse,
    ServerStatusResponse, RegisterUpdatesResponse
)


class TestConnectionMCPController:
    """Test suite for ConnectionMCPController"""

    @pytest.fixture
    def mock_connection_facade(self):
        """Create mock connection facade"""
        facade = Mock()
        # Setup default successful responses
        facade.check_server_health.return_value = HealthCheckResponse(
            success=True, status="healthy", server_name="test", version="1.0.0",
            uptime_seconds=3600, restart_count=0, authentication={}, 
            task_management={}, environment={}, connections={}, timestamp=123456789
        )
        facade.get_server_capabilities.return_value = ServerCapabilitiesResponse(
            success=True, core_features=[], available_actions={},
            authentication_enabled=True, mvp_mode=False, version="1.0.0", total_actions=5
        )
        facade.check_connection_health.return_value = ConnectionHealthResponse(
            success=True, status="healthy", connection_info={}, 
            diagnostics={}, recommendations=[]
        )
        facade.get_server_status.return_value = ServerStatusResponse(
            success=True, server_info={}, connection_stats={},
            health_status={}, capabilities_summary={}
        )
        facade.register_for_status_updates.return_value = RegisterUpdatesResponse(
            success=True, session_id="session-123", registered=True, update_info={}
        )
        return facade

    @pytest.fixture
    def controller(self, mock_connection_facade):
        """Create controller instance with mocked facade"""
        return ConnectionMCPController(mock_connection_facade)

    def test_controller_initialization(self, mock_connection_facade):
        """Test controller initializes correctly with facade"""
        controller = ConnectionMCPController(mock_connection_facade)
        
        assert controller._connection_facade == mock_connection_facade

    def test_manage_connection_health_check_success(self, controller, mock_connection_facade):
        """Test successful health check action"""
        result = controller.manage_connection(action="health_check", include_details=True)
        
        assert result["success"] is True
        assert result["status"] == "healthy"
        mock_connection_facade.check_server_health.assert_called_once_with(True, None)

    def test_manage_connection_server_capabilities_success(self, controller, mock_connection_facade):
        """Test successful server capabilities action"""
        result = controller.manage_connection(action="server_capabilities", include_details=False)
        
        assert result["success"] is True
        assert "core_features" in result
        mock_connection_facade.get_server_capabilities.assert_called_once_with(False, None)

    def test_manage_connection_connection_health_success(self, controller, mock_connection_facade):
        """Test successful connection health action"""
        result = controller.manage_connection(
            action="connection_health", 
            connection_id="conn-123",
            include_details=True
        )
        
        assert result["success"] is True
        assert result["status"] == "healthy"
        mock_connection_facade.check_connection_health.assert_called_once_with("conn-123", True, None)

    def test_manage_connection_status_success(self, controller, mock_connection_facade):
        """Test successful status action"""
        result = controller.manage_connection(action="status", include_details=True)
        
        assert result["success"] is True
        assert "server_info" in result
        mock_connection_facade.get_server_status.assert_called_once_with(True, None)

    def test_manage_connection_register_updates_success(self, controller, mock_connection_facade):
        """Test successful register updates action"""
        client_info = {"type": "test-client", "version": "1.0"}
        result = controller.manage_connection(
            action="register_updates",
            session_id="session-123", 
            client_info=client_info
        )
        
        assert result["success"] is True
        assert result["session_id"] == "session-123"
        mock_connection_facade.register_for_status_updates.assert_called_once_with(
            "session-123", client_info, None
        )

    def test_manage_connection_register_updates_default_session(self, controller, mock_connection_facade):
        """Test register updates action with default session ID"""
        result = controller.manage_connection(action="register_updates")
        
        assert result["success"] is True
        mock_connection_facade.register_for_status_updates.assert_called_once_with(
            "default_session", None, None
        )

    def test_manage_connection_invalid_action(self, controller):
        """Test invalid action handling"""
        result = controller.manage_connection(action="invalid_action")
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        assert "invalid_action" in result["error"]
        assert "available_actions" in result
        
        expected_actions = ["health_check", "server_capabilities", "connection_health", "status", "register_updates"]
        for action in expected_actions:
            assert action in result["available_actions"]

    def test_manage_connection_user_id_propagation(self, controller, mock_connection_facade):
        """Test user_id parameter is propagated correctly"""
        test_user_id = "user-123"
        
        controller.manage_connection(action="health_check", user_id=test_user_id)
        
        mock_connection_facade.check_server_health.assert_called_once_with(True, test_user_id)

    def test_client_info_json_string_parsing(self, controller, mock_connection_facade):
        """Test client_info JSON string parsing"""
        client_info_json = '{"type": "test", "version": "1.0"}'
        
        result = controller.manage_connection(
            action="register_updates",
            session_id="session-123",
            client_info=client_info_json
        )
        
        assert result["success"] is True
        # Verify the parsed dict was passed to facade
        call_args = mock_connection_facade.register_for_status_updates.call_args[0]
        assert call_args[1] == {"type": "test", "version": "1.0"}

    def test_client_info_invalid_json_handling(self, controller):
        """Test invalid JSON in client_info parameter"""
        invalid_json = '{"invalid": json}'
        
        result = controller.manage_connection(
            action="register_updates",
            client_info=invalid_json
        )
        
        assert result["success"] is False
        assert "INVALID_PARAMETER_FORMAT" in result["error_code"]
        assert "client_info" in result["error"]

    def test_handle_health_check_exception(self, controller, mock_connection_facade):
        """Test health check exception handling"""
        mock_connection_facade.check_server_health.side_effect = Exception("Health check failed")
        
        result = controller.handle_health_check()
        
        assert result["success"] is False
        assert "Health check failed" in result["error"]
        assert result["action"] == "health_check"

    def test_handle_server_capabilities_exception(self, controller, mock_connection_facade):
        """Test server capabilities exception handling"""
        mock_connection_facade.get_server_capabilities.side_effect = Exception("Capabilities failed")
        
        result = controller.handle_server_capabilities()
        
        assert result["success"] is False
        assert "Capabilities failed" in result["error"]
        assert result["action"] == "server_capabilities"

    def test_handle_connection_health_exception(self, controller, mock_connection_facade):
        """Test connection health exception handling"""
        mock_connection_facade.check_connection_health.side_effect = Exception("Connection failed")
        
        result = controller.handle_connection_health()
        
        assert result["success"] is False
        assert "Connection failed" in result["error"]
        assert result["action"] == "connection_health"

    def test_handle_server_status_exception(self, controller, mock_connection_facade):
        """Test server status exception handling"""
        mock_connection_facade.get_server_status.side_effect = Exception("Status failed")
        
        result = controller.handle_server_status()
        
        assert result["success"] is False
        assert "Status failed" in result["error"]
        assert result["action"] == "status"

    def test_handle_register_updates_exception(self, controller, mock_connection_facade):
        """Test register updates exception handling"""
        mock_connection_facade.register_for_status_updates.side_effect = Exception("Registration failed")
        
        result = controller.handle_register_updates("session-123")
        
        assert result["success"] is False
        assert "Registration failed" in result["error"]
        assert result["action"] == "register_updates"

    def test_manage_connection_general_exception(self, controller):
        """Test general exception handling in manage_connection"""
        with patch.object(controller, 'handle_health_check', side_effect=Exception("Unexpected error")):
            result = controller.manage_connection(action="health_check")
            
            assert result["success"] is False
            assert "Unexpected error" in result["error"]
            assert result["action"] == "health_check"

    def test_response_formatting_health_check(self, controller):
        """Test health check response formatting"""
        # Create a mock response with error
        mock_response = HealthCheckResponse(
            success=False, status="error", server_name="test", version="1.0.0",
            uptime_seconds=0, restart_count=0, authentication={}, 
            task_management={}, environment={}, connections={}, 
            timestamp=123456789, error="Test error"
        )
        
        formatted = controller._format_health_check_response(mock_response)
        
        assert formatted["success"] is False
        assert formatted["status"] == "error"
        assert formatted["error"] == "Test error"

    def test_response_formatting_server_capabilities(self, controller):
        """Test server capabilities response formatting"""
        mock_response = ServerCapabilitiesResponse(
            success=True, core_features=["auth", "task"], available_actions={"test": ["action"]},
            authentication_enabled=True, mvp_mode=False, version="1.0.0", total_actions=1
        )
        
        formatted = controller._format_server_capabilities_response(mock_response)
        
        assert formatted["success"] is True
        assert formatted["core_features"] == ["auth", "task"]
        assert formatted["available_actions"] == {"test": ["action"]}
        assert formatted["authentication_enabled"] is True

    def test_response_formatting_connection_health(self, controller):
        """Test connection health response formatting"""
        mock_response = ConnectionHealthResponse(
            success=True, status="healthy", connection_info={"id": "conn-123"},
            diagnostics={"latency": "5ms"}, recommendations=["all good"]
        )
        
        formatted = controller._format_connection_health_response(mock_response)
        
        assert formatted["success"] is True
        assert formatted["status"] == "healthy"
        assert formatted["connection_info"]["id"] == "conn-123"

    def test_response_formatting_server_status(self, controller):
        """Test server status response formatting"""
        mock_response = ServerStatusResponse(
            success=True, server_info={"name": "test"}, connection_stats={"active": 5},
            health_status={"status": "healthy"}, capabilities_summary={"total": 10}
        )
        
        formatted = controller._format_server_status_response(mock_response)
        
        assert formatted["success"] is True
        assert formatted["server_info"]["name"] == "test"
        assert formatted["connection_stats"]["active"] == 5

    def test_response_formatting_register_updates(self, controller):
        """Test register updates response formatting"""
        mock_response = RegisterUpdatesResponse(
            success=True, session_id="session-123", registered=True,
            update_info={"interval": "30s"}
        )
        
        formatted = controller._format_register_updates_response(mock_response)
        
        assert formatted["success"] is True
        assert formatted["session_id"] == "session-123"
        assert formatted["registered"] is True
        assert formatted["update_info"]["interval"] == "30s"

    @patch('fastmcp.connection_management.interface.controllers.connection_mcp_controller.logger')
    def test_initialization_logging(self, mock_logger, mock_connection_facade):
        """Test that controller initialization is logged"""
        ConnectionMCPController(mock_connection_facade)
        
        mock_logger.info.assert_called_with("ConnectionMCPController initialized")

    @patch('fastmcp.connection_management.interface.controllers.connection_mcp_controller.logger')
    def test_error_logging(self, mock_logger, controller, mock_connection_facade):
        """Test that errors are logged"""
        mock_connection_facade.check_server_health.side_effect = Exception("Test error")
        
        controller.manage_connection(action="health_check")
        
        mock_logger.error.assert_called_with("Error in handle_health_check: Test error")

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable"""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    # Note: The register_tools method uses hardcoded descriptions, 
    # not an external description_loader, so this test was removed