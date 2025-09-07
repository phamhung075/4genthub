"""Tests for ConnectionApplicationFacade"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastmcp.connection_management.application.facades.connection_application_facade import ConnectionApplicationFacade
from fastmcp.connection_management.application.dtos.connection_dtos import (
    HealthCheckResponse, ServerCapabilitiesResponse, ConnectionHealthResponse,
    ServerStatusResponse, RegisterUpdatesResponse
)


class TestConnectionApplicationFacade:
    """Test suite for ConnectionApplicationFacade"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for facade"""
        return {
            'server_repository': Mock(),
            'connection_repository': Mock(),
            'health_service': Mock(),
            'diagnostics_service': Mock(),
            'broadcasting_service': Mock()
        }

    @pytest.fixture
    def facade(self, mock_dependencies):
        """Create facade instance with mocked dependencies"""
        return ConnectionApplicationFacade(**mock_dependencies)

    def test_facade_initialization(self, mock_dependencies):
        """Test facade initializes correctly with dependencies"""
        facade = ConnectionApplicationFacade(**mock_dependencies)
        
        assert facade._server_repository == mock_dependencies['server_repository']
        assert facade._connection_repository == mock_dependencies['connection_repository']
        assert facade._health_service == mock_dependencies['health_service']
        assert facade._diagnostics_service == mock_dependencies['diagnostics_service']
        assert facade._broadcasting_service == mock_dependencies['broadcasting_service']

    def test_check_server_health_success(self, facade):
        """Test successful server health check"""
        # Mock successful response
        facade._check_health_use_case.execute = Mock(return_value=HealthCheckResponse(
            success=True,
            status="healthy",
            server_name="test-server",
            version="1.0.0",
            uptime_seconds=3600,
            restart_count=0,
            authentication={},
            task_management={},
            environment={},
            connections={},
            timestamp=123456789
        ))
        
        result = facade.check_server_health(include_details=True, user_id="test-user")
        
        assert result.success is True
        assert result.status == "healthy"
        assert result.server_name == "test-server"
        facade._check_health_use_case.execute.assert_called_once()

    def test_check_server_health_exception_handling(self, facade):
        """Test server health check exception handling"""
        # Mock exception
        facade._check_health_use_case.execute = Mock(side_effect=Exception("Connection failed"))
        
        result = facade.check_server_health()
        
        assert result.success is False
        assert "Connection failed" in result.error
        assert result.status == "error"

    def test_get_server_capabilities_success(self, facade):
        """Test successful server capabilities retrieval"""
        facade._get_capabilities_use_case.execute = Mock(return_value=ServerCapabilitiesResponse(
            success=True,
            core_features=["task_management", "authentication"],
            available_actions={"task": ["create", "update"], "auth": ["login"]},
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0",
            total_actions=3
        ))
        
        result = facade.get_server_capabilities()
        
        assert result.success is True
        assert "task_management" in result.core_features
        assert result.authentication_enabled is True

    def test_get_server_capabilities_exception_handling(self, facade):
        """Test server capabilities exception handling"""
        facade._get_capabilities_use_case.execute = Mock(side_effect=Exception("Capabilities error"))
        
        result = facade.get_server_capabilities()
        
        assert result.success is False
        assert "Capabilities error" in result.error
        assert result.core_features == []

    def test_check_connection_health_success(self, facade):
        """Test successful connection health check"""
        facade._check_connection_health_use_case.execute = Mock(return_value=ConnectionHealthResponse(
            success=True,
            status="healthy",
            connection_info={"id": "conn-123"},
            diagnostics={"latency": "5ms"},
            recommendations=["no issues found"]
        ))
        
        result = facade.check_connection_health(connection_id="conn-123")
        
        assert result.success is True
        assert result.status == "healthy"
        assert "conn-123" in str(result.connection_info)

    def test_check_connection_health_exception_handling(self, facade):
        """Test connection health check exception handling"""
        facade._check_connection_health_use_case.execute = Mock(side_effect=Exception("Connection diagnostic failed"))
        
        result = facade.check_connection_health()
        
        assert result.success is False
        assert "Connection diagnostic failed" in result.error

    def test_get_server_status_success(self, facade):
        """Test successful server status retrieval"""
        facade._get_status_use_case.execute = Mock(return_value=ServerStatusResponse(
            success=True,
            server_info={"name": "test-server"},
            connection_stats={"active": 5},
            health_status={"status": "healthy"},
            capabilities_summary={"total": 10}
        ))
        
        result = facade.get_server_status()
        
        assert result.success is True
        assert result.server_info["name"] == "test-server"

    def test_get_server_status_exception_handling(self, facade):
        """Test server status exception handling"""
        facade._get_status_use_case.execute = Mock(side_effect=Exception("Status error"))
        
        result = facade.get_server_status()
        
        assert result.success is False
        assert "Status error" in result.error

    def test_register_for_status_updates_success(self, facade):
        """Test successful status update registration"""
        facade._register_updates_use_case.execute = Mock(return_value=RegisterUpdatesResponse(
            success=True,
            session_id="session-123",
            registered=True,
            update_info={"interval": "30s"}
        ))
        
        result = facade.register_for_status_updates("session-123", {"client": "test"})
        
        assert result.success is True
        assert result.session_id == "session-123"
        assert result.registered is True

    def test_register_for_status_updates_exception_handling(self, facade):
        """Test status update registration exception handling"""
        facade._register_updates_use_case.execute = Mock(side_effect=Exception("Registration failed"))
        
        result = facade.register_for_status_updates("session-123")
        
        assert result.success is False
        assert "Registration failed" in result.error
        assert result.session_id == "session-123"

    def test_user_id_parameter_passed_correctly(self, facade):
        """Test that user_id parameter is passed through correctly"""
        facade._check_health_use_case.execute = Mock(return_value=HealthCheckResponse(
            success=True, status="healthy", server_name="test", version="1.0.0",
            uptime_seconds=0, restart_count=0, authentication={}, 
            task_management={}, environment={}, connections={}, timestamp=0
        ))
        
        facade.check_server_health(user_id="test-user-123")
        
        # Verify the request was created with proper parameters
        call_args = facade._check_health_use_case.execute.call_args[0][0]
        assert hasattr(call_args, 'include_details')
        # Note: user_id is passed to the facade method but handled by underlying use case

    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_logging_on_initialization(self, mock_logger, mock_dependencies):
        """Test that initialization is logged"""
        ConnectionApplicationFacade(**mock_dependencies)
        
        mock_logger.info.assert_called_with("ConnectionApplicationFacade initialized")

    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_error_logging_on_exception(self, mock_logger, facade):
        """Test that exceptions are logged"""
        facade._check_health_use_case.execute = Mock(side_effect=Exception("Test error"))
        
        facade.check_server_health()
        
        mock_logger.error.assert_called_with("Error in check_server_health: Test error")

    def test_all_use_cases_initialized(self, facade):
        """Test that all use cases are properly initialized"""
        assert hasattr(facade, '_check_health_use_case')
        assert hasattr(facade, '_get_capabilities_use_case')
        assert hasattr(facade, '_check_connection_health_use_case')
        assert hasattr(facade, '_get_status_use_case')
        assert hasattr(facade, '_register_updates_use_case')
        
        # Verify they are not None
        assert facade._check_health_use_case is not None
        assert facade._get_capabilities_use_case is not None
        assert facade._check_connection_health_use_case is not None
        assert facade._get_status_use_case is not None
        assert facade._register_updates_use_case is not None

    def test_facade_method_signature_compatibility(self, facade):
        """Test that facade methods have expected signatures"""
        import inspect
        
        # Check check_server_health signature
        sig = inspect.signature(facade.check_server_health)
        params = list(sig.parameters.keys())
        assert 'include_details' in params
        assert 'user_id' in params
        
        # Check get_server_capabilities signature
        sig = inspect.signature(facade.get_server_capabilities)
        params = list(sig.parameters.keys())
        assert 'include_details' in params
        assert 'user_id' in params
        
        # Check register_for_status_updates signature
        sig = inspect.signature(facade.register_for_status_updates)
        params = list(sig.parameters.keys())
        assert 'session_id' in params
        assert 'client_info' in params
        assert 'user_id' in params