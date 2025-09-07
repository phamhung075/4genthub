"""
Unit tests for JSON Parameter Parser utility.

Tests the automatic JSON string detection and parsing for dictionary parameters
in MCP controllers.
"""

import pytest
import json
from fastmcp.task_management.interface.utils.json_parameter_parser import (
    JSONParameterParser,
    get_dict_parameters_for_tool
)


class TestJSONParameterParser:
    """Test cases for JSONParameterParser utility."""
    
    def test_parse_dict_parameter_with_dict(self):
        """Test parsing when parameter is already a dictionary."""
        input_dict = {"key": "value", "nested": {"item": 123}}
        result = JSONParameterParser.parse_dict_parameter(input_dict, "test_param")
        assert result == input_dict
    
    def test_parse_dict_parameter_with_json_string(self):
        """Test parsing when parameter is a valid JSON string."""
        input_dict = {"key": "value", "nested": {"item": 123}}
        json_string = json.dumps(input_dict)
        result = JSONParameterParser.parse_dict_parameter(json_string, "test_param")
        assert result == input_dict
    
    def test_parse_dict_parameter_with_none(self):
        """Test parsing when parameter is None."""
        result = JSONParameterParser.parse_dict_parameter(None, "test_param")
        assert result is None
    
    def test_parse_dict_parameter_with_invalid_json(self):
        """Test parsing when parameter is an invalid JSON string."""
        with pytest.raises(ValueError) as exc_info:
            JSONParameterParser.parse_dict_parameter(
                "{invalid json", "test_param"
            )
        assert "Invalid JSON string" in str(exc_info.value)
        assert "test_param" in str(exc_info.value)
    
    def test_parse_dict_parameter_with_non_dict_json(self):
        """Test parsing when JSON string is not an object."""
        with pytest.raises(ValueError) as exc_info:
            JSONParameterParser.parse_dict_parameter(
                '["list", "not", "dict"]', "test_param"
            )
        assert "JSON must be an object, not list" in str(exc_info.value)
    
    def test_parse_dict_parameter_with_invalid_type(self):
        """Test parsing when parameter is neither dict nor string."""
        with pytest.raises(ValueError) as exc_info:
            JSONParameterParser.parse_dict_parameter(
                12345, "test_param"
            )
        assert "must be a dictionary object or JSON string, not int" in str(exc_info.value)
    
    def test_parse_multiple_dict_parameters(self):
        """Test parsing multiple dictionary parameters at once."""
        parameters = {
            "data": '{"title": "Test"}',
            "delegate_data": {"key": "value"},
            "filters": '{"status": "active"}',
            "other_param": "not a dict"
        }
        dict_param_names = ["data", "delegate_data", "filters"]
        
        result = JSONParameterParser.parse_multiple_dict_parameters(
            parameters, dict_param_names
        )
        
        assert result["data"] == {"title": "Test"}
        assert result["delegate_data"] == {"key": "value"}
        assert result["filters"] == {"status": "active"}
        assert result["other_param"] == "not a dict"
    
    def test_parse_multiple_dict_parameters_with_error(self):
        """Test parsing multiple parameters when one fails."""
        parameters = {
            "data": '{"valid": "json"}',
            "delegate_data": '{invalid json}'
        }
        dict_param_names = ["data", "delegate_data"]
        
        with pytest.raises(ValueError) as exc_info:
            JSONParameterParser.parse_multiple_dict_parameters(
                parameters, dict_param_names
            )
        assert "delegate_data" in str(exc_info.value)
    
    def test_create_error_response(self):
        """Test error response creation with helpful examples."""
        response = JSONParameterParser.create_error_response(
            "delegate_data",
            "Invalid JSON string",
            "manage_context"
        )
        
        assert response["error"] == "Invalid JSON string"
        assert response["error_code"] == "INVALID_PARAMETER_FORMAT"
        assert response["parameter"] == "delegate_data"
        assert len(response["suggestions"]) > 0
        assert "dictionary_format" in response["examples"]
        assert "json_string_format" in response["examples"]
        assert "manage_context" in response["examples"]["dictionary_format"]
    
    def test_get_dict_parameters_for_tool(self):
        """Test getting dictionary parameter names for specific tools."""
        # Test known tool
        params = get_dict_parameters_for_tool("manage_context")
        assert "data" in params
        assert "delegate_data" in params
        assert "filters" in params
        
        # Test unknown tool (should return defaults)
        params = get_dict_parameters_for_tool("unknown_tool")
        assert "data" in params
        assert "metadata" in params
        assert "config" in params
    
    def test_complex_nested_json_string(self):
        """Test parsing complex nested JSON structures."""
        complex_data = {
            "title": "Test",
            "metadata": {
                "tags": ["tag1", "tag2"],
                "settings": {
                    "enabled": True,
                    "count": 42
                }
            },
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"}
            ]
        }
        json_string = json.dumps(complex_data)
        
        result = JSONParameterParser.parse_dict_parameter(json_string, "complex_param")
        assert result == complex_data
    
    def test_json_string_with_special_characters(self):
        """Test parsing JSON strings with special characters."""
        data_with_special = {
            "text": 'String with "quotes" and \n newlines',
            "unicode": "Émojis 🎉 and special chars: €£¥",
            "escaped": "Path: C:\\Users\\Test"
        }
        json_string = json.dumps(data_with_special)
        
        result = JSONParameterParser.parse_dict_parameter(json_string, "special_param")
        assert result == data_with_special