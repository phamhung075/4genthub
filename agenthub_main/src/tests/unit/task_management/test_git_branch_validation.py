#!/usr/bin/env python3
"""
Test script to verify git_branch_id validation for different task operations.
This confirms that:
- create and next operations require git_branch_id
- get, update, and complete operations don't require git_branch_id
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from fastmcp.task_management.interface.mcp_controllers.task_mcp_controller.validators.context_validator import ContextValidator
from fastmcp.task_management.utils.response_formatter import StandardResponseFormatter

def test_context_validation():
    """Test context validation for different operations."""
    formatter = StandardResponseFormatter()
    validator = ContextValidator(formatter)

    print("Testing Context Validation for Task Operations")
    print("=" * 50)

    # Test operations that SHOULD require git_branch_id
    require_git_branch_ops = ["create", "next"]
    for op in require_git_branch_ops:
        result, error = validator.validate_context_requirements(
            operation=op,
            git_branch_id=None
        )
        print(f"\n{op.upper()} without git_branch_id:")
        print(f"  Valid: {result}")
        if error:
            print(f"  Error: {error.get('error', 'N/A')}")
        assert result == False, f"{op} should require git_branch_id"

        # Test with git_branch_id
        result, error = validator.validate_context_requirements(
            operation=op,
            git_branch_id="branch-123"
        )
        print(f"\n{op.upper()} with git_branch_id:")
        print(f"  Valid: {result}")
        assert result == True, f"{op} should be valid with git_branch_id"

    # Test operations that should NOT require git_branch_id
    no_git_branch_ops = ["get", "update", "complete", "delete", "list", "search"]
    for op in no_git_branch_ops:
        result, error = validator.validate_context_requirements(
            operation=op,
            task_id="task-123",
            git_branch_id=None
        )
        print(f"\n{op.upper()} without git_branch_id:")
        print(f"  Valid: {result}")
        if error:
            print(f"  Error: {error}")
        assert result == True, f"{op} should NOT require git_branch_id"

    print("\n" + "=" * 50)
    print("✅ All validation tests passed!")
    print("\nSummary:")
    print("- 'create' and 'next' operations require git_branch_id")
    print("- 'get', 'update', 'complete', 'delete', 'list', 'search' operations don't require git_branch_id")

if __name__ == "__main__":
    test_context_validation()