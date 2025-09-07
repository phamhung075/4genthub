"""
Test suite for Request Context Middleware

Tests the middleware that captures authentication context and makes it
available through context variables for auth_helper.py and other components.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from contextvars import ContextVar
from typing import Dict, Any, Optional

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from fastmcp.auth.middleware.request_context_middleware import (
    RequestContextMiddleware,
    get_current_user_id,
    get_current_user_email,
    get_current_auth_method,
    get_current_auth_info,
    is_request_authenticated,
    get_authentication_context,
    get_current_user_context,
    create_request_context_middleware,
    # Import context variables for testing
    _current_user_id,
    _current_user_email,
    _current_auth_method,
    _current_auth_info,
    _request_authenticated
)


class TestRequestContextMiddleware:
    """Test suite for RequestContextMiddleware"""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object"""
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/v2/test"
        request.method = "GET"
        request.state = MagicMock()
        request.scope = {}  # ASGI scope dictionary
        return request

    @pytest.fixture
    def mock_app(self):
        """Create a mock ASGI app"""
        app = MagicMock()
        return app

    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance"""
        return RequestContextMiddleware(mock_app)

    @pytest.fixture(autouse=True)
    def clear_context_vars(self):
        """Clear context variables before each test"""
        _current_user_id.set(None)
        _current_user_email.set(None)
        _current_auth_method.set(None)
        _current_auth_info.set(None)
        _request_authenticated.set(False)
        yield
        # Clear again after test
        _current_user_id.set(None)
        _current_user_email.set(None)
        _current_auth_method.set(None)
        _current_auth_info.set(None)
        _request_authenticated.set(False)

    @pytest.mark.asyncio
    async def test_dispatch_no_auth(self, middleware, mock_request):
        """Test dispatch with no authentication"""
        # No auth info in request.state
        mock_request.state = MagicMock()
        
        # Create a mock response
        expected_response = Response("OK")
        
        # Mock call_next
        async def call_next(request):
            # Context should be empty
            assert get_current_user_id() is None
            assert not is_request_authenticated()
            return expected_response
        
        response = await middleware.dispatch(mock_request, call_next)
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_dispatch_with_auth(self, middleware, mock_request):
        """Test dispatch with authentication info"""
        # Set auth info in request.state (as DualAuthMiddleware would)
        mock_request.state.user_id = "test-user-123"
        mock_request.state.auth_type = "unified"
        mock_request.state.auth_info = {
            'user_id': 'test-user-123',
            'email': 'user@example.com',
            'auth_method': 'api_token'
        }
        
        # Create a mock response
        expected_response = Response("OK")
        
        # Mock call_next
        async def call_next(request):
            # Context should be set
            assert get_current_user_id() == "test-user-123"
            assert get_current_user_email() == "user@example.com"
            assert get_current_auth_method() == "api_token"
            assert is_request_authenticated() is True
            return expected_response
        
        response = await middleware.dispatch(mock_request, call_next)
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_dispatch_mcp_endpoint(self, middleware, mock_request):
        """Test dispatch for MCP endpoint sets user in ASGI scope"""
        # Configure for MCP endpoint
        mock_request.url.path = "/mcp/tools/list"
        mock_request.state.user_id = "mcp-user-456"
        mock_request.state.auth_type = "mcp_token"
        mock_request.state.auth_info = {
            'user_id': 'mcp-user-456',
            'email': 'mcp@example.com',
            'auth_method': 'mcp_token'
        }
        
        # Create a mock response
        expected_response = Response("OK")
        
        # Mock call_next
        async def call_next(request):
            # Check that user was set in ASGI scope
            assert 'user' in request.scope
            assert request.scope['user']['user_id'] == 'mcp-user-456'
            assert request.scope['user']['auth_method'] == 'mcp_token'
            return expected_response
        
        response = await middleware.dispatch(mock_request, call_next)
        assert response == expected_response

    @pytest.mark.asyncio
    async def test_dispatch_error_handling(self, middleware, mock_request):
        """Test dispatch handles errors properly"""
        mock_request.state.user_id = "test-user"
        
        # Mock call_next to raise an error
        async def call_next(request):
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError):
            await middleware.dispatch(mock_request, call_next)
        
        # Context should be cleared after error
        assert get_current_user_id() is None
        assert not is_request_authenticated()

    def test_capture_auth_context_from_request_state(self, middleware, mock_request):
        """Test capturing auth context from request state"""
        # Set up request state
        mock_request.state.user_id = "captured-user"
        mock_request.state.auth_type = "supabase"
        mock_request.state.auth_info = {
            'user_id': 'captured-user',
            'email': 'captured@example.com',
            'auth_method': 'supabase_jwt'
        }
        
        # Capture context
        middleware._capture_auth_context_from_request_state(mock_request)
        
        # Verify context was set
        assert get_current_user_id() == "captured-user"
        assert get_current_user_email() == "captured@example.com"
        assert get_current_auth_method() == "supabase_jwt"
        assert is_request_authenticated() is True

    def test_capture_auth_context_no_request_state(self, middleware):
        """Test capturing auth context when request has no state"""
        request = MagicMock()
        # Remove state attribute
        if hasattr(request, 'state'):
            delattr(request, 'state')
        
        with patch('fastmcp.auth.middleware.request_context_middleware.logger') as mock_logger:
            middleware._capture_auth_context_from_request_state(request)
            mock_logger.warning.assert_called_once()
        
        # Context should remain empty
        assert get_current_user_id() is None
        assert not is_request_authenticated()

    def test_capture_auth_context_error(self, middleware, mock_request):
        """Test error handling in capture auth context"""
        # Set up request state to raise error when accessed
        mock_request.state = MagicMock()
        mock_request.state.__getattr__ = MagicMock(side_effect=Exception("Test error"))
        
        with patch('fastmcp.auth.middleware.request_context_middleware.logger') as mock_logger:
            middleware._capture_auth_context_from_request_state(mock_request)
            mock_logger.error.assert_called()
        
        # Context should be cleared
        assert get_current_user_id() is None

    def test_clear_auth_context(self, middleware):
        """Test clearing auth context"""
        # Set some context
        _current_user_id.set("user-to-clear")
        _current_user_email.set("clear@example.com")
        _request_authenticated.set(True)
        
        # Clear context
        middleware._clear_auth_context()
        
        # Verify cleared
        assert get_current_user_id() is None
        assert get_current_user_email() is None
        assert not is_request_authenticated()

    def test_get_current_user_id(self):
        """Test get_current_user_id helper"""
        # Initially None
        assert get_current_user_id() is None
        
        # Set a value
        _current_user_id.set("helper-user")
        assert get_current_user_id() == "helper-user"

    def test_get_current_user_email(self):
        """Test get_current_user_email helper"""
        # Initially None
        assert get_current_user_email() is None
        
        # Set a value
        _current_user_email.set("helper@example.com")
        assert get_current_user_email() == "helper@example.com"

    def test_get_current_auth_method(self):
        """Test get_current_auth_method helper"""
        # Initially None
        assert get_current_auth_method() is None
        
        # Set a value
        _current_auth_method.set("jwt_token")
        assert get_current_auth_method() == "jwt_token"

    def test_get_current_auth_info(self):
        """Test get_current_auth_info helper"""
        # Initially None
        assert get_current_auth_info() is None
        
        # Set a value
        auth_info = {'user_id': 'test', 'scopes': ['read']}
        _current_auth_info.set(auth_info)
        assert get_current_auth_info() == auth_info

    def test_is_request_authenticated(self):
        """Test is_request_authenticated helper"""
        # Initially False
        assert is_request_authenticated() is False
        
        # Set to True
        _request_authenticated.set(True)
        assert is_request_authenticated() is True

    def test_get_authentication_context(self):
        """Test get_authentication_context helper"""
        # Set up full context
        _current_user_id.set("context-user")
        _current_user_email.set("context@example.com")
        _current_auth_method.set("api_token")
        _current_auth_info.set({'extra': 'data'})
        _request_authenticated.set(True)
        
        context = get_authentication_context()
        
        assert context['user_id'] == "context-user"
        assert context['email'] == "context@example.com"
        assert context['auth_method'] == "api_token"
        assert context['auth_info'] == {'extra': 'data'}
        assert context['authenticated'] is True

    def test_get_authentication_context_error(self):
        """Test get_authentication_context with error"""
        # Mock error in get_current_user_id
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_id', 
                  side_effect=Exception("Test error")):
            context = get_authentication_context()
            
            # Should return default values
            assert context['user_id'] is None
            assert context['authenticated'] is False

    def test_get_current_user_context_backward_compat(self):
        """Test backward compatibility function"""
        # No user
        assert get_current_user_context() is None
        
        # Set user context
        _current_user_id.set("compat-user")
        _current_user_email.set("compat@example.com")
        
        user_context = get_current_user_context()
        assert user_context is not None
        assert user_context.user_id == "compat-user"
        assert user_context.email == "compat@example.com"
        assert user_context.roles == []

    def test_context_var_error_handling(self):
        """Test error handling in context variable access"""
        # Mock ContextVar.get to raise error
        with patch.object(_current_user_id, 'get', side_effect=Exception("Context error")):
            assert get_current_user_id() is None
        
        with patch.object(_current_user_email, 'get', side_effect=Exception("Context error")):
            assert get_current_user_email() is None
        
        with patch.object(_request_authenticated, 'get', side_effect=Exception("Context error")):
            assert is_request_authenticated() is False

    def test_create_request_context_middleware(self):
        """Test middleware factory function"""
        middleware_class = create_request_context_middleware()
        assert middleware_class == RequestContextMiddleware

    @pytest.mark.asyncio
    async def test_dispatch_asgi_scope_edge_cases(self, middleware, mock_request):
        """Test ASGI scope setting edge cases"""
        # Test 1: Non-MCP path shouldn't set scope
        mock_request.url.path = "/api/v2/users"
        mock_request.state.user_id = "api-user"
        mock_request.scope = {}
        
        async def check_non_mcp(request):
            assert 'user' not in request.scope
            return Response("OK")
        
        await middleware.dispatch(mock_request, check_non_mcp)
        
        # Test 2: MCP path without user_id shouldn't set scope
        mock_request.url.path = "/mcp/tools"
        mock_request.state = MagicMock()  # No user_id
        mock_request.scope = {}
        
        async def check_no_user(request):
            assert 'user' not in request.scope
            return Response("OK")
        
        await middleware.dispatch(mock_request, check_no_user)
        
        # Test 3: Missing scope attribute shouldn't crash
        mock_request.url.path = "/mcp/tools"
        mock_request.state.user_id = "mcp-user"
        delattr(mock_request, 'scope')  # Remove scope
        
        async def check_no_scope(request):
            # Should not crash
            return Response("OK")
        
        # Should not raise exception
        await middleware.dispatch(mock_request, check_no_scope)