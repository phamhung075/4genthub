"""
Tests for MCP registration routes.
"""

import pytest
import json
import time
from unittest.mock import Mock, patch
from starlette.requests import Request
from starlette.datastructures import Headers

from fastmcp.server.routes.mcp_registration_routes import (
    register_client,
    unregister_client,
    list_registrations,
    handle_options,
    active_registrations,
)


@pytest.fixture
def mock_request():
    """Create a mock request object."""
    request = Mock(spec=Request)
    request.client = Mock(host="127.0.0.1", port=12345)
    request.headers = Headers({"user-agent": "Claude-MCP-Client/1.0"})
    return request


class TestRegisterClient:
    """Test the register_client endpoint."""

    @pytest.mark.asyncio
    async def test_register_client_success(self, mock_request):
        """Test successful client registration."""
        # Mock request JSON method
        mock_request.json = Mock(return_value={
            "client_info": {"name": "Claude Desktop"},
            "capabilities": {"tools": True}
        })
        
        # Clear any existing registrations
        active_registrations.clear()
        
        response = await register_client(mock_request)
        
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        
        assert body["success"] is True
        assert "session_id" in body
        assert body["server"]["name"] == "dhafnck-mcp-server"
        assert body["endpoints"]["mcp"] == "http://localhost:8000/mcp/"
        assert body["authentication"]["type"] == "Bearer"
        assert body["capabilities"]["tools"] is True
        
        # Check that registration was stored
        assert len(active_registrations) == 1
        session_id = body["session_id"]
        assert session_id in active_registrations
        assert active_registrations[session_id]["client_ip"] == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_register_client_empty_body(self, mock_request):
        """Test client registration with empty body."""
        # Mock empty JSON body
        mock_request.json = Mock(side_effect=Exception("No JSON"))
        
        active_registrations.clear()
        
        response = await register_client(mock_request)
        
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert "session_id" in body

    @pytest.mark.asyncio
    async def test_register_client_no_content_type(self, mock_request):
        """Test client registration without Content-Type header."""
        mock_request.headers = Headers({"user-agent": "Test-Client"})
        
        active_registrations.clear()
        
        response = await register_client(mock_request)
        
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_register_client_error(self, mock_request):
        """Test registration error handling."""
        # Simulate an error
        mock_request.json = Mock(side_effect=Exception("Test error"))
        mock_request.headers = Headers({
            "user-agent": "Test-Client",
            "content-type": "application/json"
        })
        
        with patch('fastmcp.server.routes.mcp_registration_routes.uuid.uuid4', 
                  side_effect=Exception("UUID generation failed")):
            response = await register_client(mock_request)
        
        assert response.status_code == 500
        body = json.loads(response.body.decode())
        assert "error" in body
        assert body["error"] == "Registration failed"


class TestUnregisterClient:
    """Test the unregister_client endpoint."""

    @pytest.mark.asyncio
    async def test_unregister_client_success(self, mock_request):
        """Test successful client unregistration."""
        # Add a test registration
        session_id = "test-session-123"
        active_registrations[session_id] = {
            "session_id": session_id,
            "client_ip": "127.0.0.1"
        }
        
        mock_request.json = Mock(return_value={"session_id": session_id})
        
        response = await unregister_client(mock_request)
        
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["success"] is True
        assert session_id not in active_registrations

    @pytest.mark.asyncio
    async def test_unregister_client_not_found(self, mock_request):
        """Test unregistering non-existent session."""
        mock_request.json = Mock(return_value={"session_id": "non-existent"})
        
        response = await unregister_client(mock_request)
        
        assert response.status_code == 404
        body = json.loads(response.body.decode())
        assert body["error"] == "Invalid session"

    @pytest.mark.asyncio
    async def test_unregister_client_no_session_id(self, mock_request):
        """Test unregistering without session ID."""
        mock_request.json = Mock(return_value={})
        
        response = await unregister_client(mock_request)
        
        assert response.status_code == 404
        body = json.loads(response.body.decode())
        assert body["error"] == "Invalid session"

    @pytest.mark.asyncio
    async def test_unregister_client_error(self, mock_request):
        """Test unregistration error handling."""
        mock_request.json = Mock(side_effect=Exception("Parse error"))
        
        response = await unregister_client(mock_request)
        
        assert response.status_code == 500
        body = json.loads(response.body.decode())
        assert body["error"] == "Unregistration failed"


