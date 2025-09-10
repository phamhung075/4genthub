# JSON Parameter Parsing in MCP Framework

## Overview

The MCP framework now supports automatic JSON string parsing for dictionary parameters across all tools. This enhancement provides a better developer experience by accepting both dictionary objects and JSON string representations for parameters that expect dictionary/object types.

## Problem Solved

Previously, the MCP framework's schema validation would reject JSON strings for parameters that expected dictionary types, even though this is a common pattern when working with APIs. This required developers to always pass dictionary objects, which could be inconvenient in certain scenarios.

## Solution

We've implemented automatic JSON string detection and parsing that occurs before schema validation. This allows MCP tools to accept multiple formats for dictionary parameters:

1. **Dictionary objects** (existing behavior): `data={"key": "value"}`
2. **JSON strings** (new): `data='{"key": "value"}'`

## Implementation Details

### Core Components

1. **JSONParameterParser** (`json_parameter_parser.py`)
   - Handles automatic detection and parsing of JSON strings
   - Provides helpful error messages with examples when parsing fails
   - Supports complex nested JSON structures

2. **JSONParameterMixin** (`json_parameter_mixin.py`)
   - Reusable mixin for easy integration into any MCP controller
   - Provides consistent error handling across all tools

### Updated Controllers

The following controllers have been enhanced to support JSON string parsing:

1. **UnifiedContextMCPController** (`manage_context` tool)
   - `data`: Context data
   - `delegate_data`: Delegation data
   - `filters`: List filters

2. **ConnectionMCPController** (`manage_connection` tool)
   - `client_info`: Client metadata

## Usage Examples

### Before (Only Dictionary Objects)

```python
# This was the only supported format
manage_context(
    action="create",
    level="task",
    context_id="task-123",
    data={"title": "My Task", "description": "Task description"}
)

# JSON strings would fail with validation error
manage_context(
    action="create",
    level="task", 
    context_id="task-123",
    data='{"title": "My Task", "description": "Task description"}'  # ❌ Would fail
)
```

### After (Both Formats Supported)

```python
# Dictionary object (still works)
manage_context(
    action="create",
    level="task",
    context_id="task-123",
    data={"title": "My Task", "description": "Task description"}
)

# JSON string (now works!)
manage_context(
    action="create",
    level="task",
    context_id="task-123",
    data='{"title": "My Task", "description": "Task description"}'  # ✅ Works
)

# Complex nested structures
manage_context(
    action="delegate",
    level="task",
    context_id="task-123",
    delegate_to="project",
    delegate_data='''{
        "pattern_name": "auth_flow",
        "implementation": {
            "type": "JWT",
            "settings": {
                "expiry": 3600,
                "refresh": true
            }
        },
        "tags": ["security", "authentication"]
    }'''
)
```

## Error Handling

When JSON parsing fails, the system provides helpful error messages with examples:

```python
# Invalid JSON
manage_context(
    action="create",
    data='{invalid json}'
)

# Returns:
{
    "error": "Invalid JSON string in 'data' parameter: Expecting property name enclosed in double quotes",
    "error_code": "INVALID_PARAMETER_FORMAT",
    "parameter": "data",
    "suggestions": [
        "Use a dictionary object: data={'key': 'value', 'nested': {'item': 123}}",
        "Or use a JSON string: data='{\"key\": \"value\", \"nested\": {\"item\": 123}}'",
        "Ensure JSON is valid using a JSON validator"
    ],
    "examples": {
        "dictionary_format": "manage_context(action='create', data={'title': 'My Title', 'data': {'key': 'value'}})",
        "json_string_format": "manage_context(action='create', data='{\"title\": \"My Title\", \"data\": {\"key\": \"value\"}}')"
    }
}
```

## Integration Guide for New Controllers

To add JSON parameter parsing to a new controller:

### Option 1: Using JSONParameterMixin

```python
from ..utils.json_parameter_mixin import JSONParameterMixin

class MyMCPController(JSONParameterMixin):
    def register_tools(self, mcp: "FastMCP"):
        @mcp.tool(name="my_tool")
        def my_tool(
            action: str,
            config: Optional[Union[str, Dict[str, Any]]] = None
        ) -> Dict[str, Any]:
            try:
                # Parse JSON parameters
                params = self.parse_json_parameters(
                    {"config": config},
                    tool_name="my_tool",
                    custom_dict_params=["config"]
                )
                config = params["config"]
                
                # Use the parsed config
                # ...
                
            except ValueError as e:
                return self.create_json_error_response(
                    e, f"my_tool.{action}", "my_tool"
                )
```

### Option 2: Direct Usage

```python
from ..utils.json_parameter_parser import JSONParameterParser

# In your tool method:
try:
    if config is not None:
        config = JSONParameterParser.parse_dict_parameter(config, "config")
except ValueError as e:
    # Handle error
```

## Benefits

1. **Better Developer Experience**: Developers can pass JSON strings directly without manual parsing
2. **Backward Compatibility**: Existing code using dictionary objects continues to work
3. **Consistent Error Handling**: Helpful error messages guide developers to correct usage
4. **Flexibility**: Supports both simple and complex nested JSON structures
5. **Type Safety**: Validation ensures only valid dictionaries are accepted

## Testing

Comprehensive unit tests are provided in `test_json_parameter_parser.py` covering:
- Valid dictionary objects
- Valid JSON strings
- Invalid JSON strings
- Non-dictionary JSON (arrays, primitives)
- Complex nested structures
- Special characters and escaping
- Error message generation

## Future Enhancements

1. **Automatic Detection**: Extend to more dictionary parameters across all MCP tools
2. **Schema Integration**: Deep integration with FastMCP schema generation
3. **Performance Optimization**: Cache parsed JSON for repeated calls
4. **Validation Enhancement**: Add optional schema validation for parsed JSON

## Related Documentation

- [Parameter Type Validation](parameter-type-validation.md) - Boolean and integer parameter coercion
- [API Reference](../api-reference.md) - Complete MCP tool documentation
- [Error Handling](../error-handling-and-logging.md) - Error handling patterns