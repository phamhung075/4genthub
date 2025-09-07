"""
Tests for MCP Authentication Middleware for HTTP Transport

This module tests the MCPAuthMiddleware which extracts JWT tokens from HTTP 
Authorization headers and sets the user context for MCP operations.
"""

import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from contextvars import ContextVar

from fastmcp.auth.mcp_integration.mcp_auth_middleware import (
    MCPAuthMiddleware,
    get_mcp_auth_middleware
)
from fastmcp.auth.mcp_integration.jwt_auth_backend import MCPUserContext
from fastmcp.auth.middleware.request_context_middleware import current_user_context


class TestMCPAuthMiddleware:
    """Test suite for MCPAuthMiddleware"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_jwt_backend(self):
        """Create a mock JWT backend"""
        backend = Mock()
        backend.load_access_token = AsyncMock()
        backend._get_user_context = AsyncMock()
        return backend
    
    @pytest.fixture
    def middleware(self, mock_app, mock_jwt_backend):
        """Create middleware instance with mocked dependencies"""
        return MCPAuthMiddleware(mock_app, mock_jwt_backend)
    
    @pytest.mark.asyncio
    async def test_non_http_passthrough(self, middleware, mock_app):
        """Test that non-HTTP requests are passed through without processing"""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Verify app was called with original parameters
        mock_app.assert_called_once_with(scope, receive, send)
    
    @pytest.mark.asyncio
    async def test_http_request_no_auth_header(self, middleware, mock_app):
        """Test HTTP request without Authorization header"""
        scope = {
            "type": "http",
            "headers": [
                (b"content-type", b"application/json"),
                (b"user-agent", b"test-agent")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Verify app was called and no user context was set
        mock_app.assert_called_once_with(scope, receive, send)
        assert current_user_context.get(None) is None
    
    @pytest.mark.asyncio
    async def test_http_request_with_valid_token(self, middleware, mock_app, mock_jwt_backend):
        """Test HTTP request with valid Bearer token"""
        # Setup mock responses
        mock_access_token = Mock()
        mock_access_token.client_id = "test-user-123"
        mock_access_token.scopes = ["read", "write"]
        
        mock_user_context = MCPUserContext(
            user_id="test-user-123",
            email="test@example.com",
            username="testuser",
            roles=["user", "developer"],
            scopes=["read", "write"]
        )
        
        mock_jwt_backend.load_access_token.return_value = mock_access_token
        mock_jwt_backend._get_user_context.return_value = mock_user_context
        
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer valid-jwt-token"),
                (b"content-type", b"application/json")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Verify JWT backend was called with correct token
        mock_jwt_backend.load_access_token.assert_called_once_with("valid-jwt-token")
        mock_jwt_backend._get_user_context.assert_called_once_with("test-user-123")
        
        # Verify app was called with updated scope
        mock_app.assert_called_once()
        called_scope = mock_app.call_args[0][0]
        
        # Check that user context was added to scope state
        assert "state" in called_scope
        assert called_scope["state"]["user_id"] == "test-user-123"
        assert called_scope["state"]["user_email"] == "test@example.com"
        assert called_scope["state"]["user_roles"] == ["user", "developer"]
        assert called_scope["state"]["user_scopes"] == ["read", "write"]
    
    @pytest.mark.asyncio
    async def test_http_request_with_invalid_token(self, middleware, mock_app, mock_jwt_backend):
        """Test HTTP request with invalid Bearer token"""
        # Setup mock to raise exception
        mock_jwt_backend.load_access_token.side_effect = Exception("Invalid token")
        
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer invalid-jwt-token")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('fastmcp.auth.mcp_integration.mcp_auth_middleware.logger.warning') as mock_logger:
            await middleware(scope, receive, send)
            
            # Verify warning was logged
            mock_logger.assert_called_once()
            assert "Failed to validate JWT token" in str(mock_logger.call_args)
        
        # Verify app was still called despite error
        mock_app.assert_called_once_with(scope, receive, send)
    
    @pytest.mark.asyncio
    async def test_http_request_no_user_context_found(self, middleware, mock_app, mock_jwt_backend):
        """Test HTTP request with valid token but no user context found"""
        # Setup mock responses
        mock_access_token = Mock()
        mock_access_token.client_id = "test-user-456"
        mock_access_token.scopes = ["read"]
        
        mock_jwt_backend.load_access_token.return_value = mock_access_token
        mock_jwt_backend._get_user_context.return_value = None  # No user context
        
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer valid-jwt-token")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('fastmcp.auth.mcp_integration.mcp_auth_middleware.logger.warning') as mock_logger:
            await middleware(scope, receive, send)
            
            # Verify warning was logged
            mock_logger.assert_called_once()
            assert "Could not get user context for user_id: test-user-456" in str(mock_logger.call_args)
        
        # Verify app was called
        mock_app.assert_called_once_with(scope, receive, send)
    
    @pytest.mark.asyncio
    async def test_context_reset_after_request(self, middleware, mock_app, mock_jwt_backend):
        """Test that user context is reset after request completes"""
        # Setup mock responses
        mock_access_token = Mock()
        mock_access_token.client_id = "test-user-789"
        mock_access_token.scopes = ["admin"]
        
        mock_user_context = MCPUserContext(
            user_id="test-user-789",
            email="admin@example.com",
            username="admin",
            roles=["admin"],
            scopes=["admin"]
        )
        
        mock_jwt_backend.load_access_token.return_value = mock_access_token
        mock_jwt_backend._get_user_context.return_value = mock_user_context
        
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer admin-jwt-token")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Set an initial context value
        initial_token = current_user_context.set(None)
        
        await middleware(scope, receive, send)
        
        # Verify app was called with correct scope
        mock_app.assert_called_once_with(scope, receive, send)
        # Verify user context was set in scope
        assert scope.get("state", {}).get("user_id") == "test-user-789"
    
    @pytest.mark.asyncio
    async def test_middleware_error_handling(self, middleware, mock_app):
        """Test middleware handles errors gracefully"""
        scope = {
            "type": "http",
            "headers": "invalid"  # This will cause an error
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('fastmcp.auth.mcp_integration.mcp_auth_middleware.logger.error') as mock_logger:
            await middleware(scope, receive, send)
            
            # Verify error was logged
            mock_logger.assert_called_once()
            assert "Error in MCPAuthMiddleware" in str(mock_logger.call_args)
        
        # Verify app was still called despite error
        mock_app.assert_called_once_with(scope, receive, send)
    
    @pytest.mark.asyncio
    async def test_non_bearer_auth_header(self, middleware, mock_app):
        """Test HTTP request with non-Bearer authorization header"""
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Basic dXNlcjpwYXNz")  # Basic auth
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('fastmcp.auth.mcp_integration.mcp_auth_middleware.logger.debug') as mock_logger:
            await middleware(scope, receive, send)
            
            # Verify debug message about no Bearer token
            mock_logger.assert_called()
            assert "No Bearer token found in Authorization header" in str(mock_logger.call_args)
        
        # Verify app was called
        mock_app.assert_called_once_with(scope, receive, send)
    
    @pytest.mark.asyncio
    async def test_existing_scope_state_preserved(self, middleware, mock_app, mock_jwt_backend):
        """Test that existing scope state is preserved when adding user context"""
        # Setup mock responses
        mock_access_token = Mock()
        mock_access_token.client_id = "test-user-999"
        mock_access_token.scopes = ["special"]
        
        mock_user_context = MCPUserContext(
            user_id="test-user-999",
            email="special@example.com",
            username="special",
            roles=["special_role"],
            scopes=["special_scope"]
        )
        
        mock_jwt_backend.load_access_token.return_value = mock_access_token
        mock_jwt_backend._get_user_context.return_value = mock_user_context
        
        scope = {
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer special-jwt-token")
            ],
            "state": {
                "existing_key": "existing_value"
            }
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Verify app was called with updated scope
        called_scope = mock_app.call_args[0][0]
        
        # Check that existing state was preserved
        assert called_scope["state"]["existing_key"] == "existing_value"
        # And new user context was added
        assert called_scope["state"]["user_id"] == "test-user-999"


class TestGetMCPAuthMiddleware:
    """Test the factory function for creating MCPAuthMiddleware"""
    
    def test_factory_with_jwt_backend(self):
        """Test factory function with provided JWT backend"""
        mock_app = Mock()
        mock_jwt_backend = Mock()
        
        middleware = get_mcp_auth_middleware(mock_app, mock_jwt_backend)
        
        assert isinstance(middleware, MCPAuthMiddleware)
        assert middleware.app == mock_app
        assert middleware.jwt_backend == mock_jwt_backend
    
    @patch('fastmcp.auth.mcp_integration.mcp_auth_middleware.create_jwt_auth_backend')
    def test_factory_without_jwt_backend(self, mock_create_backend):
        """Test factory function creates default JWT backend when not provided"""
        mock_app = Mock()
        mock_default_backend = Mock()
        mock_create_backend.return_value = mock_default_backend
        
        middleware = get_mcp_auth_middleware(mock_app)
        
        assert isinstance(middleware, MCPAuthMiddleware)
        assert middleware.app == mock_app
        assert middleware.jwt_backend == mock_default_backend
        mock_create_backend.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])