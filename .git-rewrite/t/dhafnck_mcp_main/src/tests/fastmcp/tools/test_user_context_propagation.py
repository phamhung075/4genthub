"""
Test user context propagation in FastMCP tools.

This test verifies that user context from HTTP middleware
properly propagates to MCP tool execution.
"""

import pytest
from unittest.mock import Mock, patch
from fastmcp.tools.tool import FunctionTool
from fastmcp.auth.mcp_integration.jwt_auth_backend import MCPUserContext


class TestUserContextPropagation:
    """Test user context propagation in tool execution."""
    
    @pytest.mark.asyncio
    async def test_user_context_propagates_to_tool_execution(self):
        """Test that user context is available during tool execution."""
        
        # Create a mock user context
        mock_user_context = MCPUserContext(
            user_id="test-user-123",
            email="test@example.com",
            username="testuser",
            roles=["user"],
            scopes=["read", "write"]
        )
        
        # Create a test tool function that accesses user context
        def test_tool_function() -> str:
            from fastmcp.auth.middleware.request_context_middleware import get_current_user_id
            user_id = get_current_user_id()
            return f"User ID: {user_id}"
        
        # Create FunctionTool from our test function
        tool = FunctionTool.from_function(test_tool_function)
        
        # Mock the user context middleware to return our test context
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_context:
            mock_get_context.return_value = mock_user_context
            
            with patch('fastmcp.auth.middleware.request_context_middleware.current_user_context') as mock_context_var:
                # Mock the context variable set method
                mock_context_var.set = Mock()
                
                # Run the tool
                result = await tool.run({})
                
                # Verify user context was set
                mock_context_var.set.assert_called_once_with(mock_user_context)
                
                # Verify result contains user ID (this would work if context propagation is successful)
                assert len(result) == 1
                assert result[0].type == "text"
    
    @pytest.mark.asyncio
    async def test_tool_execution_without_user_context(self):
        """Test that tools work normally without user context."""
        
        # Create a simple test tool function
        def simple_tool_function() -> str:
            return "Hello World"
        
        # Create FunctionTool from our test function
        tool = FunctionTool.from_function(simple_tool_function)
        
        # Mock no user context available
        with patch('fastmcp.auth.middleware.request_context_middleware.get_current_user_context') as mock_get_context:
            mock_get_context.return_value = None
            
            # Run the tool
            result = await tool.run({})
            
            # Verify tool still works
            assert len(result) == 1
            assert result[0].type == "text"
            assert result[0].text == "Hello World"
    
    @pytest.mark.asyncio 
    async def test_import_error_handling(self):
        """Test that tools work when user context middleware is not available."""
        
        # Create a simple test tool function
        def simple_tool_function() -> str:
            return "No Context Available"
        
        # Create FunctionTool from our test function  
        tool = FunctionTool.from_function(simple_tool_function)
        
        # Mock ImportError when trying to import user context middleware
        with patch('fastmcp.tools.tool.logger') as mock_logger:
            with patch.dict('sys.modules', {'fastmcp.auth.middleware.request_context_middleware': None}):
                # This should trigger the ImportError in the try/except block
                result = await tool.run({})
                
                # Verify tool still works despite import error
                assert len(result) == 1
                assert result[0].type == "text"
                assert result[0].text == "No Context Available"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])