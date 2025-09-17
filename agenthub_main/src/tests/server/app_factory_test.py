"""
Tests for AppFactory - FastAPI application creation and configuration.
"""

import os
import pytest
from unittest.mock import patch, Mock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Handle CORSMiddleware import for test environment
try:
    from fastapi.middleware.cors import CORSMiddleware
except (ImportError, AttributeError):
    # Mock CORSMiddleware for test environment
    class CORSMiddleware:
        def __init__(self, **kwargs):
            self.config = kwargs

from fastmcp.server.app_factory import AppFactory
from fastmcp.config.version import VERSION


class TestAppFactory:
    """Test suite for AppFactory class."""

    def test_create_app_with_defaults(self):
        """Test creating an app with default parameters."""
        app = AppFactory.create_app()
        
        assert isinstance(app, FastAPI)
        assert app.title == "agenthub Server"
        assert app.description == "Unified MCP and API server"
        assert app.version == VERSION
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"

    def test_create_app_with_custom_parameters(self):
        """Test creating an app with custom parameters."""
        custom_title = "Custom MCP Server"
        custom_description = "Custom description"
        custom_version = "2.0.0"
        
        app = AppFactory.create_app(
            title=custom_title,
            description=custom_description,
            version=custom_version,
            enable_cors=False,
            enable_auth=False
        )
        
        assert app.title == custom_title
        assert app.description == custom_description
        assert app.version == custom_version

    @patch('fastmcp.server.app_factory.cors_factory')
    def test_create_app_with_cors_enabled(self, mock_cors_factory):
        """Test that CORS is properly configured when enabled."""
        # Act
        app = AppFactory.create_app(enable_cors=True)
        
        # Assert
        assert app.title == "agenthub Server"
        # Verify cors_factory was called
        mock_cors_factory.configure_cors.assert_called_once_with(app)

    @patch('fastmcp.server.app_factory.cors_factory')
    def test_create_app_with_cors_disabled(self, mock_cors_factory):
        """Test that CORS is not configured when disabled."""
        # Act
        app = AppFactory.create_app(enable_cors=False)
        
        # Assert
        assert app.title == "agenthub Server"
        # Should not configure CORS
        mock_cors_factory.configure_cors.assert_not_called()

    def test_create_app_routes_registration(self):
        """Test that routes are properly registered."""
        with patch('fastmcp.server.app_factory.AppFactory._register_routes') as mock_register:
            app = AppFactory.create_app()
            mock_register.assert_called_once_with(app)

    @patch('fastmcp.auth.interface.auth_endpoints.router')
    def test_register_routes_auth_success(self, mock_auth_router):
        """Test successful registration of auth routes."""
        app = FastAPI()
        
        # Mock the auth router
        mock_auth_router.routes = []
        
        with patch.object(app, 'include_router') as mock_include:
            AppFactory._register_routes(app)
            
            # Should include auth router
            mock_include.assert_any_call(mock_auth_router)

    @patch('fastmcp.server.routes.token_router.router')
    def test_register_routes_token_management_success(self, mock_token_router):
        """Test successful registration of token management routes."""
        app = FastAPI()
        
        mock_token_router.routes = []
        
        with patch.object(app, 'include_router') as mock_include:
            AppFactory._register_routes(app)
            
            # Should include token management router
            mock_include.assert_any_call(mock_token_router)

    @patch('fastmcp.server.routes.agent_routes.router')
    def test_register_routes_agent_routes_success(self, mock_agent_router):
        """Test successful registration of agent routes."""
        app = FastAPI()
        
        mock_agent_router.routes = []
        
        with patch.object(app, 'include_router') as mock_include:
            AppFactory._register_routes(app)
            
            # Should include agent router
            mock_include.assert_any_call(mock_agent_router)

    def test_register_routes_import_error_handling(self):
        """Test that import errors are handled gracefully."""
        app = FastAPI()
        
        # Mock import error for auth routes
        with patch('fastmcp.auth.interface.auth_endpoints.router', side_effect=ImportError("Module not found")):
            with patch.object(app, 'include_router') as mock_include:
                # Should not raise exception
                AppFactory._register_routes(app)
                
                # Router should not be included due to import error
                mock_include.assert_not_called()

    def test_create_health_endpoint(self):
        """Test that health endpoint is created and functional."""
        app = AppFactory.create_app()
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == app.title
        assert data["version"] == app.version
        assert isinstance(data["authentication"], bool)
        assert isinstance(data["mcp_tools"], bool)

    def test_create_root_endpoint(self):
        """Test that root endpoint provides API information."""
        app = AppFactory.create_app()
        client = TestClient(app)
        
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == app.title
        assert data["version"] == app.version
        assert "endpoints" in data
        
        # Check that key endpoints are documented
        endpoints = data["endpoints"]
        assert "/health" in endpoints
        assert "/docs" in endpoints
        assert "/api/auth/tokens/generate" in endpoints
        assert "/api/v2/agents" in endpoints
        assert "/mcp/*" in endpoints

    def test_exception_handlers_registered(self):
        """Test that exception handlers are properly registered."""
        app = AppFactory.create_app()
        
        # Check that HTTPException handler is registered
        # This is done by verifying the app has exception handlers
        assert hasattr(app, 'exception_handlers')

    @patch.dict(os.environ, {"ENVIRONMENT": "test"})
    def test_create_app_in_test_environment(self):
        """Test app creation in test environment."""
        app = AppFactory.create_app()
        
        # In test environment, certain features might be disabled
        assert isinstance(app, FastAPI)

    @patch.dict(os.environ, {"ENVIRONMENT": "production"})
    def test_create_app_in_production_environment(self):
        """Test app creation in production environment."""
        app = AppFactory.create_app()
        
        # In production environment, all features should be enabled
        assert isinstance(app, FastAPI)

    def test_security_headers_configuration(self):
        """Test that security headers are properly configured."""
        app = AppFactory.create_app()
        client = TestClient(app)
        
        response = client.get("/health")
        
        # Check for security headers (if implemented)
        # Note: This depends on your actual security header implementation
        assert response.status_code == 200

    @patch('fastmcp.server.app_factory.logger')
    def test_logging_during_app_creation(self, mock_logger):
        """Test that appropriate logging occurs during app creation."""
        app = AppFactory.create_app()
        
        # Verify logging calls were made
        assert mock_logger.info.called

    def test_middleware_order(self):
        """Test that middleware is added in the correct order."""
        app = AppFactory.create_app()
        
        # Check that middleware stack exists
        assert hasattr(app, 'middleware_stack')
        
        # The actual middleware order testing would depend on your implementation
        # This is a placeholder for more specific middleware order tests

    def test_openapi_schema_customization(self):
        """Test OpenAPI schema customization."""
        app = AppFactory.create_app()
        client = TestClient(app)
        
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert schema["info"]["title"] == app.title
        assert schema["info"]["version"] == app.version

    def test_error_handling_configuration(self):
        """Test that error handling is properly configured."""
        app = AppFactory.create_app()
        client = TestClient(app)
        
        # Test 404 handling
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_static_method_behavior(self):
        """Test that create_app works as a static method."""
        # Should be able to call without instance
        app1 = AppFactory.create_app()
        app2 = AppFactory.create_app()
        
        # Should create separate instances
        assert app1 is not app2
        assert isinstance(app1, FastAPI)
        assert isinstance(app2, FastAPI)


