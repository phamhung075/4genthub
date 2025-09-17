#!/usr/bin/env python3
"""
Parameter Validation Fix - Parameter Type Coercion System

This module provides comprehensive parameter type coercion for MCP tools,
automatically converting string parameters to appropriate types (int, bool)
to fix validation issues like: "'5' is not valid under any of the given schemas"

Main Features:
- Automatic string-to-int coercion for numeric parameters
- Flexible boolean string parsing ("true", "false", "1", "0", etc.)
- Comprehensive error handling with helpful messages
- Backward compatibility with existing parameter types
- Minimal performance overhead

Usage:
    from fastmcp.task_management.interface.utils.parameter_validation_fix import coerce_parameter_types
    
    # Coerce parameters before validation
    coerced_params = coerce_parameter_types({"limit": "5", "include_context": "true"})
    # Result: {"limit": 5, "include_context": True}
"""

import re
from typing import Dict, Any, Union, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class ParameterTypeCoercionError(Exception):
    """Raised when parameter type coercion fails"""
    
    def __init__(self, message: str, parameter: str = None, value: Any = None, expected_type: str = None):
        super().__init__(message)
        self.parameter = parameter
        self.value = value
        self.expected_type = expected_type


class ParameterTypeCoercer:
    """
    Main class for parameter type coercion.
    Handles conversion of string parameters to appropriate types.
    """
    
    # Parameters that should be coerced to integers
    INTEGER_PARAMETERS: Set[str] = {
        "limit", "progress_percentage", "timeout", "port", "offset", 
        "head_limit", "max_results", "page_size", "retry_count",
        "depth", "max_depth", "count", "size", "length"
    }
    
    # Parameters that should be coerced to booleans
    BOOLEAN_PARAMETERS: Set[str] = {
        "include_context", "force", "audit_required", "include_details", 
        "propagate_changes", "include_inherited", "force_refresh",
        "recursive", "enabled", "active", "visible", "public",
        "strict", "validate", "auto_create", "cascade"
    }
    
    # Boolean string mappings
    TRUE_VALUES: Set[str] = {
        "true", "1", "yes", "on", "enabled", "active", "y", "t"
    }
    
    FALSE_VALUES: Set[str] = {
        "false", "0", "no", "off", "disabled", "inactive", "n", "f"
    }
    
    def __init__(self):
        """Initialize the parameter type coercer"""
        pass
    
    def coerce_to_int(self, value: Any, parameter_name: str) -> int:
        """
        Coerce a value to integer with comprehensive error handling.
        
        Args:
            value: The value to coerce
            parameter_name: Name of the parameter (for error messages)
            
        Returns:
            int: The coerced integer value
            
        Raises:
            ParameterTypeCoercionError: If coercion fails
        """
        if isinstance(value, int):
            return value
        
        if isinstance(value, str):
            # Remove whitespace
            value = value.strip()
            
            if value == "":
                raise ParameterTypeCoercionError(
                    f"Parameter '{parameter_name}' cannot be empty string when expecting integer",
                    parameter=parameter_name,
                    value=value,
                    expected_type="integer"
                )
            
            try:
                return int(value)
            except ValueError:
                raise ParameterTypeCoercionError(
                    f"Parameter '{parameter_name}' value '{value}' cannot be converted to integer",
                    parameter=parameter_name,
                    value=value,
                    expected_type="integer"
                )
        
        # For other types, try direct conversion
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ParameterTypeCoercionError(
                f"Parameter '{parameter_name}' value '{value}' (type: {type(value).__name__}) cannot be converted to integer",
                parameter=parameter_name,
                value=value,
                expected_type="integer"
            )
    
    def coerce_to_bool(self, value: Any, parameter_name: str) -> bool:
        """
        Coerce a value to boolean with flexible string parsing.
        
        Args:
            value: The value to coerce
            parameter_name: Name of the parameter (for error messages)
            
        Returns:
            bool: The coerced boolean value
            
        Raises:
            ParameterTypeCoercionError: If coercion fails
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            # Normalize to lowercase for comparison
            normalized = value.lower().strip()
            
            if normalized in self.TRUE_VALUES:
                return True
            elif normalized in self.FALSE_VALUES:
                return False
            else:
                valid_values = sorted(self.TRUE_VALUES | self.FALSE_VALUES)
                raise ParameterTypeCoercionError(
                    f"Parameter '{parameter_name}' value '{value}' is not a valid boolean string. "
                    f"Valid values: {', '.join(valid_values)}",
                    parameter=parameter_name,
                    value=value,
                    expected_type="boolean"
                )
        
        # For other types, use Python's truthiness
        return bool(value)
    
    def coerce_parameter(self, key: str, value: Any) -> Any:
        """
        Coerce a single parameter based on its name and value.
        
        Args:
            key: Parameter name
            value: Parameter value
            
        Returns:
            Any: The coerced value
        """
        # Skip coercion for None values
        if value is None:
            return value
            
        if key in self.INTEGER_PARAMETERS:
            return self.coerce_to_int(value, key)
        elif key in self.BOOLEAN_PARAMETERS:
            return self.coerce_to_bool(value, key)
        else:
            # No coercion needed, return as-is
            return value
    
    @classmethod
    def coerce_parameter_types(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerce parameter types using a new instance.
        
        Args:
            params: Dictionary of parameters to coerce
            
        Returns:
            Dict[str, Any]: Dictionary with coerced parameters
        """
        instance = cls()
        return instance.coerce_parameters(params)
    
    def coerce_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coerce all parameters in a dictionary.
        
        Args:
            params: Dictionary of parameters to coerce
            
        Returns:
            Dict[str, Any]: Dictionary with coerced parameters
        """
        if not params:
            return params
        
        coerced = {}
        
        for key, value in params.items():
            try:
                coerced[key] = self.coerce_parameter(key, value)
            except ParameterTypeCoercionError:
                # Re-raise coercion errors as-is
                raise
            except Exception as e:
                # Wrap unexpected errors
                logger.warning(f"Unexpected error coercing parameter '{key}': {e}")
                coerced[key] = value  # Keep original value if coercion fails unexpectedly
        
        return coerced


class FlexibleSchemaValidator:
    """
    Validates parameters against flexible schemas that accept both original types
    and string representations.
    """
    
    def __init__(self, coercer: ParameterTypeCoercer = None):
        """Initialize with optional coercer instance"""
        self.coercer = coercer or ParameterTypeCoercer()
    
    def create_flexible_schema(self, original_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a flexible version of a schema that accepts string representations
        of integers and booleans.
        
        Args:
            original_schema: The original JSON schema
            
        Returns:
            Dict[str, Any]: Flexible schema with string alternatives
        """
        # This is a simplified implementation
        # In a full implementation, you would recursively process the schema
        flexible_schema = original_schema.copy()
        
        # Add string alternatives for integer and boolean types
        if "properties" in flexible_schema:
            for prop_name, prop_schema in flexible_schema["properties"].items():
                if prop_schema.get("type") == "integer":
                    # Allow string representations of integers
                    flexible_schema["properties"][prop_name] = {
                        "anyOf": [
                            {"type": "integer"},
                            {"type": "string", "pattern": r"^-?\d+$"}
                        ]
                    }
                elif prop_schema.get("type") == "boolean":
                    # Allow string representations of booleans
                    flexible_schema["properties"][prop_name] = {
                        "anyOf": [
                            {"type": "boolean"},
                            {"type": "string", "enum": list(self.coercer.TRUE_VALUES | self.coercer.FALSE_VALUES)}
                        ]
                    }
        
        return flexible_schema


