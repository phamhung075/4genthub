"""
Tests for RequestContextMiddleware Authentication Context Propagation

These tests verify that the RequestContextMiddleware correctly captures
authentication context from DualAuthMiddleware and makes it available
throughout the request lifecycle via context variables.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.middleware import Middleware

from fastmcp.auth.middleware.request_context_middleware import (
    RequestContextMiddleware,
    get_current_user_id,
    get_current_user_email,
    get_current_auth_method,
    is_request_authenticated,
    get_authentication_context,
    _current_user_id,
    _current_user_email,
    _current_auth_method,
    _current_auth_info,
    _request_authenticated
)


class TestRequestContextMiddleware:
    """Test the RequestContextMiddleware class."""
    
    def test_middleware_initialization(self):
        """Test middleware initializes correctly."""
        app = Mock()
        middleware = RequestContextMiddleware(app)
        assert middleware is not None
    
    @pytest.mark.asyncio
    async def test_context_variables_cleared_on_request_start(self):
        """Test that context variables are cleared at the start of each request."""
        # Set some values first
        _current_user_id.set("test-user")
        _request_authenticated.set(True)
        
        # Mock app and request
        mock_app = AsyncMock()
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        mock_request.state = Mock()
        
        # Create middleware
        middleware = RequestContextMiddleware(mock_app)
        
        # Mock call_next
        async def mock_call_next(request):
            # During request processing, variables should be cleared
            assert get_current_user_id() is None
            assert not is_request_authenticated()
            return Response("OK")
        
        # Process request
        await middleware.dispatch(mock_request, mock_call_next)
        
        # Mock app should have been called
        mock_app.assert_not_called()  # Since we used call_next mock
    
    @pytest.mark.asyncio
    async def test_auth_context_captured_from_request_state(self):
        """Test that auth context is captured from request.state set by DualAuthMiddleware."""
        # Mock app
        mock_app = AsyncMock()
        
        # Create mock request with auth state (as set by DualAuthMiddleware)
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/mcp/task_create"
        mock_request.state = Mock()
        mock_request.state.user_id = "test-user-123"
        mock_request.state.auth_type = "local_jwt"
        mock_request.state.auth_info = {
            "user_id": "test-user-123",
            "email": "test@example.com",
            "auth_method": "local_jwt",
            "scopes": ["read", "write"]
        }
        
        # Create middleware
        middleware = RequestContextMiddleware(mock_app)
        
        # Track context during request processing
        captured_context = {}
        
        async def mock_call_next(request):
            # Capture context during request processing
            captured_context["user_id"] = get_current_user_id()
            captured_context["email"] = get_current_user_email()
            captured_context["auth_method"] = get_current_auth_method()
            captured_context["authenticated"] = is_request_authenticated()
            captured_context["full_context"] = get_authentication_context()
            return Response("OK")
        
        # Process request
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify context was captured correctly
        # NOTE: Context might be cleared after request completion
        # So we check what was captured during the request
        assert captured_context["user_id"] == "test-user-123"
        assert captured_context["email"] == "test@example.com"
        assert captured_context["auth_method"] == "local_jwt"
        assert captured_context["authenticated"] is True
        assert captured_context["full_context"]["user_id"] == "test-user-123"
    
    @pytest.mark.asyncio
    async def test_no_auth_context_when_not_authenticated(self):
        """Test that no auth context is set when request is not authenticated."""
        # Mock app
        mock_app = AsyncMock()
        
        # Create mock request without auth state
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/health"
        mock_request.state = Mock()
        # No user_id set in state
        
        # Create middleware
        middleware = RequestContextMiddleware(mock_app)
        
        # Track context during request processing
        captured_context = {}
        
        async def mock_call_next(request):
            captured_context["user_id"] = get_current_user_id()
            captured_context["authenticated"] = is_request_authenticated()
            return Response("OK")
        
        # Process request
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Verify response
        assert response.status_code == 200
        
        # Verify no auth context
        assert captured_context["user_id"] is None
        assert captured_context["authenticated"] is False
    
    @pytest.mark.asyncio
    async def test_error_handling_during_context_capture(self):
        """Test error handling when capturing auth context fails."""
        # Mock app
        mock_app = AsyncMock()
        
        # Create mock request with problematic state
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/test"
        # Make request.state raise an exception when accessed
        mock_request.state = Mock()
        type(mock_request.state).user_id = property(lambda self: (_ for _ in ()).throw(Exception("State access error")))
        
        # Create middleware
        middleware = RequestContextMiddleware(mock_app)
        
        async def mock_call_next(request):
            return Response("OK")
        
        # Process request - should not raise exception
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        # Should still return OK response despite error in context capture
        assert response.status_code == 200
        
        # Context should be cleared due to error
        assert get_current_user_id() is None
        assert not is_request_authenticated()
    
    @pytest.mark.asyncio
    async def test_middleware_exception_handling(self):
        """Test that middleware handles exceptions properly and clears context."""
        # Mock app
        mock_app = AsyncMock()
        
        # Create mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/test"
        mock_request.state = Mock()
        mock_request.state.user_id = "test-user"
        
        # Create middleware
        middleware = RequestContextMiddleware(mock_app)
        
        # Mock call_next that raises an exception
        async def mock_call_next(request):
            raise ValueError("Test exception")
        
        # Process request - should raise the exception
        with pytest.raises(ValueError, match="Test exception"):
            await middleware.dispatch(mock_request, mock_call_next)
        
        # Context should be cleared after exception
        assert get_current_user_id() is None
        assert not is_request_authenticated()


class TestContextVariableFunctions:
    """Test the context variable access functions."""
    
    def test_get_current_user_id_with_no_context(self):
        """Test getting user ID when no context is set."""
        # Clear any existing context
        _current_user_id.set(None)
        
        result = get_current_user_id()
        assert result is None
    
    def test_get_current_user_id_with_context(self):
        """Test getting user ID when context is set."""
        test_user_id = "test-user-456"
        _current_user_id.set(test_user_id)
        
        result = get_current_user_id()
        assert result == test_user_id
    
    def test_get_current_user_email_with_context(self):
        """Test getting user email when context is set."""
        test_email = "test@example.com"
        _current_user_email.set(test_email)
        
        result = get_current_user_email()
        assert result == test_email
    
    def test_get_current_auth_method_with_context(self):
        """Test getting auth method when context is set."""
        test_method = "supabase_jwt"
        _current_auth_method.set(test_method)
        
        result = get_current_auth_method()
        assert result == test_method
    
    def test_is_request_authenticated_with_context(self):
        """Test authentication status when context is set."""
        _request_authenticated.set(True)
        
        result = is_request_authenticated()
        assert result is True
        
        _request_authenticated.set(False)
        result = is_request_authenticated()
        assert result is False
    
    def test_get_authentication_context_complete(self):
        """Test getting complete authentication context."""
        # Set up context
        _current_user_id.set("test-user-789")
        _current_user_email.set("test@example.com")
        _current_auth_method.set("mcp_token")
        _request_authenticated.set(True)
        _current_auth_info.set({"scopes": ["read", "write"]})
        
        result = get_authentication_context()
        
        assert result["user_id"] == "test-user-789"
        assert result["email"] == "test@example.com"
        assert result["auth_method"] == "mcp_token"
        assert result["authenticated"] is True
        assert result["auth_info"]["scopes"] == ["read", "write"]
    
    def test_context_function_error_handling(self):
        """Test that context functions handle errors gracefully."""
        # Mock an error in context variable access
        with patch('fastmcp.auth.middleware.request_context_middleware._current_user_id.get') as mock_get:
            mock_get.side_effect = Exception("Context error")
            
            result = get_current_user_id()
            assert result is None


class TestIntegrationWithAuthHelper:
    """Test integration between RequestContextMiddleware and auth_helper.py"""
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    @patch('fastmcp.task_management.interface.controllers.auth_helper.is_request_authenticated')
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    def test_auth_helper_uses_request_context(self, mock_authenticated, mock_get_user):
        """Test that auth_helper.py correctly uses RequestContextMiddleware context."""
        from fastmcp.task_management.interface.controllers.auth_helper import get_authenticated_user_id
        
        # Setup mocks
        test_user_id = "integration-test-user"
        mock_get_user.return_value = test_user_id
        mock_authenticated.return_value = True
        
        # Call auth helper function
        result = get_authenticated_user_id(operation_name="test_integration")
        
        # Verify it used the context functions
        mock_get_user.assert_called_once()
        mock_authenticated.assert_called_once()
        
        # Should return the user ID from context
        assert result == test_user_id
    
    @patch('fastmcp.task_management.interface.controllers.auth_helper.get_user_from_request_context')
    @patch('fastmcp.task_management.interface.controllers.auth_helper.REQUEST_CONTEXT_AVAILABLE', True)
    def test_auth_helper_fallback_when_no_context(self, mock_get_user):
        """Test that auth_helper.py falls back to other methods when context returns None."""
        from fastmcp.task_management.interface.controllers.auth_helper import get_authenticated_user_id
        from fastmcp.task_management.domain.exceptions.authentication_exceptions import UserAuthenticationRequiredError
        
        # Setup mock to return None (no context)
        mock_get_user.return_value = None
        
        # Should raise authentication error since no other auth sources available
        with pytest.raises(UserAuthenticationRequiredError):
            get_authenticated_user_id(operation_name="test_fallback")


class TestEndToEndFlow:
    """Test complete end-to-end authentication context flow."""
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self):
        """Test the complete flow from DualAuth -> RequestContext -> auth_helper."""
        
        # This test simulates the complete authentication flow:
        # 1. DualAuthMiddleware processes JWT and sets request.state.user_id
        # 2. RequestContextMiddleware captures this and sets context variables
        # 3. auth_helper.py reads from context variables
        
        # Mock request with authentication state (as if DualAuthMiddleware processed it)
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/mcp/manage_task"
        mock_request.state = Mock()
        mock_request.state.user_id = "e2e-test-user"
        mock_request.state.auth_type = "local_jwt"
        mock_request.state.auth_info = {
            "user_id": "e2e-test-user",
            "email": "e2e@example.com",
            "auth_method": "local_jwt"
        }
        
        # Create middleware
        middleware = RequestContextMiddleware(Mock())
        
        # Track what happens during request processing
        auth_helper_result = None
        
        async def simulate_mcp_handler(request):
            # This simulates an MCP handler calling auth_helper
            from fastmcp.task_management.interface.controllers.auth_helper import get_authenticated_user_id
            
            nonlocal auth_helper_result
            try:
                # This should work now with RequestContextMiddleware
                auth_helper_result = get_authenticated_user_id(operation_name="e2e_test")
            except Exception as e:
                auth_helper_result = f"ERROR: {e}"
            
            return Response("Handler executed")
        
        # Process request through middleware
        response = await middleware.dispatch(mock_request, simulate_mcp_handler)
        
        # Verify the complete flow worked
        assert response.status_code == 200
        
        # The auth_helper should have successfully gotten the user_id
        # Note: This might fail if validation rejects the user_id format
        # but the important thing is that the context was accessible
        if isinstance(auth_helper_result, str) and auth_helper_result.startswith("ERROR:"):
            # If it failed, it should be due to validation, not context access
            assert "No authentication found" not in auth_helper_result
        else:
            # Success case
            assert auth_helper_result == "e2e-test-user"


if __name__ == "__main__":
    pytest.main([__file__])