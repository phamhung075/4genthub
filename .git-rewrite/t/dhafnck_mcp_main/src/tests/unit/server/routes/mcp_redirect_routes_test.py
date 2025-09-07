"""
Tests for MCP Redirect Routes

Tests handling of common MCP client misconfigurations by redirecting to proper endpoints.
"""

import pytest
from starlette.testclient import TestClient
from starlette.applications import Starlette
from starlette.routing import Route
from unittest.mock import patch, Mock

from fastmcp.server.routes.mcp_redirect_routes import (
    register_redirect,
    health_check,
    mcp_redirect_routes
)


class TestRegisterRedirect:
    """Test suite for register redirect endpoint"""
    
    @pytest.fixture
    def app(self):
        """Create test Starlette app with redirect routes"""
        app = Starlette(routes=mcp_redirect_routes)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)
    
    def test_register_get_request(self, client):
        """Test GET request to /register returns proper MCP info"""
        response = client.get("/register")
        
        assert response.status_code == 404
        assert response.headers["X-MCP-Server"] == "dhafnck-mcp-server"
        assert response.headers["X-Proper-Endpoint"] == "/mcp/"
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        
        data = response.json()
        assert data["error"] == "Invalid endpoint"
        assert "MCP clients should connect to /mcp/" in data["message"]
        assert data["protocol"] == "MCP (Model Context Protocol)"
        assert data["transport"] == "streamable-http"
        assert data["initialization_endpoint"] == "/mcp/initialize"
    
    def test_register_post_request(self, client):
        """Test POST request to /register returns proper MCP info"""
        response = client.post("/register", json={"some": "data"})
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Invalid endpoint"
        assert "correct_configuration" in data
        
        # Check correct configuration structure
        config = data["correct_configuration"]
        assert config["type"] == "http"
        assert config["url"] == "http://localhost:8000/mcp/"
        assert "Authorization" in config["headers"]
        assert "Bearer YOUR_JWT_TOKEN_HERE" in config["headers"]["Authorization"]
    
    def test_register_options_request(self, client):
        """Test OPTIONS request to /register for CORS preflight"""
        response = client.options("/register")
        
        assert response.status_code == 404
        assert response.headers["Access-Control-Allow-Origin"] == "*"
    
    def test_register_with_user_agent(self, client):
        """Test request with custom user agent is logged"""
        with patch('fastmcp.server.routes.mcp_redirect_routes.logger') as mock_logger:
            response = client.post(
                "/register",
                headers={"User-Agent": "MCP-Client/1.0"}
            )
            
            assert response.status_code == 404
            
            # Verify logging
            mock_logger.info.assert_called()
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("MCP-Client/1.0" in call for call in log_calls)
            assert any("Client tried to POST to /register" in call for call in log_calls)
    
    def test_register_troubleshooting_info(self, client):
        """Test troubleshooting information in response"""
        response = client.post("/register")
        
        data = response.json()
        assert "troubleshooting" in data
        
        troubleshooting = data["troubleshooting"]
        assert troubleshooting["issue"] == "Client is trying to register instead of following MCP protocol"
        assert "Update your MCP client configuration" in troubleshooting["solution"]
        assert ".mcp.json" in troubleshooting["common_fix"]
        assert "claude_desktop_config.json" in troubleshooting["common_fix"]
    
    def test_api_register_endpoint(self, client):
        """Test /api/register also redirects properly"""
        response = client.post("/api/register")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Invalid endpoint"
        assert data["message"] == "MCP clients should connect to /mcp/ endpoint, not /register"


class TestHealthCheck:
    """Test suite for health check endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client with health route"""
        app = Starlette(routes=[
            Route("/health", endpoint=health_check, methods=["GET"])
        ])
        return TestClient(app)
    
    def test_health_check_success(self, client):
        """Test health check returns healthy status"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["server"] == "dhafnck-mcp-server"
        assert data["mcp_endpoint"] == "/mcp/"
        assert data["auth_required"] is True
    
    def test_health_check_method_not_allowed(self, client):
        """Test health check only accepts GET requests"""
        response = client.post("/health")
        assert response.status_code == 405  # Method not allowed
        
        response = client.put("/health")
        assert response.status_code == 405
        
        response = client.delete("/health")
        assert response.status_code == 405


class TestRouteConfiguration:
    """Test route configuration and integration"""
    
    def test_routes_exported(self):
        """Test that routes are properly exported"""
        assert len(mcp_redirect_routes) == 3
        
        # Check route paths
        paths = [route.path for route in mcp_redirect_routes]
        assert "/register" in paths
        assert "/api/register" in paths
        assert "/health" in paths
        
        # Check allowed methods
        register_route = next(r for r in mcp_redirect_routes if r.path == "/register")
        assert "GET" in register_route.methods
        assert "POST" in register_route.methods
        assert "OPTIONS" in register_route.methods
        
        health_route = next(r for r in mcp_redirect_routes if r.path == "/health")
        assert "GET" in health_route.methods
    
    def test_integration_with_app(self):
        """Test integration with Starlette app"""
        app = Starlette(routes=mcp_redirect_routes)
        client = TestClient(app)
        
        # Test all routes work
        response = client.get("/register")
        assert response.status_code == 404
        
        response = client.post("/api/register")
        assert response.status_code == 404
        
        response = client.get("/health")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_register_redirect_direct_call(self):
        """Test calling register_redirect directly"""
        # Mock request
        request = Mock()
        request.client = ("127.0.0.1", 12345)
        request.headers = {"user-agent": "Test-Client"}
        
        with patch('fastmcp.server.routes.mcp_redirect_routes.logger'):
            response = await register_redirect(request)
        
        assert response.status_code == 404
        assert "dhafnck-mcp-server" in response.headers["X-MCP-Server"]
    
    @pytest.mark.asyncio
    async def test_health_check_direct_call(self):
        """Test calling health_check directly"""
        request = Mock()
        
        response = await health_check(request)
        
        assert response.status_code == 200
        # Parse response body
        import json
        body = json.loads(response.body.decode())
        assert body["status"] == "healthy"