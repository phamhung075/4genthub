#!/usr/bin/env python3
"""
Flexible Schema Generator for MCP Tools

This module provides custom schema generation for MCP tools that need to accept
multiple parameter formats (e.g., arrays as JSON strings, comma-separated strings, etc.).
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union, get_origin, get_args
from pydantic import Field

logger = logging.getLogger(__name__)


class FlexibleSchemaGenerator:
    """
    Generates flexible JSON schemas for MCP tools that accept multiple parameter formats.
    
    This class modifies the standard JSON schema generation to create "anyOf" schemas
    for Union types that include List[str] and str, allowing the MCP framework to
    accept arrays in multiple formats:
    - Direct arrays: ["item1", "item2"]
    - JSON string arrays: '["item1", "item2"]'
    - Comma-separated strings: "item1, item2"
    """
    
    # Parameters that should get flexible array schemas
    FLEXIBLE_ARRAY_PARAMETERS = {
        'insights_found', 'assignees', 'labels', 'tags', 'dependencies',
        'challenges_overcome', 'deliverables', 'next_recommendations',
        'skills_learned'
    }
    
    @classmethod
    def create_flexible_schema_for_parameter(cls, param_name: str, original_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a flexible schema for a parameter that should accept multiple formats.
        
        Args:
            param_name: Name of the parameter
            original_schema: Original JSON schema for the parameter
            
        Returns:
            Flexible schema that accepts multiple formats
        """
        if param_name not in cls.FLEXIBLE_ARRAY_PARAMETERS:
            return original_schema
        
        # Check if this is already a Union/anyOf schema
        if "anyOf" in original_schema:
            return cls._enhance_existing_union_schema(original_schema)
        
        # Create a new flexible schema
        return cls._create_flexible_array_schema(param_name, original_schema)
    
    @classmethod
    def _create_flexible_array_schema(cls, param_name: str, original_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a flexible array schema that accepts multiple input formats.
        
        Args:
            param_name: Parameter name
            original_schema: Original schema
            
        Returns:
            Flexible schema with anyOf structure
        """
        # Extract description and other metadata
        description = original_schema.get("description", f"Array parameter for {param_name}")
        
        # Define the flexible schema
        flexible_schema = {
            "anyOf": [
                # Option 1: Direct array of strings
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of strings"
                },
                # Option 2: JSON string representation of array
                {
                    "type": "string",
                    "description": "JSON string representation of array (e.g., '[\"item1\", \"item2\"]')",
                    "pattern": r"^\s*\[.*\]\s*$"  # Must look like JSON array
                },
                # Option 3: Comma-separated string
                {
                    "type": "string",
                    "description": "Comma-separated string (e.g., 'item1, item2, item3')",
                    "pattern": r"^[^[\]]*$"  # Must NOT look like JSON array
                },
                # Option 4: Single string value
                {
                    "type": "string",
                    "description": "Single string value (will be converted to single-item array)"
                }
            ],
            "description": f"{description}. Accepts: array of strings, JSON string array, comma-separated string, or single string."
        }
        
        # Preserve other properties from original schema
        for key, value in original_schema.items():
            if key not in ["type", "items", "anyOf", "description"]:
                flexible_schema[key] = value
        
        return flexible_schema
    
    @classmethod
    def _enhance_existing_union_schema(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an existing Union schema to be more flexible.
        
        Args:
            schema: Existing schema with anyOf
            
        Returns:
            Enhanced schema
        """
        # If it already has anyOf, check if we need to add more options
        any_of = schema.get("anyOf", [])
        
        # Check if we already have the flexibility we need
        has_array = any(option.get("type") == "array" for option in any_of)
        has_string = any(option.get("type") == "string" for option in any_of)
        
        if has_array and has_string:
            # Already flexible enough
            return schema
        
        # Add missing options
        enhanced_any_of = list(any_of)
        
        if not has_array:
            enhanced_any_of.append({
                "type": "array",
                "items": {"type": "string"},
                "description": "Array of strings"
            })
        
        if not has_string:
            enhanced_any_of.extend([
                {
                    "type": "string",
                    "description": "JSON string representation of array or comma-separated string"
                }
            ])
        
        enhanced_schema = schema.copy()
        enhanced_schema["anyOf"] = enhanced_any_of
        
        return enhanced_schema
    
    @classmethod
    def apply_flexible_schemas_to_tool_schema(cls, tool_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply flexible schemas to all appropriate parameters in a tool schema.
        
        Args:
            tool_schema: Complete tool schema
            
        Returns:
            Tool schema with flexible parameters
        """
        if "properties" not in tool_schema:
            return tool_schema
        
        enhanced_schema = tool_schema.copy()
        enhanced_properties = {}
        
        for param_name, param_schema in tool_schema["properties"].items():
            if param_name in cls.FLEXIBLE_ARRAY_PARAMETERS:
                enhanced_properties[param_name] = cls.create_flexible_schema_for_parameter(
                    param_name, param_schema
                )
            else:
                enhanced_properties[param_name] = param_schema
        
        enhanced_schema["properties"] = enhanced_properties
        return enhanced_schema


class FlexibleToolDecorator:
    """
    Decorator that can be applied to FastMCP tools to make their schemas more flexible.
    """
    
    @staticmethod
    def enhance_tool_schema(tool_instance):
        """
        Enhance a tool instance with flexible schemas.
        
        Args:
            tool_instance: FastMCP tool instance
            
        Returns:
            Enhanced tool instance
        """
        if hasattr(tool_instance, 'parameters'):
            original_schema = tool_instance.parameters
            flexible_schema = FlexibleSchemaGenerator.apply_flexible_schemas_to_tool_schema(original_schema)
            tool_instance.parameters = flexible_schema
            
            logger.info(f"Enhanced tool schema for {getattr(tool_instance, 'name', 'unknown tool')} with flexible parameter support")
        
        return tool_instance


def create_flexible_mcp_tool_decorator():
    """
    Create a decorator for FastMCP tools that automatically applies flexible schemas.
    
    Usage:
        @create_flexible_mcp_tool_decorator()
        @mcp.tool(name="my_tool")
        def my_tool(param: Union[List[str], str] = None):
            pass
    """
    def decorator(tool_func):
        def wrapper(*args, **kwargs):
            # Call the original tool function
            result = tool_func(*args, **kwargs)
            
            # If this returns a tool instance, enhance its schema
            if hasattr(result, 'parameters'):
                return FlexibleToolDecorator.enhance_tool_schema(result)
            
            return result
        
        return wrapper
    
    return decorator


# Testing function
def test_flexible_schema_generation():
    """Test the flexible schema generation."""
    generator = FlexibleSchemaGenerator()
    
    # Test original schema for insights_found
    original_schema = {
        "type": "string",
        "description": "Insights discovered during work"
    }
    
    # Generate flexible schema
    flexible_schema = generator.create_flexible_schema_for_parameter("insights_found", original_schema)
    
    print("Original Schema:")
    print(json.dumps(original_schema, indent=2))
    
    print("\nFlexible Schema:")
    print(json.dumps(flexible_schema, indent=2))
    
    # Test with Union schema
    union_schema = {
        "anyOf": [
            {"type": "array", "items": {"type": "string"}},
            {"type": "string"}
        ],
        "description": "Union of array and string"
    }
    
    enhanced_union = generator._enhance_existing_union_schema(union_schema)
    
    print("\nEnhanced Union Schema:")
    print(json.dumps(enhanced_union, indent=2))


if __name__ == "__main__":
    test_flexible_schema_generation()