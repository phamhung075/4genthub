"""
Unit tests for CheckServerHealthUseCase - Application Layer

Tests the use case for checking server health, including server creation,
health status retrieval, and error handling.
"""

import pytest
from unittest.mock import Mock, MagicMock
import time

from fastmcp.connection_management.application.use_cases.check_server_health import CheckServerHealthUseCase
from fastmcp.connection_management.application.dtos.connection_dtos import (
    HealthCheckRequest,
    HealthCheckResponse
)
from fastmcp.connection_management.domain.repositories.server_repository import ServerRepository
from fastmcp.connection_management.domain.services.server_health_service import ServerHealthService
from fastmcp.connection_management.domain.entities.server import Server
from fastmcp.connection_management.domain.value_objects.server_status import ServerStatus
from fastmcp.connection_management.domain.exceptions.connection_exceptions import ServerHealthCheckFailedError


@pytest.fixture
def mock_server_repository():
    """Create a mock server repository"""
    repository = Mock(spec=ServerRepository)
    return repository


@pytest.fixture
def mock_health_service():
    """Create a mock health service"""
    service = Mock(spec=ServerHealthService)
    service.get_environment_info.return_value = {
        "platform": "linux",
        "python_version": "3.10.0",
        "working_directory": "/test"
    }
    service.get_authentication_status.return_value = {
        "enabled": True,
        "method": "JWT",
        "status": "configured"
    }
    service.get_task_management_info.return_value = {
        "active_tasks": 5,
        "completed_tasks": 10,
        "total_tasks": 20
    }
    service.validate_server_configuration.return_value = {
        "database": "connected",
        "cache": "connected",
        "mcp_servers": 3
    }
    return service


@pytest.fixture
def check_server_health_use_case(mock_server_repository, mock_health_service):
    """Create a CheckServerHealthUseCase instance with mocked dependencies"""
    return CheckServerHealthUseCase(
        server_repository=mock_server_repository,
        health_service=mock_health_service
    )


@pytest.fixture
def sample_server():
    """Create a sample server for testing"""
    server = Mock(spec=Server)
    server.name = "Test Server"
    server.version = "1.0.0"
    server.environment = {"platform": "linux"}
    server.authentication = {"enabled": True}
    server.task_management = {"active_tasks": 5}
    
    # Mock the check_health method to return a ServerStatus
    server_status = Mock(spec=ServerStatus)
    server_status.status = "healthy"
    server_status.server_name = "Test Server"
    server_status.version = "1.0.0"
    server_status.uptime_seconds = 3600
    server_status.restart_count = 0
    server.check_health.return_value = server_status
    
    return server


