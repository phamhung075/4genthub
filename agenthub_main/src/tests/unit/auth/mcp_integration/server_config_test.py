"""
Tests for MCP Server Configuration with JWT Authentication
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from starlette.middleware import Middleware

from fastmcp.auth.mcp_integration.server_config import (
    configure_jwt_auth_for_mcp,
    get_jwt_middleware,
    setup_mcp_with_jwt_auth,
    integrate_jwt_with_http_server,
    configure_jwt_from_env,
    validate_jwt_configuration
)
from fastmcp.auth.mcp_integration.jwt_auth_backend import JWTAuthBackend
# UserContextMiddleware has been replaced with RequestContextMiddleware
try:
    from fastmcp.auth.middleware.request_context_middleware import RequestContextMiddleware as UserContextMiddleware
except ImportError:
    UserContextMiddleware = None


class TestConfigureJwtAuthForMcp:
    """Test cases for configure_jwt_auth_for_mcp function."""
    
    @patch('fastmcp.auth.mcp_integration.server_config.create_jwt_auth_backend')
    def test_configure_with_default_scopes(self, mock_create_jwt):
        """Test configuration with default scopes."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_create_jwt.return_value = mock_backend
        
        result = configure_jwt_auth_for_mcp()
        
        mock_create_jwt.assert_called_once_with(
            database_session_factory=None,
            required_scopes=["mcp:access"]
        )
        assert result == mock_backend
    
    @patch('fastmcp.auth.mcp_integration.server_config.create_jwt_auth_backend')
    def test_configure_with_custom_scopes(self, mock_create_jwt):
        """Test configuration with custom scopes."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_create_jwt.return_value = mock_backend
        custom_scopes = ["read", "write", "admin"]
        
        result = configure_jwt_auth_for_mcp(required_scopes=custom_scopes)
        
        mock_create_jwt.assert_called_once_with(
            database_session_factory=None,
            required_scopes=custom_scopes
        )
        assert result == mock_backend
    
    @patch('fastmcp.auth.mcp_integration.server_config.create_jwt_auth_backend')
    def test_configure_with_database_factory(self, mock_create_jwt):
        """Test configuration with database session factory."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_create_jwt.return_value = mock_backend
        mock_db_factory = Mock()
        
        result = configure_jwt_auth_for_mcp(database_session_factory=mock_db_factory)
        
        mock_create_jwt.assert_called_once_with(
            database_session_factory=mock_db_factory,
            required_scopes=["mcp:access"]
        )
        assert result == mock_backend


class TestGetJwtMiddleware:
    """Test cases for get_jwt_middleware function."""
    
    def test_get_middleware_with_backend(self):
        """Test getting middleware with provided backend."""
        if UserContextMiddleware is None:
            pytest.skip("UserContextMiddleware not available")
            
        mock_backend = Mock(spec=JWTAuthBackend)
        
        result = get_jwt_middleware(jwt_backend=mock_backend)
        
        assert len(result) == 1
        assert isinstance(result[0], Middleware)
        assert result[0].cls == UserContextMiddleware
        assert result[0].kwargs['jwt_backend'] == mock_backend
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_auth_for_mcp')
    def test_get_middleware_without_backend(self, mock_configure):
        """Test getting middleware without backend (creates default)."""
        if UserContextMiddleware is None:
            pytest.skip("UserContextMiddleware not available")
            
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_configure.return_value = mock_backend
        
        result = get_jwt_middleware()
        
        mock_configure.assert_called_once()
        assert len(result) == 1
        assert isinstance(result[0], Middleware)
        assert result[0].cls == UserContextMiddleware
        assert result[0].kwargs['jwt_backend'] == mock_backend


