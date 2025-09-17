"""Test secure health check implementation"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastmcp.connection_management.infrastructure.services.mcp_server_health_service import MCPServerHealthService
from fastmcp.connection_management.interface.controllers.connection_mcp_controller import ConnectionMCPController
from fastmcp.connection_management.application.facades.connection_application_facade import ConnectionApplicationFacade


class TestSecureHealthCheck:
    """Test that health check doesn't expose sensitive information"""
    
    def test_environment_info_doesnt_expose_paths(self):
        """Test that environment info doesn't expose sensitive paths"""
        service = MCPServerHealthService()
        
        # Set some sensitive environment variables
        with patch.dict(os.environ, {
            "PYTHONPATH": "/secret/path/to/python",
            "TASKS_JSON_PATH": "/secret/data/tasks.json",
            "PROJECTS_FILE_PATH": "/secret/data/projects.json",
            "AGENT_LIBRARY_DIR_PATH": "/secret/agent/library",
            "DATABASE_URL": "postgresql://user:password@localhost/db",
            "SUPABASE_URL": "https://secret.supabase.co",
            "SECRET_KEY": "super-secret-key-123",
            "API_KEY": "secret-api-key-456"
        }):
            env_info = service.get_environment_info()
            
            # Verify no paths are exposed
            assert "pythonpath" not in env_info
            assert "tasks_json_path" not in env_info
            assert "projects_file_path" not in env_info
            assert "agent_library_dir" not in env_info
            
            # Verify no URLs are exposed
            assert "DATABASE_URL" not in str(env_info)
            assert "SUPABASE_URL" not in str(env_info)
            assert "postgresql://" not in str(env_info)
            assert "supabase.co" not in str(env_info)
            
            # Verify no secrets are exposed
            assert "SECRET_KEY" not in str(env_info)
            assert "API_KEY" not in str(env_info)
            assert "super-secret-key" not in str(env_info)
            assert "secret-api-key" not in str(env_info)
            
            # Verify only safe flags are present
            assert "auth_enabled" in env_info
            assert "cursor_tools_disabled" in env_info
            assert "mvp_mode" in env_info
            assert "database_configured" in env_info
            assert isinstance(env_info["database_configured"], bool)
    
    def test_validate_configuration_doesnt_expose_errors(self):
        """Test that configuration validation doesn't expose error details"""
        service = MCPServerHealthService()
        
        # Test that even when there's an internal import error, it doesn't expose details
        # The validate_server_configuration method catches all exceptions and returns safe data
        config_info = service.validate_server_configuration()
        
        # Verify no sensitive error details are exposed
        assert "Exception" not in str(config_info)
        assert "password" not in str(config_info).lower()
        assert "secret" not in str(config_info).lower()
        
        # Should return either healthy status or generic error
        if "status" in config_info:
            assert config_info["status"] in ["healthy", "configuration_error"]
            # If error, should have generic message
            if config_info["status"] == "configuration_error":
                assert config_info.get("message") == "Unable to validate configuration"
                # Should not have detailed error info
                assert "traceback" not in str(config_info).lower()
                assert "exception" not in str(config_info).lower()
    
    def test_controller_sanitizes_response(self):
        """Test that controller properly sanitizes the response"""
        # Create mock facade
        mock_facade = Mock(spec=ConnectionApplicationFacade)
        
        # Create response with sensitive data
        mock_response = Mock()
        mock_response.success = True
        mock_response.status = "healthy"
        mock_response.server_name = "Test Server"
        mock_response.version = "1.0.0"
        mock_response.timestamp = 1234567890
        mock_response.authentication = {
            "enabled": True,
            "mvp_mode": False,
            "secret_token": "should-not-appear",  # Sensitive
            "api_key": "secret-key"  # Sensitive
        }
        mock_response.environment = {
            "auth_enabled": True,
            "database_configured": True,
            "PYTHONPATH": "/secret/path",  # Should be filtered
            "SECRET_KEY": "secret-value"  # Should be filtered
        }
        mock_response.connections = {
            "active_connections": 5,
            "status": "healthy",
            "internal_error": "Database connection failed with password xyz",  # Should be filtered
            "connection_string": "postgresql://user:pass@host/db"  # Should be filtered
        }
        
        mock_facade.check_server_health.return_value = mock_response
        
        # Create controller and call health check
        controller = ConnectionMCPController(mock_facade)
        result = controller.health_check(include_details=True)
        
        # Verify sanitization
        assert result["success"] is True
        assert result["status"] == "healthy"
        
        # Check authentication - only safe fields
        if "authentication" in result:
            assert "enabled" in result["authentication"]
            assert "mvp_mode" in result["authentication"]
            assert "secret_token" not in result["authentication"]
            assert "api_key" not in result["authentication"]
        
        # Check environment - only allowed keys
        if "environment" in result:
            assert "auth_enabled" in result["environment"] or "database_configured" in result["environment"]
            assert "PYTHONPATH" not in result["environment"]
            assert "SECRET_KEY" not in result["environment"]
        
        # Check connections - only safe fields
        if "connections" in result:
            assert "active_connections" in result["connections"] or "status" in result["connections"]
            assert "internal_error" not in result["connections"]
            assert "connection_string" not in result["connections"]
            assert "password" not in str(result["connections"])
    
    def test_error_handling_doesnt_expose_details(self):
        """Test that error handling doesn't expose sensitive details"""
        mock_facade = Mock(spec=ConnectionApplicationFacade)
        mock_facade.check_server_health.side_effect = Exception("Database password is incorrect: mypassword123")
        
        controller = ConnectionMCPController(mock_facade)
        result = controller.health_check()
        
        # Verify error is generic
        assert result["success"] is False
        assert result["status"] == "error"
        assert "message" in result
        assert result["message"] == "Health check temporarily unavailable"
        
        # Verify no sensitive info in error
        assert "password" not in str(result).lower()
        assert "mypassword123" not in str(result)
        assert "Database" not in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])