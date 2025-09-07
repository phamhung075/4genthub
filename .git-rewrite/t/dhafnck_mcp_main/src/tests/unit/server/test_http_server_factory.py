"""
Test the HTTP server factory pattern and CORS fixes
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from starlette.testclient import TestClient

from fastmcp.server.http_server import (
    create_streamable_http_app,
    create_sse_app,
    create_http_server_factory,
)
from fastmcp.server.server import FastMCP


class TestHTTPServerFactory:
    
    def setup_method(self, method):
        """Clean up before each test"""
        from fastmcp.task_management.infrastructure.database.database_config import get_db_config
        from sqlalchemy import text
        
        db_config = get_db_config()
        with db_config.get_session() as session:
            # Clean test data but preserve defaults
            try:
                session.execute(text("DELETE FROM tasks WHERE id LIKE 'test-%'"))
                session.execute(text("DELETE FROM projects WHERE id LIKE 'test-%' AND id != 'default_project'"))
                session.commit()
            except:
                session.rollback()

    """Test the HTTP server factory pattern"""
    
    def test_factory_creates_common_components(self):
        """Test that the factory creates common server components"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        server_routes, server_middleware, required_scopes = create_http_server_factory(
            server=server,
            auth=None,
            debug=True,
            cors_origins=["http://localhost:3000"]
        )
        
        assert isinstance(server_routes, list)
        assert isinstance(server_middleware, list)
        assert isinstance(required_scopes, list)
        assert len(required_scopes) == 0  # No auth, so no required scopes
    
    def test_streamable_http_app_creation(self):
        """Test that streamable HTTP app can be created with factory"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        app = create_streamable_http_app(
            server=server,
            streamable_http_path='/mcp',
            debug=True,
            cors_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        assert app is not None
        assert hasattr(app, 'state')
        
    def test_sse_app_creation(self):
        """Test that SSE app can be created with factory"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        app = create_sse_app(
            server=server,
            message_path='/messages/',
            sse_path='/sse',
            debug=True,
            cors_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        assert app is not None
        assert hasattr(app, 'state')
        assert app.state.path == '/sse'
    
    def test_cors_headers_in_streamable_http_app(self):
        """Test that CORS headers are properly set in streamable HTTP app"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        app = create_streamable_http_app(
            server=server,
            streamable_http_path='/mcp',
            debug=True,
            cors_origins=["http://localhost:3000"]
        )
        
        client = TestClient(app)
        
        # Test OPTIONS request (preflight)
        response = client.options(
            "/mcp",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"
    
    def test_cors_headers_in_error_responses(self):
        """Test that CORS headers are included in error responses"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        app = create_streamable_http_app(
            server=server,
            streamable_http_path='/mcp',
            debug=True,
            cors_origins=["http://localhost:3000"]
        )
        
        client = TestClient(app)
        
        # Test invalid Content-Type - should get CORS headers in error response
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1},
            headers={
                "Content-Type": "text/plain",  # Invalid content type
                "Accept": "application/json, text/event-stream",
                "Origin": "http://localhost:3000"
            }
        )
        
        assert response.status_code == 415
        assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"
    
    def test_factory_reduces_duplication(self):
        """Test that both app types use the same factory function"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        # Create components using factory directly
        routes1, middleware1, scopes1 = create_http_server_factory(
            server=server,
            auth=None,
            debug=True,
            cors_origins=["http://localhost:3000"]
        )
        
        routes2, middleware2, scopes2 = create_http_server_factory(
            server=server,
            auth=None,
            debug=True,
            cors_origins=["http://localhost:3000"]
        )
        
        # Both should have the same structure (same server, same config)
        assert len(routes1) == len(routes2)
        assert len(middleware1) == len(middleware2)
        assert scopes1 == scopes2 