class TestSetupMcpWithJwtAuth:
    """Test cases for setup_mcp_with_jwt_auth function."""
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_auth_for_mcp')
    @patch('fastmcp.auth.mcp_integration.server_config.get_jwt_middleware')
    def test_setup_with_existing_middleware(self, mock_get_middleware, mock_configure):
        """Test setup when server already has middleware."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_configure.return_value = mock_backend
        
        mock_middleware = [Middleware(Mock)]
        mock_get_middleware.return_value = mock_middleware
        
        mock_server = Mock()
        mock_server.middleware = [Middleware(Mock)]  # Existing middleware
        
        setup_mcp_with_jwt_auth(mock_server)
        
        # Verify auth backend was set
        assert mock_server.auth == mock_backend
        
        # Verify middleware was extended
        assert len(mock_server.middleware) == 2
        assert mock_server.middleware[1] == mock_middleware[0]
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_auth_for_mcp')
    @patch('fastmcp.auth.mcp_integration.server_config.get_jwt_middleware')
    def test_setup_without_existing_middleware(self, mock_get_middleware, mock_configure):
        """Test setup when server has no middleware attribute."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_configure.return_value = mock_backend
        
        mock_middleware = [Middleware(Mock)]
        mock_get_middleware.return_value = mock_middleware
        
        mock_server = Mock(spec=[])  # No middleware attribute
        
        setup_mcp_with_jwt_auth(mock_server)
        
        # Verify auth backend was set
        assert mock_server.auth == mock_backend
        
        # Verify middleware was created
        assert hasattr(mock_server, 'middleware')
        assert mock_server.middleware == mock_middleware
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_auth_for_mcp')
    def test_setup_with_custom_parameters(self, mock_configure):
        """Test setup with custom scopes and database factory."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_configure.return_value = mock_backend
        
        mock_server = Mock()
        mock_db_factory = Mock()
        custom_scopes = ["admin", "user"]
        
        setup_mcp_with_jwt_auth(
            mock_server,
            required_scopes=custom_scopes,
            database_session_factory=mock_db_factory
        )
        
        mock_configure.assert_called_once_with(
            required_scopes=custom_scopes,
            database_session_factory=mock_db_factory
        )


class TestIntegrateJwtWithHttpServer:
    """Test cases for integrate_jwt_with_http_server function."""
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_auth_for_mcp')
    @patch('fastmcp.auth.mcp_integration.server_config.get_jwt_middleware')
    def test_integrate_with_empty_kwargs(self, mock_get_middleware, mock_configure):
        """Test integration with empty kwargs."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_configure.return_value = mock_backend
        
        mock_middleware = [Middleware(Mock)]
        mock_get_middleware.return_value = mock_middleware
        
        kwargs = {}
        result = integrate_jwt_with_http_server(kwargs)
        
        assert result['auth'] == mock_backend
        assert result['middleware'] == mock_middleware
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_auth_for_mcp')
    @patch('fastmcp.auth.mcp_integration.server_config.get_jwt_middleware')
    def test_integrate_with_existing_middleware(self, mock_get_middleware, mock_configure):
        """Test integration with existing middleware in kwargs."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_configure.return_value = mock_backend
        
        mock_jwt_middleware = [Middleware(Mock)]
        mock_get_middleware.return_value = mock_jwt_middleware
        
        existing_middleware = [Middleware(Mock)]
        kwargs = {'middleware': existing_middleware.copy()}
        
        result = integrate_jwt_with_http_server(kwargs)
        
        assert result['auth'] == mock_backend
        assert len(result['middleware']) == 2
        assert result['middleware'][0] == existing_middleware[0]
        assert result['middleware'][1] == mock_jwt_middleware[0]
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_auth_for_mcp')
    def test_integrate_with_database_factory(self, mock_configure):
        """Test integration with database session factory."""
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_configure.return_value = mock_backend
        
        mock_db_factory = Mock()
        kwargs = {}
        
        result = integrate_jwt_with_http_server(kwargs, database_session_factory=mock_db_factory)
        
        mock_configure.assert_called_once_with(database_session_factory=mock_db_factory)
        assert result['auth'] == mock_backend


class TestConfigureJwtFromEnv:
    """Test cases for configure_jwt_from_env function."""
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'test-secret-key-that-is-long-enough-for-security',
        'JWT_ISSUER': 'test-issuer',
        'JWT_ALGORITHM': 'HS512',
        'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '30',
        'JWT_REFRESH_TOKEN_EXPIRE_DAYS': '7'
    })
    def test_configure_from_env_all_values(self):
        """Test configuration with all environment variables set."""
        config = configure_jwt_from_env()
        
        assert config['secret_key'] == 'test-secret-key-that-is-long-enough-for-security'
        assert config['issuer'] == 'test-issuer'
        assert config['audience'] == 'mcp-server'
        assert config['algorithm'] == 'HS512'
        assert config['access_token_expire_minutes'] == 30
        assert config['refresh_token_expire_days'] == 7
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'test-secret-key'
    }, clear=True)
    def test_configure_from_env_defaults(self):
        """Test configuration with default values."""
        config = configure_jwt_from_env()
        
        assert config['secret_key'] == 'test-secret-key'
        assert config['issuer'] == 'agenthub'
        assert config['audience'] == 'mcp-server'
        assert config['algorithm'] == 'HS256'
        assert config['access_token_expire_minutes'] == 15
        assert config['refresh_token_expire_days'] == 30
    
    @patch.dict(os.environ, {}, clear=True)
    def test_configure_from_env_missing_secret(self):
        """Test configuration raises error when JWT_SECRET_KEY is missing."""
        with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable must be set"):
            configure_jwt_from_env()
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'test-secret',
        'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': 'not-a-number'
    })
    def test_configure_from_env_invalid_number(self):
        """Test configuration with invalid number format."""
        with pytest.raises(ValueError):
            configure_jwt_from_env()


class TestValidateJwtConfiguration:
    """Test cases for validate_jwt_configuration function."""
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'a-very-long-secret-key-that-is-at-least-32-characters',
        'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '15',
        'JWT_REFRESH_TOKEN_EXPIRE_DAYS': '30'
    })
    def test_validate_valid_configuration(self):
        """Test validation with valid configuration."""
        result = validate_jwt_configuration()
        assert result is True
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'short-key'
    })
    def test_validate_short_secret_key(self):
        """Test validation fails with short secret key."""
        with pytest.raises(ValueError, match="JWT_SECRET_KEY should be at least 32 characters"):
            validate_jwt_configuration()
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'a-very-long-secret-key-that-is-at-least-32-characters',
        'JWT_ACCESS_TOKEN_EXPIRE_MINUTES': '3'
    })
    def test_validate_short_access_token_expiry(self):
        """Test validation fails with short access token expiry."""
        with pytest.raises(ValueError, match="Access token expiration should be at least 5 minutes"):
            validate_jwt_configuration()
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'a-very-long-secret-key-that-is-at-least-32-characters',
        'JWT_REFRESH_TOKEN_EXPIRE_DAYS': '0'
    })
    def test_validate_short_refresh_token_expiry(self):
        """Test validation fails with short refresh token expiry."""
        with pytest.raises(ValueError, match="Refresh token expiration should be at least 1 day"):
            validate_jwt_configuration()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_missing_configuration(self):
        """Test validation fails when configuration is missing."""
        with pytest.raises(ValueError, match="JWT configuration validation failed"):
            validate_jwt_configuration()
    
    @patch('fastmcp.auth.mcp_integration.server_config.configure_jwt_from_env')
    def test_validate_configuration_error_handling(self, mock_configure):
        """Test validation handles configuration errors properly."""
        mock_configure.side_effect = Exception("Configuration error")
        
        with pytest.raises(ValueError, match="JWT configuration validation failed: Configuration error"):
            validate_jwt_configuration()


class TestIntegrationScenarios:
    """Test integration scenarios for server configuration."""
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'a-very-long-secret-key-that-is-at-least-32-characters'
    })
    @patch('fastmcp.auth.mcp_integration.server_config.create_jwt_auth_backend')
    def test_full_mcp_setup_flow(self, mock_create_jwt):
        """Test complete MCP server setup flow."""
        # Setup mocks
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_create_jwt.return_value = mock_backend
        
        mock_server = Mock()
        mock_server.middleware = []
        
        # Perform setup
        setup_mcp_with_jwt_auth(mock_server)
        
        # Verify results
        assert mock_server.auth == mock_backend
        if UserContextMiddleware is not None:
            assert len(mock_server.middleware) == 1
            assert mock_server.middleware[0].cls == UserContextMiddleware
        else:
            assert len(mock_server.middleware) == 0
    
    @patch.dict(os.environ, {
        'JWT_SECRET_KEY': 'a-very-long-secret-key-that-is-at-least-32-characters'
    })
    @patch('fastmcp.auth.mcp_integration.server_config.create_jwt_auth_backend')
    def test_http_server_kwargs_integration(self, mock_create_jwt):
        """Test HTTP server kwargs integration."""
        # Setup mocks
        mock_backend = Mock(spec=JWTAuthBackend)
        mock_create_jwt.return_value = mock_backend
        
        # Start with basic kwargs
        kwargs = {
            'debug': True,
            'cors_origins': ['http://localhost:3000']
        }
        
        # Integrate JWT auth
        result = integrate_jwt_with_http_server(kwargs.copy())
        
        # Verify original kwargs preserved
        assert result['debug'] is True
        assert result['cors_origins'] == ['http://localhost:3000']
        
        # Verify JWT auth added
        assert 'auth' in result
        assert result['auth'] == mock_backend
        assert 'middleware' in result
        if UserContextMiddleware is not None:
            assert len(result['middleware']) > 0
        else:
            assert len(result['middleware']) == 0


if __name__ == "__main__":
    pytest.main([__file__])