"""
Tests for MCP Registration Routes

Tests the /register endpoint expected by Claude and other MCP clients
for proper MCP protocol registration and session management.
"""

import pytest
import uuid
import time
from unittest.mock import patch, Mock
from starlette.testclient import TestClient
from starlette.applications import Starlette

from fastmcp.server.routes.mcp_registration_routes import (
    register_client,
    unregister_client,
    list_registrations,
    handle_options,
    mcp_registration_routes,
    active_registrations
)


class TestRegisterClient:
    """Test suite for client registration endpoint"""
    
    @pytest.fixture
    def app(self):
        """Create test Starlette app with registration routes"""
        app = Starlette(routes=mcp_registration_routes)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def clear_registrations(self):
        """Clear active registrations before each test"""
        active_registrations.clear()
        yield
        active_registrations.clear()
    
    def test_register_client_success(self, client):
        """Test successful client registration"""
        response = client.post(
            "/register",
            json={"client_info": {"name": "test-client"}, "capabilities": {"tools": True}},
            headers={"User-Agent": "Test-MCP-Client/1.0"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["success"] is True
        assert "session_id" in data
        assert data["server"]["name"] == "dhafnck-mcp-server"
        assert data["server"]["version"] == "2.1.0"
        assert data["server"]["protocol_version"] == "2025-06-18"
        
        # Check endpoints
        assert data["endpoints"]["mcp"] == "http://localhost:8000/mcp/"
        assert data["endpoints"]["initialize"] == "http://localhost:8000/mcp/initialize"
        assert data["endpoints"]["tools"] == "http://localhost:8000/mcp/tools/list"
        assert data["endpoints"]["health"] == "http://localhost:8000/health"
        
        # Check transport and auth
        assert data["transport"] == "streamable-http"
        assert data["authentication"]["required"] is True
        assert data["authentication"]["type"] == "Bearer"
        
        # Check capabilities
        assert data["capabilities"]["tools"] is True
        assert data["capabilities"]["resources"] is True
        assert data["capabilities"]["prompts"] is True
        
        # Check headers
        assert response.headers["X-MCP-Server"] == "dhafnck-mcp-server"
        assert "X-Session-ID" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        
        # Verify registration was stored
        session_id = data["session_id"]
        assert session_id in active_registrations
        assert active_registrations[session_id]["user_agent"] == "Test-MCP-Client/1.0"
    
    def test_register_client_empty_body(self, client):
        """Test registration with empty body"""
        response = client.post("/register")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data
    
    def test_register_client_non_json_body(self, client):
        """Test registration with non-JSON content type"""
        response = client.post(
            "/register",
            data="not json",
            headers={"Content-Type": "text/plain"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_register_client_stores_info(self, client):
        """Test that client info is properly stored"""
        client_data = {
            "client_info": {"name": "claude-desktop", "version": "1.0"},
            "capabilities": {"streaming": True}
        }
        
        response = client.post("/register", json=client_data)
        session_id = response.json()["session_id"]
        
        # Check stored registration
        reg = active_registrations[session_id]
        assert reg["client_info"] == client_data["client_info"]
        assert reg["capabilities"] == client_data["capabilities"]
        assert reg["client_ip"] == "testclient"  # TestClient default
        assert "registered_at" in reg
        assert "last_activity" in reg
    
    def test_register_client_error_handling(self, client):
        """Test error handling during registration"""
        with patch('fastmcp.server.routes.mcp_registration_routes.uuid.uuid4', side_effect=Exception("UUID error")):
            response = client.post("/register")
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "Registration failed"
            assert "UUID error" in data["message"]
            assert response.headers["X-MCP-Server"] == "dhafnck-mcp-server"
    
    def test_register_alternative_endpoints(self, client):
        """Test registration works on alternative endpoints"""
        # Test /api/register
        response = client.post("/api/register")
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Test /mcp/register
        response = client.post("/mcp/register")
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestUnregisterClient:
    """Test suite for client unregistration endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client with unregister route"""
        app = Starlette(routes=mcp_registration_routes)
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def clear_registrations(self):
        """Clear active registrations before each test"""
        active_registrations.clear()
        yield
        active_registrations.clear()
    
    def test_unregister_client_success(self, client):
        """Test successful client unregistration"""
        # First register a client
        reg_response = client.post("/register")
        session_id = reg_response.json()["session_id"]
        
        # Then unregister
        response = client.post("/unregister", json={"session_id": session_id})
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Client unregistered successfully"
        
        # Verify registration was removed
        assert session_id not in active_registrations
    
    def test_unregister_invalid_session(self, client):
        """Test unregistering with invalid session ID"""
        response = client.post("/unregister", json={"session_id": "invalid-session-id"})
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Invalid session"
        assert data["message"] == "Session ID not found"
    
    def test_unregister_missing_session_id(self, client):
        """Test unregistering without session ID"""
        response = client.post("/unregister", json={})
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Invalid session"
    
    def test_unregister_error_handling(self, client):
        """Test error handling during unregistration"""
        with patch('starlette.requests.Request.json', side_effect=Exception("JSON error")):
            response = client.post("/unregister")
            
            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "Unregistration failed"
            assert "JSON error" in data["message"]


class TestListRegistrations:
    """Test suite for list registrations endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app = Starlette(routes=mcp_registration_routes)
        return TestClient(app)
    
    @pytest.fixture(autouse=True)
    def clear_registrations(self):
        """Clear active registrations before each test"""
        active_registrations.clear()
        yield
        active_registrations.clear()
    
    def test_list_empty_registrations(self, client):
        """Test listing when no registrations exist"""
        response = client.get("/registrations")
        
        assert response.status_code == 200
        data = response.json()
        assert data["active_registrations"] == 0
        assert data["sessions"] == []
        assert data["details"] == []
    
    def test_list_multiple_registrations(self, client):
        """Test listing multiple active registrations"""
        # Register multiple clients
        session_ids = []
        for i in range(3):
            response = client.post("/register", json={"client_info": {"id": i}})
            session_ids.append(response.json()["session_id"])
        
        # List registrations
        response = client.get("/registrations")
        
        assert response.status_code == 200
        data = response.json()
        assert data["active_registrations"] == 3
        assert len(data["sessions"]) == 3
        assert all(sid in data["sessions"] for sid in session_ids)
        
        # Check details
        assert len(data["details"]) == 3
        for detail in data["details"]:
            assert "session_id" in detail
            assert "client_ip" in detail
            assert "user_agent" in detail
            assert "registered_at" in detail
            assert "last_activity" in detail
    
    def test_list_cleans_expired_sessions(self, client):
        """Test that listing cleans up expired sessions"""
        # Create an old registration
        old_session = str(uuid.uuid4())
        active_registrations[old_session] = {
            "session_id": old_session,
            "client_ip": "127.0.0.1",
            "user_agent": "Old-Client",
            "registered_at": time.time() - 7200,  # 2 hours ago
            "last_activity": time.time() - 7200,  # 2 hours ago
            "client_info": {},
            "capabilities": {}
        }
        
        # Create a new registration
        new_response = client.post("/register")
        new_session = new_response.json()["session_id"]
        
        # List should clean up old session
        response = client.get("/registrations")
        
        data = response.json()
        assert data["active_registrations"] == 1
        assert old_session not in data["sessions"]
        assert new_session in data["sessions"]


class TestHandleOptions:
    """Test suite for CORS options handling"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        app = Starlette(routes=mcp_registration_routes)
        return TestClient(app)
    
    def test_options_register(self, client):
        """Test OPTIONS request for /register"""
        response = client.options("/register")
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "Content-Type, Authorization" in response.headers["Access-Control-Allow-Headers"]
        assert "GET, POST, OPTIONS, DELETE" in response.headers["Access-Control-Allow-Methods"]
    
    def test_options_alternative_endpoints(self, client):
        """Test OPTIONS for alternative endpoints"""
        endpoints = ["/api/register", "/mcp/register"]
        
        for endpoint in endpoints:
            response = client.options(endpoint)
            assert response.status_code == 200
            assert response.headers["Access-Control-Allow-Origin"] == "*"


class TestRouteConfiguration:
    """Test route configuration"""
    
    def test_routes_exported(self):
        """Test that all routes are properly exported"""
        assert len(mcp_registration_routes) == 9
        
        # Check main endpoints
        paths = [route.path for route in mcp_registration_routes]
        assert "/register" in paths
        assert "/api/register" in paths
        assert "/mcp/register" in paths
        assert "/unregister" in paths
        assert "/registrations" in paths
        
        # Check methods
        register_routes = [r for r in mcp_registration_routes if r.path == "/register"]
        methods = set()
        for route in register_routes:
            methods.update(route.methods)
        assert "POST" in methods
        assert "OPTIONS" in methods
    
    @pytest.mark.asyncio
    async def test_register_client_direct_call(self):
        """Test calling register_client directly"""
        request = Mock()
        request.client = Mock(host="192.168.1.1", port=12345)
        request.headers = {"user-agent": "Direct-Test", "content-type": "application/json"}
        request.json = Mock(return_value={"client_info": {"test": True}})
        
        with patch('fastmcp.server.routes.mcp_registration_routes.logger'):
            response = await register_client(request)
        
        assert response.status_code == 200
        body = response.body.decode()
        import json
        data = json.loads(body)
        assert data["success"] is True
        assert "session_id" in data