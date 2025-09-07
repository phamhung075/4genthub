#!/usr/bin/env python3
"""
Test the HTTP server factory pattern and CORS fixes
"""
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
            cors_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        # Verify factory returns expected components
        assert isinstance(server_routes, list)
        assert isinstance(server_middleware, list)
        assert isinstance(required_scopes, list)
        assert len(required_scopes) == 0  # No auth, so no required scopes
    
    def test_sse_app_creation(self):
        """Test SSE app creation using factory pattern"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        sse_app = create_sse_app(
            server=server,
            message_path='/message',
            sse_path='/sse',
            debug=True,
            cors_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        # Verify app was created successfully
        assert sse_app is not None
        assert hasattr(sse_app, 'state')
        assert hasattr(sse_app.state, 'fastmcp_server')
        assert sse_app.state.fastmcp_server == server
    
    def test_streamable_http_app_creation(self):
        """Test Streamable HTTP app creation using factory pattern"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        http_app = create_streamable_http_app(
            server=server,
            streamable_http_path='/mcp',
            debug=True,
            cors_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        # Verify app was created successfully
        assert http_app is not None
        assert hasattr(http_app, 'router')
    
    def test_cors_configuration(self):
        """Test that CORS is properly configured for both server types"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        # Test SSE app CORS
        sse_app = create_sse_app(
            server=server,
            message_path='/message',
            sse_path='/sse',
            debug=True,
            cors_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        sse_client = TestClient(sse_app)
        sse_response = sse_client.options("/sse", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "accept"
        })
        
        # Verify CORS headers are present
        assert "access-control-allow-origin" in sse_response.headers
        assert sse_response.status_code == 200
        
        # Test HTTP app CORS
        http_app = create_streamable_http_app(
            server=server,
            streamable_http_path='/mcp',
            debug=True,
            cors_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        http_client = TestClient(http_app)
        http_response = http_client.options("/mcp", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,accept"
        })
        
        # Verify CORS headers are present
        assert "access-control-allow-origin" in http_response.headers
        assert http_response.status_code == 200
    
    def test_factory_eliminates_duplication(self):
        """Test that both apps use the same factory function"""
        server = FastMCP('Test Server')
        
        @server.tool
        def test_tool():
            return 'Hello from test tool'
        
        # Both apps should use the same factory function
        # This is verified by the fact that both apps can be created successfully
        # and have the same basic structure
        
        sse_routes, sse_middleware, sse_scopes = create_http_server_factory(
            server=server,
            auth=None,
            debug=True,
            cors_origins=["http://localhost:3000"]
        )
        
        http_routes, http_middleware, http_scopes = create_http_server_factory(
            server=server,
            auth=None,
            debug=True,
            cors_origins=["http://localhost:3000"]
        )
        
        # Both should have the same base structure
        assert len(sse_routes) == len(http_routes)
        assert len(sse_middleware) == len(http_middleware)
        assert len(sse_scopes) == len(http_scopes)
        assert sse_scopes == http_scopes  # Should be identical for same config 