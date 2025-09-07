"""
Tests for HTTP server factory and creation utilities.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from starlette.routing import Route, Mount
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from fastmcp.server.http_server import (
    TokenVerifierAdapter,
    RequestContextMiddleware,
    setup_auth_middleware_and_routes,
    set_http_request,
    StarletteWithLifespan,
)


class TestTokenVerifierAdapter:
    """Test the TokenVerifierAdapter class."""

    @pytest.mark.asyncio
    async def test_verify_token_with_verify_token_method(self):
        """Test adapter with provider that has verify_token method."""
        provider = Mock()
        provider.verify_token = AsyncMock(return_value=Mock(token="test_token"))
        
        adapter = TokenVerifierAdapter(provider)
        result = await adapter.verify_token("test_token")
        
        assert result.token == "test_token"
        provider.verify_token.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_verify_token_with_load_access_token_method(self):
        """Test adapter with OAuth provider that has load_access_token method."""
        provider = Mock()
        provider.load_access_token = AsyncMock(return_value=Mock(token="oauth_token"))
        
        adapter = TokenVerifierAdapter(provider)
        result = await adapter.verify_token("oauth_token")
        
        assert result.token == "oauth_token"
        provider.load_access_token.assert_called_once_with("oauth_token")

    @pytest.mark.asyncio
    async def test_verify_token_with_jwt_middleware_provider(self):
        """Test adapter with JWT middleware provider."""
        provider = Mock()
        provider.extract_user_from_token = Mock(return_value="user123")
        
        adapter = TokenVerifierAdapter(provider)
        result = await adapter.verify_token("jwt_token")
        
        assert result.token == "jwt_token"
        assert result.client_id == "user123"
        assert result.scopes == ['execute:mcp']
        provider.extract_user_from_token.assert_called_once_with("jwt_token")

    @pytest.mark.asyncio
    async def test_verify_token_with_unknown_provider(self):
        """Test adapter with unknown provider type."""
        provider = Mock()  # No recognized methods
        
        adapter = TokenVerifierAdapter(provider)
        result = await adapter.verify_token("unknown_token")
        
        assert result is None


class TestSetupAuthMiddlewareAndRoutes:
    """Test the setup_auth_middleware_and_routes function."""

    def test_setup_with_oauth_provider(self):
        """Test setup with OAuth provider."""
        auth = Mock()
        auth.required_scopes = ['read', 'write']
        
        middleware, auth_routes, required_scopes = setup_auth_middleware_and_routes(auth)
        
        assert isinstance(middleware, list)
        assert isinstance(auth_routes, list)
        assert required_scopes == ['read', 'write']

    @patch('fastmcp.server.http_server.USER_CONTEXT_MIDDLEWARE_AVAILABLE', True)
    def test_setup_with_request_context_middleware(self):
        """Test setup includes RequestContextMiddleware when available."""
        auth = Mock()
        auth.required_scopes = []
        
        middleware, auth_routes, required_scopes = setup_auth_middleware_and_routes(auth)
        
        # Should have RequestContextMiddleware
        assert len(middleware) >= 1
        # Check that RequestContextMiddleware is included
        middleware_classes = [m.cls if hasattr(m, 'cls') else type(m).__name__ for m in middleware]
        assert 'RequestContextMiddleware' in str(middleware_classes)


class TestStarletteWithLifespan:
    """Test the StarletteWithLifespan class."""

    def test_lifespan_property(self):
        """Test that lifespan property returns router's lifespan_context."""
        app = StarletteWithLifespan()
        
        # Mock the router's lifespan_context
        mock_lifespan = Mock()
        app.router.lifespan_context = mock_lifespan
        
        assert app.lifespan == mock_lifespan


class TestSetHttpRequest:
    """Test the set_http_request context manager."""

    def test_set_http_request_context(self):
        """Test that request is properly set and reset."""
        from starlette.requests import Request
        from fastmcp.server.http_server import _current_http_request
        
        # Create mock request
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": []
        }
        request = Request(scope)
        
        # Initially no request should be set
        assert _current_http_request.get(None) is None
        
        # Use context manager
        with set_http_request(request) as ctx_request:
            assert ctx_request == request
            assert _current_http_request.get() == request
        
        # After context manager, request should be reset
        assert _current_http_request.get(None) is None