class TestListRegistrations:
    """Test the list_registrations endpoint."""

    @pytest.mark.asyncio
    async def test_list_registrations_empty(self, mock_request):
        """Test listing with no registrations."""
        active_registrations.clear()
        
        response = await list_registrations(mock_request)
        
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["active_registrations"] == 0
        assert body["sessions"] == []
        assert body["details"] == []

    @pytest.mark.asyncio
    async def test_list_registrations_with_active_sessions(self, mock_request):
        """Test listing with active sessions."""
        current_time = time.time()
        
        active_registrations.clear()
        active_registrations["session-1"] = {
            "session_id": "session-1",
            "client_ip": "192.168.1.100",
            "user_agent": "Client-1",
            "registered_at": current_time,
            "last_activity": current_time
        }
        active_registrations["session-2"] = {
            "session_id": "session-2",
            "client_ip": "192.168.1.101",
            "user_agent": "Client-2",
            "registered_at": current_time,
            "last_activity": current_time
        }
        
        response = await list_registrations(mock_request)
        
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["active_registrations"] == 2
        assert "session-1" in body["sessions"]
        assert "session-2" in body["sessions"]
        assert len(body["details"]) == 2

    @pytest.mark.asyncio
    async def test_list_registrations_cleanup_expired(self, mock_request):
        """Test that expired sessions are cleaned up."""
        current_time = time.time()
        
        active_registrations.clear()
        # Add active session
        active_registrations["active"] = {
            "session_id": "active",
            "client_ip": "192.168.1.100",
            "user_agent": "Active-Client",
            "registered_at": current_time,
            "last_activity": current_time
        }
        # Add expired session (2 hours old)
        active_registrations["expired"] = {
            "session_id": "expired",
            "client_ip": "192.168.1.101",
            "user_agent": "Expired-Client",
            "registered_at": current_time - 7200,
            "last_activity": current_time - 7200
        }
        
        response = await list_registrations(mock_request)
        
        assert response.status_code == 200
        body = json.loads(response.body.decode())
        assert body["active_registrations"] == 1
        assert "active" in body["sessions"]
        assert "expired" not in body["sessions"]
        assert "expired" not in active_registrations


class TestHandleOptions:
    """Test the CORS preflight handler."""

    @pytest.mark.asyncio
    async def test_handle_options_cors_headers(self, mock_request):
        """Test OPTIONS response includes proper CORS headers."""
        response = await handle_options(mock_request)
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]
        assert "Authorization" in response.headers["Access-Control-Allow-Headers"]
        assert "GET" in response.headers["Access-Control-Allow-Methods"]
        assert "POST" in response.headers["Access-Control-Allow-Methods"]
        assert "OPTIONS" in response.headers["Access-Control-Allow-Methods"]


class TestRegistrationRoutes:
    """Test the route definitions."""

    def test_route_definitions(self):
        """Test that all expected routes are defined."""
        from fastmcp.server.routes.mcp_registration_routes import mcp_registration_routes
        
        paths = [route.path for route in mcp_registration_routes]
        
        # Check main endpoints
        assert "/register" in paths
        assert "/api/register" in paths
        assert "/mcp/register" in paths
        assert "/unregister" in paths
        assert "/registrations" in paths
        
        # Check that each endpoint has both POST and OPTIONS methods
        register_routes = [r for r in mcp_registration_routes if r.path == "/register"]
        assert any("POST" in r.methods for r in register_routes)
        assert any("OPTIONS" in r.methods for r in register_routes)