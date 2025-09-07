#!/usr/bin/env python3
"""
MCP Parameter Validator Integration

This module provides a simple integration wrapper for the parameter validation fix
that can be easily integrated into MCP controllers.
"""

import logging
from typing import Dict, Any, Optional
try:
    from .parameter_validation_fix import coerce_parameter_types, validate_parameters
except ImportError:
    # For standalone testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from parameter_validation_fix import coerce_parameter_types, validate_parameters

logger = logging.getLogger(__name__)


class MCPParameterValidator:
    """
    Simple wrapper for integrating parameter validation into MCP controllers.
    """
    
    @staticmethod
    def validate_and_coerce_mcp_parameters(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and coerce MCP parameters for a given action.
        
        This method should be called at the beginning of MCP controller methods
        to ensure parameters are properly typed before business logic processing.
        
        Args:
            action: The MCP action being performed
            params: Raw parameters from the MCP call
            
        Returns:
            Dictionary with validation result and coerced parameters
            
        Example usage in MCP controller:
            ```python
            def manage_task(self, action: str, **raw_params):
                # Validate and coerce parameters
                validation_result = MCPParameterValidator.validate_and_coerce_mcp_parameters(
                    action, raw_params
                )
                
                if not validation_result["success"]:
                    return validation_result  # Return validation error
                
                # Use coerced parameters for business logic
                coerced_params = validation_result["coerced_params"]
                limit = coerced_params.get("limit")  # Now guaranteed to be int if present
                include_context = coerced_params.get("include_context")  # Now guaranteed to be bool if present
                
                # Continue with business logic...
            ```
        """
        try:
            # Step 1: Coerce parameter types
            coerced_params = coerce_parameter_types(params)
            
            # Step 2: Validate the coerced parameters
            validation_result = validate_parameters(action, coerced_params)
            
            if validation_result["success"]:
                logger.debug(f"Parameter validation successful for action '{action}'")
                return {
                    "success": True,
                    "coerced_params": validation_result["coerced_params"],
                    "action": action,
                    "validation_notes": "Parameters validated and coerced successfully"
                }
            else:
                logger.warning(f"Parameter validation failed for action '{action}': {validation_result.get('error')}")
                return validation_result
                
        except Exception as e:
            logger.error(f"Unexpected error during parameter validation for action '{action}': {e}")
            return {
                "success": False,
                "error": f"Parameter validation error: {str(e)}",
                "error_code": "VALIDATION_ERROR",
                "action": action,
                "hint": "Please check parameter types and values"
            }
    
    @staticmethod
    def create_parameter_validation_decorator():
        """
        Create a decorator that automatically validates and coerces parameters.
        
        This can be used to decorate MCP controller methods for automatic validation.
        
        Example:
            ```python
            @MCPParameterValidator.create_parameter_validation_decorator()
            def manage_task(self, action: str, **params):
                # params are now validated and coerced
                # If validation failed, the method won't be called
                pass
            ```
        """
        def decorator(func):
            def wrapper(self, action: str, **params):
                # Validate parameters
                validation_result = MCPParameterValidator.validate_and_coerce_mcp_parameters(action, params)
                
                if not validation_result["success"]:
                    return validation_result
                
                # Call original function with coerced parameters
                return func(self, action=action, **validation_result["coerced_params"])
            
            return wrapper
        return decorator


# Quick integration functions for immediate use
def validate_mcp_parameters(action: str, **params) -> Dict[str, Any]:
    """
    Quick function to validate MCP parameters.
    
    Usage:
        result = validate_mcp_parameters("search", query="test", limit="5")
        if result["success"]:
            coerced_params = result["coerced_params"]
            # Use coerced_params...
    """
    return MCPParameterValidator.validate_and_coerce_mcp_parameters(action, params)


def coerce_mcp_parameters(**params) -> Dict[str, Any]:
    """
    Quick function to just coerce parameter types without full validation.
    
    Usage:
        coerced = coerce_mcp_parameters(limit="5", include_context="true")
        # coerced = {"limit": 5, "include_context": True}
    """
    return coerce_parameter_types(params)


# Example integration pattern for MCP controllers
def example_mcp_controller_integration():
    """
    Example showing how to integrate parameter validation into MCP controllers.
    """
    
    # Before fix - this would fail:
    # manage_task(action="search", query="test", limit="5")  # Error: '5' is not valid
    
    # After fix - this works:
    raw_params = {"query": "test", "limit": "5", "include_context": "true"}
    
    # Step 1: Validate and coerce parameters
    validation_result = validate_mcp_parameters("search", **raw_params)
    
    if validation_result["success"]:
        coerced_params = validation_result["coerced_params"]
        
        # Step 2: Use properly typed parameters in business logic
        query = coerced_params["query"]          # str
        limit = coerced_params["limit"]          # int (was "5", now 5)
        include_context = coerced_params["include_context"]  # bool (was "true", now True)
        
        print(f"✅ Parameters validated successfully:")
        print(f"   query: {query} (type: {type(query).__name__})")
        print(f"   limit: {limit} (type: {type(limit).__name__})")
        print(f"   include_context: {include_context} (type: {type(include_context).__name__})")
        
        return {"success": True, "message": "Parameters processed successfully"}
    else:
        print(f"❌ Validation failed: {validation_result['error']}")
        return validation_result


if __name__ == "__main__":
    print("🧪 Testing MCP Parameter Validator Integration")
    print("=" * 50)
    
    # Run the example
    result = example_mcp_controller_integration()
    print(f"\nResult: {result}")
    
    print("\n🎯 MCP Parameter Validator Integration Test Complete!")