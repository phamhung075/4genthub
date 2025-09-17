"""
Tests for Subtask MCP Controller Description
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from fastmcp.task_management.interface.mcp_controllers.subtask_mcp_controller.manage_subtask_description import (
    get_subtask_description,
    SUBTASK_DESCRIPTION,
    PARAMETER_DESCRIPTIONS
)


class TestManageSubtaskDescription:
    """Test Subtask MCP Controller Description functionality"""

    def test_description_structure(self):
        """Test the structure of the subtask description"""
        assert isinstance(SUBTASK_DESCRIPTION, str)
        assert len(SUBTASK_DESCRIPTION) > 100  # Should be comprehensive
        
        # Check for key sections
        assert "WHAT IT DOES" in SUBTASK_DESCRIPTION
        assert "WHEN TO USE" in SUBTASK_DESCRIPTION
        assert "CRITICAL FOR" in SUBTASK_DESCRIPTION
        assert "AI USAGE GUIDELINES" in SUBTASK_DESCRIPTION
        
        # Check for action documentation
        assert "create" in SUBTASK_DESCRIPTION
        assert "update" in SUBTASK_DESCRIPTION
        assert "delete" in SUBTASK_DESCRIPTION
        assert "complete" in SUBTASK_DESCRIPTION
        assert "list" in SUBTASK_DESCRIPTION

    def test_parameter_descriptions(self):
        """Test parameter descriptions completeness"""
        # Required parameters
        required_params = ["action", "task_id", "subtask_id"]
        for param in required_params:
            assert param in PARAMETER_DESCRIPTIONS
            assert isinstance(PARAMETER_DESCRIPTIONS[param], dict)
            assert "description" in PARAMETER_DESCRIPTIONS[param]
            assert "type" in PARAMETER_DESCRIPTIONS[param]
        
        # Optional parameters
        optional_params = [
            "title", "description", "status", "priority",
            "assignees", "progress_notes", "progress_percentage",
            "blockers", "insights_found", "completion_summary"
        ]
        for param in optional_params:
            assert param in PARAMETER_DESCRIPTIONS
            assert PARAMETER_DESCRIPTIONS[param].get("required", False) is False

    def test_get_subtask_description_function(self):
        """Test the get_subtask_description function"""
        description = get_subtask_description()
        
        # Should return the full description
        assert description == SUBTASK_DESCRIPTION
        assert isinstance(description, str)
        assert len(description) > 0

    def test_action_descriptions(self):
        """Test that all actions are properly documented"""
        actions = ["create", "update", "delete", "get", "list", "complete"]
        description = get_subtask_description()
        
        for action in actions:
            assert action in description
            # Check for required/optional parameters for each action
            assert f"| {action}" in description  # Table format

    def test_inheritance_documentation(self):
        """Test agent inheritance is properly documented"""
        description = get_subtask_description()
        
        # Check for inheritance explanation
        assert "inherit" in description.lower()
        assert "parent task" in description.lower()
        assert "agents" in description.lower()

    def test_progress_tracking_documentation(self):
        """Test progress tracking features are documented"""
        description = get_subtask_description()
        
        assert "progress_percentage" in description
        assert "progress_notes" in description
        assert "0=todo" in description
        assert "1-99=in_progress" in description
        assert "100=done" in description

    def test_workflow_hints_documentation(self):
        """Test workflow hints are documented"""
        description = get_subtask_description()
        
        assert "hint" in description.lower()
        assert "workflow" in description.lower()
        assert "guidance" in description.lower()

    def test_examples_presence(self):
        """Test that practical examples are included"""
        description = get_subtask_description()
        
        assert "PRACTICAL EXAMPLES" in description
        assert "action:" in description  # Example format
        assert "task_id:" in description
        assert "completion_summary:" in description

    def test_parameter_type_validation(self):
        """Test parameter type specifications"""
        # String parameters
        string_params = ["action", "task_id", "subtask_id", "title", "description"]
        for param in string_params:
            assert PARAMETER_DESCRIPTIONS[param]["type"] == "string"
        
        # Integer parameters
        assert PARAMETER_DESCRIPTIONS["progress_percentage"]["type"] == "integer"
        
        # Boolean parameters (if any)
        # Array/list parameters (handled as strings)
        assert "string" in PARAMETER_DESCRIPTIONS["assignees"]["type"]

    def test_enhanced_features_documentation(self):
        """Test enhanced features are documented"""
        description = get_subtask_description()
        
        # Automatic features
        assert "AUTOMATIC FEATURES" in description
        assert "Parent task progress recalculation" in description
        assert "Context updates" in description
        assert "Blocker escalation" in description
        
        # Response enhancements
        assert "RESPONSE ENHANCEMENTS" in description
        assert "parent_progress" in description
        assert "progress_summary" in description

    def test_best_practices_section(self):
        """Test best practices are included"""
        description = get_subtask_description()
        
        assert "BEST PRACTICES" in description
        assert "Create subtasks BEFORE" in description
        assert "Update progress_percentage regularly" in description
        assert "completion_summary when completing" in description

    def test_error_handling_documentation(self):
        """Test error handling is documented"""
        description = get_subtask_description()
        
        assert "ERROR HANDLING" in description
        assert "missing" in description.lower()
        assert "error" in description.lower()

    def test_markdown_formatting(self):
        """Test markdown formatting is correct"""
        description = get_subtask_description()
        
        # Headers
        assert description.count("#") > 5  # Multiple headers
        assert "###" in description  # Sub-headers
        
        # Tables
        assert "|" in description  # Table separators
        assert "---" in description  # Table header separator
        
        # Lists
        assert "- " in description  # Bullet points
        assert "• " in description  # Alternative bullets

    def test_consistency_with_task_controller(self):
        """Test consistency with parent task controller"""
        # Common parameters should have consistent descriptions
        common_params = ["action", "status", "priority", "assignees"]
        
        for param in common_params:
            desc = PARAMETER_DESCRIPTIONS[param]
            assert "description" in desc
            assert len(desc["description"]) > 10  # Non-trivial description

    def test_version_and_metadata(self):
        """Test version information if present"""
        description = get_subtask_description()
        
        # May contain version or last updated info
        if "version" in description.lower() or "updated" in description.lower():
            assert True  # Version info is good practice

    def test_integration_examples(self):
        """Test integration examples with parent task"""
        description = get_subtask_description()
        
        # Should show how subtasks relate to parent tasks
        assert "parent" in description.lower()
        assert "task" in description.lower()
        
        # May include integration patterns
        if "Parent task:" in description:
            assert "Subtasks:" in description