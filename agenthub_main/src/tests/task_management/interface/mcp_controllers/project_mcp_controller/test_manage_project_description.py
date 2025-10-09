"""
Test suite for manage_project_description module.

Tests the comprehensive documentation for the manage_project MCP tool,
ensuring all constants, functions, and parameter definitions work correctly.
"""

import pytest
from fastmcp.task_management.interface.mcp_controllers.project_mcp_controller.manage_project_description import (
    MANAGE_PROJECT_DESCRIPTION,
    MANAGE_PROJECT_PARAMETERS_DESCRIPTION,
    MANAGE_PROJECT_PARAMS,
    get_manage_project_parameters,
    get_manage_project_description,
)


class TestManageProjectDescription:
    """Test class for manage project description constants and functions."""

    def test_manage_project_description_exists(self):
        """Test that MANAGE_PROJECT_DESCRIPTION constant exists and is not empty."""
        assert MANAGE_PROJECT_DESCRIPTION is not None
        assert isinstance(MANAGE_PROJECT_DESCRIPTION, str)
        assert len(MANAGE_PROJECT_DESCRIPTION) > 0
        
    def test_manage_project_description_contains_required_sections(self):
        """Test that description contains all required documentation sections."""
        required_sections = [
            "PROJECT MANAGEMENT SYSTEM",
            "WHAT IT DOES:",
            "WHEN TO USE:",
            "CRITICAL FOR:",
            "AI USAGE GUIDELINES:",
            "USAGE GUIDELINES:",
            "AI DECISION TREES:",
            "ERROR HANDLING:",
        ]
        
        for section in required_sections:
            assert section in MANAGE_PROJECT_DESCRIPTION, f"Missing required section: {section}"
    
    def test_manage_project_description_contains_action_table(self):
        """Test that description contains the action table with all actions."""
        expected_actions = [
            "create",
            "get",
            "list",
            "update",
            "delete",
            "project_health_check",
            "cleanup_obsolete",
            "validate_integrity",
            "rebalance_agents",
        ]
        
        for action in expected_actions:
            assert action in MANAGE_PROJECT_DESCRIPTION, f"Missing action in table: {action}"
            
    def test_manage_project_description_contains_workflows(self):
        """Test that description contains the workflow examples."""
        workflows = [
            "PROJECT CREATION WORKFLOW:",
            "PROJECT HEALTH MONITORING:",
        ]
        
        for workflow in workflows:
            assert workflow in MANAGE_PROJECT_DESCRIPTION, f"Missing workflow: {workflow}"


class TestManageProjectParametersDescription:
    """Test class for manage project parameters description dictionary."""
    
    def test_parameters_description_exists(self):
        """Test that MANAGE_PROJECT_PARAMETERS_DESCRIPTION exists and is a dict."""
        assert MANAGE_PROJECT_PARAMETERS_DESCRIPTION is not None
        assert isinstance(MANAGE_PROJECT_PARAMETERS_DESCRIPTION, dict)
    
    def test_parameters_description_contains_all_keys(self):
        """Test that all expected parameter descriptions are present."""
        expected_keys = ["action", "project_id", "name", "description", "user_id", "force"]
        
        for key in expected_keys:
            assert key in MANAGE_PROJECT_PARAMETERS_DESCRIPTION, f"Missing parameter description: {key}"
            assert isinstance(MANAGE_PROJECT_PARAMETERS_DESCRIPTION[key], str)
            assert len(MANAGE_PROJECT_PARAMETERS_DESCRIPTION[key]) > 0
    
    def test_action_parameter_description(self):
        """Test the action parameter description content."""
        action_desc = MANAGE_PROJECT_PARAMETERS_DESCRIPTION["action"]
        assert "Project management action to perform" in action_desc
        assert "Valid values:" in action_desc
        
        # Check all valid actions are listed
        valid_actions = [
            "create", "get", "list", "update", "delete",
            "project_health_check", "cleanup_obsolete",
            "validate_integrity", "rebalance_agents"
        ]
        for action in valid_actions:
            assert action in action_desc, f"Action '{action}' not listed in description"
    
    def test_optional_parameter_descriptions(self):
        """Test that optional parameters are marked as [OPTIONAL]."""
        optional_params = ["project_id", "name", "description", "user_id", "force"]
        
        for param in optional_params:
            desc = MANAGE_PROJECT_PARAMETERS_DESCRIPTION[param]
            assert "[OPTIONAL]" in desc, f"Parameter '{param}' should be marked as [OPTIONAL]"


