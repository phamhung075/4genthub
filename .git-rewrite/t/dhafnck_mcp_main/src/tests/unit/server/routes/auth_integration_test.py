"""
Tests for Auth API Integration

This module tests the authentication endpoints integrated into the MCP server.
Tests cover registration, login, token refresh, and health check endpoints.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from starlette.requests import Request
from starlette.responses import JSONResponse
import json
import sys


class TestAuthIntegrationRoutes:
    """Test suite for auth integration routes."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        return session
    
    @pytest.fixture
    def mock_db_config(self, mock_db_session):
        """Create a mock database config."""
        config = Mock()
        config.get_session = Mock(return_value=mock_db_session)
        return config
    
    @pytest.fixture
    def mock_jwt_service_instance(self):
        """Create a mock JWT service instance for patching."""
        jwt = Mock()
        jwt.create_access_token = Mock(return_value="mock_access_token")
        jwt.create_refresh_token = Mock(return_value="mock_refresh_token")
        jwt.verify_refresh_token = Mock(return_value={"sub": "user123"})
        return jwt
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock Starlette request."""
        request = Mock(spec=Request)
        request.json = AsyncMock()
        return request
    
    def setUp(self):
        """Set up test environment with all necessary mocks."""
        # Ensure the auth modules can be imported before we try to patch them
        self.auth_patches = {}
        
    @pytest.mark.asyncio
    async def test_register_endpoint_success(self, mock_request, mock_db_config, mock_jwt_service_instance):
        """Test successful user registration."""
        mock_request.json.return_value = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "SecurePass123!"
        }
        
        # Setup successful registration result
        mock_user = Mock()
        mock_user.username = "testuser"
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.user = mock_user
        mock_result.error_message = None
        
        mock_auth_instance = Mock()
        mock_auth_instance.register_user = AsyncMock(return_value=mock_result)
        
        with patch('fastmcp.auth.application.services.auth_service.AuthService', return_value=mock_auth_instance):
            with patch('fastmcp.auth.infrastructure.repositories.user_repository.UserRepository'):
                with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_service_instance):
                    with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', return_value=mock_db_config):
                        # Import and call the endpoint
                        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
                        routes = create_auth_integration_routes()
                        
                        # Find register endpoint
                        register_endpoint = None
                        for route in routes:
                            if route.path == "/api/auth/register":
                                register_endpoint = route.endpoint
                                break
                        
                        assert register_endpoint is not None
                        
                        # Call the endpoint
                        response = await register_endpoint(mock_request)
                        
                        # Assertions
                        assert isinstance(response, JSONResponse)
                        assert response.status_code == 200
                        
                        # Check database commit was called
                        mock_db_config.get_session().commit.assert_called_once()
                        mock_db_config.get_session().close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_endpoint_failure(self, mock_request, mock_db_config, mock_jwt_service_instance):
        """Test failed user registration."""
        mock_request.json.return_value = {
            "email": "existing@example.com",
            "username": "existinguser", 
            "password": "password"
        }
        
        # Setup failed registration result
        mock_result = Mock()
        mock_result.success = False
        mock_result.user = None
        mock_result.error_message = "User already exists"
        
        mock_auth_instance = Mock()
        mock_auth_instance.register_user = AsyncMock(return_value=mock_result)
        
        with patch('fastmcp.auth.application.services.auth_service.AuthService', return_value=mock_auth_instance):
            with patch('fastmcp.auth.infrastructure.repositories.user_repository.UserRepository'):
                with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_service_instance):
                    with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', return_value=mock_db_config):
                        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
                        routes = create_auth_integration_routes()
                        
                        register_endpoint = None
                        for route in routes:
                            if route.path == "/api/auth/register":
                                register_endpoint = route.endpoint
                                break
                        
                        assert register_endpoint is not None
                        
                        response = await register_endpoint(mock_request)
                        
                        assert isinstance(response, JSONResponse)
                        assert response.status_code == 400
                        
                        mock_db_config.get_session().rollback.assert_called_once()
                        mock_db_config.get_session().close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_endpoint_success(self, mock_request, mock_db_config, mock_jwt_service_instance):
        """Test successful user login."""
        mock_request.json.return_value = {
            "email": "test@example.com",
            "password": "SecurePass123!"
        }
        
        mock_result = Mock()
        mock_result.success = True
        mock_result.access_token = "mock_access_token"
        mock_result.refresh_token = "mock_refresh_token"
        mock_result.error_message = None
        
        mock_auth_instance = Mock()
        mock_auth_instance.login = AsyncMock(return_value=mock_result)
        
        with patch('fastmcp.auth.application.services.auth_service.AuthService', return_value=mock_auth_instance):
            with patch('fastmcp.auth.infrastructure.repositories.user_repository.UserRepository'):
                with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_service_instance):
                    with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', return_value=mock_db_config):
                        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
                        routes = create_auth_integration_routes()
                        
                        login_endpoint = None
                        for route in routes:
                            if route.path == "/api/auth/login":
                                login_endpoint = route.endpoint
                                break
                        
                        assert login_endpoint is not None
                        
                        response = await login_endpoint(mock_request)
                        
                        assert isinstance(response, JSONResponse)
                        assert response.status_code == 200
                        
                        mock_db_config.get_session().commit.assert_called_once()
                        mock_db_config.get_session().close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_endpoint_invalid_credentials(self, mock_request, mock_db_config, mock_jwt_service_instance):
        """Test login with invalid credentials."""
        mock_request.json.return_value = {
            "email": "test@example.com",
            "password": "WrongPassword"
        }
        
        mock_result = Mock()
        mock_result.success = False
        mock_result.access_token = None
        mock_result.refresh_token = None
        mock_result.error_message = "Invalid credentials"
        
        mock_auth_instance = Mock()
        mock_auth_instance.login = AsyncMock(return_value=mock_result)
        
        with patch('fastmcp.auth.application.services.auth_service.AuthService', return_value=mock_auth_instance):
            with patch('fastmcp.auth.infrastructure.repositories.user_repository.UserRepository'):
                with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_service_instance):
                    with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', return_value=mock_db_config):
                        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
                        routes = create_auth_integration_routes()
                        
                        login_endpoint = None
                        for route in routes:
                            if route.path == "/api/auth/login":
                                login_endpoint = route.endpoint
                                break
                        
                        assert login_endpoint is not None
                        
                        response = await login_endpoint(mock_request)
                        
                        assert isinstance(response, JSONResponse)
                        assert response.status_code == 401
                        
                        mock_db_config.get_session().rollback.assert_called_once()
                        mock_db_config.get_session().close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_success(self, mock_request, mock_jwt_service_instance):
        """Test successful token refresh."""
        mock_request.json.return_value = {
            "refresh_token": "valid_refresh_token"
        }
        
        with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_service_instance):
            from fastmcp.server.routes.auth_integration import create_auth_integration_routes
            routes = create_auth_integration_routes()
            
            refresh_endpoint = None
            for route in routes:
                if route.path == "/api/auth/refresh":
                    refresh_endpoint = route.endpoint
                    break
            
            assert refresh_endpoint is not None
            
            response = await refresh_endpoint(mock_request)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_invalid_token(self, mock_request):
        """Test token refresh with invalid token."""
        mock_request.json.return_value = {
            "refresh_token": "invalid_refresh_token"
        }
        
        # Mock JWT service to return None for invalid token
        mock_jwt_invalid = Mock()
        mock_jwt_invalid.verify_refresh_token = Mock(return_value=None)
        
        with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_invalid):
            from fastmcp.server.routes.auth_integration import create_auth_integration_routes
            routes = create_auth_integration_routes()
            
            refresh_endpoint = None
            for route in routes:
                if route.path == "/api/auth/refresh":
                    refresh_endpoint = route.endpoint
                    break
            
            assert refresh_endpoint is not None
            
            response = await refresh_endpoint(mock_request)
            
            assert isinstance(response, JSONResponse)
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_missing_token(self, mock_request):
        """Test token refresh without providing token."""
        mock_request.json.return_value = {}
        
        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
        routes = create_auth_integration_routes()
        
        refresh_endpoint = None
        for route in routes:
            if route.path == "/api/auth/refresh":
                refresh_endpoint = route.endpoint
                break
        
        assert refresh_endpoint is not None
        
        response = await refresh_endpoint(mock_request)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_auth_health_endpoint(self, mock_request):
        """Test auth health check endpoint."""
        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
        routes = create_auth_integration_routes()
        
        health_endpoint = None
        for route in routes:
            if route.path == "/api/auth/health":
                health_endpoint = route.endpoint
                break
        
        assert health_endpoint is not None
        
        response = await health_endpoint(mock_request)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_register_endpoint_exception_handling(self, mock_request, mock_db_config, mock_jwt_service_instance):
        """Test register endpoint exception handling."""
        mock_request.json.return_value = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "password"
        }
        
        # Setup auth service to raise exception
        mock_auth_instance = Mock()
        mock_auth_instance.register_user = AsyncMock(side_effect=Exception("Database error"))
        
        with patch('fastmcp.auth.application.services.auth_service.AuthService', return_value=mock_auth_instance):
            with patch('fastmcp.auth.infrastructure.repositories.user_repository.UserRepository'):
                with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_service_instance):
                    with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', return_value=mock_db_config):
                        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
                        routes = create_auth_integration_routes()
                        
                        register_endpoint = None
                        for route in routes:
                            if route.path == "/api/auth/register":
                                register_endpoint = route.endpoint
                                break
                        
                        assert register_endpoint is not None
                        
                        response = await register_endpoint(mock_request)
                        
                        assert isinstance(response, JSONResponse)
                        assert response.status_code == 400
                        
                        mock_db_config.get_session().rollback.assert_called_once()
                        mock_db_config.get_session().close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_login_endpoint_exception_handling(self, mock_request, mock_db_config, mock_jwt_service_instance):
        """Test login endpoint exception handling."""
        mock_request.json.return_value = {
            "email": "test@example.com",
            "password": "password"
        }
        
        # Setup auth service to raise exception
        mock_auth_instance = Mock()
        mock_auth_instance.login = AsyncMock(side_effect=Exception("Authentication error"))
        
        with patch('fastmcp.auth.application.services.auth_service.AuthService', return_value=mock_auth_instance):
            with patch('fastmcp.auth.infrastructure.repositories.user_repository.UserRepository'):
                with patch('fastmcp.auth.domain.services.jwt_service.JWTService', return_value=mock_jwt_service_instance):
                    with patch('fastmcp.task_management.infrastructure.database.database_config.get_db_config', return_value=mock_db_config):
                        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
                        routes = create_auth_integration_routes()
                        
                        login_endpoint = None
                        for route in routes:
                            if route.path == "/api/auth/login":
                                login_endpoint = route.endpoint
                                break
                        
                        assert login_endpoint is not None
                        
                        response = await login_endpoint(mock_request)
                        
                        assert isinstance(response, JSONResponse)
                        assert response.status_code == 400
                        
                        mock_db_config.get_session().rollback.assert_called_once()
                        mock_db_config.get_session().close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_invalid_json(self, mock_request):
        """Test register endpoint with invalid JSON."""
        # Setup - simulate JSON parsing error
        mock_request.json.side_effect = Exception("Invalid JSON")
        
        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
        routes = create_auth_integration_routes()
        
        register_endpoint = None
        for route in routes:
            if route.path == "/api/auth/register":
                register_endpoint = route.endpoint
                break
        
        assert register_endpoint is not None
        
        response = await register_endpoint(mock_request)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
    
    def test_create_auth_integration_routes_import_error(self):
        """Test route creation when imports fail."""
        # Mock bcrypt to fail import
        with patch.dict('sys.modules', {'bcrypt': None}):
            from fastmcp.server.routes.auth_integration import create_auth_integration_routes
            # Clear module cache to force re-import
            if 'fastmcp.server.routes.auth_integration' in sys.modules:
                del sys.modules['fastmcp.server.routes.auth_integration']
            
            # This should handle the import error gracefully
            routes = create_auth_integration_routes()
            
            # Should still create routes if other dependencies are available
            assert isinstance(routes, list)
    
    def test_route_paths_and_methods(self):
        """Test that all expected routes are created with correct paths and methods."""
        from fastmcp.server.routes.auth_integration import create_auth_integration_routes
        routes = create_auth_integration_routes()
        
        # Should have routes since dependencies are now available
        assert len(routes) > 0
        
        # Check that routes have expected structure
        for route in routes:
            assert hasattr(route, 'path')
            assert hasattr(route, 'methods')
            assert route.path.startswith('/api/auth/')