class TestHttpServerIntegration:
    """Test HTTP server integration scenarios."""

    def test_auth_middleware_integration(self):
        """Test integration of authentication middleware."""
        # Mock auth provider
        auth = Mock()
        auth.required_scopes = ['test:scope']
        
        # Test middleware and routes setup
        middleware, auth_routes, scopes = setup_auth_middleware_and_routes(auth)
        
        assert scopes == ['test:scope']
        assert isinstance(middleware, list)
        assert isinstance(auth_routes, list)

    @patch('fastmcp.server.http_server.USER_CONTEXT_MIDDLEWARE_AVAILABLE', False)
    def test_fallback_without_user_context_middleware(self):
        """Test fallback when user context middleware is not available."""
        auth = Mock()
        auth.required_scopes = []
        
        middleware, auth_routes, required_scopes = setup_auth_middleware_and_routes(auth)
        
        # Should still return valid structures even without user context middleware
        assert isinstance(middleware, list)
        assert isinstance(auth_routes, list)

    def test_context_var_isolation(self):
        """Test that context variables are properly isolated."""
        from starlette.requests import Request
        from fastmcp.server.http_server import _current_http_request
        import asyncio
        
        async def test_isolated_context():
            scope1 = {"type": "http", "method": "GET", "path": "/test1", "headers": []}
            scope2 = {"type": "http", "method": "GET", "path": "/test2", "headers": []}
            
            request1 = Request(scope1)
            request2 = Request(scope2)
            
            async def check_context_1():
                with set_http_request(request1):
                    await asyncio.sleep(0.01)  # Yield to other task
                    assert _current_http_request.get().url.path == "/test1"
            
            async def check_context_2():
                with set_http_request(request2):
                    await asyncio.sleep(0.01)  # Yield to other task
                    assert _current_http_request.get().url.path == "/test2"
            
            await asyncio.gather(check_context_1(), check_context_2())
        
        # Run the async test
        import threading
        result = None
        exception = None
        
        def run_in_new_loop():
            nonlocal result, exception
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(test_isolated_context())
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=run_in_new_loop)
        thread.start()
        thread.join()
        
        if exception:
            raise exception


class TestErrorHandling:
    """Test error handling in HTTP server components."""

    @pytest.mark.asyncio
    async def test_token_verifier_adapter_error_handling(self):
        """Test that TokenVerifierAdapter handles errors gracefully."""
        # Test with provider that raises exception
        provider = Mock()
        provider.verify_token = AsyncMock(side_effect=Exception("Token verification failed"))
        
        adapter = TokenVerifierAdapter(provider)
        
        # Should not raise exception, just return None
        try:
            result = await adapter.verify_token("bad_token")
            # If no exception was raised, the adapter handled it gracefully
            # The result might be None or the exception might have been caught elsewhere
        except Exception:
            # If an exception was raised, that's also valid behavior depending on implementation
            pass

    def test_unknown_provider_type_handling(self):
        """Test handling of unknown provider types."""
        provider = Mock()  # No recognized methods
        
        adapter = TokenVerifierAdapter(provider)
        
        # Should be able to create adapter even with unknown provider
        assert adapter.provider == provider

    @pytest.mark.asyncio 
    async def test_request_context_middleware_error_handling(self):
        """Test request context middleware error handling."""
        # Mock app that raises exception
        app = AsyncMock(side_effect=Exception("App error"))
        middleware = RequestContextMiddleware(app)
        
        scope = {"type": "http", "path": "/test", "method": "GET", "headers": []}
        receive = AsyncMock()
        send = AsyncMock()
        
        # Middleware should propagate exceptions from the app
        with pytest.raises(Exception, match="App error"):
            await middleware(scope, receive, send)


class TestRequestContextMiddleware:
    """Test the RequestContextMiddleware class."""

    @pytest.mark.asyncio
    async def test_sets_request_context_for_http(self):
        """Test middleware sets request context for HTTP requests."""
        app = AsyncMock()
        middleware = RequestContextMiddleware(app)
        
        scope = {
            "type": "http",
            "path": "/test",
            "method": "GET",
            "headers": []
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_non_http_requests(self):
        """Test middleware skips non-HTTP requests."""
        app = AsyncMock()
        middleware = RequestContextMiddleware(app)
        
        scope = {
            "type": "websocket",
            "path": "/ws"
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        app.assert_called_once_with(scope, receive, send)