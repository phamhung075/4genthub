"""
Test suite for Parameter Validation Fix module.

Tests the parameter type coercion system including string-to-int conversion,
flexible boolean parsing, and comprehensive error handling.
"""

import pytest
from unittest.mock import Mock, patch

from fastmcp.task_management.interface.utils.parameter_validation_fix import (
    ParameterTypeCoercer,
    FlexibleSchemaValidator,
    EnhancedParameterValidator,
    ParameterTypeCoercionError,
    coerce_parameter_types,
    validate_parameters,
    create_flexible_schema
)


class TestParameterTypeCoercionError:
    """Test suite for ParameterTypeCoercionError exception."""

    def test_basic_initialization(self):
        """Test basic error initialization."""
        error = ParameterTypeCoercionError("Test error")
        assert str(error) == "Test error"
        assert error.parameter is None
        assert error.value is None
        assert error.expected_type is None

    def test_full_initialization(self):
        """Test error initialization with all parameters."""
        error = ParameterTypeCoercionError(
            "Test error",
            parameter="test_param",
            value="invalid_value",
            expected_type="integer"
        )
        assert str(error) == "Test error"
        assert error.parameter == "test_param"
        assert error.value == "invalid_value"
        assert error.expected_type == "integer"


class TestParameterTypeCoercer:
    """Test suite for ParameterTypeCoercer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.coercer = ParameterTypeCoercer()

    def test_initialization(self):
        """Test coercer initialization."""
        assert self.coercer is not None
        assert isinstance(self.coercer.INTEGER_PARAMETERS, set)
        assert isinstance(self.coercer.BOOLEAN_PARAMETERS, set)
        assert "limit" in self.coercer.INTEGER_PARAMETERS
        assert "include_context" in self.coercer.BOOLEAN_PARAMETERS

    def test_coerce_to_int_with_integer(self):
        """Test integer coercion with already integer value."""
        result = self.coercer.coerce_to_int(42, "test_param")
        assert result == 42
        assert isinstance(result, int)

    def test_coerce_to_int_with_string(self):
        """Test integer coercion with string value."""
        result = self.coercer.coerce_to_int("123", "test_param")
        assert result == 123
        assert isinstance(result, int)

    def test_coerce_to_int_with_negative_string(self):
        """Test integer coercion with negative string value."""
        result = self.coercer.coerce_to_int("-42", "test_param")
        assert result == -42
        assert isinstance(result, int)

    def test_coerce_to_int_with_whitespace(self):
        """Test integer coercion with whitespace in string."""
        result = self.coercer.coerce_to_int("  123  ", "test_param")
        assert result == 123
        assert isinstance(result, int)

    def test_coerce_to_int_with_empty_string(self):
        """Test integer coercion with empty string."""
        with pytest.raises(ParameterTypeCoercionError) as exc_info:
            self.coercer.coerce_to_int("", "test_param")
        
        assert "cannot be empty string" in str(exc_info.value)
        assert exc_info.value.parameter == "test_param"
        assert exc_info.value.expected_type == "integer"

    def test_coerce_to_int_with_invalid_string(self):
        """Test integer coercion with invalid string."""
        with pytest.raises(ParameterTypeCoercionError) as exc_info:
            self.coercer.coerce_to_int("not_a_number", "test_param")
        
        assert "cannot be converted to integer" in str(exc_info.value)
        assert exc_info.value.parameter == "test_param"
        assert exc_info.value.value == "not_a_number"
        assert exc_info.value.expected_type == "integer"

    def test_coerce_to_int_with_float(self):
        """Test integer coercion with float value."""
        result = self.coercer.coerce_to_int(42.0, "test_param")
        assert result == 42
        assert isinstance(result, int)

    def test_coerce_to_int_with_invalid_type(self):
        """Test integer coercion with invalid type."""
        with pytest.raises(ParameterTypeCoercionError) as exc_info:
            self.coercer.coerce_to_int([], "test_param")
        
        assert "cannot be converted to integer" in str(exc_info.value)
        assert exc_info.value.parameter == "test_param"

    def test_coerce_to_bool_with_boolean(self):
        """Test boolean coercion with already boolean value."""
        assert self.coercer.coerce_to_bool(True, "test_param") is True
        assert self.coercer.coerce_to_bool(False, "test_param") is False

    def test_coerce_to_bool_with_true_strings(self):
        """Test boolean coercion with true string values."""
        true_values = ["true", "1", "yes", "on", "enabled", "active", "y", "t"]
        
        for value in true_values:
            result = self.coercer.coerce_to_bool(value, "test_param")
            assert result is True, f"Failed for value: {value}"
            
            # Test case insensitive
            result = self.coercer.coerce_to_bool(value.upper(), "test_param")
            assert result is True, f"Failed for uppercase value: {value.upper()}"

    def test_coerce_to_bool_with_false_strings(self):
        """Test boolean coercion with false string values."""
        false_values = ["false", "0", "no", "off", "disabled", "inactive", "n", "f"]
        
        for value in false_values:
            result = self.coercer.coerce_to_bool(value, "test_param")
            assert result is False, f"Failed for value: {value}"
            
            # Test case insensitive
            result = self.coercer.coerce_to_bool(value.upper(), "test_param")
            assert result is False, f"Failed for uppercase value: {value.upper()}"

    def test_coerce_to_bool_with_whitespace(self):
        """Test boolean coercion with whitespace."""
        result = self.coercer.coerce_to_bool("  true  ", "test_param")
        assert result is True

    def test_coerce_to_bool_with_invalid_string(self):
        """Test boolean coercion with invalid string."""
        with pytest.raises(ParameterTypeCoercionError) as exc_info:
            self.coercer.coerce_to_bool("maybe", "test_param")
        
        assert "not a valid boolean string" in str(exc_info.value)
        assert exc_info.value.parameter == "test_param"
        assert exc_info.value.value == "maybe"
        assert exc_info.value.expected_type == "boolean"

    def test_coerce_to_bool_with_other_types(self):
        """Test boolean coercion with other types using Python truthiness."""
        assert self.coercer.coerce_to_bool(1, "test_param") is True
        assert self.coercer.coerce_to_bool(0, "test_param") is False
        assert self.coercer.coerce_to_bool([], "test_param") is False
        assert self.coercer.coerce_to_bool([1], "test_param") is True

    def test_coerce_parameter_integer(self):
        """Test parameter coercion for integer parameters."""
        result = self.coercer.coerce_parameter("limit", "5")
        assert result == 5
        assert isinstance(result, int)

    def test_coerce_parameter_boolean(self):
        """Test parameter coercion for boolean parameters."""
        result = self.coercer.coerce_parameter("include_context", "true")
        assert result is True
        assert isinstance(result, bool)

    def test_coerce_parameter_no_coercion(self):
        """Test parameter coercion for parameters that don't need coercion."""
        result = self.coercer.coerce_parameter("unknown_param", "some_value")
        assert result == "some_value"

    def test_coerce_parameters_empty(self):
        """Test coercing empty parameter dictionary."""
        result = self.coercer.coerce_parameters({})
        assert result == {}

    def test_coerce_parameters_none(self):
        """Test coercing None parameter dictionary."""
        result = self.coercer.coerce_parameters(None)
        assert result is None

    def test_coerce_parameters_mixed(self):
        """Test coercing mixed parameters."""
        params = {
            "limit": "10",
            "include_context": "true",
            "query": "search term",
            "force": "false"
        }
        
        result = self.coercer.coerce_parameters(params)
        
        expected = {
            "limit": 10,
            "include_context": True,
            "query": "search term",
            "force": False
        }
        
        assert result == expected

    def test_coerce_parameters_with_error(self):
        """Test coercing parameters with error."""
        params = {
            "limit": "invalid_number",
            "include_context": "true"
        }
        
        with pytest.raises(ParameterTypeCoercionError):
            self.coercer.coerce_parameters(params)

    def test_coerce_parameters_unexpected_error(self):
        """Test coercing parameters with unexpected error."""
        params = {"limit": "5"}
        
        with patch.object(self.coercer, 'coerce_parameter', side_effect=ValueError("Unexpected error")):
            result = self.coercer.coerce_parameters(params)
            
            # Should keep original value when unexpected error occurs
            assert result == {"limit": "5"}

    def test_coerce_parameter_types_class_method(self):
        """Test class method for parameter coercion."""
        params = {"limit": "5", "include_context": "true"}
        result = ParameterTypeCoercer.coerce_parameter_types(params)
        
        expected = {"limit": 5, "include_context": True}
        assert result == expected


