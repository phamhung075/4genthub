# Server Initialization Patterns

## Overview
Starting from FastMCP version 2.8.0, certain parameters are deprecated when creating a server instance and should be provided when calling `run()` or as global settings instead.

## Deprecated Parameters
The following parameters should NO longer be provided when creating a FastMCP server:
- `log_level`
- `debug`
- `json_response`
- `stateless_http`
- `host`
- `port`
- `sse_path`
- `message_path`
- `streamable_http_path`

## Correct Initialization Pattern

### ❌ Old Pattern (Deprecated)
```python
from fastmcp import FastMCP

# DEPRECATED - Don't do this
server = FastMCP(
    name="My Server",
    log_level="DEBUG",        # ❌ Deprecated
    debug=True,                # ❌ Deprecated
    json_response=True,        # ❌ Deprecated
    stateless_http=True        # ❌ Deprecated
)
```

### ✅ New Pattern (Recommended)
```python
from fastmcp import FastMCP

# Create server with only non-deprecated parameters
server = FastMCP(
    name="My Server",
    instructions="Server instructions",
    version="1.0.0",
    enable_task_management=True,
    on_duplicate_tools="ignore"
)

# Provide runtime settings when calling run()
if __name__ == "__main__":
    server.run(
        log_level="DEBUG",
        debug=True,
        json_response=True,
        stateless_http=True
    )
```

### Alternative: Global Settings
```python
import fastmcp

# Set global settings before creating server
fastmcp.settings.log_level = "DEBUG"
fastmcp.settings.debug = True
fastmcp.settings.json_response = True
fastmcp.settings.stateless_http = True

# Create server without deprecated parameters
server = FastMCP(name="My Server")
```

## For HTTP/Uvicorn Servers
When using uvicorn, log_level is configured in uvicorn.Config, not FastMCP:

```python
from fastmcp import FastMCP
import uvicorn

# Create FastMCP server
server = FastMCP(
    name="My HTTP Server",
    enable_task_management=True
)

# Create HTTP app
app = server.http_app(path="/mcp", transport="streamable-http")

# Configure uvicorn with its own settings
config = uvicorn.Config(
    app=app,
    host="127.0.0.1",
    port=8000,
    log_level="info"  # This is uvicorn's log_level, not FastMCP's
)

server_instance = uvicorn.Server(config)
```

## Migration Guide

If you have existing code using deprecated parameters:

1. **Identify deprecated usage**:
   ```bash
   grep -r "FastMCP(" . --include="*.py" | grep -E "(log_level|debug|json_response|stateless_http)"
   ```

2. **Update initialization**:
   - Remove deprecated parameters from FastMCP() constructor
   - Move them to run() method or global settings

3. **Test your changes**:
   - Ensure server starts without deprecation warnings
   - Verify logging and debug settings work as expected

## Suppressing Deprecation Warnings

If you need time to migrate:

```python
import fastmcp

# Temporarily disable deprecation warnings
fastmcp.settings.deprecation_warnings = False

# Your old code will work without warnings
server = FastMCP(name="Server", log_level="DEBUG")  # No warning
```

**Note**: This is temporary. Plan to migrate to the new pattern.

## Best Practices

1. **Keep server creation clean**: Only include core server identity parameters
2. **Use run() for runtime config**: Pass operational settings when starting the server
3. **Use environment variables**: For production deployments, consider using environment variables for settings
4. **Document your settings**: Keep a clear record of what settings your server requires

## Example: Complete Server Setup

```python
#!/usr/bin/env python3
"""Example of properly configured FastMCP server"""

from fastmcp import FastMCP
from fastmcp.task_management.interface.ddd_compliant_mcp_tools import DDDCompliantMCPTools

def create_server():
    """Create and configure the FastMCP server"""
    
    # Create server with only core parameters
    server = FastMCP(
        name="Production Server",
        instructions="Main application server",
        version="2.0.0",
        enable_task_management=True
    )
    
    # Register task management tools
    tools = DDDCompliantMCPTools()
    tools.register_tools(server)
    
    return server

def main():
    """Main entry point"""
    server = create_server()
    
    # Run with runtime configuration
    server.run(
        log_level="INFO",
        debug=False,
        transport="stdio"  # or "sse" for Server-Sent Events
    )

if __name__ == "__main__":
    main()
```

## Testing Considerations

When writing tests, follow the same pattern:

```python
import pytest
from fastmcp import FastMCP

@pytest.fixture
def test_server():
    """Create a test server without deprecated parameters"""
    return FastMCP(
        name="Test Server",
        enable_task_management=False
    )

def test_server_creation(test_server):
    """Test that server is created without warnings"""
    assert test_server.name == "Test Server"
    # No deprecation warnings should appear
```

## Summary

- **DO**: Create servers with only core identity parameters
- **DO**: Pass runtime settings to run() method
- **DO**: Use global settings for application-wide configuration
- **DON'T**: Pass log_level, debug, json_response, or stateless_http to FastMCP()
- **DON'T**: Ignore deprecation warnings without a migration plan