"""
JSON Parameter Mixin for MCP Controllers

This mixin provides automatic JSON string parsing for dictionary parameters
across all MCP controllers, ensuring consistent behavior and better developer experience.
"""

import logging
from typing import Dict, Any, Optional, Union, List

from .json_parameter_parser import JSONParameterParser, get_dict_parameters_for_tool
from .response_formatter import StandardResponseFormatter

logger = logging.getLogger(__name__)


class JSONParameterMixin:
    """
    Mixin class to add JSON parameter parsing capabilities to MCP controllers.
    
    This mixin automatically detects and parses JSON strings for dictionary parameters,
    providing a consistent interface across all MCP tools.
    """
    
    def parse_json_parameters(
        self,
        parameters: Dict[str, Any],
        tool_name: Optional[str] = None,
        custom_dict_params: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Parse JSON string parameters to dictionaries for a tool.
        
        Args:
            parameters: Dictionary of all parameters from the tool call
            tool_name: Name of the tool (used to get tool-specific dict params)
            custom_dict_params: Optional list of custom dict parameter names
            
        Returns:
            Updated parameters dictionary with parsed JSON values
            
        Raises:
            ValueError: If JSON parsing fails
        """
        # Get dictionary parameter names
        if custom_dict_params:
            dict_param_names = custom_dict_params
        elif tool_name:
            dict_param_names = get_dict_parameters_for_tool(tool_name)
        else:
            # Default common dictionary parameters
            dict_param_names = ['data', 'metadata', 'config', 'filters']
        
        # Parse the parameters
        try:
            return JSONParameterParser.parse_multiple_dict_parameters(
                parameters, dict_param_names
            )
        except ValueError as e:
            logger.warning(f"JSON parameter parsing failed: {e}")
            raise
    
    def create_json_error_response(
        self,
        error: Exception,
        operation: str,
        tool_name: str = "manage_tool"
    ) -> Dict[str, Any]:
        """
        Create a standardized error response for JSON parsing failures.
        
        Args:
            error: The exception that occurred
            operation: The operation being performed
            tool_name: Name of the tool for context
            
        Returns:
            Standardized error response with helpful examples
        """
        error_str = str(error)
        
        # Extract parameter name from error message if possible
        param_name = "parameter"
        if "'" in error_str:
            parts = error_str.split("'")
            if len(parts) >= 2:
                param_name = parts[1]
        
        # Create error metadata with helpful examples
        error_metadata = JSONParameterParser.create_error_response(
            param_name, error_str, tool_name
        )
        
        # Use StandardResponseFormatter for consistent error format
        return StandardResponseFormatter.create_error_response(
            operation=operation,
            error=error_str,
            error_code="INVALID_PARAMETER_FORMAT",
            metadata=error_metadata
        )
    
    def safe_parse_dict_parameter(
        self,
        param_value: Optional[Union[str, Dict[str, Any]]],
        param_name: str,
        default: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Safely parse a single dictionary parameter with fallback.
        
        Args:
            param_value: The parameter value to parse
            param_name: Name of the parameter
            default: Default value if parsing fails
            
        Returns:
            Parsed dictionary or default value
        """
        if param_value is None:
            return default
        
        try:
            return JSONParameterParser.parse_dict_parameter(param_value, param_name)
        except ValueError as e:
            logger.warning(f"Failed to parse {param_name}, using default: {e}")
            return default