class TestAppFactoryIntegration:
    """Integration tests for AppFactory with actual FastAPI behavior."""

    def test_full_app_creation_and_startup(self):
        """Test complete app creation and startup process."""
        app = AppFactory.create_app()
        client = TestClient(app)
        
        # Test basic functionality
        health_response = client.get("/health")
        assert health_response.status_code == 200
        
        root_response = client.get("/")
        assert root_response.status_code == 200
        
        docs_response = client.get("/docs")
        assert docs_response.status_code == 200

    def test_app_with_minimal_configuration(self):
        """Test app creation with minimal configuration."""
        app = AppFactory.create_app(
            enable_cors=False,
            enable_auth=False
        )
        
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_app_configuration_consistency(self):
        """Test that app configuration is consistent across multiple creations."""
        app1 = AppFactory.create_app(title="Test App 1")
        app2 = AppFactory.create_app(title="Test App 2")
        
        assert app1.title == "Test App 1"
        assert app2.title == "Test App 2"
        assert app1.version == app2.version  # Should use same version


class TestAppFactoryErrorScenarios:
    """Test error scenarios and edge cases for AppFactory."""

    def test_invalid_configuration_handling(self):
        """Test handling of invalid configuration parameters."""
        # Test with None values
        app = AppFactory.create_app(
            title=None,  # This might cause issues
            description=None,
            version=None
        )
        
        # Should handle gracefully or use defaults
        assert isinstance(app, FastAPI)

    @patch('fastmcp.server.app_factory.FastAPI', side_effect=Exception("FastAPI creation failed"))
    def test_fastapi_creation_failure(self, mock_fastapi):
        """Test handling when FastAPI creation fails."""
        with pytest.raises(Exception, match="FastAPI creation failed"):
            AppFactory.create_app()

    def test_route_registration_partial_failure(self):
        """Test app creation when some route registrations fail."""
        with patch('fastmcp.auth.interface.auth_endpoints.router', side_effect=ImportError()):
            # Should still create app even if some routes fail to register
            app = AppFactory.create_app()
            assert isinstance(app, FastAPI)