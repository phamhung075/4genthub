#!/usr/bin/env python3
"""
TDD Test Suite for Parameter Type Coercion Fix

This test suite implements the test cases that need to pass for fixing
the parameter validation issue: "Input validation error: '5' is not valid under any of the given schemas"

The tests are written BEFORE implementing the fix (TDD approach).
"""

import unittest
import json
from typing import Dict, Any, Union, List, Optional

# Import our implementation from the utils directory
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from fastmcp.task_management.interface.utils.parameter_validation_fix import (
    coerce_parameter_types,
    validate_parameters,
    create_flexible_schema,
    ParameterTypeCoercionError
)


class ParameterTypeCoercionTests(unittest.TestCase):
    """Test cases for parameter type coercion functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Use the actual implementations
        self.coerce_parameter_types = coerce_parameter_types
        self.validate_parameters = validate_parameters
        
    def test_integer_string_coercion(self):
        """Test that string integers are coerced to integers"""
        test_cases = [
            # (input_value, expected_output, parameter_name)
            ("5", 5, "limit"),
            ("50", 50, "progress_percentage"),
            ("30", 30, "timeout"),
            ("8080", 8080, "port"),
            ("0", 0, "progress_percentage"),
            ("100", 100, "progress_percentage"),
        ]
        
        for input_val, expected, param_name in test_cases:
            with self.subTest(input_val=input_val, param=param_name):
                params = {param_name: input_val}
                schema = self._get_test_schema_for_param(param_name)
                
                # This should NOT raise an exception after our fix
                try:
                    coerced_params = self._coerce_parameter_types(params, schema)
                    self.assertEqual(coerced_params[param_name], expected)
                    self.assertIsInstance(coerced_params[param_name], int)
                except Exception as e:
                    self.fail(f"Parameter coercion failed for {param_name}='{input_val}': {e}")
    
    def test_boolean_string_coercion(self):
        """Test that string booleans are coerced to booleans"""
        test_cases = [
            # (input_value, expected_output, parameter_name)
            ("true", True, "include_context"),
            ("True", True, "force"),
            ("TRUE", True, "audit_required"),
            ("false", False, "include_details"),
            ("False", False, "include_context"),
            ("FALSE", False, "force"),
            ("1", True, "audit_required"),
            ("0", False, "include_details"),
            ("yes", True, "force"),
            ("no", False, "include_context"),
            ("on", True, "audit_required"),
            ("off", False, "include_details"),
        ]
        
        for input_val, expected, param_name in test_cases:
            with self.subTest(input_val=input_val, param=param_name):
                params = {param_name: input_val}
                schema = self._get_test_schema_for_param(param_name)
                
                try:
                    coerced_params = self._coerce_parameter_types(params, schema)
                    self.assertEqual(coerced_params[param_name], expected)
                    self.assertIsInstance(coerced_params[param_name], bool)
                except Exception as e:
                    self.fail(f"Boolean coercion failed for {param_name}='{input_val}': {e}")
    
    def test_invalid_integer_strings_raise_error(self):
        """Test that invalid integer strings raise proper errors"""
        invalid_cases = [
            ("abc", "limit"),
            ("5.5", "progress_percentage"),
            ("", "timeout"),
            ("infinity", "port"),
            ("null", "limit"),
        ]
        
        for input_val, param_name in invalid_cases:
            with self.subTest(input_val=input_val, param=param_name):
                params = {param_name: input_val}
                schema = self._get_test_schema_for_param(param_name)
                
                with self.assertRaises(ValueError) as context:
                    self._coerce_parameter_types(params, schema)
                
                # Check that the error message indicates it's about integer conversion
                error_msg = str(context.exception)
                self.assertTrue(
                    "cannot be converted to integer" in error_msg or 
                    "cannot be empty when expecting an integer" in error_msg,
                    f"Expected integer conversion error, got: {error_msg}"
                )
    
    def test_progress_percentage_validation(self):
        """Test progress percentage specific validation (0-100 range)"""
        valid_cases = [
            ("0", 0),
            ("50", 50),
            ("100", 100),
            (0, 0),        # Already integer
            (75, 75),      # Already integer
        ]
        
        for input_val, expected in valid_cases:
            with self.subTest(input_val=input_val):
                params = {"progress_percentage": input_val}
                schema = self._get_test_schema_for_param("progress_percentage")
                
                try:
                    coerced_params = self._coerce_parameter_types(params, schema)
                    result = self._validate_parameters("update", coerced_params)
                    
                    self.assertTrue(result.get("success", True))
                    self.assertEqual(coerced_params["progress_percentage"], expected)
                except Exception as e:
                    self.fail(f"Progress percentage validation failed for '{input_val}': {e}")
    
    def test_limit_parameter_validation(self):
        """Test limit parameter validation (1-100 range typically)"""
        valid_cases = [
            ("1", 1),
            ("5", 5),     # The original failing case
            ("50", 50),
            ("100", 100),
            (25, 25),     # Already integer
        ]
        
        for input_val, expected in valid_cases:
            with self.subTest(input_val=input_val):
                params = {"limit": input_val}
                schema = self._get_test_schema_for_param("limit")
                
                try:
                    coerced_params = self._coerce_parameter_types(params, schema)
                    result = self._validate_parameters("search", coerced_params)
                    
                    self.assertTrue(result.get("success", True))
                    self.assertEqual(coerced_params["limit"], expected)
                except Exception as e:
                    self.fail(f"Limit validation failed for '{input_val}': {e}")
    
    def test_mixed_parameter_types(self):
        """Test validation with multiple parameters of different types"""
        params = {
            "limit": "5",              # String integer
            "include_context": "true", # String boolean
            "progress_percentage": 75, # Already integer
            "force": False,            # Already boolean
        }
        
        schema = {
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                "include_context": {"type": "boolean"},
                "progress_percentage": {"type": "integer", "minimum": 0, "maximum": 100},
                "force": {"type": "boolean"},
            }
        }
        
        try:
            coerced_params = self._coerce_parameter_types(params, schema)
            
            # Verify all types are correct
            self.assertIsInstance(coerced_params["limit"], int)
            self.assertEqual(coerced_params["limit"], 5)
            
            self.assertIsInstance(coerced_params["include_context"], bool)
            self.assertEqual(coerced_params["include_context"], True)
            
            self.assertIsInstance(coerced_params["progress_percentage"], int)
            self.assertEqual(coerced_params["progress_percentage"], 75)
            
            self.assertIsInstance(coerced_params["force"], bool)
            self.assertEqual(coerced_params["force"], False)
            
        except Exception as e:
            self.fail(f"Mixed parameter validation failed: {e}")
    
    def test_original_failing_cases(self):
        """Test the specific cases mentioned in the issue"""
        failing_cases = [
            # Case 1: limit as string "5"
            {
                "action": "search",
                "params": {"query": "test", "limit": "5"},
                "expected_limit": 5
            },
            # Case 2: progress_percentage as string "50"
            {
                "action": "update",
                "params": {"task_id": "test", "progress_percentage": "50"},
                "expected_progress": 50
            },
        ]
        
        for case in failing_cases:
            with self.subTest(case=case["action"]):
                try:
                    # This is the main test - these should NOT fail after our fix
                    result = self._validate_parameters_full(case["action"], case["params"])
                    self.assertTrue(result.get("success", True), 
                                  f"Validation failed for {case}: {result}")
                    
                    # Verify specific coercions worked
                    if "limit" in case["params"]:
                        self.assertEqual(result["coerced_params"]["limit"], 
                                       case["expected_limit"])
                    
                    if "progress_percentage" in case["params"]:
                        self.assertEqual(result["coerced_params"]["progress_percentage"], 
                                       case["expected_progress"])
                        
                except Exception as e:
                    self.fail(f"Original failing case failed: {case['action']} - {e}")
    
    def test_flexible_schema_validation(self):
        """Test that flexible schemas accept both integers and string integers"""
        flexible_schema = {
            "properties": {
                "limit": {
                    "anyOf": [
                        {"type": "integer", "minimum": 1, "maximum": 100},
                        {"type": "string", "pattern": "^[1-9][0-9]?$|^100$"}
                    ]
                },
                "progress_percentage": {
                    "anyOf": [
                        {"type": "integer", "minimum": 0, "maximum": 100},
                        {"type": "string", "pattern": "^(100|[1-9]?[0-9])$"}
                    ]
                }
            }
        }
        
        test_cases = [
            {"limit": 5, "progress_percentage": 50},      # Integers
            {"limit": "5", "progress_percentage": "50"},  # Strings
            {"limit": 5, "progress_percentage": "50"},    # Mixed
            {"limit": "5", "progress_percentage": 50},    # Mixed reverse
        ]
        
        for params in test_cases:
            with self.subTest(params=params):
                try:
                    # Schema should accept both formats
                    result = self._validate_with_flexible_schema(params, flexible_schema)
                    self.assertTrue(result.get("success", True))
                except Exception as e:
                    self.fail(f"Flexible schema validation failed for {params}: {e}")
    
    # Helper methods that will be replaced with actual implementations
    
    def _coerce_parameter_types(self, params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for the actual coerce_parameter_types function"""
        if self.coerce_parameter_types:
            return self.coerce_parameter_types(params, schema)
        else:
            self.skipTest("coerce_parameter_types not implemented yet")
    
    def _validate_parameters(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Placeholder for the actual validate_parameters function"""
        if self.validate_parameters:
            return self.validate_parameters(action, params)
        else:
            self.skipTest("validate_parameters not implemented yet")
    
    def _validate_parameters_full(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Full validation with coercion"""
        return validate_parameters(action, params)
    
    def _validate_with_flexible_schema(self, params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Flexible schema validation"""
        return validate_parameters("test", params, schema)
    
    def _get_test_schema_for_param(self, param_name: str) -> Dict[str, Any]:
        """Get a test schema for a specific parameter"""
        schemas = {
            "limit": {
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100}
                }
            },
            "progress_percentage": {
                "properties": {
                    "progress_percentage": {"type": "integer", "minimum": 0, "maximum": 100}
                }
            },
            "timeout": {
                "properties": {
                    "timeout": {"type": "integer", "minimum": 1}
                }
            },
            "port": {
                "properties": {
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535}
                }
            },
            "include_context": {
                "properties": {
                    "include_context": {"type": "boolean"}
                }
            },
            "force": {
                "properties": {
                    "force": {"type": "boolean"}
                }
            },
            "audit_required": {
                "properties": {
                    "audit_required": {"type": "boolean"}
                }
            },
            "include_details": {
                "properties": {
                    "include_details": {"type": "boolean"}
                }
            },
        }
        
        return schemas.get(param_name, {"properties": {}})


if __name__ == "__main__":
    # Print test plan
    print("🧪 TDD Test Suite for Parameter Type Coercion")
    print("=" * 50)
    print("These tests WILL FAIL initially - that's expected in TDD!")
    print("We implement the fix to make these tests pass.")
    print()
    
    # Run the tests
    unittest.main(verbosity=2)