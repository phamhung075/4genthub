#!/usr/bin/env python3
"""
Schema Monkey Patch for FastMCP Tools

This module provides a monkey patch for FastMCP's schema generation to handle
Union[List[str], str] types more flexibly, allowing JSON string arrays and
comma-separated strings to be accepted by MCP tools.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)


class SchemaPatcher:
    """
    Patches FastMCP's schema generation to create flexible schemas for list and boolean parameters.
    """
    
    # Parameters that should get flexible array schemas
    FLEXIBLE_ARRAY_PARAMETERS = {
        'insights_found', 'assignees', 'labels', 'tags', 'dependencies',
        'challenges_overcome', 'deliverables', 'next_recommendations',
        'skills_learned'
    }
    
    # Parameters that should get flexible boolean schemas
    FLEXIBLE_BOOLEAN_PARAMETERS = {
        'include_context', 'force', 'audit_required', 'include_details',
        'propagate_changes', 'force_refresh', 'include_inherited',
        'next_thought_needed', 'is_revision', 'needs_more_thoughts', 
        'replace_all', 'multiline'
    }
    
    @classmethod
    def patch_schema_for_flexible_parameters(cls, original_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Patch a tool schema to make array and boolean parameters more flexible.
        
        Args:
            original_schema: Original JSON schema
            
        Returns:
            Patched schema with flexible array and boolean parameters
        """
        if "properties" not in original_schema:
            return original_schema
        
        patched_schema = original_schema.copy()
        patched_properties = {}
        
        for param_name, param_schema in original_schema["properties"].items():
            if param_name in cls.FLEXIBLE_ARRAY_PARAMETERS:
                patched_properties[param_name] = cls._create_flexible_array_schema(param_name, param_schema)
            elif param_name in cls.FLEXIBLE_BOOLEAN_PARAMETERS:
                patched_properties[param_name] = cls._create_flexible_boolean_schema(param_name, param_schema)
            else:
                patched_properties[param_name] = param_schema
        
        patched_schema["properties"] = patched_properties
        return patched_schema
    
    @classmethod
    def patch_schema_for_flexible_arrays(cls, original_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy method - use patch_schema_for_flexible_parameters instead.
        """
        return cls.patch_schema_for_flexible_parameters(original_schema)
    
    @classmethod
    def _create_flexible_array_schema(cls, param_name: str, original_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a flexible schema for an array parameter.
        
        Args:
            param_name: Parameter name
            original_schema: Original parameter schema
            
        Returns:
            Flexible schema that accepts multiple formats
        """
        # Check if it's already flexible (has anyOf)
        if "anyOf" in original_schema:
            return cls._enhance_existing_union_schema(original_schema)
        
        # Extract description and other metadata
        description = original_schema.get("description", f"Array parameter for {param_name}")
        
        # Create flexible schema
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
                    "description": "JSON string representation of array (e.g., '[\"item1\", \"item2\"]')"
                }
            ],
            "description": f"{description}. Accepts array of strings or JSON string array."
        }
        
        # Preserve other properties
        for key, value in original_schema.items():
            if key not in ["type", "items", "anyOf", "description"]:
                flexible_schema[key] = value
        
        logger.debug(f"Created flexible schema for {param_name}")
        return flexible_schema
    
    @classmethod
    def _create_flexible_boolean_schema(cls, param_name: str, original_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a flexible schema for a boolean parameter.
        
        Args:
            param_name: Parameter name
            original_schema: Original parameter schema
            
        Returns:
            Flexible schema that accepts boolean strings and actual booleans
        """
        # Check if it's already flexible (has anyOf)
        if "anyOf" in original_schema:
            return cls._enhance_existing_boolean_union_schema(original_schema)
        
        # Extract description and other metadata
        description = original_schema.get("description", f"Boolean parameter for {param_name}")
        
        # Create flexible schema
        flexible_schema = {
            "anyOf": [
                # Option 1: Actual boolean
                {
                    "type": "boolean",
                    "description": "Actual boolean value"
                },
                # Option 2: String representation of boolean
                {
                    "type": "string",
                    "pattern": "^(true|false|True|False|TRUE|FALSE|1|0|yes|no|Yes|No|YES|NO|on|off|On|Off|ON|OFF|enabled?|disabled?)$",
                    "description": "String representation of boolean (e.g., 'true', 'false', 'yes', 'no', '1', '0', 'on', 'off')"
                }
            ],
            "description": f"{description}. Accepts boolean or string representation."
        }
        
        # Preserve other properties
        for key, value in original_schema.items():
            if key not in ["type", "anyOf", "description"]:
                flexible_schema[key] = value
        
        logger.debug(f"Created flexible boolean schema for {param_name}")
        return flexible_schema
    
    @classmethod
    def _enhance_existing_union_schema(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an existing Union schema to be more flexible.
        """
        any_of = schema.get("anyOf", [])
        
        # Check if we already have the flexibility we need
        has_array = any(option.get("type") == "array" for option in any_of)
        has_string = any(option.get("type") == "string" for option in any_of)
        
        if has_array and has_string:
            return schema
        
        enhanced_any_of = list(any_of)
        
        if not has_array:
            enhanced_any_of.append({
                "type": "array",
                "items": {"type": "string"},
                "description": "Array of strings"
            })
        
        if not has_string:
            enhanced_any_of.append({
                "type": "string",
                "description": "String representation (JSON array or comma-separated)"
            })
        
        enhanced_schema = schema.copy()
        enhanced_schema["anyOf"] = enhanced_any_of
        
        return enhanced_schema
    
    @classmethod
    def _enhance_existing_boolean_union_schema(cls, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance an existing Union schema for boolean parameters to be more flexible.
        """
        any_of = schema.get("anyOf", [])
        
        # Check if we already have the flexibility we need
        has_boolean = any(option.get("type") == "boolean" for option in any_of)
        has_string = any(option.get("type") == "string" for option in any_of)
        
        if has_boolean and has_string:
            return schema
        
        enhanced_any_of = list(any_of)
        
        if not has_boolean:
            enhanced_any_of.append({
                "type": "boolean",
                "description": "Actual boolean value"
            })
        
        if not has_string:
            enhanced_any_of.append({
                "type": "string",
                "pattern": "^(true|false|True|False|TRUE|FALSE|1|0|yes|no|Yes|No|YES|NO|on|off|On|Off|ON|OFF|enabled?|disabled?)$",
                "description": "String representation of boolean"
            })
        
        enhanced_schema = schema.copy()
        enhanced_schema["anyOf"] = enhanced_any_of
        
        return enhanced_schema


def patch_parsed_function_from_function():
    """
    Monkey patch the ParsedFunction.from_function method to create flexible schemas.
    """
    from fastmcp.tools.tool import ParsedFunction
    
    # Store the original method
    original_from_function = ParsedFunction.from_function
    
    @classmethod
    @wraps(original_from_function)
    def patched_from_function(cls, fn, exclude_args=None, validate=True):
        """Patched version that creates flexible schemas."""
        # Call the original method
        parsed_function = original_from_function(fn, exclude_args, validate)
        
        # Patch the schema to make array and boolean parameters flexible
        original_parameters = parsed_function.parameters
        patched_parameters = SchemaPatcher.patch_schema_for_flexible_parameters(original_parameters)
        
        # Update the parameters
        parsed_function.parameters = patched_parameters
        
        logger.debug(f"Patched schema for function {parsed_function.name}")
        return parsed_function
    
    # Apply the monkey patch
    ParsedFunction.from_function = patched_from_function
    logger.info("Applied schema monkey patch for flexible array parameters")


def patch_function_tool_from_function():
    """
    Monkey patch the FunctionTool.from_function method to create flexible schemas.
    """
    from fastmcp.tools.tool import FunctionTool
    
    # Store the original method
    original_from_function = FunctionTool.from_function
    
    @classmethod
    @wraps(original_from_function)
    def patched_from_function(cls, fn, name=None, description=None, tags=None, 
                             annotations=None, exclude_args=None, serializer=None, enabled=None):
        """Patched version that creates flexible schemas."""
        # Call the original method
        function_tool = original_from_function(
            fn=fn, name=name, description=description, tags=tags,
            annotations=annotations, exclude_args=exclude_args, 
            serializer=serializer, enabled=enabled
        )
        
        # Patch the schema to make array and boolean parameters flexible
        original_parameters = function_tool.parameters
        patched_parameters = SchemaPatcher.patch_schema_for_flexible_parameters(original_parameters)
        
        # Update the parameters
        function_tool.parameters = patched_parameters
        
        logger.debug(f"Patched schema for tool {function_tool.name}")
        return function_tool
    
    # Apply the monkey patch
    FunctionTool.from_function = patched_from_function
    logger.info("Applied schema monkey patch for FunctionTool.from_function")


def apply_all_schema_patches():
    """
    Apply all schema monkey patches to FastMCP.
    
    This should be called before registering any tools that need flexible array or boolean parameters.
    """
    logger.info("Applying FastMCP schema monkey patches for flexible array and boolean parameters")
    
    try:
        patch_parsed_function_from_function()
        patch_function_tool_from_function()
        logger.info("✅ Schema monkey patches applied successfully")
    except Exception as e:
        logger.error(f"❌ Failed to apply schema monkey patches: {e}")
        raise


def test_schema_patching():
    """Test the schema patching functionality."""
    # Test schema patching
    original_schema = {
        "type": "object",
        "properties": {
            "insights_found": {
                "anyOf": [
                    {"type": "array", "items": {"type": "string"}},
                    {"type": "string"}
                ],
                "description": "Insights discovered"
            },
            "normal_param": {
                "type": "string",
                "description": "Normal parameter"
            }
        }
    }
    
    patched_schema = SchemaPatcher.patch_schema_for_flexible_arrays(original_schema)
    
    print("Original Schema:")
    print(json.dumps(original_schema, indent=2))
    
    print("\nPatched Schema:")
    print(json.dumps(patched_schema, indent=2))


if __name__ == "__main__":
    test_schema_patching()