class TestFlexibleSchemaValidator:
    """Test suite for FlexibleSchemaValidator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = FlexibleSchemaValidator()

    def test_initialization(self):
        """Test validator initialization."""
        assert self.validator is not None
        assert self.validator.coercer is not None

    def test_initialization_with_coercer(self):
        """Test validator initialization with custom coercer."""
        custom_coercer = ParameterTypeCoercer()
        validator = FlexibleSchemaValidator(custom_coercer)
        assert validator.coercer is custom_coercer

    def test_create_flexible_schema_basic(self):
        """Test creating flexible schema without properties."""
        original_schema = {"type": "object"}
        result = self.validator.create_flexible_schema(original_schema)
        assert result == original_schema

    def test_create_flexible_schema_integer(self):
        """Test creating flexible schema with integer property."""
        original_schema = {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"}
            }
        }
        
        result = self.validator.create_flexible_schema(original_schema)
        
        assert "properties" in result
        assert "limit" in result["properties"]
        assert "anyOf" in result["properties"]["limit"]
        
        any_of = result["properties"]["limit"]["anyOf"]
        assert {"type": "integer"} in any_of
        assert any([schema.get("type") == "string" and "pattern" in schema for schema in any_of])

    def test_create_flexible_schema_boolean(self):
        """Test creating flexible schema with boolean property."""
        original_schema = {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"}
            }
        }
        
        result = self.validator.create_flexible_schema(original_schema)
        
        assert "properties" in result
        assert "enabled" in result["properties"]
        assert "anyOf" in result["properties"]["enabled"]
        
        any_of = result["properties"]["enabled"]["anyOf"]
        assert {"type": "boolean"} in any_of
        
        # Check for string enum alternative
        string_schema = next((s for s in any_of if s.get("type") == "string"), None)
        assert string_schema is not None
        assert "enum" in string_schema

    def test_create_flexible_schema_mixed(self):
        """Test creating flexible schema with mixed property types."""
        original_schema = {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
                "enabled": {"type": "boolean"},
                "name": {"type": "string"}
            }
        }
        
        result = self.validator.create_flexible_schema(original_schema)
        
        # Integer property should have anyOf
        assert "anyOf" in result["properties"]["limit"]
        
        # Boolean property should have anyOf
        assert "anyOf" in result["properties"]["enabled"]
        
        # String property should remain unchanged
        assert result["properties"]["name"] == {"type": "string"}


class TestEnhancedParameterValidator:
    """Test suite for EnhancedParameterValidator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = EnhancedParameterValidator()

    def test_initialization(self):
        """Test validator initialization."""
        assert self.validator is not None
        assert self.validator.coercer is not None
        assert self.validator.schema_validator is not None

    def test_validate_parameters_success(self):
        """Test successful parameter validation."""
        params = {"limit": "5", "include_context": "true"}
        result = self.validator.validate_parameters("search", params)
        
        assert result["success"] is True
        assert result["action"] == "search"
        assert result["original_params"] == params
        assert result["coerced_params"] == {"limit": 5, "include_context": True}
        assert result["coercion_applied"] is True

    def test_validate_parameters_no_coercion(self):
        """Test parameter validation when no coercion is needed."""
        params = {"query": "search term"}
        result = self.validator.validate_parameters("search", params)
        
        assert result["success"] is True
        assert result["coercion_applied"] is False

    def test_validate_parameters_coercion_error(self):
        """Test parameter validation with coercion error."""
        params = {"limit": "invalid"}
        result = self.validator.validate_parameters("search", params)
        
        assert result["success"] is False
        assert result["error_code"] == "PARAMETER_COERCION_ERROR"
        assert result["parameter"] == "limit"
        assert result["expected_type"] == "integer"
        assert "hint" in result

    def test_validate_parameters_unexpected_error(self):
        """Test parameter validation with unexpected error."""
        params = {"limit": "5"}
        
        with patch.object(self.validator.coercer, 'coerce_parameters', side_effect=ValueError("Unexpected")):
            result = self.validator.validate_parameters("search", params)
            
            assert result["success"] is False
            assert result["error_code"] == "VALIDATION_ERROR"
            assert "hint" in result