class EnhancedParameterValidator:
    """
    Complete parameter validation pipeline with coercion and validation.
    """
    
    def __init__(self):
        """Initialize the enhanced validator"""
        self.coercer = ParameterTypeCoercer()
        self.schema_validator = FlexibleSchemaValidator(self.coercer)
    
    def validate_parameters(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete parameter validation with coercion.
        
        Args:
            action: The action being performed
            params: Parameters to validate
            
        Returns:
            Dict[str, Any]: Validation result with coerced parameters
        """
        try:
            # Step 1: Coerce parameters
            coerced_params = self.coercer.coerce_parameters(params)
            
            # Step 2: Basic validation (could be extended with actual schema validation)
            validation_result = {
                "success": True,
                "action": action,
                "original_params": params,
                "coerced_params": coerced_params,
                "coercion_applied": coerced_params != params
            }
            
            return validation_result
            
        except ParameterTypeCoercionError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "PARAMETER_COERCION_ERROR",
                "parameter": e.parameter,
                "provided_value": str(e.value),
                "expected_type": e.expected_type,
                "hint": "Check parameter format. Numeric parameters can be provided as strings or integers."
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Validation error: {str(e)}",
                "error_code": "VALIDATION_ERROR",
                "hint": "Please check your parameters and try again."
            }


# Global instances for convenient access
_default_coercer = ParameterTypeCoercer()
_default_validator = EnhancedParameterValidator()


# Public API functions
def coerce_parameter_types(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coerce parameter types using the default coercer.
    
    Args:
        params: Dictionary of parameters to coerce
        
    Returns:
        Dict[str, Any]: Dictionary with coerced parameters
        
    Example:
        >>> coerce_parameter_types({"limit": "5", "include_context": "true"})
        {"limit": 5, "include_context": True}
    """
    return _default_coercer.coerce_parameters(params)


def validate_parameters(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate parameters with automatic coercion.
    
    Args:
        action: The action being performed
        params: Parameters to validate
        
    Returns:
        Dict[str, Any]: Validation result
        
    Example:
        >>> result = validate_parameters("search", {"limit": "5"})
        >>> if result["success"]:
        ...     coerced_params = result["coerced_params"]
    """
    return _default_validator.validate_parameters(action, params)


def create_flexible_schema(original_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a flexible schema that accepts string representations.
    
    Args:
        original_schema: The original JSON schema
        
    Returns:
        Dict[str, Any]: Flexible schema
    """
    return _default_validator.schema_validator.create_flexible_schema(original_schema)


# Export the main classes for advanced usage
__all__ = [
    "ParameterTypeCoercer",
    "FlexibleSchemaValidator", 
    "EnhancedParameterValidator",
    "ParameterTypeCoercionError",
    "coerce_parameter_types",
    "validate_parameters",
    "create_flexible_schema"
]


# Demo/testing function
def _demo():
    """Demonstrate the parameter validation fix functionality"""
    print("Parameter Validation Fix Demo")
    print("=" * 40)
    
    # Test cases that previously failed
    test_cases = [
        {"limit": "5", "include_context": "true"},
        {"progress_percentage": "50", "force": "false"},
        {"timeout": "30", "audit_required": "1"},
        {"offset": "0", "enabled": "yes"}
    ]
    
    for i, params in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"  Original: {params}")
        try:
            coerced = coerce_parameter_types(params)
            print(f"  Coerced:  {coerced}")
        except Exception as e:
            print(f"  Error:    {e}")
    
    print("\n" + "=" * 40)
    print("Demo completed!")


if __name__ == "__main__":
    _demo()