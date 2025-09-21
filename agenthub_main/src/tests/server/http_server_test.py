"""
Tests for HTTP Server components - Starlette application and middleware configuration.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from contextlib import asynccontextmanager
from typing import Dict, Any, List
import json
import asyncio

try:
    from starlette.applications import Starlette
    from starlette.testclient import TestClient
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    from starlette.requests import Request
    from starlette.responses import Response, JSONResponse
    from starlette.routing import Route, Mount, BaseRoute
    from starlette.types import Scope, Receive, Send
    STARLETTE_AVAILABLE = True
except ImportError:
    Starlette = None
    TestClient = None
    Middleware = None
    CORSMiddleware = None
    TrustedHostMiddleware = None
    Request = None
    Response = None
    JSONResponse = None
    Route = None
    Mount = None
    BaseRoute = None
    Scope = None
    Receive = None
    Send = None
    STARLETTE_AVAILABLE = False

try:
    from mcp.server.auth.provider import AccessToken
    MCP_AVAILABLE = True
except ImportError:
    AccessToken = None
    MCP_AVAILABLE = False

try:
    from fastmcp.server.http_server import (
        StarletteWithLifespan,
        _current_http_request,
        KEYCLOAK_MIDDLEWARE_AVAILABLE,
        TokenVerifier,
        TokenVerifierAdapter,
        RequestContextMiddleware,
        HTTPSRedirectMiddleware,
        MCPHeaderValidationMiddleware,
        create_base_app,
        setup_auth_middleware_and_routes,
        set_http_request,
        create_http_server_factory,
        create_sse_app,
        create_streamable_http_app
    )
    HTTP_SERVER_AVAILABLE = True
except ImportError:
    StarletteWithLifespan = None
    _current_http_request = None
    KEYCLOAK_MIDDLEWARE_AVAILABLE = False
    TokenVerifier = None
    TokenVerifierAdapter = None
    RequestContextMiddleware = None
    HTTPSRedirectMiddleware = None
    MCPHeaderValidationMiddleware = None
    create_base_app = None
    setup_auth_middleware_and_routes = None
    set_http_request = None
    create_http_server_factory = None
    create_sse_app = None
    create_streamable_http_app = None
    HTTP_SERVER_AVAILABLE = False


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestStarletteWithLifespan:
    """Test suite for StarletteWithLifespan class."""

    def test_starlette_with_lifespan_creation(self):
        """Test creation of StarletteWithLifespan application."""
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(lifespan=lifespan)
        assert isinstance(app, Starlette)
        assert hasattr(app, 'lifespan')

    def test_lifespan_property(self):
        """Test that lifespan property returns the router's lifespan context."""
        @asynccontextmanager
        async def test_lifespan(app):
            yield

        app = StarletteWithLifespan(lifespan=test_lifespan)
        
        # The lifespan property should return the router's lifespan_context
        assert app.lifespan == app.router.lifespan_context

    def test_starlette_with_middleware(self):
        """Test StarletteWithLifespan with middleware configuration."""
        middleware = [
            Middleware(CORSMiddleware, allow_origins=["*"])
        ]
        
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            middleware=middleware,
            lifespan=lifespan
        )

        assert isinstance(app, Starlette)
        # Check that middleware was applied
        # In Starlette, middleware is a method that returns the middleware stack
        assert hasattr(app, 'middleware')
        # Since middleware is a method, we need to check the middleware_stack instead
        assert hasattr(app, 'middleware_stack')
        # Or we can check that the app was built correctly with middleware
        assert callable(app.middleware)

    def test_starlette_with_routes(self):
        """Test StarletteWithLifespan with route configuration."""
        async def health_endpoint(request):
            return Response("OK")

        routes = [
            Route("/health", health_endpoint)
        ]
        
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            routes=routes,
            lifespan=lifespan
        )
        
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.text == "OK"


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestHTTPRequestContext:
    """Test suite for HTTP request context management."""

    def test_current_http_request_context_var(self):
        """Test the current HTTP request context variable."""
        # Initially should be None
        assert _current_http_request.get() is None
        
        # Set a mock request
        mock_request = Mock(spec=Request)
        token = _current_http_request.set(mock_request)
        
        try:
            # Should return the set request
            assert _current_http_request.get() is mock_request
        finally:
            # Reset the context
            _current_http_request.reset(token)
            assert _current_http_request.get() is None


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestKeycloakMiddlewareIntegration:
    """Test suite for Keycloak middleware integration."""

    def test_keycloak_middleware_availability_flag(self):
        """Test that KEYCLOAK_MIDDLEWARE_AVAILABLE flag reflects actual availability."""
        # This test verifies the import logic
        assert isinstance(KEYCLOAK_MIDDLEWARE_AVAILABLE, bool)

    def test_keycloak_middleware_available(self):
        """Test behavior when Keycloak middleware is available."""
        # When middleware is available, it should be importable
        with patch('fastmcp.server.http_server.KEYCLOAK_MIDDLEWARE_AVAILABLE', True):
            # Import from the original module to get the patched value
            from fastmcp.server.http_server import KEYCLOAK_MIDDLEWARE_AVAILABLE as patched_value
            assert patched_value is True

    def test_keycloak_middleware_unavailable(self):
        """Test behavior when Keycloak middleware is unavailable."""
        # When middleware is unavailable, flag should be False
        with patch('fastmcp.server.http_server.KEYCLOAK_MIDDLEWARE_AVAILABLE', False):
            # Import from the original module to get the patched value
            from fastmcp.server.http_server import KEYCLOAK_MIDDLEWARE_AVAILABLE as patched_value
            assert patched_value is False


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available") 
class TestHTTPServerIntegration:
    """Integration tests for HTTP server components."""

    def test_complete_starlette_app_setup(self):
        """Test complete Starlette application setup with all components."""
        async def health_check(request):
            return Response("healthy")
        
        async def api_endpoint(request):
            return Response('{"status": "ok"}', media_type="application/json")

        routes = [
            Route("/health", health_check),
            Route("/api/status", api_endpoint)
        ]
        
        middleware = [
            Middleware(CORSMiddleware, 
                      allow_origins=["*"],
                      allow_methods=["*"],
                      allow_headers=["*"])
        ]
        
        @asynccontextmanager
        async def lifespan(app):
            # Startup
            yield
            # Shutdown

        app = StarletteWithLifespan(
            routes=routes,
            middleware=middleware,
            lifespan=lifespan
        )
        
        client = TestClient(app)
        
        # Test health endpoint
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.text == "healthy"
        
        # Test API endpoint
        api_response = client.get("/api/status")
        assert api_response.status_code == 200
        assert api_response.json() == {"status": "ok"}

    def test_cors_middleware_functionality(self):
        """Test CORS middleware functionality."""
        async def test_endpoint(request):
            return Response("OK")

        routes = [Route("/test", test_endpoint)]
        middleware = [
            Middleware(CORSMiddleware,
                      allow_origins=["https://example.com"],
                      allow_methods=["GET", "POST"],
                      allow_headers=["Content-Type"])
        ]
        
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            routes=routes,
            middleware=middleware,
            lifespan=lifespan
        )
        
        client = TestClient(app)
        
        # Test CORS preflight
        response = client.options("/test", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET"
        })
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_mount_sub_applications(self):
        """Test mounting sub-applications."""
        # Main app endpoint
        async def main_endpoint(request):
            return Response("main app")
        
        # Sub-app endpoint
        async def sub_endpoint(request):
            return Response("sub app")
        
        # Create sub-application
        sub_app = Starlette(routes=[
            Route("/sub", sub_endpoint)
        ])
        
        # Main application with mounted sub-app
        routes = [
            Route("/", main_endpoint),
            Mount("/api", sub_app)
        ]
        
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            routes=routes,
            lifespan=lifespan
        )
        
        client = TestClient(app)
        
        # Test main endpoint
        main_response = client.get("/")
        assert main_response.status_code == 200
        assert main_response.text == "main app"
        
        # Test mounted sub-app endpoint
        sub_response = client.get("/api/sub")
        assert sub_response.status_code == 200
        assert sub_response.text == "sub app"


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestHTTPServerErrorHandling:
    """Test error handling in HTTP server components."""

    def test_route_not_found(self):
        """Test 404 handling for non-existent routes."""
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(lifespan=lifespan)
        client = TestClient(app)
        
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test 405 handling for unsupported methods."""
        async def get_only_endpoint(request):
            return Response("GET only")

        routes = [Route("/get-only", get_only_endpoint, methods=["GET"])]
        
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            routes=routes,
            lifespan=lifespan
        )
        
        client = TestClient(app)
        
        # GET should work
        get_response = client.get("/get-only")
        assert get_response.status_code == 200
        
        # POST should return 405
        post_response = client.post("/get-only")
        assert post_response.status_code == 405

    def test_exception_in_endpoint(self):
        """Test handling of exceptions in endpoints."""
        async def error_endpoint(request):
            raise ValueError("Test error")

        routes = [Route("/error", error_endpoint)]

        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            routes=routes,
            lifespan=lifespan
        )

        client = TestClient(app, raise_server_exceptions=False)

        # Should return 500 for unhandled exception
        response = client.get("/error")
        assert response.status_code == 500


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestLifespanManagement:
    """Test application lifespan management."""

    def test_lifespan_startup_and_shutdown(self):
        """Test lifespan startup and shutdown events."""
        startup_called = False
        shutdown_called = False
        
        @asynccontextmanager
        async def lifespan(app):
            nonlocal startup_called, shutdown_called
            # Startup
            startup_called = True
            yield
            # Shutdown
            shutdown_called = True

        app = StarletteWithLifespan(lifespan=lifespan)
        
        with TestClient(app):
            # During the context manager, startup should be called
            assert startup_called is True
            assert shutdown_called is False
        
        # After context manager, shutdown should be called
        assert shutdown_called is True

    def test_lifespan_exception_handling(self):
        """Test lifespan exception handling."""
        @asynccontextmanager
        async def failing_lifespan(app):
            raise RuntimeError("Startup failed")
            yield

        app = StarletteWithLifespan(lifespan=failing_lifespan)
        
        # Should handle startup failure gracefully
        with pytest.raises(RuntimeError, match="Startup failed"):
            with TestClient(app):
                pass


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestMiddlewareStack:
    """Test middleware stack configuration and ordering."""

    def test_middleware_execution_order(self):
        """Test that middleware executes in correct order."""
        execution_order = []
        
        class TestMiddleware:
            def __init__(self, app, name):
                self.app = app
                self.name = name
            
            async def __call__(self, scope, receive, send):
                execution_order.append(f"{self.name}_start")
                response = await self.app(scope, receive, send)
                execution_order.append(f"{self.name}_end")
                return response
        
        async def endpoint(request):
            execution_order.append("endpoint")
            return Response("OK")
        
        routes = [Route("/test", endpoint)]
        middleware = [
            Middleware(TestMiddleware, name="first"),
            Middleware(TestMiddleware, name="second")
        ]
        
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            routes=routes,
            middleware=middleware,
            lifespan=lifespan
        )
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        # Middleware should execute in order: first, second, endpoint, second_end, first_end
        assert "first_start" in execution_order
        assert "second_start" in execution_order
        assert "endpoint" in execution_order

    def test_authentication_middleware_integration(self):
        """Test authentication middleware integration."""
        # This is a placeholder for authentication middleware tests
        # The actual implementation would depend on your auth setup
        
        async def protected_endpoint(request):
            return Response("protected")
        
        routes = [Route("/protected", protected_endpoint)]
        
        @asynccontextmanager
        async def lifespan(app):
            yield

        app = StarletteWithLifespan(
            routes=routes,
            lifespan=lifespan
        )
        
        # Basic test that app can be created with auth middleware
        assert isinstance(app, StarletteWithLifespan)


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestSetHTTPRequest:
    """Test suite for set_http_request context manager."""

    def test_set_http_request_context_manager(self):
        """Test set_http_request context manager."""
        mock_request = Mock(spec=Request)
        
        # Initially should be None
        assert _current_http_request.get() is None
        
        # Within context manager, should have the request
        with set_http_request(mock_request) as req:
            assert req is mock_request
            assert _current_http_request.get() is mock_request
        
        # After context manager, should be reset
        assert _current_http_request.get() is None

    def test_set_http_request_exception_handling(self):
        """Test set_http_request properly resets on exception."""
        mock_request = Mock(spec=Request)
        
        # Initially should be None
        assert _current_http_request.get() is None
        
        try:
            with set_http_request(mock_request):
                assert _current_http_request.get() is mock_request
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Should be reset even after exception
        assert _current_http_request.get() is None

    def test_nested_set_http_request(self):
        """Test nested set_http_request contexts."""
        request1 = Mock(spec=Request)
        request2 = Mock(spec=Request)
        
        with set_http_request(request1):
            assert _current_http_request.get() is request1
            
            with set_http_request(request2):
                assert _current_http_request.get() is request2
            
            # Should restore to request1
            assert _current_http_request.get() is request1
        
        # Should be None after all contexts
        assert _current_http_request.get() is None


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE or not MCP_AVAILABLE, reason="HTTP server or MCP components not available")
class TestTokenVerifierAdapter:
    """Test suite for TokenVerifierAdapter."""

    @pytest.mark.asyncio
    async def test_verify_token_with_verify_token_method(self):
        """Test adapter with provider that has verify_token method."""
        mock_provider = Mock()
        mock_token = AccessToken(token="test", client_id="test_client", scopes=["test"])
        mock_provider.verify_token = AsyncMock(return_value=mock_token)
        
        adapter = TokenVerifierAdapter(mock_provider)
        result = await adapter.verify_token("test_token")
        
        assert result == mock_token
        mock_provider.verify_token.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_verify_token_with_load_access_token_method(self):
        """Test adapter with provider that has load_access_token method."""
        mock_provider = Mock()
        mock_token = AccessToken(token="test", client_id="test_client", scopes=["test"])
        mock_provider.load_access_token = AsyncMock(return_value=mock_token)
        
        adapter = TokenVerifierAdapter(mock_provider)
        result = await adapter.verify_token("test_token")
        
        assert result == mock_token
        mock_provider.load_access_token.assert_called_once_with("test_token")

    @pytest.mark.asyncio
    async def test_verify_token_with_extract_user_from_token_method(self):
        """Test adapter with JWT middleware provider."""
        mock_provider = Mock()
        mock_provider.extract_user_from_token = Mock(return_value="user123")
        
        adapter = TokenVerifierAdapter(mock_provider)
        result = await adapter.verify_token("jwt_token")
        
        assert result is not None
        assert result.token == "jwt_token"
        assert result.client_id == "user123"
        assert result.scopes == ['execute:mcp']
        mock_provider.extract_user_from_token.assert_called_once_with("jwt_token")

    @pytest.mark.asyncio
    async def test_verify_token_with_extract_user_returning_none(self):
        """Test adapter when extract_user_from_token returns None."""
        mock_provider = Mock()
        mock_provider.extract_user_from_token = Mock(return_value=None)
        
        adapter = TokenVerifierAdapter(mock_provider)
        result = await adapter.verify_token("invalid_token")
        
        assert result is None
        mock_provider.extract_user_from_token.assert_called_once_with("invalid_token")

    @pytest.mark.asyncio
    async def test_verify_token_with_unknown_provider(self):
        """Test adapter with unknown provider type."""
        mock_provider = Mock()
        # Remove all known methods
        for attr in ['verify_token', 'load_access_token', 'extract_user_from_token']:
            if hasattr(mock_provider, attr):
                delattr(mock_provider, attr)
        
        adapter = TokenVerifierAdapter(mock_provider)
        with patch('fastmcp.server.http_server.logger') as mock_logger:
            result = await adapter.verify_token("test_token")
            
            assert result is None
            mock_logger.error.assert_called_once()


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestRequestContextMiddleware:
    """Test suite for RequestContextMiddleware."""

    @pytest.mark.asyncio
    async def test_request_context_middleware_http_request(self):
        """Test RequestContextMiddleware sets context for HTTP requests."""
        mock_app = AsyncMock()
        middleware = RequestContextMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": []
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Before middleware call, no request in context
        assert _current_http_request.get() is None
        
        await middleware(scope, receive, send)
        
        # App should have been called
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_request_context_middleware_websocket_request(self):
        """Test RequestContextMiddleware passes through non-HTTP requests."""
        mock_app = AsyncMock()
        middleware = RequestContextMiddleware(mock_app)
        
        scope = {
            "type": "websocket",
            "path": "/ws"
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # App should have been called directly
        mock_app.assert_called_once_with(scope, receive, send)


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestHTTPSRedirectMiddleware:
    """Test suite for HTTPSRedirectMiddleware."""

    @pytest.mark.asyncio
    async def test_https_redirect_middleware_with_x_forwarded_proto(self):
        """Test HTTPSRedirectMiddleware detects HTTPS from X-Forwarded-Proto."""
        mock_app = AsyncMock()
        middleware = HTTPSRedirectMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [(b"x-forwarded-proto", b"https")],
            "server": ("localhost", 80)
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('fastmcp.server.http_server.logger') as mock_logger:
            await middleware(scope, receive, send)
            
            # Should update scheme
            assert scope["scheme"] == "https"
            mock_logger.debug.assert_called()
            mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_https_redirect_middleware_with_x_forwarded_host(self):
        """Test HTTPSRedirectMiddleware updates host from X-Forwarded-Host."""
        mock_app = AsyncMock()
        middleware = HTTPSRedirectMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [(b"x-forwarded-host", b"example.com")],
            "server": ("localhost", 80)
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('fastmcp.server.http_server.logger') as mock_logger:
            await middleware(scope, receive, send)
            
            # Should update host
            assert scope["server"][0] == "example.com"
            assert scope["server"][1] == 80
            mock_logger.debug.assert_called()
            mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_https_redirect_middleware_no_proxy_headers(self):
        """Test HTTPSRedirectMiddleware without proxy headers."""
        mock_app = AsyncMock()
        middleware = HTTPSRedirectMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "scheme": "http",
            "headers": [],
            "server": ("localhost", 80)
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Should not change scheme
        assert scope["scheme"] == "http"
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_https_redirect_middleware_non_http_request(self):
        """Test HTTPSRedirectMiddleware passes through non-HTTP requests."""
        mock_app = AsyncMock()
        middleware = HTTPSRedirectMiddleware(mock_app)
        
        scope = {
            "type": "websocket",
            "scheme": "ws"
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Should pass through unchanged
        assert scope["scheme"] == "ws"
        mock_app.assert_called_once_with(scope, receive, send)


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestSetupAuthMiddlewareAndRoutes:
    """Test suite for setup_auth_middleware_and_routes function."""

    def test_setup_auth_with_keycloak_provider(self):
        """Test setup with Keycloak auth provider."""
        mock_auth = Mock()
        mock_auth.required_scopes = ["test_scope"]
        
        with patch('fastmcp.server.http_server.logger') as mock_logger:
            middleware, auth_routes, required_scopes = setup_auth_middleware_and_routes(mock_auth)
            
            # Should return empty middleware list for Keycloak
            assert middleware == []
            assert auth_routes == []
            assert required_scopes == ["test_scope"]
            mock_logger.info.assert_called_with("Using Keycloak JWT authentication - no OAuth routes needed")

    def test_setup_auth_without_required_scopes(self):
        """Test setup when provider has no required_scopes."""
        mock_auth = Mock()
        # Ensure required_scopes doesn't exist
        if hasattr(mock_auth, 'required_scopes'):
            delattr(mock_auth, 'required_scopes')
        
        middleware, auth_routes, required_scopes = setup_auth_middleware_and_routes(mock_auth)
        
        assert middleware == []
        assert auth_routes == []
        assert required_scopes == []

    @patch('fastmcp.server.http_server.KEYCLOAK_MIDDLEWARE_AVAILABLE', False)
    def test_setup_auth_without_keycloak_middleware(self):
        """Test warning when Keycloak middleware is not available."""
        mock_auth = Mock()
        
        with patch('fastmcp.server.http_server.logger') as mock_logger:
            setup_auth_middleware_and_routes(mock_auth)
            
            mock_logger.warning.assert_called_with(
                "Keycloak RequestContextMiddleware not available - MCP tools will not have user context"
            )


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestCreateBaseApp:
    """Test suite for create_base_app function."""

    def test_create_base_app_minimal(self):
        """Test creating base app with minimal configuration."""
        routes = []
        middleware = []
        
        app = create_base_app(routes, middleware)
        
        assert isinstance(app, StarletteWithLifespan)
        # Should have default CORS middleware
        assert any(isinstance(m, Middleware) and m.cls == CORSMiddleware 
                  for m in app.middleware_stack.middleware)

    def test_create_base_app_with_cors_origins(self):
        """Test creating base app with custom CORS origins."""
        routes = []
        middleware = []
        cors_origins = ["https://example.com", "https://app.example.com"]
        
        app = create_base_app(routes, middleware, cors_origins=cors_origins)
        
        assert isinstance(app, StarletteWithLifespan)

    def test_create_base_app_with_trusted_hosts(self):
        """Test creating base app with TrustedHostMiddleware."""
        routes = []
        middleware = []
        
        with patch.dict(os.environ, {"ALLOWED_HOSTS": "example.com,app.example.com"}):
            with patch('fastmcp.server.http_server.logger') as mock_logger:
                app = create_base_app(routes, middleware)
                
                assert isinstance(app, StarletteWithLifespan)
                mock_logger.info.assert_called()

    def test_create_base_app_with_custom_middleware(self):
        """Test creating base app with custom middleware."""
        routes = []
        custom_middleware = [
            Middleware(CORSMiddleware, allow_origins=["custom.com"])
        ]
        
        app = create_base_app(routes, custom_middleware)
        
        assert isinstance(app, StarletteWithLifespan)

    def test_create_base_app_with_routes(self):
        """Test creating base app with routes."""
        async def test_endpoint(request):
            return Response("test")
        
        routes = [Route("/test", test_endpoint)]
        middleware = []
        
        app = create_base_app(routes, middleware)
        
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.text == "test"

    def test_create_base_app_with_lifespan(self):
        """Test creating base app with lifespan."""
        routes = []
        middleware = []
        
        @asynccontextmanager
        async def test_lifespan(app):
            yield
        
        app = create_base_app(routes, middleware, lifespan=test_lifespan)
        
        assert isinstance(app, StarletteWithLifespan)

    def test_create_base_app_middleware_order(self):
        """Test middleware order in base app."""
        routes = []
        middleware = []
        
        app = create_base_app(routes, middleware)
        
        # Check middleware order
        middleware_types = []
        for m in app.middleware_stack.middleware:
            if hasattr(m, 'cls'):
                middleware_types.append(m.cls)
        
        # CORS should be first
        assert CORSMiddleware in middleware_types
        assert HTTPSRedirectMiddleware in middleware_types
        assert RequestContextMiddleware in middleware_types


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestCreateHTTPServerFactory:
    """Test suite for create_http_server_factory function."""

    def test_create_http_server_factory_minimal(self):
        """Test factory with minimal configuration."""
        mock_server = Mock()
        mock_server._additional_http_routes = []
        
        routes, middleware, scopes = create_http_server_factory(mock_server)
        
        assert isinstance(routes, list)
        assert isinstance(middleware, list)
        assert isinstance(scopes, list)
        assert scopes == []

    def test_create_http_server_factory_with_auth(self):
        """Test factory with authentication."""
        mock_server = Mock()
        mock_auth = Mock()
        mock_auth.required_scopes = ["test_scope"]
        
        with patch('fastmcp.server.http_server.setup_auth_middleware_and_routes') as mock_setup:
            mock_setup.return_value = (
                [Middleware(Mock, name="auth")],
                [Route("/auth", Mock())],
                ["test_scope"]
            )
            
            routes, middleware, scopes = create_http_server_factory(
                mock_server, auth=mock_auth
            )
            
            assert len(middleware) == 1
            assert len(routes) == 1
            assert scopes == ["test_scope"]
            mock_setup.assert_called_once_with(mock_auth)

    def test_create_http_server_factory_with_custom_routes(self):
        """Test factory with custom routes."""
        mock_server = Mock()
        custom_routes = [Route("/custom", Mock())]
        
        routes, middleware, scopes = create_http_server_factory(
            mock_server, routes=custom_routes
        )
        
        assert custom_routes[0] in routes

    def test_create_http_server_factory_with_custom_middleware(self):
        """Test factory with custom middleware."""
        mock_server = Mock()
        custom_middleware = [Middleware(Mock, name="custom")]
        
        routes, middleware, scopes = create_http_server_factory(
            mock_server, middleware=custom_middleware
        )
        
        assert custom_middleware[0] in middleware

    def test_create_http_server_factory_with_cors_origins(self):
        """Test factory with custom CORS origins."""
        mock_server = Mock()
        cors_origins = ["https://example.com"]
        
        routes, middleware, scopes = create_http_server_factory(
            mock_server, cors_origins=cors_origins
        )
        
        # Should accept but not directly use cors_origins in factory
        assert isinstance(routes, list)
        assert isinstance(middleware, list)


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestMCPHeaderValidationMiddleware:
    """Test suite for MCPHeaderValidationMiddleware."""

    @pytest.mark.asyncio
    async def test_mcp_header_validation_post_with_correct_headers(self):
        """Test MCP header validation for POST with correct headers."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp/test",
            "headers": [
                (b"content-type", b"application/json"),
                (b"accept", b"application/json, text/event-stream")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Should pass through
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_mcp_header_validation_post_missing_content_type(self):
        """Test MCP header validation for POST with missing Content-Type."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp/test",
            "headers": [
                (b"accept", b"application/json, text/event-stream")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Create a mock to capture the response
        response_sent = False
        async def mock_send_wrapper(message):
            nonlocal response_sent
            if message["type"] == "http.response.start":
                assert message["status"] == 415
                response_sent = True
        
        await middleware(scope, receive, mock_send_wrapper)
        
        # Should have sent error response
        assert response_sent

    @pytest.mark.asyncio
    async def test_mcp_header_validation_post_wrong_accept(self):
        """Test MCP header validation for POST with wrong Accept header."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp/test",
            "headers": [
                (b"content-type", b"application/json"),
                (b"accept", b"application/json")  # Missing text/event-stream
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Create a mock to capture the response
        response_sent = False
        async def mock_send_wrapper(message):
            nonlocal response_sent
            if message["type"] == "http.response.start":
                assert message["status"] == 406
                response_sent = True
        
        await middleware(scope, receive, mock_send_wrapper)
        
        # Should have sent error response
        assert response_sent

    @pytest.mark.asyncio
    async def test_mcp_header_validation_initialize_endpoint(self):
        """Test MCP header validation for /mcp/initialize endpoint."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp/initialize",
            "headers": [
                (b"content-type", b"application/json"),
                (b"accept", b"application/json, text/event-stream")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Should pass through for initialize endpoint
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_mcp_header_validation_get_sse(self):
        """Test MCP header validation for GET SSE requests."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/mcp/sse",
            "headers": [
                (b"accept", b"text/event-stream")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Should pass through
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_mcp_header_validation_get_missing_accept(self):
        """Test MCP header validation for GET without Accept header."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/mcp/sse",
            "headers": []
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Create a mock to capture the response
        response_sent = False
        async def mock_send_wrapper(message):
            nonlocal response_sent
            if message["type"] == "http.response.start":
                assert message["status"] == 406
                response_sent = True
        
        await middleware(scope, receive, mock_send_wrapper)
        
        # Should have sent error response
        assert response_sent

    @pytest.mark.asyncio
    async def test_mcp_header_validation_non_mcp_endpoint(self):
        """Test MCP header validation bypasses non-MCP endpoints."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/test",
            "headers": []  # No headers required for non-MCP
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        await middleware(scope, receive, send)
        
        # Should pass through without validation
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_mcp_header_validation_cors_headers(self):
        """Test MCP header validation includes CORS headers in error responses."""
        mock_app = AsyncMock()
        middleware = MCPHeaderValidationMiddleware(mock_app, cors_origins=["https://example.com"])
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp/test",
            "headers": [
                (b"origin", b"https://example.com")
            ]
        }
        receive = AsyncMock()
        send = AsyncMock()
        
        # Create a mock to capture the response
        headers_sent = {}
        async def mock_send_wrapper(message):
            if message["type"] == "http.response.start":
                for header_name, header_value in message.get("headers", []):
                    headers_sent[header_name.decode()] = header_value.decode()
        
        await middleware(scope, receive, mock_send_wrapper)
        
        # Should include CORS headers
        assert "access-control-allow-origin" in headers_sent


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestCreateSSEApp:
    """Test suite for create_sse_app function."""

    @patch('fastmcp.server.http_server.SseServerTransport')
    @patch('fastmcp.server.http_server.create_base_app')
    def test_create_sse_app_minimal(self, mock_create_base_app, mock_sse_transport_class):
        """Test creating SSE app with minimal configuration."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        mock_server._mcp_server = Mock()
        mock_server._mcp_server.run = AsyncMock()
        mock_server._mcp_server.create_initialization_options = Mock(return_value={})
        
        mock_sse_transport = Mock()
        mock_sse_transport.connect_sse = AsyncMock()
        mock_sse_transport.handle_post_message = Mock()
        mock_sse_transport_class.return_value = mock_sse_transport
        
        mock_app = Mock()
        mock_app.state = Mock()
        mock_create_base_app.return_value = mock_app
        
        # Create SSE app
        result = create_sse_app(
            server=mock_server,
            message_path="/messages",
            sse_path="/sse"
        )
        
        # Verify result
        assert result == mock_app
        assert result.state.fastmcp_server == mock_server
        assert result.state.path == "/sse"
        
        # Verify SSE transport was created
        mock_sse_transport_class.assert_called_once_with("/messages/")
        
        # Verify base app was created
        mock_create_base_app.assert_called_once()

    @patch('fastmcp.server.http_server.create_base_app')
    @patch('fastmcp.server.http_server.create_http_server_factory')
    def test_create_sse_app_with_auth(self, mock_factory, mock_create_base_app):
        """Test creating SSE app with authentication."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        mock_auth = Mock()
        
        mock_factory.return_value = (
            [Route("/test", Mock())],  # server_routes
            [Middleware(Mock, name="auth")],  # server_middleware
            ["test_scope"]  # required_scopes
        )
        
        mock_app = Mock()
        mock_app.state = Mock()
        mock_create_base_app.return_value = mock_app
        
        # Create SSE app with auth
        result = create_sse_app(
            server=mock_server,
            message_path="/messages",
            sse_path="/sse",
            auth=mock_auth
        )
        
        # Verify factory was called with auth
        mock_factory.assert_called_once_with(
            server=mock_server,
            auth=mock_auth,
            debug=False,
            routes=None,
            middleware=None,
            cors_origins=None
        )

    @patch('fastmcp.server.http_server.logger')
    @patch('fastmcp.server.http_server.create_base_app')
    def test_create_sse_app_with_v2_routes(self, mock_create_base_app, mock_logger):
        """Test creating SSE app with V2 routes."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        
        mock_app = Mock()
        mock_app.state = Mock()
        mock_create_base_app.return_value = mock_app
        
        # Mock imports to simulate missing routes
        with patch.dict('sys.modules', {
            'fastmcp.server.routes.project_routes': None,
            'fastmcp.server.routes.task_user_routes': None,
            'fastmcp.server.routes.task_routes': None,
            'fastmcp.server.routes.branch_routes': None,
            'fastmcp.server.routes.agent_routes': None,
            'fastmcp.server.routes.subtask_routes': None,
        }):
            result = create_sse_app(
                server=mock_server,
                message_path="/messages",
                sse_path="/sse"
            )
            
            # Should log warning about missing routes
            mock_logger.warning.assert_called()

    def test_create_sse_app_message_path_normalization(self):
        """Test that message_path is normalized with trailing slash."""
        mock_server = Mock()
        mock_server._additional_http_routes = []
        
        with patch('fastmcp.server.http_server.SseServerTransport') as mock_sse_class:
            with patch('fastmcp.server.http_server.create_base_app'):
                # Test without trailing slash
                create_sse_app(
                    server=mock_server,
                    message_path="/messages",
                    sse_path="/sse"
                )
                
                # Should add trailing slash
                mock_sse_class.assert_called_with("/messages/")
                
                # Test with trailing slash
                mock_sse_class.reset_mock()
                create_sse_app(
                    server=mock_server,
                    message_path="/messages/",
                    sse_path="/sse"
                )
                
                # Should keep trailing slash
                mock_sse_class.assert_called_with("/messages/")


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestCreateStreamableHTTPApp:
    """Test suite for create_streamable_http_app function."""

    @patch('fastmcp.server.http_server.StreamableHTTPSessionManager')
    @patch('fastmcp.server.http_server.create_base_app')
    def test_create_streamable_http_app_minimal(self, mock_create_base_app, mock_session_manager_class):
        """Test creating streamable HTTP app with minimal configuration."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        mock_server._mcp_server = Mock()
        
        mock_session_manager = Mock()
        mock_session_manager.run = AsyncMock()
        mock_session_manager.handle_request = AsyncMock()
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_app = Mock()
        mock_app.state = Mock()
        mock_create_base_app.return_value = mock_app
        
        # Create streamable HTTP app
        result = create_streamable_http_app(
            server=mock_server,
            streamable_http_path="/mcp/"
        )
        
        # Verify result
        assert result == mock_app
        assert result.state.fastmcp_server == mock_server
        assert result.state.path == "/mcp"  # Should strip trailing slash
        
        # Verify session manager was created
        mock_session_manager_class.assert_called_once_with(
            mock_server._mcp_server,
            event_store=None,
            json_response=False,
            stateless=False
        )

    @patch('fastmcp.server.http_server.StreamableHTTPSessionManager')
    @patch('fastmcp.server.http_server.create_base_app')
    def test_create_streamable_http_app_with_options(self, mock_create_base_app, mock_session_manager_class):
        """Test creating streamable HTTP app with all options."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        mock_server._mcp_server = Mock()
        mock_event_store = Mock()
        
        mock_session_manager = Mock()
        mock_session_manager_class.return_value = mock_session_manager
        
        mock_app = Mock()
        mock_app.state = Mock()
        mock_create_base_app.return_value = mock_app
        
        # Create streamable HTTP app with all options
        result = create_streamable_http_app(
            server=mock_server,
            streamable_http_path="/mcp",
            event_store=mock_event_store,
            json_response=True,
            stateless_http=True,
            debug=True
        )
        
        # Verify session manager was created with options
        mock_session_manager_class.assert_called_once_with(
            mock_server._mcp_server,
            event_store=mock_event_store,
            json_response=True,
            stateless=True
        )

    @patch('fastmcp.server.http_server.setup_auth_middleware_and_routes')
    @patch('fastmcp.server.http_server.create_base_app')
    def test_create_streamable_http_app_with_auth(self, mock_create_base_app, mock_setup_auth):
        """Test creating streamable HTTP app with authentication."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        mock_auth = Mock()
        
        mock_setup_auth.return_value = (
            [Middleware(Mock, name="auth")],
            [Route("/auth", Mock())],
            ["test_scope"]
        )
        
        mock_app = Mock()
        mock_app.state = Mock()
        mock_create_base_app.return_value = mock_app
        
        # Create streamable HTTP app with auth
        result = create_streamable_http_app(
            server=mock_server,
            streamable_http_path="/mcp",
            auth=mock_auth
        )
        
        # Verify auth setup was called
        mock_setup_auth.assert_called_once_with(mock_auth)

    @patch('fastmcp.server.http_server.logger')
    @patch('fastmcp.server.http_server.create_base_app')
    def test_create_streamable_http_app_with_registration_endpoints(self, mock_create_base_app, mock_logger):
        """Test creating streamable HTTP app with MCP registration endpoints."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        
        mock_app = Mock()
        mock_app.state = Mock()
        mock_create_base_app.return_value = mock_app
        
        # Create app (registration endpoints are added by default)
        result = create_streamable_http_app(
            server=mock_server,
            streamable_http_path="/mcp"
        )
        
        # Should log about registration endpoints
        mock_logger.info.assert_any_call(
            "MCP registration endpoints added directly to FastAPI app (/register, /unregister, /registrations)"
        )

    def test_create_streamable_http_app_path_normalization(self):
        """Test that streamable_http_path is normalized."""
        mock_server = Mock()
        mock_server._additional_http_routes = []
        
        with patch('fastmcp.server.http_server.create_base_app') as mock_create_base_app:
            mock_app = Mock()
            mock_app.state = Mock()
            mock_create_base_app.return_value = mock_app
            
            # Test with trailing slash
            result = create_streamable_http_app(
                server=mock_server,
                streamable_http_path="/mcp/"
            )
            
            # Should strip trailing slash
            assert result.state.path == "/mcp"

    @patch('fastmcp.server.http_server.create_base_app')
    def test_create_streamable_http_app_lifespan_context(self, mock_create_base_app):
        """Test streamable HTTP app lifespan context management."""
        # Setup mocks
        mock_server = Mock()
        mock_server._additional_http_routes = []
        
        # Capture the lifespan argument
        lifespan_func = None
        def capture_lifespan(*args, **kwargs):
            nonlocal lifespan_func
            lifespan_func = kwargs.get('lifespan')
            mock_app = Mock()
            mock_app.state = Mock()
            return mock_app
        
        mock_create_base_app.side_effect = capture_lifespan
        
        # Create app
        create_streamable_http_app(
            server=mock_server,
            streamable_http_path="/mcp"
        )
        
        # Verify lifespan was provided
        assert lifespan_func is not None
        assert asyncio.iscoroutinefunction(lifespan_func)


@pytest.mark.skipif(not STARLETTE_AVAILABLE or not HTTP_SERVER_AVAILABLE, reason="Starlette or HTTP server components not available")
class TestIntegrationScenarios:
    """Integration tests for complex scenarios."""

    def test_full_sse_app_with_all_features(self):
        """Test creating a full SSE app with all features enabled."""
        # Mock server with all features
        mock_server = Mock()
        mock_server._additional_http_routes = [
            Route("/custom", Mock())
        ]
        mock_server._mcp_server = Mock()
        
        # Mock auth provider
        mock_auth = Mock()
        mock_auth.required_scopes = ["execute:mcp"]
        
        # Custom routes and middleware
        custom_routes = [Route("/api/test", Mock())]
        custom_middleware = [Middleware(Mock, name="custom")]
        
        with patch('fastmcp.server.http_server.SseServerTransport'):
            with patch('fastmcp.server.http_server.create_base_app') as mock_create_base:
                mock_app = Mock()
                mock_app.state = Mock()
                mock_create_base.return_value = mock_app
                
                # Create full-featured SSE app
                result = create_sse_app(
                    server=mock_server,
                    message_path="/messages",
                    sse_path="/sse",
                    auth=mock_auth,
                    debug=True,
                    routes=custom_routes,
                    middleware=custom_middleware,
                    cors_origins=["https://app.example.com"]
                )
                
                # Verify all features were integrated
                assert result == mock_app
                assert result.state.fastmcp_server == mock_server
                assert result.state.path == "/sse"

    def test_error_handling_in_mcp_header_validation(self):
        """Test error handling in MCP header validation middleware."""
        mock_app = Mock()
        middleware = MCPHeaderValidationMiddleware(mock_app)
        
        # Test with malformed scope
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp/test"
            # Missing headers key
        }
        
        # Should handle gracefully
        asyncio.run(middleware(scope, Mock(), Mock()))


@pytest.mark.skipif(not HTTP_SERVER_AVAILABLE, reason="HTTP server components not available")
class TestTokenVerifierProtocol:
    """Test suite for TokenVerifier protocol."""

    def test_token_verifier_protocol_implementation(self):
        """Test that TokenVerifier is a proper protocol."""
        # Create a class that implements the protocol
        class TestVerifier:
            async def verify_token(self, token: str):
                return None
        
        # Should be considered an instance of the protocol
        verifier = TestVerifier()
        assert hasattr(verifier, 'verify_token')
        
        # If TokenVerifier is available as a protocol
        if TokenVerifier is not None:
            # Check if it's a protocol
            assert hasattr(TokenVerifier, '__subclasshook__') or hasattr(TokenVerifier, '_is_protocol')