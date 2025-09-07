"""
JSON Parameter Parser Utility

This utility provides automatic JSON string detection and parsing for dictionary parameters
in MCP controllers. It handles various input formats to provide a better developer experience.
"""

import json
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class JSONParameterParser:
    """
    Utility class for parsing JSON strings to dictionary objects for MCP parameters.
    
    This parser provides automatic detection and conversion of JSON strings to dictionaries,
    enabling MCP tools to accept both dictionary objects and JSON string representations.
    """
    
    @staticmethod
    def parse_dict_parameter(
        param_value: Optional[Union[str, Dict[str, Any]]],
        param_name: str = "parameter"
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a parameter that should be a dictionary but might be a JSON string.
        
        Args:
            param_value: The parameter value (either dict or JSON string)
            param_name: Name of the parameter for error messages
            
        Returns:
            Parsed dictionary or None if param_value is None
            
        Raises:
            ValueError: If the parameter cannot be parsed as a valid dictionary
        """
        if param_value is None:
            return None
            
        if isinstance(param_value, dict):
            return param_value
            
        if isinstance(param_value, str):
            try:
                # Try to parse as JSON
                parsed = json.loads(param_value)
                if not isinstance(parsed, dict):
                    raise ValueError(
                        f"Parameter '{param_name}' JSON must be an object, not {type(parsed).__name__}"
                    )
                return parsed
            except json.JSONDecodeError as e:
                # Provide helpful error message with examples
                raise ValueError(
                    f"Invalid JSON string in '{param_name}' parameter: {str(e)}. "
                    f"Valid formats: {param_name}={{'key': 'value'}} or "
                    f"{param_name}='{json.dumps({'key': 'value'})}'"
                )
        else:
            raise ValueError(
                f"Parameter '{param_name}' must be a dictionary object or JSON string, "
                f"not {type(param_value).__name__}"
            )
    
    @staticmethod
    def parse_multiple_dict_parameters(
        parameters: Dict[str, Any],
        dict_param_names: list[str]
    ) -> Dict[str, Any]:
        """
        Parse multiple dictionary parameters in a parameter set.
        
        Args:
            parameters: Dictionary of all parameters
            dict_param_names: List of parameter names that should be dictionaries
            
        Returns:
            Updated parameters dictionary with parsed values
        """
        parsed_params = parameters.copy()
        
        for param_name in dict_param_names:
            if param_name in parsed_params and parsed_params[param_name] is not None:
                try:
                    parsed_params[param_name] = JSONParameterParser.parse_dict_parameter(
                        parsed_params[param_name],
                        param_name
                    )
                except ValueError as e:
                    logger.warning(f"Failed to parse {param_name}: {e}")
                    # Re-raise with enhanced error message
                    raise ValueError(str(e))
        
        return parsed_params
    
    @staticmethod
    def create_error_response(
        param_name: str,
        error_message: str,
        tool_name: str = "manage_tool"
    ) -> Dict[str, Any]:
        """
        Create a standardized error response for JSON parsing failures.
        
        Args:
            param_name: Name of the parameter that failed
            error_message: The error message
            tool_name: Name of the tool for context
            
        Returns:
            Standardized error response with examples
        """
        return {
            "error": error_message,
            "error_code": "INVALID_PARAMETER_FORMAT",
            "parameter": param_name,
            "suggestions": [
                f"Use a dictionary object: {param_name}={{'key': 'value', 'nested': {{'item': 123}}}}",
                f"Or use a JSON string: {param_name}='{json.dumps({'key': 'value', 'nested': {'item': 123}})}'",
                f"Ensure JSON is valid using a JSON validator"
            ],
            "examples": {
                "dictionary_format": f"{tool_name}(action='create', {param_name}={{'title': 'My Title', 'data': {{'key': 'value'}}}})",
                "json_string_format": f"{tool_name}(action='create', {param_name}='{json.dumps({'title': 'My Title', 'data': {'key': 'value'}})}')"
            }
        }


# Define common dictionary parameters across MCP tools
COMMON_DICT_PARAMETERS = [
    # Context management
    'data',
    'delegate_data',
    'filters',
    'data_metadata',
    
    # Connection management
    'client_info',
    
    # Dependency management
    'dependency_data',
    
    # Agent management
    'agent_config',
    'agent_metadata',
    
    # Rule management
    'rule_data',
    'rule_config',
    
    # Generic
    'metadata',
    'config',
    'settings',
    'options',
    'params',
    'context',
    'payload'
]


def get_dict_parameters_for_tool(tool_name: str) -> list[str]:
    """
    Get the list of dictionary parameters for a specific tool.
    
    Args:
        tool_name: Name of the MCP tool
        
    Returns:
        List of parameter names that should be parsed as dictionaries
    """
    # Tool-specific dictionary parameters
    tool_specific = {
        'manage_context': ['data', 'delegate_data', 'filters', 'data_metadata'],
        'manage_connection': ['client_info'],
        'manage_dependency': ['dependency_data'],
        'manage_agent': ['agent_config', 'agent_metadata'],
        'manage_rule': ['rule_data', 'rule_config'],
        # Add more tools as needed
    }
    
    # Return tool-specific params or common ones
    return tool_specific.get(tool_name, ['data', 'metadata', 'config'])