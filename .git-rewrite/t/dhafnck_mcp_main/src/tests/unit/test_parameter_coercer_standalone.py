#!/usr/bin/env python3
"""
Standalone Test for ParameterTypeCoercer Boolean Parameter Fix

Tests just the ParameterTypeCoercer class without complex dependencies.
Verifies that the boolean parameter fix works for context management parameters.
"""

import pytest

from fastmcp.task_management.interface.utils.parameter_validation_fix import ParameterTypeCoercer


class TestParameterTypeCoercerStandalone:
    
    def setup_method(self, method):
        """Clean up before each test"""
        # This is a standalone test that doesn't need database setup
        pass

    """Standalone tests for the ParameterTypeCoercer boolean parameter fix."""
    
    def test_context_boolean_parameters_included(self):
        """Test that context management boolean parameters are included in BOOLEAN_PARAMETERS."""
        boolean_params = ParameterTypeCoercer.BOOLEAN_PARAMETERS
        
        # Verify that context management boolean parameters are included
        assert 'include_inherited' in boolean_params
        assert 'force_refresh' in boolean_params
        assert 'propagate_changes' in boolean_params
        
        print(f"✅ Context boolean parameters found in BOOLEAN_PARAMETERS: {boolean_params}")
    
    def test_boolean_string_coercion_true_values(self):
        """Test that various string representations of True are coerced correctly."""
        test_params = {
            'include_inherited': 'true',
            'force_refresh': 'True',
            'propagate_changes': '1'
        }
        
        coerced = ParameterTypeCoercer.coerce_parameter_types(test_params)
        
        assert coerced['include_inherited'] is True
        assert coerced['force_refresh'] is True
        assert coerced['propagate_changes'] is True
        
        print(f"✅ True string values coerced correctly: {coerced}")
    
    def test_boolean_string_coercion_false_values(self):
        """Test that various string representations of False are coerced correctly."""
        test_params = {
            'include_inherited': 'false',
            'force_refresh': 'False',
            'propagate_changes': '0'
        }
        
        coerced = ParameterTypeCoercer.coerce_parameter_types(test_params)
        
        assert coerced['include_inherited'] is False
        assert coerced['force_refresh'] is False
        assert coerced['propagate_changes'] is False
        
        print(f"✅ False string values coerced correctly: {coerced}")
    
    def test_boolean_actual_values_preserved(self):
        """Test that actual boolean values are preserved without modification."""
        test_params = {
            'include_inherited': True,
            'force_refresh': False,
            'propagate_changes': True
        }
        
        coerced = ParameterTypeCoercer.coerce_parameter_types(test_params)
        
        assert coerced['include_inherited'] is True
        assert coerced['force_refresh'] is False
        assert coerced['propagate_changes'] is True
        
        print(f"✅ Actual boolean values preserved: {coerced}")
    
    def test_boolean_alternative_string_formats(self):
        """Test alternative string formats like yes/no, on/off."""
        test_params = {
            'include_inherited': 'yes',
            'force_refresh': 'on',
            'propagate_changes': 'no'
        }
        
        coerced = ParameterTypeCoercer.coerce_parameter_types(test_params)
        
        assert coerced['include_inherited'] is True
        assert coerced['force_refresh'] is True
        assert coerced['propagate_changes'] is False
        
        print(f"✅ Alternative boolean string formats coerced correctly: {coerced}")
    
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
        
        print(f"✅ All boolean string variations work correctly")
        print(f"   TRUE values tested: {true_values}")
        print(f"   FALSE values tested: {false_values}")
    
    def test_invalid_boolean_string_raises_error(self):
        """Test that invalid boolean strings raise appropriate errors."""
        test_params = {
            'include_inherited': 'maybe',
            'force_refresh': 'sometimes'
        }
        
        with pytest.raises(Exception) as exc_info:
            ParameterTypeCoercer.coerce_parameter_types(test_params)
        
        # Should mention valid boolean values
        error_message = str(exc_info.value)
        assert 'boolean' in error_message.lower()
        assert ('true' in error_message.lower() or 'false' in error_message.lower())
        
        print(f"✅ Invalid boolean strings properly raise errors: {error_message}")
    
    def test_mixed_parameter_types_coercion(self):
        """Test coercion when mixing boolean and other parameter types."""
        test_params = {
            'include_inherited': 'true',  # Boolean
            'force_refresh': False,       # Already boolean
            'context_id': 'test-id',     # String (no coercion needed)
            'propagate_changes': 'on'    # Boolean
        }
        
        coerced = ParameterTypeCoercer.coerce_parameter_types(test_params)
        
        # Check boolean coercions
        assert coerced['include_inherited'] is True
        assert coerced['force_refresh'] is False
        assert coerced['propagate_changes'] is True
        
        # Check that non-boolean params are preserved
        assert coerced['context_id'] == 'test-id'
        
        print(f"✅ Mixed parameter types handled correctly: {coerced}")


def test_parameter_validation_fix_demo():
    """
    Demonstration test showing the boolean parameter fix works.
    This would be the test case that reproduces the original issue.
    """
    print("\n🧪 Testing Parameter Validation Fix")
    print("=" * 50)
    
    # This was the original failing case:
    # Input validation error: 'true' is not valid under any of the given schemas
    
    original_failing_params = {
        'include_inherited': 'true',  # This used to fail
        'force_refresh': 'false',     # This used to fail
        'propagate_changes': 'yes'    # This used to fail
    }
    
    print(f"\n🔍 Original failing parameters: {original_failing_params}")
    
    # Now with the fix, this should work
    try:
        coerced_params = ParameterTypeCoercer.coerce_parameter_types(original_failing_params)
        print(f"✅ SUCCESS: Parameters coerced successfully!")
        print(f"   Coerced to: {coerced_params}")
        
        # Verify types
        assert isinstance(coerced_params['include_inherited'], bool)
        assert isinstance(coerced_params['force_refresh'], bool)
        assert isinstance(coerced_params['propagate_changes'], bool)
        
        # Verify values
        assert coerced_params['include_inherited'] is True
        assert coerced_params['force_refresh'] is False
        assert coerced_params['propagate_changes'] is True
        
        print(f"✅ All assertions passed - boolean parameter fix is working!")
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        raise
    
    print(f"\n🎯 Parameter Validation Fix Test Complete!")


if __name__ == "__main__":
    # Run individual tests
    test_instance = TestParameterTypeCoercerStandalone()
    test_instance.test_context_boolean_parameters_included()
    test_instance.test_boolean_string_coercion_true_values()
    test_instance.test_boolean_string_coercion_false_values()
    test_instance.test_boolean_actual_values_preserved()
    test_instance.test_boolean_alternative_string_formats()
    test_instance.test_all_boolean_string_variations()
    test_instance.test_invalid_boolean_string_raises_error()
    test_instance.test_mixed_parameter_types_coercion()
    
    # Run demonstration
    test_parameter_validation_fix_demo()
    
    print("\n🎉 All standalone parameter coercion tests passed!")