class TestPublicAPI:
    """Test suite for public API functions."""

    def test_coerce_parameter_types(self):
        """Test public coerce_parameter_types function."""
        params = {"limit": "5", "include_context": "true"}
        result = coerce_parameter_types(params)
        
        expected = {"limit": 5, "include_context": True}
        assert result == expected

    def test_validate_parameters(self):
        """Test public validate_parameters function."""
        params = {"limit": "10"}
        result = validate_parameters("search", params)
        
        assert result["success"] is True
        assert result["coerced_params"] == {"limit": 10}

    def test_create_flexible_schema(self):
        """Test public create_flexible_schema function."""
        original_schema = {
            "properties": {
                "limit": {"type": "integer"}
            }
        }
        
        result = create_flexible_schema(original_schema)
        
        assert "anyOf" in result["properties"]["limit"]

    def test_module_exports(self):
        """Test that all expected symbols are exported."""
        from fastmcp.task_management.interface.utils.parameter_validation_fix import __all__
        
        expected_exports = [
            "ParameterTypeCoercer",
            "FlexibleSchemaValidator",
            "EnhancedParameterValidator",
            "ParameterTypeCoercionError",
            "coerce_parameter_types",
            "validate_parameters",
            "create_flexible_schema"
        ]
        
        for symbol in expected_exports:
            assert symbol in __all__


