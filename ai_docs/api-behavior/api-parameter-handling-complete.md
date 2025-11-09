# MCP API Parameter Handling Reference

## Quick Reference

| Feature | Input Format | Output | Status |
|---------|-------------|--------|--------|
| **JSON Strings** | `data='{"key": "val"}'` | Dictionary | ✅ All controllers |
| **Boolean Coercion** | `"true"`, `"1"`, `"yes"`, `"on"` | `True` | ✅ Automatic |
| **Integer Coercion** | `"50"`, `"100"` | Integer | ✅ Automatic |
| **Nested JSON** | Complex structures | Parsed objects | ✅ Supported |

---

## JSON Parameter Parsing

### Supported Formats
MCP tools accept both dictionary objects and JSON strings for dictionary parameters:

```python
# Dictionary object (native)
manage_context(action="create", data={"title": "Task", "tags": ["auth"]})

# JSON string (auto-parsed)
manage_context(action="create", data='{"title": "Task", "tags": ["auth"]}')

# Complex nested (multi-line)
manage_context(
    action="delegate",
    delegate_data='''{
        "pattern": "auth_flow",
        "settings": {"expiry": 3600, "refresh": true},
        "tags": ["security"]
    }'''
)
```

### Controllers with JSON Support

| Tool | Parameters Accepting JSON Strings |
|------|-----------------------------------|
| `manage_context` | `data`, `delegate_data`, `filters` |
| `manage_connection` | `client_info` |
| All MCP tools | Any dictionary-type parameter |

---

## Type Coercion

### Boolean Conversion

| String Input | Converts To | Case Sensitive? |
|--------------|-------------|-----------------|
| `"true"`, `"1"`, `"yes"`, `"on"`, `"enabled"` | `True` | No |
| `"false"`, `"0"`, `"no"`, `"off"`, `"disabled"` | `False` | No |

**Example:**
```python
# All these work identically
manage_context(include_inherited=True)
manage_context(include_inherited="true")
manage_context(include_inherited="1")
manage_context(include_inherited="YES")  # Case-insensitive
```

### Integer Conversion

| String Input | Converts To | Validation |
|--------------|-------------|------------|
| `"50"` | `50` | Range checked |
| `"100"` | `100` | Min/max bounds |
| `"abc"` | Error | Cannot convert |

**Common Integer Parameters:**
- `limit`: Result count (0-100)
- `progress_percentage`: Task progress (0-100)
- `timeout`: Milliseconds
- `offset`: Pagination offset

---

## Implementation

### Using JSONParameterMixin

```python
from ..utils.json_parameter_mixin import JSONParameterMixin

class MyController(JSONParameterMixin):
    def register_tools(self, mcp: "FastMCP"):
        @mcp.tool(name="my_tool")
        def my_tool(config: Optional[Union[str, Dict]] = None):
            try:
                params = self.parse_json_parameters(
                    {"config": config},
                    tool_name="my_tool",
                    custom_dict_params=["config"]
                )
                config = params["config"]
                # Use parsed config...
            except ValueError as e:
                return self.create_json_error_response(e, "my_tool", "my_tool")
```

### Direct JSON Parsing

```python
from ..utils.json_parameter_parser import JSONParameterParser

# Parse single parameter
config = JSONParameterParser.parse_dict_parameter(config, "config")
```

---

## Error Handling

### Invalid JSON
```python
manage_context(data='{invalid json}')

# Returns:
{
    "error": "Invalid JSON string in 'data' parameter: Expecting property name...",
    "error_code": "INVALID_PARAMETER_FORMAT",
    "parameter": "data",
    "suggestions": [
        "Use dictionary: data={'key': 'value', 'nested': {'item': 123}}",
        "Or JSON string: data='{\"key\": \"value\"}'"
    ],
    "examples": {
        "dictionary": "manage_context(action='create', data={'title': 'My Title'})",
        "json_string": "manage_context(action='create', data='{\"title\": \"My Title\"}')"
    }
}
```

### Invalid Type Conversion
```python
manage_task(limit="abc")  # Cannot convert to integer

# Returns:
{
    "error": "Parameter 'limit' value 'abc' cannot be converted to integer",
    "error_code": "PARAMETER_COERCION_ERROR",
    "hint": "Check parameter format and try again"
}
```

---

## Controller Support Matrix

| Controller | Boolean Coercion | Integer Coercion | JSON Parsing | Method |
|-----------|-----------------|-----------------|--------------|--------|
| Task | ✅ | ✅ | ✅ | Built-in `_coerce_to_bool` |
| Context | ✅ | ✅ | ✅ | Framework + mixin |
| Subtask | ✅ | ✅ | ✅ | Inherited from Task |
| Project | ✅ | ✅ | ✅ | Framework-level |
| Git Branch | ✅ | ✅ | ✅ | Framework-level |
| Agent | ✅ | ✅ | ✅ | Framework-level |
| Connection | ✅ | ✅ | ✅ | JSONParameterMixin |

**All controllers** support automatic type coercion via FastMCP framework or explicit implementation.

---

## Best Practices

### Development
1. **Use native types** for clarity: `True` not `"true"`
2. **Let system coerce** when receiving API calls
3. **Test both formats** if building client libraries
4. **Handle errors** - invalid conversions still error

### API Integration
```python
# ✅ GOOD - Both formats work
manage_task(action="list", limit=50)              # Native
manage_task(action="list", limit="50")            # String (auto-converted)

# ✅ GOOD - Complex JSON
manage_context(
    action="create",
    data='{"workflow": {"steps": [1, 2, 3], "parallel": true}}'
)

# ❌ BAD - Will error
manage_task(action="list", limit="invalid")      # Cannot convert
manage_context(data="{not valid json}")           # Parse error
```

---

## Testing

### Validation Test Cases
```python
# Boolean coercion tests (all pass)
"true"  → True
"false" → False
"1"     → True
"0"     → False
"YES"   → True (case-insensitive)
"Off"   → False

# Integer coercion tests (all pass)
"5"     → 5
"100"   → 100
"abc"   → Error (cannot convert)

# JSON parsing tests (all pass)
'{"key": "val"}' → {"key": "val"}
'{"nested": {"deep": true}}' → Nested dict
'{invalid}' → Error (invalid JSON)
```

---

## Benefits

| Benefit | Description |
|---------|-------------|
| **User-Friendly** | Accept common string representations |
| **Backward Compatible** | Works with various input formats |
| **Type Safety** | Ensures correct types after conversion |
| **Clear Errors** | Only fails when conversion impossible |
| **Flexibility** | Supports simple and complex structures |
| **Consistent** | Same behavior across all controllers |

---

## Implementation Files

| Component | File | Purpose |
|-----------|------|---------|
| JSON Parser | `json_parameter_parser.py` | Auto-detect and parse JSON strings |
| Parameter Mixin | `json_parameter_mixin.py` | Reusable controller integration |
| Type Coercer | `parameter_validation_fix.py` | Boolean/integer conversion |
| Task Controller | `task_mcp_controller.py` | Built-in `_coerce_to_bool` |

---

## Related Documentation
- [MCP Tools Reference](../.claude/ai_docs/claude-code/tools-and-mcp-reference.md)
- [API Integration Guide](../api-integration/)
- [Error Handling](../development-guides/)