class TestManageProjectParams:
    """Test class for manage project parameter schema definition."""
    
    def test_params_structure(self):
        """Test that MANAGE_PROJECT_PARAMS has correct structure."""
        assert MANAGE_PROJECT_PARAMS is not None
        assert isinstance(MANAGE_PROJECT_PARAMS, dict)
        assert "type" in MANAGE_PROJECT_PARAMS
        assert MANAGE_PROJECT_PARAMS["type"] == "object"
        assert "properties" in MANAGE_PROJECT_PARAMS
        assert "required" in MANAGE_PROJECT_PARAMS
        assert "additionalProperties" in MANAGE_PROJECT_PARAMS
        
    def test_params_required_fields(self):
        """Test that only 'action' is required at schema level."""
        required = MANAGE_PROJECT_PARAMS["required"]
        assert isinstance(required, list)
        assert len(required) == 1
        assert "action" in required
        
    def test_params_additional_properties_false(self):
        """Test that additionalProperties is set to False."""
        assert MANAGE_PROJECT_PARAMS["additionalProperties"] is False
        
    def test_params_properties_structure(self):
        """Test that all expected properties are defined."""
        properties = MANAGE_PROJECT_PARAMS["properties"]
        expected_props = ["action", "project_id", "name", "description", "user_id", "force"]
        
        for prop in expected_props:
            assert prop in properties, f"Missing property: {prop}"
            assert "type" in properties[prop]
            assert properties[prop]["type"] == "string"
            assert "description" in properties[prop]
            
    def test_params_descriptions_match(self):
        """Test that property descriptions match MANAGE_PROJECT_PARAMETERS_DESCRIPTION."""
        properties = MANAGE_PROJECT_PARAMS["properties"]
        
        for key, prop in properties.items():
            expected_desc = MANAGE_PROJECT_PARAMETERS_DESCRIPTION[key]
            assert prop["description"] == expected_desc, f"Description mismatch for {key}"


class TestGetManageProjectParameters:
    """Test class for get_manage_project_parameters function."""
    
    def test_function_returns_properties(self):
        """Test that function returns the properties dictionary."""
        result = get_manage_project_parameters()
        assert result is not None
        assert isinstance(result, dict)
        assert result == MANAGE_PROJECT_PARAMS["properties"]
        
    def test_function_returns_correct_structure(self):
        """Test that returned properties have correct structure."""
        result = get_manage_project_parameters()
        
        # Check all expected properties
        expected_props = ["action", "project_id", "name", "description", "user_id", "force"]
        for prop in expected_props:
            assert prop in result
            assert "type" in result[prop]
            assert "description" in result[prop]
            
    def test_function_returns_mutable_copy(self):
        """Test that function returns a reference (not a copy) to the properties."""
        result1 = get_manage_project_parameters()
        result2 = get_manage_project_parameters()
        
        # Should return the same object reference
        assert result1 is result2


class TestGetManageProjectDescription:
    """Test class for get_manage_project_description function."""
    
    def test_function_returns_description(self):
        """Test that function returns the description string."""
        result = get_manage_project_description()
        assert result is not None
        assert isinstance(result, str)
        assert result == MANAGE_PROJECT_DESCRIPTION
        
    def test_function_returns_non_empty_string(self):
        """Test that returned description is not empty."""
        result = get_manage_project_description()
        assert len(result) > 0
        
    def test_function_consistency(self):
        """Test that function returns consistent results."""
        result1 = get_manage_project_description()
        result2 = get_manage_project_description()
        assert result1 == result2