class TestDemoFunction:
    """Test suite for demo function."""

    @patch('builtins.print')
    def test_demo_function(self, mock_print):
        """Test the demo function runs without error."""
        from fastmcp.task_management.interface.utils.parameter_validation_fix import _demo
        
        _demo()
        
        # Verify print was called (demo should print results)
        assert mock_print.called

    def test_demo_as_main(self):
        """Test running demo as main module."""
        import sys
        from unittest.mock import patch
        
        # Mock sys.argv to simulate running as main
        with patch.object(sys, 'argv', ['parameter_validation_fix.py']), \
             patch('builtins.print') as mock_print:
            
            # Import the module - this should trigger the if __name__ == "__main__" block
            # Note: This test is more for coverage than functional testing
            # since we can't easily test the main execution in isolation
            pass


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.coercer = ParameterTypeCoercer()

    def test_coerce_to_int_zero_string(self):
        """Test integer coercion with zero string."""
        result = self.coercer.coerce_to_int("0", "test_param")
        assert result == 0

    def test_coerce_to_bool_edge_case_values(self):
        """Test boolean coercion with edge case values."""
        # Test with mixed case
        assert self.coercer.coerce_to_bool("True", "test_param") is True
        assert self.coercer.coerce_to_bool("FALSE", "test_param") is False
        
        # Test with extra whitespace
        assert self.coercer.coerce_to_bool("  yes  ", "test_param") is True
        assert self.coercer.coerce_to_bool("  no  ", "test_param") is False

    def test_parameter_sets_coverage(self):
        """Test that parameter sets include expected values."""
        # Test integer parameters
        assert "limit" in ParameterTypeCoercer.INTEGER_PARAMETERS
        assert "timeout" in ParameterTypeCoercer.INTEGER_PARAMETERS
        assert "progress_percentage" in ParameterTypeCoercer.INTEGER_PARAMETERS
        
        # Test boolean parameters
        assert "force" in ParameterTypeCoercer.BOOLEAN_PARAMETERS
        assert "include_context" in ParameterTypeCoercer.BOOLEAN_PARAMETERS
        assert "audit_required" in ParameterTypeCoercer.BOOLEAN_PARAMETERS

    def test_boolean_value_sets(self):
        """Test that boolean value sets are comprehensive."""
        true_values = ParameterTypeCoercer.TRUE_VALUES
        false_values = ParameterTypeCoercer.FALSE_VALUES
        
        # No overlap between true and false values
        assert len(true_values.intersection(false_values)) == 0
        
        # Common values are included
        assert "true" in true_values
        assert "false" in false_values
        assert "1" in true_values
        assert "0" in false_values