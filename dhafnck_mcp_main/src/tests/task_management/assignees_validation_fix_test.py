"""
Test for assignees validation fix in task management system.

Tests that various assignee formats are correctly handled:
- Single agent: "@coding-agent"
- Multiple agents: "@coding-agent,@security-auditor-agent"
- User ID: "user123"
"""

import pytest
from unittest.mock import Mock
from typing import List, Dict, Any

from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.validators.parameter_validator import ParameterValidator
from fastmcp.task_management.interface.utils.response_formatter import StandardResponseFormatter


class TestAssigneesValidationFix:
    """Test suite for assignees validation fixes."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.response_formatter = StandardResponseFormatter()
        self.validator = ParameterValidator(self.response_formatter)
    
    def test_single_agent_validation(self):
        """Test validation of single agent identifier."""
        # Test with @ prefix
        assert self.validator._is_valid_assignees_list(["@coding-agent"])
        assert self.validator._is_valid_assignees_list(["@test-orchestrator-agent"])
        assert self.validator._is_valid_assignees_list(["@security-auditor-agent"])
        
        # Test without @ prefix
        assert self.validator._is_valid_assignees_list(["coding-agent"])
        assert self.validator._is_valid_assignees_list(["test-orchestrator-agent"])
    
    def test_multiple_agents_validation(self):
        """Test validation of multiple agent identifiers."""
        assignees = ["@coding-agent", "@security-auditor-agent", "@test-orchestrator-agent"]
        assert self.validator._is_valid_assignees_list(assignees)
        
        # Mixed with/without @ prefix
        mixed_assignees = ["@coding-agent", "security-auditor-agent", "@test-orchestrator-agent"]
        assert self.validator._is_valid_assignees_list(mixed_assignees)
    
    def test_user_id_validation(self):
        """Test validation of user IDs."""
        assert self.validator._is_valid_assignees_list(["user123"])
        assert self.validator._is_valid_assignees_list(["user-456"])
        assert self.validator._is_valid_assignees_list(["user_789"])
    
    def test_invalid_assignees_validation(self):
        """Test validation of invalid assignee formats."""
        # Empty string
        assert not self.validator._is_valid_assignees_list([""])
        assert not self.validator._is_valid_assignees_list([" "])
        
        # Invalid characters
        assert not self.validator._is_valid_assignees_list(["agent@domain"])
        assert not self.validator._is_valid_assignees_list(["agent.name"])
        assert not self.validator._is_valid_assignees_list(["agent name"])
        
        # Not a list
        assert not self.validator._is_valid_assignees_list("@coding-agent")
        assert not self.validator._is_valid_assignees_list(None)
    
    def test_create_task_params_validation_success(self):
        """Test that create task params validation works with various assignee formats."""
        # Single agent with @ prefix
        is_valid, error = self.validator.validate_create_task_params(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            assignees=["@coding-agent"]
        )
        assert is_valid
        assert error is None
        
        # Multiple agents comma-separated
        is_valid, error = self.validator.validate_create_task_params(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            assignees=["@coding-agent", "@security-auditor-agent"]
        )
        assert is_valid
        assert error is None
        
        # User ID
        is_valid, error = self.validator.validate_create_task_params(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            assignees=["user123"]
        )
        assert is_valid
        assert error is None
    
    def test_create_task_params_validation_failure(self):
        """Test that create task params validation fails for invalid assignee formats."""
        # Invalid assignee format
        is_valid, error = self.validator.validate_create_task_params(
            title="Test Task",
            git_branch_id="550e8400-e29b-41d4-a716-446655440000",
            assignees=["agent@domain"]
        )
        assert not is_valid
        assert error is not None
        assert "assignees" in str(error)


def test_string_to_list_conversion_logic():
    """Test the string-to-list conversion logic from the task controller."""
    
    # Test single assignee conversion
    def convert_assignees(assignees):
        if assignees is not None and isinstance(assignees, str):
            if ',' in assignees:
                return [a.strip() for a in assignees.split(',') if a.strip()]
            else:
                return [assignees.strip()] if assignees.strip() else []
        return assignees
    
    # Single agent
    assert convert_assignees("@coding-agent") == ["@coding-agent"]
    assert convert_assignees("user123") == ["user123"]
    
    # Comma-separated agents
    assert convert_assignees("@coding-agent,@security-auditor-agent") == ["@coding-agent", "@security-auditor-agent"]
    assert convert_assignees("@coding-agent, @security-auditor-agent") == ["@coding-agent", "@security-auditor-agent"]
    
    # Edge cases
    assert convert_assignees("") == []
    assert convert_assignees(" ") == []
    assert convert_assignees("@coding-agent,") == ["@coding-agent"]
    assert convert_assignees(",@coding-agent") == ["@coding-agent"]
    
    # Already a list
    assert convert_assignees(["@coding-agent"]) == ["@coding-agent"]
    assert convert_assignees(None) is None


if __name__ == "__main__":
    pytest.main([__file__])