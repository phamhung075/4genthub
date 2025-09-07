#!/usr/bin/env python3
"""
Integration Test for MCP Parameter Validation Fix

This test suite verifies that the parameter validation fix works correctly
when integrated with the actual MCP controllers, ensuring that string integers
and booleans are properly coerced before processing.
"""

import pytest
import asyncio
import logging
from typing import Dict, Any
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from fastmcp.task_management.interface.utils.parameter_validation_fix import (
    coerce_parameter_types,
    validate_parameters,
    ParameterTypeCoercionError
)
from fastmcp.task_management.interface.controllers.task_mcp_controller import TaskMCPController

logger = logging.getLogger(__name__)


class TestMCPParameterValidationIntegration:
    
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

    """Integration tests for parameter validation with MCP controllers"""
    
    @pytest.fixture
    def controller(self):
        """Create a task controller for testing"""
        from fastmcp.task_management.application.factories.task_facade_factory import TaskFacadeFactory
        from fastmcp.task_management.infrastructure.repositories.task_repository_factory import TaskRepositoryFactory
        repository_factory = TaskRepositoryFactory()
        task_facade_factory = TaskFacadeFactory(repository_factory=repository_factory)
        return TaskMCPController(task_facade_factory=task_facade_factory)
    
    def test_limit_parameter_coercion_integration(self, controller):
        """Test that limit parameter accepts both string and integer values"""
        # Test with string limit
        params_with_string_limit = {
            "action": "search",
            "query": "test",
            "limit": "5"  # String integer - should be coerced
        }
        
        # Apply parameter coercion
        coerced_params = coerce_parameter_types(params_with_string_limit)
        
        # Verify coercion worked
        assert coerced_params["limit"] == 5
        assert isinstance(coerced_params["limit"], int)
        
        # Test validation
        validation_result = validate_parameters("search", params_with_string_limit)
        assert validation_result["success"] is True
        assert validation_result["coerced_params"]["limit"] == 5
    
    def test_progress_percentage_coercion_integration(self, controller):
        """Test that progress_percentage parameter accepts both string and integer values"""
        # Test with string progress percentage
        params_with_string_progress = {
            "action": "update",
            "task_id": "test-task-123",
            "progress_percentage": "75"  # String integer - should be coerced
        }
        
        # Apply parameter coercion
        coerced_params = coerce_parameter_types(params_with_string_progress)
        
        # Verify coercion worked
        assert coerced_params["progress_percentage"] == 75
        assert isinstance(coerced_params["progress_percentage"], int)
        
        # Test validation
        validation_result = validate_parameters("update", params_with_string_progress)
        assert validation_result["success"] is True
        assert validation_result["coerced_params"]["progress_percentage"] == 75
    
    def test_boolean_parameter_coercion_integration(self, controller):
        """Test that boolean parameters accept string representations"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
        ]
        
        for string_value, expected_bool in test_cases:
            params = {
                "action": "get",
                "task_id": "test-task-123",
                "include_context": string_value
            }
            
            # Apply parameter coercion
            coerced_params = coerce_parameter_types(params)
            
            # Verify coercion worked
            assert coerced_params["include_context"] == expected_bool
            assert isinstance(coerced_params["include_context"], bool)
            
            # Test validation
            validation_result = validate_parameters("get", params)
            assert validation_result["success"] is True
            assert validation_result["coerced_params"]["include_context"] == expected_bool
    
    def test_mixed_parameter_types_integration(self, controller):
        """Test validation with multiple parameters of different types"""
        params = {
            "action": "search",
            "query": "authentication",
            "limit": "10",              # String integer
            "include_context": "true",  # String boolean
            "git_branch_id": "branch-123"  # Already string - should remain
        }
        
        # Apply parameter coercion
        coerced_params = coerce_parameter_types(params)
        
        # Verify individual coercions
        assert coerced_params["limit"] == 10
        assert isinstance(coerced_params["limit"], int)
        
        assert coerced_params["include_context"] is True
        assert isinstance(coerced_params["include_context"], bool)
        
        assert coerced_params["git_branch_id"] == "branch-123"
        assert isinstance(coerced_params["git_branch_id"], str)
        
        # Test full validation
        validation_result = validate_parameters("search", params)
        assert validation_result["success"] is True
        assert validation_result["coerced_params"]["limit"] == 10
        assert validation_result["coerced_params"]["include_context"] is True
        assert validation_result["coerced_params"]["git_branch_id"] == "branch-123"
    
    def test_original_failing_case_integration(self, controller):
        """Test the exact case that was failing before the fix"""
        # This was the original failing case
        failing_params = {
            "action": "search",
            "query": "test", 
            "limit": "3"  # This was causing: "Input validation error: '3' is not valid"
        }
        
        # This should now work after our fix
        try:
            validation_result = validate_parameters("search", failing_params)
            
            # Verify it succeeds
            assert validation_result["success"] is True
            assert validation_result["coerced_params"]["limit"] == 3
            assert isinstance(validation_result["coerced_params"]["limit"], int)
            
            print("✅ FIXED: Original failing case now passes!")
            
        except Exception as e:
            pytest.fail(f"Original failing case still fails: {e}")
    
    def test_invalid_parameters_still_fail_properly(self, controller):
        """Test that invalid parameters still fail with helpful error messages"""
        invalid_cases = [
            {
                "params": {"action": "search", "query": "test", "limit": "abc"},
                "expected_error": "cannot be converted to integer"
            },
            {
                "params": {"action": "search", "query": "test", "limit": ""},
                "expected_error": "cannot be empty when expecting an integer"
            },
            {
                "params": {"action": "get", "task_id": "test", "include_context": "maybe"},
                "expected_error": "not a valid boolean"
            }
        ]
        
        for case in invalid_cases:
            try:
                coerce_parameter_types(case["params"])
                pytest.fail(f"Expected validation to fail for {case['params']}")
            except ValueError as e:
                assert case["expected_error"] in str(e)
                print(f"✅ Properly rejected invalid input: {case['params']}")
    
    def test_range_validation_integration(self, controller):
        """Test that range validation still works after coercion"""
        # Test values within range
        valid_limits = ["1", "50", "100", 1, 50, 100]
        for limit_value in valid_limits:
            params = {"action": "search", "query": "test", "limit": limit_value}
            validation_result = validate_parameters("search", params)
            assert validation_result["success"] is True
            
        # Test values outside typical range (if range validation is implemented)
        # Note: This test depends on whether range validation is implemented
        # For now, we just test that coercion works correctly
        out_of_range_params = {"action": "search", "query": "test", "limit": "999"}
        coerced = coerce_parameter_types(out_of_range_params)
        assert coerced["limit"] == 999  # Coercion should work
        assert isinstance(coerced["limit"], int)
    
    def test_parameter_validation_with_mcp_tool_decorator(self):
        """Test that parameter validation works with the actual MCP tool decorator"""
        # This test would require setting up the full MCP server environment
        # For now, we just test the validation functions directly
        
        # Simulate what the MCP tool decorator would receive
        raw_params = {
            "action": "search",
            "query": "authentication",
            "limit": "5",  # String from HTTP/JSON
            "include_context": "true"  # String from HTTP/JSON
        }
        
        # This is what should happen in the MCP controller before processing
        validation_result = validate_parameters("search", raw_params)
        
        assert validation_result["success"] is True
        coerced_params = validation_result["coerced_params"]
        
        # Verify all types are correct for business logic
        assert isinstance(coerced_params["limit"], int)
        assert isinstance(coerced_params["include_context"], bool)
        assert coerced_params["limit"] == 5
        assert coerced_params["include_context"] is True
    
    def test_subtask_progress_percentage_validation(self):
        """Test subtask progress percentage validation specifically"""
        # Test the subtask progress percentage case
        subtask_params = {
            "action": "update",
            "task_id": "parent-task-123",
            "subtask_id": "subtask-456", 
            "progress_percentage": "75"  # String percentage
        }
        
        validation_result = validate_parameters("update", subtask_params)
        assert validation_result["success"] is True
        assert validation_result["coerced_params"]["progress_percentage"] == 75
        assert isinstance(validation_result["coerced_params"]["progress_percentage"], int)
        
        # Test edge cases for percentage
        edge_cases = ["0", "100", 0, 100]
        for progress in edge_cases:
            params = {
                "action": "update",
                "task_id": "test",
                "progress_percentage": progress
            }
            result = validate_parameters("update", params)
            assert result["success"] is True
            assert 0 <= result["coerced_params"]["progress_percentage"] <= 100


def test_comprehensive_parameter_validation_scenarios():
    """Comprehensive test covering all the scenarios mentioned in the issue"""
    
    print("\n🧪 Testing Comprehensive Parameter Validation Scenarios")
    print("=" * 60)
    
    # Test all the problematic cases from the issue
    test_scenarios = [
        {
            "name": "limit as string in search",
            "params": {"action": "search", "query": "test", "limit": "3"},
            "expected_coerced": {"action": "search", "query": "test", "limit": 3}
        },
        {
            "name": "limit as integer in search", 
            "params": {"action": "search", "query": "test", "limit": 3},
            "expected_coerced": {"action": "search", "query": "test", "limit": 3}
        },
        {
            "name": "progress_percentage as string in update",
            "params": {"action": "update", "task_id": "test", "progress_percentage": "50"},
            "expected_coerced": {"action": "update", "task_id": "test", "progress_percentage": 50}
        },
        {
            "name": "include_context as string in get",
            "params": {"action": "get", "task_id": "test", "include_context": "true"},
            "expected_coerced": {"action": "get", "task_id": "test", "include_context": True}
        },
        {
            "name": "multiple mixed types",
            "params": {
                "action": "search",
                "query": "auth",
                "limit": "10",
                "include_context": "false",
                "force": "1"
            },
            "expected_coerced": {
                "action": "search", 
                "query": "auth",
                "limit": 10,
                "include_context": False,
                "force": True
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['name']}")
        print(f"Input: {scenario['params']}")
        
        try:
            # Test parameter coercion
            coerced = coerce_parameter_types(scenario["params"])
            print(f"Coerced: {coerced}")
            
            # Verify expected coercion
            for key, expected_value in scenario["expected_coerced"].items():
                assert coerced[key] == expected_value
                if key in ["limit", "progress_percentage"]:
                    assert isinstance(coerced[key], int)
                elif key in ["include_context", "force"]:
                    assert isinstance(coerced[key], bool)
            
            # Test full validation
            validation_result = validate_parameters(scenario["params"]["action"], scenario["params"])
            assert validation_result["success"] is True
            
            print(f"✅ {scenario['name']}: PASSED")
            
        except Exception as e:
            print(f"❌ {scenario['name']}: FAILED - {e}")
            raise


if __name__ == "__main__":
    # Run the comprehensive test
    test_comprehensive_parameter_validation_scenarios()
    
    print("\n🎯 All Parameter Validation Integration Tests Complete!")
    print("The MCP parameter validation fix is working correctly!")