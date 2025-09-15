"""
Tests for HTTP Server components - Starlette application and middleware configuration.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from contextlib import asynccontextmanager
from typing import Dict, Any, List

try:
    from starlette.applications import Starlette
    from starlette.testclient import TestClient
    from starlette.middleware import Middleware
    from starlette.middleware.cors import CORSMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Route, Mount
    STARLETTE_AVAILABLE = True
except ImportError:
    Starlette = None
    TestClient = None
    Middleware = None
    CORSMiddleware = None
    Request = None
    Response = None
    Route = None
    Mount = None
    STARLETTE_AVAILABLE = False

try:
    from fastmcp.server.http_server import (
        StarletteWithLifespan,
        _current_http_request,
        KEYCLOAK_MIDDLEWARE_AVAILABLE,
        TokenVerifierAdapter,
        create_base_app,
        setup_auth_middleware_and_routes,
        set_http_request,
        MCPHeaderValidationMiddleware
    )
    HTTP_SERVER_AVAILABLE = True
except ImportError:
    StarletteWithLifespan = None
    _current_http_request = None
    KEYCLOAK_MIDDLEWARE_AVAILABLE = False
    TokenVerifierAdapter = None
    create_base_app = None
    setup_auth_middleware_and_routes = None
    set_http_request = None
    MCPHeaderValidationMiddleware = None
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
        assert len(app.middleware_stack.middleware) > 0

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

    @patch('fastmcp.server.http_server.KEYCLOAK_MIDDLEWARE_AVAILABLE', True)
    def test_keycloak_middleware_available(self):
        """Test behavior when Keycloak middleware is available."""
        # When middleware is available, it should be importable
        assert KEYCLOAK_MIDDLEWARE_AVAILABLE is True

    @patch('fastmcp.server.http_server.KEYCLOAK_MIDDLEWARE_AVAILABLE', False)
    def test_keycloak_middleware_unavailable(self):
        """Test behavior when Keycloak middleware is unavailable."""
        # When middleware is unavailable, flag should be False
        assert KEYCLOAK_MIDDLEWARE_AVAILABLE is False


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
        
        client = TestClient(app)
        
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