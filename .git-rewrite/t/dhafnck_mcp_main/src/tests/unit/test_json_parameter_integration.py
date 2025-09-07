"""
Unit tests for JSON parameter parsing across MCP controllers.

Tests the functionality of JSON string parsing for dictionary parameters
in various MCP tools without requiring database connections.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch

# Prevent database initialization during import
import os
os.environ['SKIP_DB_INIT'] = 'true'

from fastmcp.task_management.interface.controllers.unified_context_controller import UnifiedContextMCPController
from fastmcp.connection_management.interface.controllers.connection_mcp_controller import ConnectionMCPController
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.connection_management.application.facades.connection_application_facade import ConnectionApplicationFacade


class TestJSONParameterIntegration:
    """Integration tests for JSON parameter parsing in MCP controllers."""
    
    @pytest.fixture
    def mock_unified_context_facade(self):
        """Create a mock unified context facade."""
        facade = Mock()
        facade.create_context = Mock(return_value={"success": True, "context_id": "test-123"})
        facade.delegate_context = Mock(return_value={"success": True, "delegated": True})
        facade.list_contexts = Mock(return_value={"success": True, "contexts": []})
        return facade
    
    @pytest.fixture
    def mock_facade_factory(self, mock_unified_context_facade):
        """Create a mock facade factory."""
        factory = Mock(spec=UnifiedContextFacadeFactory)
        factory.create_facade = Mock(return_value=mock_unified_context_facade)
        return factory
    
    @pytest.fixture
    def unified_context_controller(self, mock_facade_factory):
        """Create unified context controller with mocks."""
        controller = UnifiedContextMCPController(mock_facade_factory)
        # Mock the description getter
        controller._get_context_management_descriptions = Mock(return_value={
            "description": "Test description",
            "parameters": {}
        })
        
        # Create a mock MCP server and register tools to create the manage_context method
        mock_mcp = Mock()
        tools = {}
        
        def mock_tool(name=None, description=None):
            def decorator(func):
                tools[name] = func
                # Make the function available as a method on the controller
                setattr(controller, name.replace("-", "_"), func)
                return func
            return decorator
        
        mock_mcp.tool = mock_tool
        controller.register_tools(mock_mcp)
        
        return controller
    
    @pytest.fixture
    def mock_connection_facade(self):
        """Create a mock connection facade."""
        facade = Mock(spec=ConnectionApplicationFacade)
        facade.register_for_status_updates = Mock(return_value=Mock(
            success=True,
            session_id="test-session",
            registration_time="2025-01-22T12:00:00Z"
        ))
        return facade
    
    @pytest.fixture
    def connection_controller(self, mock_connection_facade):
        """Create connection controller with mocks."""
        return ConnectionMCPController(mock_connection_facade)
    
    def test_unified_context_data_parameter_as_json_string(self, unified_context_controller, mock_unified_context_facade):
        """Test that 'data' parameter accepts JSON strings in manage_context."""
        # Prepare JSON string
        data_dict = {"title": "Test Task", "description": "Test Description", "metadata": {"key": "value"}}
        data_json = json.dumps(data_dict)
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = "test-user-123"
            
            # Register tools to get the manage_context function
            mcp = Mock()
            tools = {}
            
            def mock_tool(name=None, description=None):
                def decorator(func):
                    tools[name] = func
                    return func
                return decorator
            
            mcp.tool = mock_tool
            unified_context_controller.register_tools(mcp)
            manage_context = tools["manage_context"]
            
            # Mock the manage_context method to test parameter parsing
            result = manage_context(
                action="create",
                level="task",
                context_id="task-123",
                data=data_json
            )
            
            # Verify facade was called with parsed dictionary
            mock_unified_context_facade.create_context.assert_called_once_with(
                level="task",
                context_id="task-123",
                data=data_dict
            )
            
            assert result["success"] is True
    
    def test_unified_context_delegate_data_as_json_string(self, unified_context_controller, mock_unified_context_facade):
        """Test that 'delegate_data' parameter accepts JSON strings."""
        # Prepare JSON string for delegation
        delegate_dict = {
            "pattern_name": "auth_flow",
            "implementation": {"type": "JWT", "expiry": 3600},
            "tags": ["security", "authentication"]
        }
        delegate_json = json.dumps(delegate_dict)
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = "test-user-123"
            
            # Register tools to get the manage_context function
            mcp = Mock()
            tools = {}
            
            def mock_tool(name=None, description=None):
                def decorator(func):
                    tools[name] = func
                    return func
                return decorator
            
            mcp.tool = mock_tool
            unified_context_controller.register_tools(mcp)
            manage_context = tools["manage_context"]
            
            # Call with JSON string
            result = manage_context(
                action="delegate",
                level="task",
                context_id="task-123",
                delegate_to="project",
                delegate_data=delegate_json,
                delegation_reason="Reusable pattern"
            )
        
        # Verify facade was called with parsed dictionary
        mock_unified_context_facade.delegate_context.assert_called_once_with(
            level="task",
            context_id="task-123",
            delegate_to="project",
            data=delegate_dict,  # delegate_data becomes data
            delegation_reason="Reusable pattern"
        )
        
        assert result["success"] is True
    
    def test_unified_context_filters_as_json_string(self, unified_context_controller, mock_unified_context_facade):
        """Test that 'filters' parameter accepts JSON strings."""
        # Prepare JSON string for filters
        filters_dict = {"status": "active", "priority": "high", "tags": ["important"]}
        filters_json = json.dumps(filters_dict)
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = "test-user-123"
            
            # Register tools to get the manage_context function
            mcp = Mock()
            tools = {}
            
            def mock_tool(name=None, description=None):
                def decorator(func):
                    tools[name] = func
                    return func
                return decorator
            
            mcp.tool = mock_tool
            unified_context_controller.register_tools(mcp)
            manage_context = tools["manage_context"]
            
            # Call with JSON string
            result = manage_context(
                action="list",
                level="task",
                filters=filters_json
            )
        
        # Verify facade was called with parsed dictionary
        mock_unified_context_facade.list_contexts.assert_called_once_with(
            level="task",
            filters=filters_dict
        )
        
        assert result["success"] is True
    
    def test_connection_client_info_as_json_string(self, connection_controller, mock_connection_facade):
        """Test that 'client_info' parameter accepts JSON strings in manage_connection."""
        # Prepare JSON string
        client_info_dict = {
            "client_type": "web",
            "version": "1.0.0",
            "features": ["real-time", "notifications"],
            "metadata": {"user_agent": "Test Client"}
        }
        client_info_json = json.dumps(client_info_dict)
        
        # Call with JSON string
        result = connection_controller.manage_connection(
            action="register_updates",
            session_id="test-session",
            client_info=client_info_json
        )
        
        # Verify facade was called with parsed dictionary and user_id parameter
        mock_connection_facade.register_for_status_updates.assert_called_once_with(
            "test-session",
            client_info_dict,
            None  # user_id parameter defaults to None
        )
        
        assert result["success"] is True
    
    def test_invalid_json_string_returns_helpful_error(self, unified_context_controller):
        """Test that invalid JSON strings return helpful error messages."""
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = "test-user-123"
            
            # Register tools to get the manage_context function
            mcp = Mock()
            tools = {}
            
            def mock_tool(name=None, description=None):
                def decorator(func):
                    tools[name] = func
                    return func
                return decorator
            
            mcp.tool = mock_tool
            unified_context_controller.register_tools(mcp)
            manage_context = tools["manage_context"]
            
            # Call with invalid JSON
            result = manage_context(
                action="create",
                level="task",
                context_id="task-123",
                data='{invalid json string}'
            )
        
        # Verify error response
        assert result["success"] is False
        # The error response structure includes metadata with the error details
        if "error_code" in result:
            assert result["error_code"] == "INVALID_PARAMETER_FORMAT"
        elif "metadata" in result and "error_code" in result["metadata"]:
            assert result["metadata"]["error_code"] == "INVALID_PARAMETER_FORMAT"
        
        # Check for error message
        error_msg = result.get("error", {})
        if isinstance(error_msg, dict) and "message" in error_msg:
            assert "Invalid JSON string" in error_msg["message"]
        else:
            assert "Invalid JSON string" in str(error_msg)
        
        # Check for helpful information
        assert "suggestions" in result.get("metadata", result)
        assert "examples" in result.get("metadata", result)
    
    def test_mixed_parameter_formats(self, unified_context_controller, mock_unified_context_facade):
        """Test mixing dictionary objects and JSON strings in same call."""
        # Mix formats - data as dict, delegate_data as JSON string
        data_dict = {"title": "Test"}
        delegate_json = '{"pattern": "test_pattern"}'
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = "test-user-123"
            
            # Register tools to get the manage_context function
            mcp = Mock()
            tools = {}
            
            def mock_tool(name=None, description=None):
                def decorator(func):
                    tools[name] = func
                    return func
                return decorator
            
            mcp.tool = mock_tool
            unified_context_controller.register_tools(mcp)
            manage_context = tools["manage_context"]
            
            # First create with dict
            manage_context(
                action="create",
                level="task",
                context_id="task-123",
                data=data_dict
            )
            
            # Then delegate with JSON string
            result = manage_context(
                action="delegate",
                level="task",
                context_id="task-123",
                delegate_to="project",
                delegate_data=delegate_json
            )
        
        # Verify both calls succeeded
        assert mock_unified_context_facade.create_context.called
        assert mock_unified_context_facade.delegate_context.called
        
        # Verify delegate was called with parsed JSON
        delegate_call_args = mock_unified_context_facade.delegate_context.call_args
        assert delegate_call_args[1]["data"] == {"pattern": "test_pattern"}
    
    def test_none_values_handled_correctly(self, unified_context_controller, mock_unified_context_facade):
        """Test that None values for dict parameters are handled correctly."""
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = "test-user-123"
            
            # Register tools to get the manage_context function
            mcp = Mock()
            tools = {}
            
            def mock_tool(name=None, description=None):
                def decorator(func):
                    tools[name] = func
                    return func
                return decorator
            
            mcp.tool = mock_tool
            unified_context_controller.register_tools(mcp)
            manage_context = tools["manage_context"]
            
            # Call with None values
            result = manage_context(
                action="create",
                level="task",
                context_id="task-123",
                data=None,
                delegate_data=None,
                filters=None
            )
        
        # Should succeed with empty dict for data
        mock_unified_context_facade.create_context.assert_called_once_with(
            level="task",
            context_id="task-123",
            data={}  # None becomes empty dict for create
        )
    
    def test_complex_nested_json_parsing(self, unified_context_controller, mock_unified_context_facade):
        """Test parsing of complex nested JSON structures."""
        complex_data = {
            "title": "Complex Task",
            "metadata": {
                "nested": {
                    "deeply": {
                        "nested": {
                            "value": 42,
                            "array": [1, 2, 3],
                            "bool": True
                        }
                    }
                },
                "tags": ["tag1", "tag2", "tag3"],
                "settings": {
                    "enabled": True,
                    "config": {"key": "value"}
                }
            }
        }
        complex_json = json.dumps(complex_data)
        
        # Mock authentication helper to return test user
        with patch('fastmcp.task_management.interface.controllers.unified_context_controller.get_authenticated_user_id') as mock_auth:
            mock_auth.return_value = "test-user-123"
            
            # Register tools to get the manage_context function
            mcp = Mock()
            tools = {}
            
            def mock_tool(name=None, description=None):
                def decorator(func):
                    tools[name] = func
                    return func
                return decorator
            
            mcp.tool = mock_tool
            unified_context_controller.register_tools(mcp)
            manage_context = tools["manage_context"]
            
            # Call with complex JSON
            result = manage_context(
                action="create",
                level="task",
                context_id="task-123",
                data=complex_json
            )
        
        # Verify complex structure was parsed correctly
        mock_unified_context_facade.create_context.assert_called_once_with(
            level="task",
            context_id="task-123",
            data=complex_data
        )