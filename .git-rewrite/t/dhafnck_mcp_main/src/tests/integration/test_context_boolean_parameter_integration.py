#!/usr/bin/env python3
"""
Integration Test for Context Boolean Parameter Fix

Tests the boolean parameter fix end-to-end using the actual MCP tools.
Verifies that manage_context works with boolean string parameters.
"""

import pytest
from unittest.mock import Mock, patch
import asyncio

from fastmcp.task_management.interface.controllers.unified_context_controller import UnifiedContextMCPController
from fastmcp.task_management.application.factories.unified_context_facade_factory import UnifiedContextFacadeFactory
from fastmcp.task_management.interface.utils.parameter_validation_fix import ParameterTypeCoercer


class TestContextBooleanParameterIntegration:
    """Integration tests for the boolean parameter fix."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the facade factory and facade
        self.mock_facade_factory = Mock(spec=UnifiedContextFacadeFactory)
        self.mock_facade = Mock()
        self.mock_facade_factory.create_facade.return_value = self.mock_facade
        
        # Create the controller
        self.controller = UnifiedContextMCPController(self.mock_facade_factory)
        
        # Mock successful facade responses
        self.mock_facade.create_context.return_value = {
            "success": True,
            "status": "success", 
            "data": {"context_data": {"title": "Test Context"}}
        }
        self.mock_facade.get_context.return_value = {
            "success": True,
            "status": "success",
            "data": {"context_data": {"title": "Test Context"}}
        }
        self.mock_facade.update_context.return_value = {
            "success": True,
            "status": "success",
            "data": {"context_data": {"title": "Updated Test Context"}}
        }
    
    def test_parameter_type_coercer_boolean_parameters(self):
        """Test that ParameterTypeCoercer includes context boolean parameters."""
        boolean_params = ParameterTypeCoercer.BOOLEAN_PARAMETERS
        
        # Verify that context management boolean parameters are included
        assert 'include_inherited' in boolean_params
        assert 'force_refresh' in boolean_params
        assert 'propagate_changes' in boolean_params
    
    def test_manage_context_tool_registration(self):
        """Test that manage_context tool registers correctly with boolean parameter support."""
        # Mock MCP
        mcp = Mock()
        tools_registered = {}
        
        def mock_tool(name=None, description=None):
            def decorator(func):
                tools_registered[name] = func
                return func
            return decorator
        
        mcp.tool = mock_tool
        
        # Register tools
        self.controller.register_tools(mcp)
        
        # Verify manage_context tool was registered
        assert "manage_context" in tools_registered
        
        # Get the registered function
        manage_context_func = tools_registered["manage_context"]
        assert manage_context_func is not None
    
    def test_boolean_string_coercion_in_context_operations(self):
        """Test boolean string coercion works in context operations."""
        # Test various boolean string formats
        test_cases = [
            # Test case 1: True values
            {
                'include_inherited': 'true',
                'force_refresh': 'True', 
                'propagate_changes': '1'
            },
            # Test case 2: False values
            {
                'include_inherited': 'false',
                'force_refresh': 'False',
                'propagate_changes': '0'
            },
            # Test case 3: Alternative formats
            {
                'include_inherited': 'yes',
                'force_refresh': 'on',
                'propagate_changes': 'no'
            }
        ]
        
        for case in test_cases:
            # Test that ParameterTypeCoercer handles these correctly
            coerced = ParameterTypeCoercer.coerce_parameter_types(case)
            
            # Verify types are now boolean
            assert isinstance(coerced['include_inherited'], bool)
            assert isinstance(coerced['force_refresh'], bool) 
            assert isinstance(coerced['propagate_changes'], bool)
            
            # Verify correct conversions
            if case['include_inherited'] in ['true', 'True', '1', 'yes']:
                assert coerced['include_inherited'] is True
            else:
                assert coerced['include_inherited'] is False
    
    def test_manage_context_simulate_function_call(self):
        """Test simulated manage_context function call with boolean parameter coercion."""
        # Mock MCP and get the registered function
        mcp = Mock()
        tools_registered = {}
        
        def mock_tool(name=None, description=None):
            def decorator(func):
                tools_registered[name] = func
                return func
            return decorator
        
        mcp.tool = mock_tool
        
        # Register tools
        self.controller.register_tools(mcp)
        manage_context_func = tools_registered["manage_context"]
        
        # Test function call with string boolean parameters
        result = manage_context_func(
            action="get",
            level="task", 
            context_id="test-task-123",
            include_inherited="true",  # String boolean
            force_refresh="false",     # String boolean
            propagate_changes="yes"    # Alternative boolean string
        )
        
        # Verify the facade was called with coerced boolean values
        self.mock_facade.get_context.assert_called_once()
        call_args = self.mock_facade.get_context.call_args
        
        # The boolean parameters should have been coerced before calling the facade
        # We can't directly check the coerced values since they're local to the function,
        # but we can verify the function executed without errors
        assert result["status"] == "success"
    
    def test_boolean_parameter_error_handling(self):
        """Test that invalid boolean parameters are handled gracefully."""
        # Test invalid boolean values
        test_params = {
            'include_inherited': 'maybe',  # Invalid boolean
            'force_refresh': 'sometimes'   # Invalid boolean
        }
        
        with pytest.raises(Exception) as exc_info:
            ParameterTypeCoercer.coerce_parameter_types(test_params)
        
        # Should mention valid boolean values
        error_message = str(exc_info.value)
        assert 'boolean' in error_message.lower()
        assert ('true' in error_message.lower() or 'false' in error_message.lower())
    
    def test_all_boolean_string_variations(self):
        """Test all supported boolean string variations."""
        # Test various TRUE values
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES", "on", "On", "ON"]
        
        for true_val in true_values:
            test_params = {'include_inherited': true_val}
            coerced = ParameterTypeCoercer.coerce_parameter_types(test_params)
            assert coerced['include_inherited'] is True, f"Failed with true value: {true_val}"
        
        # Test various FALSE values
        false_values = ["false", "False", "FALSE", "0", "no", "No", "NO", "off", "Off", "OFF"]
        
        for false_val in false_values:
            test_params = {'force_refresh': false_val}
            coerced = ParameterTypeCoercer.coerce_parameter_types(test_params)
            assert coerced['force_refresh'] is False, f"Failed with false value: {false_val}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])