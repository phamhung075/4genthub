"""Unit tests for ServerHealthService Interface following DDD patterns"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

from fastmcp.connection_management.domain.services.server_health_service import ServerHealthService
from fastmcp.connection_management.domain.entities.server import Server
from fastmcp.connection_management.domain.value_objects.server_status import ServerStatus


class MockServerHealthService(ServerHealthService):
    """Mock implementation of ServerHealthService for testing"""
    
    def __init__(self):
        self.check_server_health_called = False
        self.get_environment_info_called = False
        self.get_authentication_status_called = False
        self.get_task_management_info_called = False
        self.validate_server_configuration_called = False
    
    def check_server_health(self, server: Server) -> ServerStatus:
        """Mock implementation of server health check"""
        self.check_server_health_called = True
        return ServerStatus(
            status="healthy",
            server_name=server.name,
            version="1.0.0",
            uptime_seconds=3600.0,
            restart_count=0,
            details={"memory_usage": "50%", "cpu_usage": "30%"}
        )
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Mock implementation of environment info retrieval"""
        self.get_environment_info_called = True
        return {
            "python_version": "3.9.0",
            "platform": "linux",
            "hostname": "test-server",
            "cpu_count": 4,
            "memory_gb": 16
        }
    
    def get_authentication_status(self) -> Dict[str, Any]:
        """Mock implementation of authentication status retrieval"""
        self.get_authentication_status_called = True
        return {
            "enabled": True,
            "type": "JWT",
            "provider": "Supabase",
            "mvp_mode": False
        }
    
    def get_task_management_info(self) -> Dict[str, Any]:
        """Mock implementation of task management info retrieval"""
        self.get_task_management_info_called = True
        return {
            "total_projects": 5,
            "active_tasks": 12,
            "completed_tasks": 45,
            "database_status": "connected"
        }
    
    def validate_server_configuration(self) -> Dict[str, Any]:
        """Mock implementation of server configuration validation"""
        self.validate_server_configuration_called = True
        return {
            "valid": True,
            "errors": [],
            "warnings": ["Consider enabling SSL"],
            "configuration_complete": True
        }


class TestServerHealthService:
    """Test suite for ServerHealthService interface following DDD patterns"""
    
    def test_interface_methods_exist(self):
        """Test that all required interface methods exist"""
        required_methods = [
            'check_server_health',
            'get_environment_info',
            'get_authentication_status',
            'get_task_management_info',
            'validate_server_configuration'
        ]
        
        for method in required_methods:
            assert hasattr(ServerHealthService, method)
    
    def test_check_server_health_implementation(self):
        """Test check_server_health method implementation"""
        service = MockServerHealthService()
        server = Mock(spec=Server)
        server.name = "test-server"
        
        result = service.check_server_health(server)
        
        assert service.check_server_health_called is True
        assert isinstance(result, ServerStatus)
        assert result.status == "healthy"
        assert result.server_name == "test-server"
        assert result.uptime_seconds == 3600.0
    
    def test_get_environment_info_implementation(self):
        """Test get_environment_info method implementation"""
        service = MockServerHealthService()
        
        result = service.get_environment_info()
        
        assert service.get_environment_info_called is True
        assert isinstance(result, dict)
        assert result["python_version"] == "3.9.0"
        assert result["platform"] == "linux"
        assert result["hostname"] == "test-server"
        assert result["cpu_count"] == 4
        assert result["memory_gb"] == 16
    
    def test_get_authentication_status_implementation(self):
        """Test get_authentication_status method implementation"""
        service = MockServerHealthService()
        
        result = service.get_authentication_status()
        
        assert service.get_authentication_status_called is True
        assert isinstance(result, dict)
        assert result["enabled"] is True
        assert result["type"] == "JWT"
        assert result["provider"] == "Supabase"
        assert result["mvp_mode"] is False
    
    def test_get_task_management_info_implementation(self):
        """Test get_task_management_info method implementation"""
        service = MockServerHealthService()
        
        result = service.get_task_management_info()
        
        assert service.get_task_management_info_called is True
        assert isinstance(result, dict)
        assert result["total_projects"] == 5
        assert result["active_tasks"] == 12
        assert result["completed_tasks"] == 45
        assert result["database_status"] == "connected"
    
    def test_validate_server_configuration_implementation(self):
        """Test validate_server_configuration method implementation"""
        service = MockServerHealthService()
        
        result = service.validate_server_configuration()
        
        assert service.validate_server_configuration_called is True
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == ["Consider enabling SSL"]
        assert result["configuration_complete"] is True
    
    def test_abstract_methods_cannot_be_instantiated(self):
        """Test that abstract ServerHealthService cannot be instantiated directly"""
        with pytest.raises(TypeError):
            # This should fail because ServerHealthService is abstract
            ServerHealthService()
    
    def test_service_integration_workflow(self):
        """Test a complete workflow using the service"""
        service = MockServerHealthService()
        server = Mock(spec=Server)
        server.name = "test-server"
        
        # Perform health check
        health_status = service.check_server_health(server)
        assert health_status.status == "healthy"
        
        # Get environment info
        env_info = service.get_environment_info()
        assert env_info["platform"] in ["linux", "windows", "darwin"]
        
        # Check authentication
        auth_status = service.get_authentication_status()
        assert "enabled" in auth_status
        
        # Get task management info
        task_info = service.get_task_management_info()
        assert "total_projects" in task_info
        
        # Validate configuration
        config_validation = service.validate_server_configuration()
        assert "valid" in config_validation
        
        # Verify all methods were called
        assert service.check_server_health_called is True
        assert service.get_environment_info_called is True
        assert service.get_authentication_status_called is True
        assert service.get_task_management_info_called is True
        assert service.validate_server_configuration_called is True
    
    def test_service_with_unhealthy_server(self):
        """Test service behavior with unhealthy server scenario"""
        class UnhealthyServerHealthService(ServerHealthService):
            def check_server_health(self, server: Server) -> ServerStatus:
                return ServerStatus(
                    status="unhealthy",
                    server_name=server.name,
                    version="unknown",
                    uptime_seconds=0.0,
                    restart_count=5,
                    details={"error": "Server is not responding"}
                )
            
            def get_environment_info(self) -> Dict[str, Any]:
                return {"error": "Cannot retrieve environment info"}
            
            def get_authentication_status(self) -> Dict[str, Any]:
                return {"enabled": False, "error": "Auth service unavailable"}
            
            def get_task_management_info(self) -> Dict[str, Any]:
                return {"database_status": "disconnected", "error": "Database unreachable"}
            
            def validate_server_configuration(self) -> Dict[str, Any]:
                return {
                    "valid": False,
                    "errors": ["Missing configuration file", "Invalid database URL"],
                    "warnings": [],
                    "configuration_complete": False
                }
        
        service = UnhealthyServerHealthService()
        server = Mock(spec=Server)
        server.name = "unhealthy-server"
        
        # Check unhealthy server
        health = service.check_server_health(server)
        assert health.status == "unhealthy"
        assert health.restart_count == 5
        
        # Check error conditions
        env_info = service.get_environment_info()
        assert "error" in env_info
        
        auth_status = service.get_authentication_status()
        assert auth_status["enabled"] is False
        assert "error" in auth_status
        
        task_info = service.get_task_management_info()
        assert task_info["database_status"] == "disconnected"
        
        config = service.validate_server_configuration()
        assert config["valid"] is False
        assert len(config["errors"]) > 0