class TestIntegration:
    """Integration tests for the module's components working together."""
    
    def test_all_actions_in_params_are_documented(self):
        """Test that all actions in the description are valid per the schema."""
        # Extract actions from description
        desc_actions = [
            "create", "get", "list", "update", "delete",
            "project_health_check", "cleanup_obsolete",
            "validate_integrity", "rebalance_agents"
        ]
        
        # Get action parameter description
        action_desc = MANAGE_PROJECT_PARAMETERS_DESCRIPTION["action"]
        
        # Verify all actions are mentioned in the parameter description
        for action in desc_actions:
            assert action in action_desc, f"Action '{action}' not in parameter description"
            
    def test_parameter_consistency_across_components(self):
        """Test that parameters are consistent across all module components."""
        # Get all parameter names from different sources
        desc_params = set(MANAGE_PROJECT_PARAMETERS_DESCRIPTION.keys())
        schema_params = set(MANAGE_PROJECT_PARAMS["properties"].keys())
        
        # They should be identical
        assert desc_params == schema_params, "Parameter mismatch between description and schema"
        
    def test_required_parameters_logic(self):
        """Test that required parameters make sense for the actions."""
        # Only 'action' is required at schema level
        required = MANAGE_PROJECT_PARAMS["required"]
        assert required == ["action"]
        
        # Verify the description mentions business logic validation
        assert "business logic validates per action" in str(MANAGE_PROJECT_PARAMS)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_parameter_handling(self):
        """Test that the schema allows empty strings for optional parameters."""
        properties = get_manage_project_parameters()
        
        # All parameters are strings, which can be empty
        for param, config in properties.items():
            assert config["type"] == "string"
            # No minLength constraint means empty strings are allowed
            assert "minLength" not in config
            
    def test_no_enum_constraints(self):
        """Test that action parameter doesn't have enum constraint at schema level."""
        properties = get_manage_project_parameters()
        action_property = properties["action"]
        
        # Should not have enum constraint - validation happens in business logic
        assert "enum" not in action_property
        
    def test_description_formatting(self):
        """Test that descriptions use consistent formatting."""
        # Check for consistent use of [OPTIONAL] tags
        for param, desc in MANAGE_PROJECT_PARAMETERS_DESCRIPTION.items():
            if param != "action":  # action is always required
                assert "[OPTIONAL]" in desc, f"Parameter '{param}' missing [OPTIONAL] tag"


class TestDocumentationQuality:
    """Test the quality and completeness of documentation."""
    
    def test_description_has_examples(self):
        """Test that description includes example workflows."""
        desc = MANAGE_PROJECT_DESCRIPTION
        assert "IF new_feature_request:" in desc
        assert "IF starting_work_on_project:" in desc
        
    def test_description_has_emoji_markers(self):
        """Test that description uses emoji markers for sections."""
        desc = MANAGE_PROJECT_DESCRIPTION
        emoji_markers = ["📁", "⭐", "📋", "🎯", "🤖", "💡", "🔍", "🛑"]
        
        for emoji in emoji_markers:
            assert emoji in desc, f"Missing emoji marker: {emoji}"
            
    def test_table_formatting(self):
        """Test that the action table is properly formatted."""
        desc = MANAGE_PROJECT_DESCRIPTION
        
        # Check for table headers
        assert "| Action" in desc
        assert "| Required Parameters" in desc
        assert "| Optional Parameters" in desc
        assert "| Description" in desc
        
        # Check for table separator line
        assert "|--" in desc
        
    def test_code_block_formatting(self):
        """Test that code blocks are properly formatted."""
        desc = MANAGE_PROJECT_DESCRIPTION
        
        # Check for code block markers
        assert "```" in desc
        assert desc.count("```") % 2 == 0  # Should be paired