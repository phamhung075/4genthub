"""
Comprehensive Unit Tests for Connection Application Facade

This module tests the ConnectionApplicationFacade which serves as the main entry point
for connection management operations, coordinating multiple use cases and handling
cross-cutting concerns following DDD patterns.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import logging
from typing import Dict, Any

from fastmcp.connection_management.application.facades.connection_application_facade import ConnectionApplicationFacade
from fastmcp.connection_management.application.dtos.connection_dtos import (
    HealthCheckRequest, HealthCheckResponse,
    ServerCapabilitiesRequest, ServerCapabilitiesResponse,
    ConnectionHealthRequest, ConnectionHealthResponse,
    ServerStatusRequest, ServerStatusResponse,
    RegisterUpdatesRequest, RegisterUpdatesResponse
)
from fastmcp.connection_management.domain.repositories.server_repository import ServerRepository
from fastmcp.connection_management.domain.repositories.connection_repository import ConnectionRepository
from fastmcp.connection_management.domain.services.server_health_service import ServerHealthService
from fastmcp.connection_management.domain.services.connection_diagnostics_service import ConnectionDiagnosticsService
from fastmcp.connection_management.domain.services.status_broadcasting_service import StatusBroadcastingService


class TestConnectionApplicationFacade:
    """Test suite for ConnectionApplicationFacade"""
    
    @pytest.fixture
    def server_repository(self):
        """Mock server repository"""
        return Mock(spec=ServerRepository)
    
    @pytest.fixture  
    def connection_repository(self):
        """Mock connection repository"""
        return Mock(spec=ConnectionRepository)
    
    @pytest.fixture
    def health_service(self):
        """Mock server health service"""
        return Mock(spec=ServerHealthService)
    
    @pytest.fixture
    def diagnostics_service(self):
        """Mock connection diagnostics service"""
        return Mock(spec=ConnectionDiagnosticsService)
    
    @pytest.fixture
    def broadcasting_service(self):
        """Mock status broadcasting service"""
        return Mock(spec=StatusBroadcastingService)
    
    @pytest.fixture
    def facade(self, server_repository, connection_repository, health_service, 
              diagnostics_service, broadcasting_service):
        """Create ConnectionApplicationFacade instance for testing"""
        return ConnectionApplicationFacade(
            server_repository=server_repository,
            connection_repository=connection_repository,
            health_service=health_service,
            diagnostics_service=diagnostics_service,
            broadcasting_service=broadcasting_service
        )
    
    def test_facade_initialization(self, facade, server_repository, connection_repository, 
                                  health_service, diagnostics_service, broadcasting_service):
        """Test facade initializes correctly with all dependencies"""
        assert facade._server_repository == server_repository
        assert facade._connection_repository == connection_repository
        assert facade._health_service == health_service
        assert facade._diagnostics_service == diagnostics_service
        assert facade._broadcasting_service == broadcasting_service
        
        # Verify use cases are initialized
        assert facade._check_health_use_case is not None
        assert facade._get_capabilities_use_case is not None
        assert facade._check_connection_health_use_case is not None
        assert facade._get_status_use_case is not None
        assert facade._register_updates_use_case is not None
    
    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_facade_initialization_logging(
        self, mock_logger, server_repository, connection_repository,
        health_service, diagnostics_service, broadcasting_service
    ):
        """Test facade logs initialization"""
        # Create facade after patching logger
        facade = ConnectionApplicationFacade(
            server_repository=server_repository,
            connection_repository=connection_repository,
            health_service=health_service,
            diagnostics_service=diagnostics_service,
            broadcasting_service=broadcasting_service
        )
        
        # Verify initialization log was called
        mock_logger.info.assert_called_with("ConnectionApplicationFacade initialized")


class TestCheckServerHealth:
    """Test suite for check_server_health method"""
    
    @pytest.fixture
    def facade(self, server_repository, connection_repository, health_service, 
              diagnostics_service, broadcasting_service):
        """Create facade for testing"""
        return ConnectionApplicationFacade(
            server_repository, connection_repository, health_service,
            diagnostics_service, broadcasting_service
        )
    
    def test_check_server_health_success(self, facade):
        """Test successful server health check"""
        # Arrange
        expected_response = HealthCheckResponse(
            success=True,
            status="healthy",
            server_name="test-server",
            version="1.0.0",
            uptime_seconds=3600,
            restart_count=0,
            authentication={"enabled": True},
            task_management={"active_tasks": 5},
            environment={"mode": "production"},
            connections={"active": 10},
            timestamp=1234567890
        )
        
        facade._check_health_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.check_server_health(include_details=True, user_id="test-user")
        
        # Assert
        assert result == expected_response
        facade._check_health_use_case.execute.assert_called_once()
        
        # Verify request was created correctly
        call_args = facade._check_health_use_case.execute.call_args[0][0]
        assert isinstance(call_args, HealthCheckRequest)
        assert call_args.include_details is True
    
    def test_check_server_health_with_defaults(self, facade):
        """Test server health check with default parameters"""
        # Arrange
        expected_response = HealthCheckResponse(
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
            timestamp=1234567890
        )
        
        facade._check_health_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.check_server_health()
        
        # Assert
        assert result == expected_response
        call_args = facade._check_health_use_case.execute.call_args[0][0]
        assert call_args.include_details is True  # Default value
    
    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_check_server_health_exception_handling(self, mock_logger, facade):
        """Test exception handling in server health check"""
        # Arrange
        error_message = "Database connection failed"
        facade._check_health_use_case.execute = Mock(side_effect=Exception(error_message))
        
        # Act
        result = facade.check_server_health(include_details=True, user_id="test-user")
        
        # Assert
        assert result.success is False
        assert result.status == "error"
        assert result.server_name == "Unknown"
        assert result.version == "Unknown"
        assert result.uptime_seconds == 0
        assert result.restart_count == 0
        assert result.error == error_message
        
        # Verify error logging
        mock_logger.error.assert_called_once_with(f"Error in check_server_health: {error_message}")


class TestGetServerCapabilities:
    """Test suite for get_server_capabilities method"""
    
    @pytest.fixture
    def facade(self, server_repository, connection_repository, health_service, 
              diagnostics_service, broadcasting_service):
        """Create facade for testing"""
        return ConnectionApplicationFacade(
            server_repository, connection_repository, health_service,
            diagnostics_service, broadcasting_service
        )
    
    def test_get_server_capabilities_success(self, facade):
        """Test successful server capabilities retrieval"""
        # Arrange
        expected_response = ServerCapabilitiesResponse(
            success=True,
            core_features=["authentication", "task_management"],
            available_actions={"create_task": True, "list_tasks": True},
            authentication_enabled=True,
            mvp_mode=False,
            version="1.0.0",
            total_actions=50
        )
        
        facade._get_capabilities_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.get_server_capabilities(include_details=False, user_id="test-user")
        
        # Assert
        assert result == expected_response
        facade._get_capabilities_use_case.execute.assert_called_once()
        
        # Verify request was created correctly
        call_args = facade._get_capabilities_use_case.execute.call_args[0][0]
        assert isinstance(call_args, ServerCapabilitiesRequest)
        assert call_args.include_details is False
    
    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_get_server_capabilities_exception_handling(self, mock_logger, facade):
        """Test exception handling in get server capabilities"""
        # Arrange
        error_message = "Service unavailable"
        facade._get_capabilities_use_case.execute = Mock(side_effect=Exception(error_message))
        
        # Act
        result = facade.get_server_capabilities()
        
        # Assert
        assert result.success is False
        assert result.core_features == []
        assert result.available_actions == {}
        assert result.authentication_enabled is False
        assert result.mvp_mode is False
        assert result.version == "Unknown"
        assert result.total_actions == 0
        assert result.error == error_message
        
        # Verify error logging
        mock_logger.error.assert_called_once_with(f"Error in get_server_capabilities: {error_message}")


class TestCheckConnectionHealth:
    """Test suite for check_connection_health method"""
    
    @pytest.fixture
    def facade(self, server_repository, connection_repository, health_service, 
              diagnostics_service, broadcasting_service):
        """Create facade for testing"""
        return ConnectionApplicationFacade(
            server_repository, connection_repository, health_service,
            diagnostics_service, broadcasting_service
        )
    
    def test_check_connection_health_success(self, facade):
        """Test successful connection health check"""
        # Arrange
        expected_response = ConnectionHealthResponse(
            success=True,
            status="healthy",
            connection_info={"id": "conn-123", "type": "websocket"},
            diagnostics={"latency_ms": 50, "packet_loss": 0},
            recommendations=["Consider connection pooling"]
        )
        
        facade._check_connection_health_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.check_connection_health(
            connection_id="conn-123", 
            include_details=True, 
            user_id="test-user"
        )
        
        # Assert
        assert result == expected_response
        facade._check_connection_health_use_case.execute.assert_called_once()
        
        # Verify request was created correctly
        call_args = facade._check_connection_health_use_case.execute.call_args[0][0]
        assert isinstance(call_args, ConnectionHealthRequest)
        assert call_args.connection_id == "conn-123"
        assert call_args.include_details is True
    
    def test_check_connection_health_no_connection_id(self, facade):
        """Test connection health check without specific connection ID"""
        # Arrange
        expected_response = ConnectionHealthResponse(
            success=True,
            status="healthy",
            connection_info={},
            diagnostics={},
            recommendations=[]
        )
        
        facade._check_connection_health_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.check_connection_health()
        
        # Assert
        assert result == expected_response
        call_args = facade._check_connection_health_use_case.execute.call_args[0][0]
        assert call_args.connection_id is None
    
    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_check_connection_health_exception_handling(self, mock_logger, facade):
        """Test exception handling in connection health check"""
        # Arrange
        error_message = "Connection timeout"
        facade._check_connection_health_use_case.execute = Mock(side_effect=Exception(error_message))
        
        # Act
        result = facade.check_connection_health(connection_id="conn-123")
        
        # Assert
        assert result.success is False
        assert result.status == "error"
        assert result.connection_info == {}
        assert result.diagnostics == {}
        assert result.recommendations == []
        assert result.error == error_message
        
        # Verify error logging
        mock_logger.error.assert_called_once_with(f"Error in check_connection_health: {error_message}")


class TestGetServerStatus:
    """Test suite for get_server_status method"""
    
    @pytest.fixture
    def facade(self, server_repository, connection_repository, health_service, 
              diagnostics_service, broadcasting_service):
        """Create facade for testing"""
        return ConnectionApplicationFacade(
            server_repository, connection_repository, health_service,
            diagnostics_service, broadcasting_service
        )
    
    def test_get_server_status_success(self, facade):
        """Test successful server status retrieval"""
        # Arrange
        expected_response = ServerStatusResponse(
            success=True,
            server_info={"name": "mcp-server", "version": "1.0.0"},
            connection_stats={"active": 10, "total": 25},
            health_status={"status": "healthy", "uptime": 3600},
            capabilities_summary={"features": 15, "actions": 50}
        )
        
        facade._get_status_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.get_server_status(include_details=True, user_id="test-user")
        
        # Assert
        assert result == expected_response
        facade._get_status_use_case.execute.assert_called_once()
        
        # Verify request was created correctly
        call_args = facade._get_status_use_case.execute.call_args[0][0]
        assert isinstance(call_args, ServerStatusRequest)
        assert call_args.include_details is True
    
    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_get_server_status_exception_handling(self, mock_logger, facade):
        """Test exception handling in get server status"""
        # Arrange
        error_message = "Status service error"
        facade._get_status_use_case.execute = Mock(side_effect=Exception(error_message))
        
        # Act
        result = facade.get_server_status()
        
        # Assert
        assert result.success is False
        assert result.server_info == {}
        assert result.connection_stats == {}
        assert result.health_status == {}
        assert result.capabilities_summary == {}
        assert result.error == error_message
        
        # Verify error logging
        mock_logger.error.assert_called_once_with(f"Error in get_server_status: {error_message}")


class TestRegisterStatusUpdates:
    """Test suite for register_for_status_updates method"""
    
    @pytest.fixture
    def facade(self, server_repository, connection_repository, health_service, 
              diagnostics_service, broadcasting_service):
        """Create facade for testing"""
        return ConnectionApplicationFacade(
            server_repository, connection_repository, health_service,
            diagnostics_service, broadcasting_service
        )
    
    def test_register_for_status_updates_success(self, facade):
        """Test successful status updates registration"""
        # Arrange
        session_id = "session-123"
        client_info = {"user_agent": "test-client", "version": "1.0.0"}
        
        expected_response = RegisterUpdatesResponse(
            success=True,
            session_id=session_id,
            registered=True,
            update_info={"frequency": "real-time", "channels": ["health", "status"]}
        )
        
        facade._register_updates_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.register_for_status_updates(
            session_id=session_id,
            client_info=client_info,
            user_id="test-user"
        )
        
        # Assert
        assert result == expected_response
        facade._register_updates_use_case.execute.assert_called_once()
        
        # Verify request was created correctly
        call_args = facade._register_updates_use_case.execute.call_args[0][0]
        assert isinstance(call_args, RegisterUpdatesRequest)
        assert call_args.session_id == session_id
        assert call_args.client_info == client_info
    
    def test_register_for_status_updates_no_client_info(self, facade):
        """Test status updates registration without client info"""
        # Arrange
        session_id = "session-456"
        
        expected_response = RegisterUpdatesResponse(
            success=True,
            session_id=session_id,
            registered=True,
            update_info={}
        )
        
        facade._register_updates_use_case.execute = Mock(return_value=expected_response)
        
        # Act
        result = facade.register_for_status_updates(session_id=session_id)
        
        # Assert
        assert result == expected_response
        call_args = facade._register_updates_use_case.execute.call_args[0][0]
        assert call_args.session_id == session_id
        assert call_args.client_info is None
    
    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_register_for_status_updates_exception_handling(self, mock_logger, facade):
        """Test exception handling in register status updates"""
        # Arrange
        session_id = "session-error"
        error_message = "Registration service unavailable"
        facade._register_updates_use_case.execute = Mock(side_effect=Exception(error_message))
        
        # Act
        result = facade.register_for_status_updates(session_id=session_id)
        
        # Assert
        assert result.success is False
        assert result.session_id == session_id
        assert result.registered is False
        assert result.update_info == {}
        assert result.error == error_message
        
        # Verify error logging
        mock_logger.error.assert_called_once_with(f"Error in register_for_status_updates: {error_message}")


class TestFacadeIntegration:
    """Integration tests for facade coordination"""
    
    @pytest.fixture
    def facade(self, server_repository, connection_repository, health_service, 
              diagnostics_service, broadcasting_service):
        """Create facade for testing"""
        return ConnectionApplicationFacade(
            server_repository, connection_repository, health_service,
            diagnostics_service, broadcasting_service
        )
    
    def test_facade_coordinates_multiple_operations(self, facade):
        """Test facade can coordinate multiple operations sequentially"""
        # Arrange - mock all use cases
        health_response = HealthCheckResponse(
            success=True, status="healthy", server_name="test", version="1.0.0",
            uptime_seconds=3600, restart_count=0, authentication={}, 
            task_management={}, environment={}, connections={}, timestamp=123456
        )
        capabilities_response = ServerCapabilitiesResponse(
            success=True, core_features=["auth"], available_actions={},
            authentication_enabled=True, mvp_mode=False, version="1.0.0", total_actions=10
        )
        
        facade._check_health_use_case.execute = Mock(return_value=health_response)
        facade._get_capabilities_use_case.execute = Mock(return_value=capabilities_response)
        
        # Act
        health_result = facade.check_server_health()
        capabilities_result = facade.get_server_capabilities()
        
        # Assert
        assert health_result.success is True
        assert capabilities_result.success is True
        assert facade._check_health_use_case.execute.call_count == 1
        assert facade._get_capabilities_use_case.execute.call_count == 1
    
    def test_facade_maintains_use_case_independence(self, facade):
        """Test that use case failures don't affect other operations"""
        # Arrange - one use case fails, others succeed
        facade._check_health_use_case.execute = Mock(side_effect=Exception("Health check failed"))
        facade._get_capabilities_use_case.execute = Mock(return_value=ServerCapabilitiesResponse(
            success=True, core_features=[], available_actions={},
            authentication_enabled=False, mvp_mode=False, version="1.0.0", total_actions=0
        ))
        
        # Act
        health_result = facade.check_server_health()
        capabilities_result = facade.get_server_capabilities()
        
        # Assert
        assert health_result.success is False  # Failed operation
        assert capabilities_result.success is True  # Successful operation
        assert health_result.error == "Health check failed"
        assert capabilities_result.error is None
    
    @patch('fastmcp.connection_management.application.facades.connection_application_facade.logger')
    def test_facade_error_logging_isolation(self, mock_logger, facade):
        """Test that error logging is isolated per operation"""
        # Arrange
        facade._check_health_use_case.execute = Mock(side_effect=Exception("Error 1"))
        facade._get_capabilities_use_case.execute = Mock(side_effect=Exception("Error 2"))
        
        # Act
        facade.check_server_health()
        facade.get_server_capabilities()
        
        # Assert - verify each error was logged separately
        assert mock_logger.error.call_count == 2
        mock_logger.error.assert_any_call("Error in check_server_health: Error 1")
        mock_logger.error.assert_any_call("Error in get_server_capabilities: Error 2")


@pytest.fixture
def server_repository():
    """Fixture for server repository"""
    return Mock(spec=ServerRepository)


@pytest.fixture  
def connection_repository():
    """Fixture for connection repository"""
    return Mock(spec=ConnectionRepository)


@pytest.fixture
def health_service():
    """Fixture for health service"""
    return Mock(spec=ServerHealthService)


@pytest.fixture
def diagnostics_service():
    """Fixture for diagnostics service"""
    return Mock(spec=ConnectionDiagnosticsService)


@pytest.fixture
def broadcasting_service():
    """Fixture for broadcasting service"""
    return Mock(spec=StatusBroadcastingService)