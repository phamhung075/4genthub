#!/usr/bin/env python3
"""
Test Unified Context Controller Description Loading

This test verifies that the unified context controller correctly:
1. Loads descriptions from the description loader system
2. Handles both flat and nested parameter formats
3. Falls back to defaults when description loading fails
4. Properly registers tools with MCP
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from fastmcp.task_management.interface.controllers.unified_context_controller import UnifiedContextMCPController
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory


class TestUnifiedContextDescriptionLoading:
    
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

    """Test unified context controller description loading functionality."""
    
    @pytest.fixture
    def mock_facade_factory(self):
        """Create mock facade factory."""
        return Mock(spec=UnifiedContextFacadeFactory)
    
    @pytest.fixture
    def controller(self, mock_facade_factory):
        """Create controller with mock dependencies."""
        return UnifiedContextMCPController(mock_facade_factory)
    
    def test_get_param_description_flat_format(self, controller):
        """Test _get_param_description with flat string format."""
        desc = {
            "parameters": {
                "action": "Context management action",
                "level": "Context hierarchy level"
            }
        }
        
        # Test flat string format
        result = controller._get_param_description(desc, "action", "default")
        assert result == "Context management action"
        
        # Test default when parameter not found
        result = controller._get_param_description(desc, "missing", "default value")
        assert result == "default value"
    
    def test_get_param_description_nested_format(self, controller):
        """Test _get_param_description with nested dict format."""
        desc = {
            "parameters": {
                "action": {
                    "description": "Context management action",
                    "type": "string",
                    "required": True
                },
                "level": {
                    "description": "Context hierarchy level",
                    "default": "task"
                }
            }
        }
        
        # Test nested dict format with description key
        result = controller._get_param_description(desc, "action", "default")
        assert result == "Context management action"
        
        result = controller._get_param_description(desc, "level", "default")
        assert result == "Context hierarchy level"
    
    def test_get_param_description_mixed_formats(self, controller):
        """Test _get_param_description with mixed formats."""
        desc = {
            "parameters": {
                "action": "Simple string description",
                "level": {
                    "description": "Nested description",
                    "type": "string"
                },
                "context_id": {
                    "no_description": "This won't be found",
                    "type": "string"
                }
            }
        }
        
        # Flat string
        assert controller._get_param_description(desc, "action", "default") == "Simple string description"
        
        # Nested with description
        assert controller._get_param_description(desc, "level", "default") == "Nested description"
        
        # Nested without description key
        assert controller._get_param_description(desc, "context_id", "default") == str({
            "no_description": "This won't be found",
            "type": "string"
        })
    
    @patch('fastmcp.task_management.interface.controllers.unified_context_controller.description_loader')
    def test_get_context_management_descriptions_success(self, mock_loader, controller):
        """Test successful description loading from loader."""
        # Mock successful loading
        mock_loader.get_all_descriptions.return_value = {
            "context": {
                "manage_context": {
                    "description": "Loaded description",
                    "parameters": {
                        "action": "Loaded action param"
                    }
                }
            }
        }
        
        result = controller._get_context_management_descriptions()
        
        assert result["description"] == "Loaded description"
        assert result["parameters"]["action"] == "Loaded action param"
        mock_loader.get_all_descriptions.assert_called_once()
    
    @patch('fastmcp.task_management.interface.controllers.unified_context_controller.description_loader')
    def test_get_context_management_descriptions_fallback(self, mock_loader, controller):
        """Test fallback to default descriptions when loading fails."""
        # Mock loading failure
        mock_loader.get_all_descriptions.side_effect = Exception("Loading failed")
        
        result = controller._get_context_management_descriptions()
        
        # Should fall back to imported defaults
        assert "UNIFIED CONTEXT MANAGEMENT SYSTEM" in result["description"]
        assert "action" in result["parameters"]
        assert isinstance(result["parameters"]["action"], str)
    
    @patch('fastmcp.task_management.interface.controllers.unified_context_controller.description_loader')
    def test_get_context_management_descriptions_missing_key(self, mock_loader, controller):
        """Test fallback when expected keys are missing."""
        # Mock incomplete structure
        mock_loader.get_all_descriptions.return_value = {
            "context": {
                # Missing manage_context key
                "other_tool": {}
            }
        }
        
        result = controller._get_context_management_descriptions()
        
        # Should fall back to imported defaults
        assert "UNIFIED CONTEXT MANAGEMENT SYSTEM" in result["description"]
        assert "action" in result["parameters"]
    
    def test_register_tools_with_descriptions(self, controller, mock_facade_factory):
        """Test that register_tools uses loaded descriptions."""
        # Mock MCP server
        mock_mcp = MagicMock()
        mock_tool_decorator = MagicMock()
        mock_mcp.tool.return_value = mock_tool_decorator
        
        # Register tools
        controller.register_tools(mock_mcp)
        
        # Verify tool was registered with description
        mock_mcp.tool.assert_called_once()
        call_args = mock_mcp.tool.call_args
        
        # Check that name and description were passed
        assert call_args[1]["name"] == "manage_context"
        # The actual loaded description should contain "UNIFIED CONTEXT MANAGEMENT SYSTEM"
        assert "UNIFIED CONTEXT MANAGEMENT SYSTEM" in call_args[1]["description"]
    
    @patch('fastmcp.task_management.interface.controllers.unified_context_controller.description_loader')
    def test_tool_function_parameter_descriptions(self, mock_loader, controller, mock_facade_factory):
        """Test that tool function parameters use loaded descriptions."""
        # Mock successful loading with parameter descriptions
        mock_loader.get_all_descriptions.return_value = {
            "context": {
                "manage_context": {
                    "description": "Test description",
                    "parameters": {
                        "action": "Action parameter description",
                        "level": "Level parameter description",
                        "context_id": "Context ID description"
                    }
                }
            }
        }
        
        # Mock MCP server
        mock_mcp = MagicMock()
        
        # Capture the tool function
        tool_function = None
        def capture_tool_function(name, description):
            def decorator(func):
                nonlocal tool_function
                tool_function = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool_function
        
        # Register tools
        controller.register_tools(mock_mcp)
        
        # Verify the function was captured
        assert tool_function is not None
        
        # Check function annotations include Field with descriptions
        import inspect
        sig = inspect.signature(tool_function)
        
        # The parameters should have Annotated types with Field descriptions
        assert "action" in sig.parameters
        assert "level" in sig.parameters
        assert "context_id" in sig.parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])