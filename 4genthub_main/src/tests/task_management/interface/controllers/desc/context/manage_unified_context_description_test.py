"""
Test suite for manage_unified_context_description.py - Unified Context Management Description

Tests the documentation and parameter descriptions for the unified context management tool.
Ensures the description content is complete, accurate, and properly formatted.
"""

import pytest
import re
import json

from fastmcp.task_management.interface.mcp_controllers.unified_context_controller.manage_unified_context_description import (
    MANAGE_UNIFIED_CONTEXT_DESCRIPTION,
    MANAGE_UNIFIED_CONTEXT_PARAMETERS
)

class TestManageUnifiedContextDescription:
    """Test MANAGE_UNIFIED_CONTEXT_DESCRIPTION constant"""
    
    def test_description_exists_and_not_empty(self):
        """Test that description exists and is not empty"""
        assert MANAGE_UNIFIED_CONTEXT_DESCRIPTION is not None
        assert isinstance(MANAGE_UNIFIED_CONTEXT_DESCRIPTION, str)
        assert len(MANAGE_UNIFIED_CONTEXT_DESCRIPTION.strip()) > 0
    
    def test_description_has_title_section(self):
        """Test that description has proper title section"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Should have title with emojis and unified context management
        assert "🔗 UNIFIED CONTEXT MANAGEMENT SYSTEM" in description
        assert "4-Tier Context Operations" in description
    
    def test_description_has_what_when_critical_sections(self):
        """Test that description has WHAT IT DOES, WHEN TO USE, CRITICAL FOR sections"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "⭐ WHAT IT DOES:" in description
        assert "📋 WHEN TO USE:" in description
        assert "🎯 CRITICAL FOR:" in description
    
    def test_description_has_hierarchy_structure(self):
        """Test that description explains the hierarchy structure"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Should explain the 4-tier hierarchy
        assert "🏗️ HIERARCHY STRUCTURE:" in description
        assert "GLOBAL" in description
        assert "PROJECT" in description
        assert "BRANCH" in description
        assert "TASK" in description
        
        # Should show inheritance flow
        assert "↓ inherits to" in description
    
    def test_description_has_actions_table(self):
        """Test that description contains actions table with all operations"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Should have table headers
        assert "Action" in description
        assert "Required Parameters" in description
        assert "Optional Parameters" in description
        assert "Description" in description
        
        # Should list all actions
        required_actions = [
            "create", "get", "update", "delete", 
            "resolve", "delegate", "add_insight", "add_progress", "list"
        ]
        
        for action in required_actions:
            assert action in description
    
    def test_description_has_level_parameter_section(self):
        """Test that description explains level parameter values"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "🎯 LEVEL PARAMETER:" in description
        assert "'global':" in description
        assert "'project':" in description
        assert "'branch':" in description
        assert "'task':" in description
    
    def test_description_has_usage_guidelines(self):
        """Test that description includes usage guidelines"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "💡 USAGE GUIDELINES:" in description
        assert "Always specify 'level' parameter" in description
        assert "Use 'context_id' appropriate for the level" in description
    
    def test_description_has_key_features(self):
        """Test that description lists key features"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "🔄 KEY FEATURES:" in description
        
        key_features = [
            "Unified API", "Full Hierarchy Support", "Automatic Inheritance",
            "Smart Caching", "Change Propagation", "Delegation Queue", "Backward Compatible"
        ]
        
        for feature in key_features:
            assert feature in description
    
    def test_description_has_advanced_parameters(self):
        """Test that description explains advanced parameters"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "📊 ADVANCED PARAMETERS:" in description
        
        advanced_params = [
            "force_refresh", "include_inherited", "propagate_changes",
            "delegate_to", "filters", "data"
        ]
        
        for param in advanced_params:
            assert param in description
    
    def test_description_has_example_usage(self):
        """Test that description includes example usage"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "🚀 EXAMPLE USAGE:" in description
        
        # Should have various example formats
        assert "Dictionary format" in description
        assert "JSON string format" in description
        assert "Legacy parameter format" in description
    
    def test_description_has_backward_compatibility_section(self):
        """Test that description explains backward compatibility"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "⚠️ BACKWARD COMPATIBILITY:" in description
        assert "task_id → context_id" in description
        assert "data_title, data_description" in description
    
    def test_description_has_error_handling_section(self):
        """Test that description explains error handling"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        assert "🛡️ ERROR HANDLING:" in description
        assert "Validates level and context_id" in description
        assert "Provides clear error messages" in description
    
    def test_description_action_parameter_consistency(self):
        """Test that all actions mentioned in table are documented consistently"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Extract action names from the table (simple regex)
        # Look for lines with "| action_name |"
        table_actions = re.findall(r'\|\s*(\w+)\s*\|', description)
        
        # Remove table headers and empty matches
        table_actions = [action for action in table_actions if action not in ['Action', 'Required', 'Optional', 'Description']]
        
        expected_actions = ['create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list']
        
        for expected_action in expected_actions:
            assert expected_action in table_actions, f"Action '{expected_action}' not found in table"
    
    def test_description_example_code_validity(self):
        """Test that example code snippets are properly formatted"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION

        # Check that examples contain proper parameter syntax
        assert 'action="create"' in description
        assert 'level="task"' in description
        assert 'context_id="task456"' in description
        
        # Check JSON string examples are valid JSON-like
        json_examples = re.findall(r"data='({.*?})'", description)
        for example in json_examples:
            # Should be valid JSON format (basic check)
            assert example.startswith('{')
            assert example.endswith('}')
            assert ':' in example

class TestManageUnifiedContextParameters:
    """Test MANAGE_UNIFIED_CONTEXT_PARAMETERS constant"""
    
    def test_parameters_exists_and_is_dict(self):
        """Test that parameters exists and is a dictionary"""
        assert MANAGE_UNIFIED_CONTEXT_PARAMETERS is not None
        assert isinstance(MANAGE_UNIFIED_CONTEXT_PARAMETERS, dict)
        assert len(MANAGE_UNIFIED_CONTEXT_PARAMETERS) > 0
    
    def test_parameters_has_core_parameters(self):
        """Test that parameters includes all core parameters"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        core_parameters = [
            "action", "level", "context_id", "data", "user_id",
            "project_id", "git_branch_id"
        ]
        
        for param in core_parameters:
            assert param in params, f"Core parameter '{param}' missing"
            assert isinstance(params[param], str), f"Parameter '{param}' description should be string"
            assert len(params[param].strip()) > 0, f"Parameter '{param}' description should not be empty"
    
    def test_parameters_has_advanced_parameters(self):
        """Test that parameters includes advanced parameters"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        advanced_parameters = [
            "force_refresh", "include_inherited", "propagate_changes",
            "delegate_to", "delegate_data", "delegation_reason"
        ]
        
        for param in advanced_parameters:
            assert param in params, f"Advanced parameter '{param}' missing"
            assert isinstance(params[param], str)
            assert len(params[param].strip()) > 0
    
    def test_parameters_has_operation_specific_parameters(self):
        """Test that parameters includes operation-specific parameters"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        operation_parameters = [
            "content", "category", "importance", "agent", "filters"
        ]
        
        for param in operation_parameters:
            assert param in params, f"Operation parameter '{param}' missing"
            assert isinstance(params[param], str)
            assert len(params[param].strip()) > 0
    
    def test_parameters_has_legacy_parameters(self):
        """Test that parameters includes legacy parameters for backward compatibility"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        legacy_parameters = [
            "task_id", "data_title", "data_description", 
            "data_status", "data_priority", "data_tags", "data_metadata"
        ]
        
        for param in legacy_parameters:
            assert param in params, f"Legacy parameter '{param}' missing"
            assert "Legacy:" in params[param], f"Legacy parameter '{param}' should be marked as legacy"
    
    def test_parameters_action_description_completeness(self):
        """Test that action parameter description lists all valid actions"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        action_desc = params["action"]
        
        expected_actions = [
            "create", "get", "update", "delete", "resolve", 
            "delegate", "add_insight", "add_progress", "list"
        ]
        
        for action in expected_actions:
            assert action in action_desc, f"Action '{action}' not mentioned in action parameter description"
    
    def test_parameters_level_description_completeness(self):
        """Test that level parameter description lists all valid levels"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        level_desc = params["level"]
        
        expected_levels = ["global", "project", "branch", "task"]
        
        for level in expected_levels:
            assert level in level_desc, f"Level '{level}' not mentioned in level parameter description"
    
    def test_parameters_data_description_format_support(self):
        """Test that data parameter description mentions format support"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        data_desc = params["data"]
        
        # Should mention both dictionary and JSON string support
        assert "dictionary object" in data_desc.lower()
        assert "json string" in data_desc.lower()
        assert "automatically parsed" in data_desc.lower()
    
    def test_parameters_boolean_parameters_have_defaults(self):
        """Test that boolean parameters mention their default values"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        boolean_params = {
            "force_refresh": "false",
            "include_inherited": "false", 
            "propagate_changes": "true"
        }
        
        for param, default_value in boolean_params.items():
            param_desc = params[param]
            assert "boolean" in param_desc.lower() or "bool" in param_desc.lower()
            assert f"default: {default_value}" in param_desc.lower() or f"default {default_value}" in param_desc.lower()
    
    def test_parameters_category_values_listed(self):
        """Test that category parameter lists valid values"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        category_desc = params["category"]
        
        expected_categories = ["technical", "business", "performance", "risk", "discovery"]
        
        for category in expected_categories:
            assert category in category_desc, f"Category '{category}' not mentioned in category parameter description"
    
    def test_parameters_importance_values_listed(self):
        """Test that importance parameter lists valid values"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        importance_desc = params["importance"]
        
        expected_importance = ["low", "medium", "high", "critical"]
        
        for importance in expected_importance:
            assert importance in importance_desc, f"Importance '{importance}' not mentioned in importance parameter description"


class TestDocumentationQuality:
    """Test overall documentation quality"""
    
    def test_description_has_consistent_emoji_usage(self):
        """Test that description uses emojis consistently for sections"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Count different emoji patterns
        emoji_sections = re.findall(r'^[⭐📋🎯🏗️💡🔄📊🚀⚠️🛡️]\s', description, re.MULTILINE)
        
        # Should have multiple emoji-marked sections
        assert len(emoji_sections) > 5, "Should have multiple emoji-marked sections"
    
    def test_description_line_length_reasonable(self):
        """Test that description lines are not excessively long"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        lines = description.split('\n')
        
        excessively_long_lines = [line for line in lines if len(line) > 120]
        
        # Allow some long lines (like table headers) but not too many
        assert len(excessively_long_lines) < 10, f"Too many excessively long lines: {len(excessively_long_lines)}"
    
    def test_description_has_proper_table_formatting(self):
        """Test that the actions table is properly formatted"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Should have table separators
        assert "|-" in description or "|---" in description, "Table should have separator rows"
        
        # Should have pipe characters for table columns
        table_lines = [line for line in description.split('\n') if line.strip().startswith('|') and line.strip().endswith('|')]
        
        # Should have multiple table rows
        assert len(table_lines) > 5, "Should have multiple table rows"
    
    def test_parameter_descriptions_are_informative(self):
        """Test that parameter descriptions provide sufficient information"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        for param_name, param_desc in params.items():
            # Each description should be at least 20 characters
            assert len(param_desc) >= 20, f"Parameter '{param_name}' description too short: '{param_desc}'"
            
            # Should not end with period (consistent style)
            # Allow exceptions for legacy parameters which may have different format
            if not param_desc.startswith("Legacy:"):
                assert not param_desc.endswith('.'), f"Parameter '{param_name}' description should not end with period"
    
    def test_description_mentions_json_parsing(self):
        """Test that description mentions automatic JSON parsing for data parameter"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Should mention JSON parsing capability
        assert "automatically parsed" in description.lower() or "auto-parsed" in description.lower()
        assert "json string" in description.lower()
    
    def test_description_covers_inheritance_concept(self):
        """Test that description adequately covers inheritance concept"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        inheritance_keywords = ["inherit", "inherits", "inheritance", "cascade", "flow"]
        
        # Should mention inheritance concept multiple times
        inheritance_mentions = sum(1 for keyword in inheritance_keywords 
                                 if keyword in description.lower())
        
        assert inheritance_mentions >= 3, "Should mention inheritance concept multiple times"

class TestParameterConsistency:
    """Test consistency between description and parameters"""
    
    def test_action_parameters_match_description_table(self):
        """Test that action parameters match what's described in the table"""
        # Extract actions from parameter description
        action_param = MANAGE_UNIFIED_CONTEXT_PARAMETERS["action"]
        
        # Should contain "Valid:" followed by actions
        valid_section = action_param.split("Valid:")[1] if "Valid:" in action_param else action_param
        
        # Extract action names (simple approach)
        mentioned_actions = []
        for word in valid_section.split():
            # Remove punctuation, quotes, and check if it's a likely action name
            clean_word = word.strip(',').strip('.').strip("'").strip()
            if clean_word in ['create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list']:
                mentioned_actions.append(clean_word)
        
        # Should mention all major actions
        expected_actions = ['create', 'get', 'update', 'delete']
        for action in expected_actions:
            assert action in mentioned_actions, f"Action '{action}' should be mentioned in action parameter"
    
    def test_level_parameters_match_hierarchy_description(self):
        """Test that level parameters match the hierarchy description"""
        level_param = MANAGE_UNIFIED_CONTEXT_PARAMETERS["level"]
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Both should mention the same levels
        levels = ["global", "project", "branch", "task"]
        
        for level in levels:
            assert level in level_param, f"Level '{level}' should be in level parameter description"
            assert level in description.upper() or level.upper() in description, f"Level '{level}' should be in main description"
    
    def test_legacy_parameters_are_documented_consistently(self):
        """Test that legacy parameters are consistently marked and documented"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        legacy_params = {k: v for k, v in params.items() if "Legacy:" in v}
        
        # Should have multiple legacy parameters
        assert len(legacy_params) >= 5, "Should have several legacy parameters"
        
        # All legacy parameters should suggest modern alternatives
        for param_name, param_desc in legacy_params.items():
            if param_name == "task_id":
                assert "context_id" in param_desc, f"Legacy parameter '{param_name}' should mention modern alternative"
            elif param_name.startswith("data_"):
                assert "data." in param_desc, f"Legacy data parameter '{param_name}' should mention modern data object usage"

class TestContentAccuracy:
    """Test accuracy of technical content"""
    
    def test_hierarchy_flow_is_correct(self):
        """Test that the hierarchy flow description is technically accurate"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Should show correct inheritance direction (top-down)
        hierarchy_section = description[description.find("HIERARCHY STRUCTURE"):description.find("| Action")]
        
        # Should mention Global at the top
        global_pos = hierarchy_section.find("GLOBAL")
        project_pos = hierarchy_section.find("PROJECT")
        branch_pos = hierarchy_section.find("BRANCH")
        task_pos = hierarchy_section.find("TASK")
        
        # Positions should be in correct order
        assert global_pos < project_pos, "GLOBAL should appear before PROJECT"
        assert project_pos < branch_pos, "PROJECT should appear before BRANCH"
        assert branch_pos < task_pos, "BRANCH should appear before TASK"
    
    def test_user_scoped_global_context_mentioned(self):
        """Test that description mentions user-scoped nature of global contexts"""
        description = MANAGE_UNIFIED_CONTEXT_DESCRIPTION
        
        # Should clarify that global contexts are per-user
        assert "User-scoped" in description or "per-user" in description
        assert "each user has their own" in description.lower()
    
    def test_boolean_parameter_defaults_are_accurate(self):
        """Test that boolean parameter defaults match expected system behavior"""
        params = MANAGE_UNIFIED_CONTEXT_PARAMETERS
        
        # These defaults should match the actual system behavior
        expected_defaults = {
            "force_refresh": "false",  # Cache should be used by default
            "include_inherited": "false",  # Don't include inheritance by default for performance
            "propagate_changes": "true"  # Changes should propagate by default
        }
        
        for param, expected_default in expected_defaults.items():
            param_desc = params[param].lower()
            assert f"default: {expected_default}" in param_desc or f"default {expected_default}" in param_desc, \
                f"Parameter '{param}' should have correct default value '{expected_default}'"

if __name__ == "__main__":
    pytest.main([__file__])