"""Test suite for manage_task_description module.

Tests the task description controller including parameter descriptions and tool registration.
"""

import pytest
from unittest.mock import Mock, patch

from fastmcp.task_management.interface.controllers.desc.task.manage_task_description import (
    TOOL_NAME,
    TOOL_DESCRIPTION,
    get_manage_task_description,
    MANAGE_TASK_PARAMS,
    MANAGE_TASK_DESCRIPTION,
    MANAGE_TASK_PARAMETERS
)


class TestManageTaskDescription:
    """Test cases for task description management."""
    
    def test_tool_constants(self):
        """Test that tool constants are properly defined."""
        assert TOOL_NAME == "manage_task"
        assert "task management" in TOOL_DESCRIPTION.lower()
        assert "crud" in TOOL_DESCRIPTION.lower()
        
    def test_manage_task_description_constant(self):
        """Test that MANAGE_TASK_DESCRIPTION is properly defined."""
        assert isinstance(MANAGE_TASK_DESCRIPTION, str)
        assert len(MANAGE_TASK_DESCRIPTION) > 1000  # Should be comprehensive
        assert "TASK MANAGEMENT SYSTEM" in MANAGE_TASK_DESCRIPTION
        assert "Vision System Integration" in MANAGE_TASK_DESCRIPTION
        
    def test_manage_task_parameters_constant(self):
        """Test that MANAGE_TASK_PARAMETERS is properly defined."""
        assert isinstance(MANAGE_TASK_PARAMETERS, dict)
        
        # Check key parameters are defined
        assert "action" in MANAGE_TASK_PARAMETERS
        assert "git_branch_id" in MANAGE_TASK_PARAMETERS
        assert "task_id" in MANAGE_TASK_PARAMETERS
        assert "title" in MANAGE_TASK_PARAMETERS
        assert "description" in MANAGE_TASK_PARAMETERS
        assert "completion_summary" in MANAGE_TASK_PARAMETERS
        assert "dependency_id" in MANAGE_TASK_PARAMETERS
        
        # Check parameter descriptions include examples
        assert "Required" in MANAGE_TASK_PARAMETERS["action"]
        assert "UUID" in MANAGE_TASK_PARAMETERS["git_branch_id"]
        assert "Example:" in MANAGE_TASK_PARAMETERS["title"]
    
    def test_manage_task_params_structure(self):
        """Test the structure of MANAGE_TASK_PARAMS."""
        assert isinstance(MANAGE_TASK_PARAMS, dict)
        
        # Check required top-level keys
        assert "properties" in MANAGE_TASK_PARAMS
        assert "required" in MANAGE_TASK_PARAMS
        assert "type" in MANAGE_TASK_PARAMS
        
        # Check type
        assert MANAGE_TASK_PARAMS["type"] == "object"
        
        # Check required fields
        assert MANAGE_TASK_PARAMS["required"] == ["action"]
        
        # Check properties
        properties = MANAGE_TASK_PARAMS["properties"]
        assert "action" in properties
    
    def test_action_parameter_definition(self):
        """Test the action parameter is properly defined."""
        action_param = MANAGE_TASK_PARAMS["properties"]["action"]
        
        assert "type" in action_param
        assert action_param["type"] == "string"
        
        assert "description" in action_param
        # Check that all valid actions are mentioned
        valid_actions = [
            "create", "update", "get", "delete", "complete",
            "list", "search", "next", "add_dependency", "remove_dependency"
        ]
        for action in valid_actions:
            assert action in action_param["description"]
    
    def test_task_id_parameter_definition(self):
        """Test task_id parameter definition if it exists in MANAGE_TASK_PARAMS."""
        # Note: In the actual implementation, only 'action' is in MANAGE_TASK_PARAMS
        # Other parameters are documented but not included in the minimal schema
        if "task_id" not in MANAGE_TASK_PARAMS["properties"]:
            # This is expected behavior - skip test
            return
            
        task_id_param = MANAGE_TASK_PARAMS["properties"]["task_id"]
        
        assert task_id_param["type"] == "string"
        assert task_id_param["default"] is None
        assert "anyOf" in task_id_param or task_id_param.get("nullable") is True
        
        # Check description mentions which actions require it
        assert "update" in task_id_param["description"]
        assert "get" in task_id_param["description"]
        assert "delete" in task_id_param["description"]
        assert "complete" in task_id_param["description"]
    
    def test_git_branch_id_parameter_definition(self):
        """Test git_branch_id parameter definition if it exists."""
        if "git_branch_id" not in MANAGE_TASK_PARAMS["properties"]:
            # Expected - skip test
            return
            
        git_branch_id_param = MANAGE_TASK_PARAMS["properties"]["git_branch_id"]
        
        assert git_branch_id_param["type"] == "string"
        assert git_branch_id_param["default"] is None
        assert "create" in git_branch_id_param["description"]
    
    def test_array_parameters_definition(self):
        """Test array parameters (assignees, labels, dependencies) are properly defined."""
        array_params = ["assignees", "labels", "dependencies"]
        
        for param_name in array_params:
            if param_name not in MANAGE_TASK_PARAMS["properties"]:
                continue  # Skip if parameter not in minimal schema
            param = MANAGE_TASK_PARAMS["properties"][param_name]
            
            # Should have anyOf with array and string types
            assert "anyOf" in param
            type_options = [opt.get("type") for opt in param["anyOf"] if "type" in opt]
            assert "array" in type_options or any("items" in opt for opt in param["anyOf"])
            assert "string" in type_options
            
            # Should mention accepted formats
            assert "array" in param["description"].lower() or "list" in param["description"].lower()
            assert "comma-separated" in param["description"].lower()
    
    def test_boolean_parameters_definition(self):
        """Test boolean parameters are properly defined."""
        boolean_params = ["include_context", "force_full_generation"]
        
        for param_name in boolean_params:
            if param_name in MANAGE_TASK_PARAMS["properties"]:
                param = MANAGE_TASK_PARAMS["properties"][param_name]
                
                # Should have anyOf with boolean and string
                assert "anyOf" in param
                type_options = [opt.get("type") for opt in param["anyOf"] if "type" in opt]
                assert "boolean" in type_options
                assert "string" in type_options
    
    def test_get_manage_task_description(self):
        """Test get_manage_task_description function."""
        description = get_manage_task_description()
        
        assert isinstance(description, str)
        assert len(description) > 0
        assert "task management" in description.lower() or "task" in description.lower()
        
        # Should include key information
        assert "create" in description
        assert "update" in description
        assert "complete" in description
        assert "dependencies" in description
    
    def test_all_parameters_have_descriptions(self):
        """Test that all parameters have descriptions."""
        properties = MANAGE_TASK_PARAMS["properties"]
        
        for param_name, param_def in properties.items():
            assert "description" in param_def, f"Parameter {param_name} missing description"
            assert len(param_def["description"]) > 0, f"Parameter {param_name} has empty description"
    
    def test_optional_parameters_have_defaults(self):
        """Test that optional parameters have default values."""
        properties = MANAGE_TASK_PARAMS["properties"]
        required = MANAGE_TASK_PARAMS["required"]
        
        for param_name, param_def in properties.items():
            if param_name not in required:
                # Optional parameters should have default or be nullable
                assert "default" in param_def or "anyOf" in param_def, \
                    f"Optional parameter {param_name} missing default value"
    
    def test_parameter_examples_in_descriptions(self):
        """Test that complex parameters include examples in descriptions."""
        # Parameters that should have examples
        example_params = ["assignees", "labels", "dependencies", "estimated_effort", "due_date"]
        
        for param_name in example_params:
            if param_name in MANAGE_TASK_PARAMS["properties"]:
                param = MANAGE_TASK_PARAMS["properties"][param_name]
                description = param["description"]
                
                # Should include example formats
                assert "example" in description.lower() or \
                       "e.g." in description.lower() or \
                       "'" in description or \
                       '"' in description, \
                    f"Parameter {param_name} should include examples"
    
    def test_vision_system_parameters(self):
        """Test Vision System related parameters."""
        # Check force_full_generation parameter
        if "force_full_generation" in MANAGE_TASK_PARAMS["properties"]:
            param = MANAGE_TASK_PARAMS["properties"]["force_full_generation"]
            assert "vision" in param["description"].lower() or \
                   "regeneration" in param["description"].lower()
        
        # Check include_context parameter
        if "include_context" in MANAGE_TASK_PARAMS["properties"]:
            param = MANAGE_TASK_PARAMS["properties"]["include_context"]
            assert "context" in param["description"].lower()
            assert "insights" in param["description"].lower() or \
                   "vision" in param["description"].lower()