class TestCheckServerHealthUseCase:
    """Test the CheckServerHealthUseCase"""
    
    def test_successful_health_check_with_existing_server(
        self,
        check_server_health_use_case,
        mock_server_repository,
        sample_server
    ):
        """Test successful health check with an existing server"""
        # Arrange
        mock_server_repository.get_current_server.return_value = sample_server
        request = HealthCheckRequest(include_details=False)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.status == "healthy"
        assert response.server_name == "Test Server"
        assert response.version == "1.0.0"
        assert response.uptime_seconds == 3600
        assert response.restart_count == 0
        assert response.authentication == {"enabled": True}
        assert response.task_management == {"active_tasks": 5}
        mock_server_repository.save_server.assert_not_called()
    
    def test_successful_health_check_with_details(
        self,
        check_server_health_use_case,
        mock_server_repository,
        mock_health_service,
        sample_server
    ):
        """Test successful health check with additional details requested"""
        # Arrange
        mock_server_repository.get_current_server.return_value = sample_server
        request = HealthCheckRequest(include_details=True)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.connections == {
            "database": "connected",
            "cache": "connected",
            "mcp_servers": 3
        }
        mock_health_service.validate_server_configuration.assert_called_once()
    
    def test_health_check_creates_server_if_none_exists(
        self,
        check_server_health_use_case,
        mock_server_repository,
        mock_health_service
    ):
        """Test health check creates a new server if none exists"""
        # Arrange
        mock_server_repository.get_current_server.return_value = None
        
        # Create a mock server to be returned by create_server
        new_server = Mock(spec=Server)
        new_server.name = "4genthub - Task Management & Agent Orchestration"
        new_server.version = "0.0.2c"
        new_server.environment = {"platform": "linux", "python_version": "3.10.0", "working_directory": "/test"}
        new_server.authentication = {"enabled": True, "method": "JWT", "status": "configured"}
        new_server.task_management = {"active_tasks": 5, "completed_tasks": 10, "total_tasks": 20}
        
        server_status = Mock(spec=ServerStatus)
        server_status.status = "healthy"
        server_status.server_name = new_server.name
        server_status.version = new_server.version
        server_status.uptime_seconds = 0
        server_status.restart_count = 0
        new_server.check_health.return_value = server_status
        
        mock_server_repository.create_server.return_value = new_server
        
        request = HealthCheckRequest(include_details=False)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.server_name == "4genthub - Task Management & Agent Orchestration"
        assert response.version == "0.0.2c"
        mock_server_repository.create_server.assert_called_once_with(
            name="4genthub - Task Management & Agent Orchestration",
            version="0.0.2c",
            environment={"platform": "linux", "python_version": "3.10.0", "working_directory": "/test"},
            authentication={"enabled": True, "method": "JWT", "status": "configured"},
            task_management={"active_tasks": 5, "completed_tasks": 10, "total_tasks": 20}
        )
        mock_server_repository.save_server.assert_called_once_with(new_server)
    
    def test_health_check_handles_connection_info_error(
        self,
        check_server_health_use_case,
        mock_server_repository,
        mock_health_service,
        sample_server
    ):
        """Test health check handles errors when getting connection info"""
        # Arrange
        mock_server_repository.get_current_server.return_value = sample_server
        mock_health_service.validate_server_configuration.side_effect = Exception("Connection error")
        request = HealthCheckRequest(include_details=True)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.status == "healthy"
        assert response.connections == {"error": "Connection error"}
    
    def test_health_check_handles_server_health_check_failure(
        self,
        check_server_health_use_case,
        mock_server_repository,
        sample_server
    ):
        """Test health check handles ServerHealthCheckFailedError"""
        # Arrange
        sample_server.check_health.side_effect = ServerHealthCheckFailedError("Health check failed")
        mock_server_repository.get_current_server.return_value = sample_server
        request = HealthCheckRequest(include_details=False)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.success is False
        assert response.status == "error"
        assert response.server_name == "Unknown"
        assert response.version == "Unknown"
        assert response.error == "Server health check failed: Health check failed"
        assert response.uptime_seconds == 0
        assert response.restart_count == 0
    
    def test_health_check_handles_unexpected_exception(
        self,
        check_server_health_use_case,
        mock_server_repository
    ):
        """Test health check handles unexpected exceptions"""
        # Arrange
        mock_server_repository.get_current_server.side_effect = Exception("Unexpected error")
        request = HealthCheckRequest(include_details=False)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.success is False
        assert response.status == "error"
        assert response.server_name == "Unknown"
        assert response.version == "Unknown"
        assert "Unexpected error" in response.error
        assert response.uptime_seconds == 0
        assert response.restart_count == 0
    
    def test_health_check_response_includes_timestamp(
        self,
        check_server_health_use_case,
        mock_server_repository,
        sample_server
    ):
        """Test that health check response includes a timestamp"""
        # Arrange
        mock_server_repository.get_current_server.return_value = sample_server
        request = HealthCheckRequest(include_details=False)
        
        # Act
        before_time = time.time()
        response = check_server_health_use_case.execute(request)
        after_time = time.time()
        
        # Assert
        assert response.timestamp is not None
        assert before_time <= response.timestamp <= after_time
    
    def test_health_check_with_empty_details(
        self,
        check_server_health_use_case,
        mock_server_repository,
        mock_health_service,
        sample_server
    ):
        """Test health check when service returns empty details"""
        # Arrange
        mock_server_repository.get_current_server.return_value = sample_server
        mock_health_service.validate_server_configuration.return_value = {}
        request = HealthCheckRequest(include_details=True)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.success is True
        assert response.connections == {}
    
    def test_health_check_preserves_server_configuration(
        self,
        check_server_health_use_case,
        mock_server_repository,
        sample_server
    ):
        """Test that health check preserves all server configuration data"""
        # Arrange
        sample_server.environment = {
            "platform": "linux",
            "python_version": "3.10.0",
            "custom_setting": "value"
        }
        sample_server.authentication = {
            "enabled": True,
            "method": "JWT",
            "expires_in": 3600
        }
        sample_server.task_management = {
            "active_tasks": 10,
            "queue_size": 50,
            "worker_count": 4
        }
        mock_server_repository.get_current_server.return_value = sample_server
        request = HealthCheckRequest(include_details=False)
        
        # Act
        response = check_server_health_use_case.execute(request)
        
        # Assert
        assert response.environment == sample_server.environment
        assert response.authentication == sample_server.authentication
        assert response.task_management == sample_server.task_management