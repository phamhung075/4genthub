"""Tests for Simplified ConnectionMCPController"""

import pytest
from unittest.mock import Mock, patch

from fastmcp.connection_management.interface.controllers.connection_mcp_controller import ConnectionMCPController
from fastmcp.connection_management.application.dtos.connection_dtos import HealthCheckResponse


class TestConnectionMCPController:
    """Test suite for Simplified ConnectionMCPController"""

    @pytest.fixture
    def mock_connection_facade(self):
        """Create mock connection facade"""
        facade = Mock()
        # Setup default successful health check response
        facade.check_server_health.return_value = HealthCheckResponse(
            success=True, status="healthy", server_name="test", version="1.0.0",
            uptime_seconds=3600, restart_count=0, authentication={}, 
            task_management={}, environment={}, connections={}, timestamp=123456789
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

    def test_health_check_success(self, controller, mock_connection_facade):
        """Test successful health check"""
        result = controller.health_check(include_details=True)
        
        assert result["success"] is True
        assert result["status"] == "healthy"
        assert result["server_name"] == "test"
        assert result["version"] == "1.0.0"
        mock_connection_facade.check_server_health.assert_called_once_with(True, None)

    def test_health_check_without_details(self, controller, mock_connection_facade):
        """Test health check without details"""
        result = controller.health_check(include_details=False)
        
        assert result["success"] is True
        mock_connection_facade.check_server_health.assert_called_once_with(False, None)

    def test_health_check_with_user_id(self, controller, mock_connection_facade):
        """Test health check with user_id parameter"""
        test_user_id = "user-123"
        
        result = controller.health_check(user_id=test_user_id)
        
        assert result["success"] is True
        mock_connection_facade.check_server_health.assert_called_once_with(True, test_user_id)

    def test_health_check_exception_handling(self, controller, mock_connection_facade):
        """Test health check exception handling"""
        mock_connection_facade.check_server_health.side_effect = Exception("Health check failed")

        result = controller.health_check()

        assert result["success"] is False
        assert result["message"] == "Health check temporarily unavailable"  # Sanitized message
        assert result["action"] == "health_check"

    def test_response_formatting_success(self, controller):
        """Test successful health check response formatting"""
        mock_response = HealthCheckResponse(
            success=True, status="healthy", server_name="4genthub", version="1.2.3",
            uptime_seconds=7200, restart_count=1,
            authentication={"enabled": True, "mvp_mode": False},
            task_management={"task_management_enabled": True, "status": "operational"},
            environment={"auth_enabled": True, "database_configured": True},
            connections={"active_connections": 5, "status": "connected"},
            timestamp=1234567890
        )

        formatted = controller._format_health_check_response(mock_response)

        assert formatted["success"] is True
        assert formatted["status"] == "healthy"
        assert formatted["server_name"] == "4genthub"
        assert formatted["version"] == "1.2.3"
        assert formatted["authentication"]["enabled"] is True
        assert formatted["authentication"]["mvp_mode"] is False
        assert formatted["task_management"]["enabled"] is True  # Sanitized response only includes "enabled"
        assert formatted["environment"]["auth_enabled"] is True
        assert formatted["environment"]["database_configured"] is True
        assert formatted["connections"]["active_connections"] == 5
        assert formatted["connections"]["status"] == "connected"
        assert formatted["timestamp"] == 1234567890

    def test_response_formatting_error(self, controller):
        """Test error health check response formatting"""
        mock_response = HealthCheckResponse(
            success=False, status="error", server_name="test", version="1.0.0",
            uptime_seconds=0, restart_count=0, authentication={},
            task_management={}, environment={}, connections={},
            timestamp=123456789, error="Database connection failed"
        )

        formatted = controller._format_health_check_response(mock_response)

        assert formatted["success"] is False
        assert formatted["status"] == "error"
        assert formatted["message"] == "Health check failed"  # Sanitized to generic message
        assert formatted["timestamp"] == 123456789

    @patch('fastmcp.connection_management.interface.controllers.connection_mcp_controller.logger')
    def test_initialization_logging(self, mock_logger, mock_connection_facade):
        """Test that simplified controller initialization is logged"""
        ConnectionMCPController(mock_connection_facade)
        
        mock_logger.info.assert_called_with("Simplified ConnectionMCPController initialized with health check only")

    @patch('fastmcp.connection_management.interface.controllers.connection_mcp_controller.logger')
    def test_error_logging(self, mock_logger, controller, mock_connection_facade):
        """Test that errors are logged"""
        mock_connection_facade.check_server_health.side_effect = Exception("Test error")
        
        controller.health_check()
        
        mock_logger.error.assert_called_with("Error in health_check: Test error")

    def test_register_tools_method_exists(self, controller):
        """Test that register_tools method exists and is callable"""
        assert hasattr(controller, 'register_tools')
        assert callable(controller.register_tools)

    def test_health_check_method_exists(self, controller):
        """Test that health_check method exists and is callable"""
        assert hasattr(controller, 'health_check')
        assert callable(controller.health_check)

    def test_no_deprecated_methods(self, controller):
        """Test that deprecated complex methods have been removed"""
        deprecated_methods = [
            'manage_connection',
            'handle_health_check',
            'handle_server_capabilities',
            'handle_connection_health',
            'handle_server_status',
            'handle_register_updates',
            '_format_server_capabilities_response',
            '_format_connection_health_response',
            '_format_server_status_response',
            '_format_register_updates_response'
        ]
        
        for method_name in deprecated_methods:
            assert not hasattr(controller, method_name), f"Method {method_name} should have been removed"

    def test_only_health_check_functionality(self, controller):
        """Test that controller only provides health check functionality"""
        # Should have these methods
        assert hasattr(controller, 'health_check')
        assert hasattr(controller, '_format_health_check_response')
        assert hasattr(controller, 'register_tools')
        
        # Should not have complex action routing
        assert not hasattr(controller, 'manage_connection')
        
        # Test that it works
        result = controller.health_check()
        assert "success" in result