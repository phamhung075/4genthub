# Tool Configuration System

This module provides a flexible configuration system for enabling/disabling MCP tools at server startup.

## Overview

The tool configuration system allows you to:
- Enable/disable authentication tools based on configuration
- Respect environment variables (AUTH_ENABLED)
- Define dependencies for tools
- Support environment-specific overrides
- Provide graceful fallbacks when configuration fails

## Files

### Configuration Files
- `tool_config.yaml` - Main configuration file defining which tools are enabled
- Located in: `/agenthub_main/src/config/tool_config.yaml`

### Python Modules
- `tool_config_loader.py` - Loads and validates YAML configuration
- `tool_registry.py` - Manages conditional tool mounting to FastMCP server
- `auth_tools.py` - Authentication tool implementations
- `__init__.py` - Module exports

## Configuration Format

```yaml
version: "1.0.0"

tools:
  authentication:
    enabled: true  # Global enable/disable for group
    tools:
      validate_token:
        enabled: true
        description: "Validate authentication tokens"
        dependencies: ["auth_middleware"]

      generate_token:
        enabled: false  # Disabled by default (deprecated)
        deprecated: true

global:
  respect_auth_env: true  # Respect AUTH_ENABLED environment variable
  auth_env_override: true  # AUTH_ENABLED=false disables all auth tools

environment_overrides:
  development:
    authentication:
      tools:
        generate_token:
          enabled: true  # Enable in dev for testing
```

## Environment Variables

### AUTH_ENABLED
- `AUTH_ENABLED=false` - Disables ALL authentication tools regardless of config
- `AUTH_ENABLED=true` - Enables tools based on configuration file
- Default: `true`

### ENVIRONMENT
- `ENVIRONMENT=development` - Uses development overrides
- `ENVIRONMENT=production` - Uses production overrides
- Default: `development`

## Usage Examples

### Basic Usage in Server Startup

```python
from fastmcp.config import ToolRegistry, create_authentication_tools

# Create tool registry and load configuration
tool_registry = ToolRegistry()
tool_registry.load_configuration()

# Add dependencies
if auth_middleware:
    tool_registry.add_dependency("auth_middleware")

# Register authentication tools
auth_tools = create_authentication_tools(auth_middleware)
tool_registry.register_tool_group("authentication", auth_tools)

# Mount tools to server
mounting_stats = tool_registry.mount_tools_to_server(server)
```

### Check Tool Status

```python
# Check if a specific tool is enabled
enabled = tool_registry.config_loader.is_tool_enabled("authentication", "validate_token")

# Get enabled tools in a group
enabled_tools = tool_registry.config_loader.get_enabled_tools("authentication")

# Get tool configuration
tool_config = tool_registry.config_loader.get_tool_config("authentication", "validate_token")
```

## Backward Compatibility

The system maintains full backward compatibility:

1. **AUTH_ENABLED Environment Variable**: Still respected
   - `AUTH_ENABLED=false` disables all auth tools
   - `AUTH_ENABLED=true` enables based on config

2. **Legacy Fallback**: If configuration system fails, falls back to legacy tool registration

3. **Default Behavior**: When config file is missing, enables all tools (same as before)

## Configuration Scenarios

### Scenario 1: Disable All Auth Tools
```bash
export AUTH_ENABLED=false
# Result: No auth tools mounted, regardless of config file
```

### Scenario 2: Enable Only Essential Tools
```yaml
tools:
  authentication:
    tools:
      validate_token:
        enabled: true
      get_auth_status:
        enabled: true
      generate_token:
        enabled: false  # Deprecated
      get_rate_limit_status:
        enabled: false  # Not needed
      revoke_token:
        enabled: false  # Not needed
```

### Scenario 3: Development vs Production
```yaml
environment_overrides:
  development:
    authentication:
      tools:
        generate_token:
          enabled: true  # Enable deprecated tool for testing

  production:
    authentication:
      tools:
        generate_token:
          enabled: false  # Ensure disabled in production
```

## Tool Dependencies

Tools can define dependencies that must be available:

```yaml
tools:
  authentication:
    tools:
      validate_token:
        dependencies: ["auth_middleware"]
```

If `auth_middleware` is not available, the tool will be skipped.

## Error Handling

The system provides graceful error handling:

1. **Configuration File Missing**: Uses default configuration
2. **YAML Parse Error**: Logs error and uses defaults
3. **Tool Mounting Failure**: Continues with other tools
4. **Dependency Missing**: Skips tool but continues

## Logging

The system provides detailed logging:

```
INFO: Tool configuration loaded from /path/to/tool_config.yaml
INFO: Authentication tools registered with configuration system
INFO: Tool mounting completed: 4 mounted, 1 disabled, 0 dependency failures
INFO: === Tool Mounting Summary ===
INFO: Total tools found: 5
INFO: Successfully mounted: 4
INFO: Disabled by config: 1
```

## Extending the System

### Adding New Tool Groups

1. Add configuration in `tool_config.yaml`:
```yaml
tools:
  my_new_group:
    enabled: true
    tools:
      my_tool:
        enabled: true
        description: "My custom tool"
```

2. Create tool implementations:
```python
def create_my_tools():
    return {
        "my_tool": my_tool_function
    }
```

3. Register tools:
```python
my_tools = create_my_tools()
tool_registry.register_tool_group("my_new_group", my_tools)
```

### Adding Dependencies

```python
tool_registry.add_dependency("my_service")
tool_registry.add_dependency("my_database")
```

## Testing

The configuration system can be tested by:

1. Creating test configurations
2. Checking mounting statistics
3. Verifying tool availability
4. Testing environment overrides

```python
# Test configuration loading
tool_registry = ToolRegistry("/path/to/test/config.yaml")
tool_registry.load_configuration()

# Test tool status
assert tool_registry.is_tool_enabled("authentication", "validate_token")

# Test mounting
stats = tool_registry.mount_tools_to_server(test_server)
assert stats["mounted_tools"] > 0
```