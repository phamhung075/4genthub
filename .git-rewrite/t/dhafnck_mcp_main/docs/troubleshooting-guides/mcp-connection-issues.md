# MCP Connection Issues and Solutions

## Overview
This document covers the comprehensive testing of DhafnckMCP tools and the issues encountered when attempting to establish MCP (Model Context Protocol) connectivity between Claude Code and the DhafnckMCP server.

## Issues Encountered

### 1. MCP Server Connection Failure
**Problem**: Claude Code cannot establish MCP connection with the server
```
Failed to reconnect to dhafnck_mcp_http.
```

**Root Causes**:
1. **Missing `/register` endpoint**: The server returns 404 for `/register` endpoint that Claude Code expects for MCP registration
2. **Incorrect MCP protocol implementation**: The server expects `Accept: text/event-stream` headers but Claude Code might be sending different headers
3. **Authentication issues**: Server has authentication enabled by default (`DHAFNCK_AUTH_ENABLED=true`)

### 2. Docker Configuration Issues
**Problem**: Docker containers not starting with correct network configuration
```
network dhafnck-network not found
```

**Solutions**:
- Use correct network name: `dhafnck-network`
- Set authentication to disabled: `DHAFNCK_AUTH_ENABLED=false`
- Use proper Docker compose configuration

### 3. Authentication Token Issues
**Problem**: Existing JWT tokens invalid or expired
```
Status: 401
Response: {"detail":"Invalid token: missing user ID"}
```

**Analysis**:
- Current token in `.mcp.json` may be expired
- Server requires valid JWT with proper scopes: `["read:tasks", "read:context", "write:context", "write:tasks", "read:agents", "write:agents", "execute:mcp"]`

### 4. Import and Dependency Issues
**Problem**: Server startup fails due to missing dependencies
```
ImportError: cannot import name 'FastMCP' from 'fastmcp'
ModuleNotFoundError: No module named 'supabase'
```

## Working Solutions

### 1. Disable Authentication for Testing
Set environment variable to bypass authentication:
```bash
DHAFNCK_AUTH_ENABLED=false
```

### 2. Direct API Testing Method
Since MCP connection is failing, we can test the tools directly via HTTP API:

```python
import requests

# Test endpoint with auth disabled
response = requests.post(
    'http://localhost:8000/api/v2/projects/',
    json={'name': 'Test Project', 'description': 'Test Description'},
    headers={'Content-Type': 'application/json'}
)
```

### 3. Available API Endpoints
The server provides these endpoints (discovered via `/openapi.json`):

**Project Management**:
- `POST /api/v2/projects/` - Create project
- `GET /api/v2/projects/` - List projects
- `GET /api/v2/projects/{project_id}` - Get project

**Task Management**:
- `POST /api/tasks/` - Create task
- `GET /api/tasks/{task_id}` - Get task
- `PUT /api/tasks/{task_id}` - Update task

**Context Management**:
- `POST /api/v2/contexts/{level}` - Create context
- `GET /api/v2/contexts/{level}/{context_id}` - Get context
- `PUT /api/v2/contexts/{level}/{context_id}` - Update context

## Recommended Testing Approach

Since MCP connection is problematic, use direct HTTP API testing:

### Phase 1: Direct API Testing
1. Start server with authentication disabled
2. Test all endpoints directly via HTTP
3. Verify functionality without MCP layer

### Phase 2: MCP Protocol Investigation
1. Investigate why `/register` endpoint is missing
2. Check MCP protocol implementation
3. Fix authentication token generation

### Phase 3: Claude Code Integration
1. Update `.mcp.json` with working configuration
2. Test MCP tools connectivity
3. Validate end-to-end workflow

## Configuration Files

### Working .mcp.json Template
```json
{
    "mcpServers": {
        "dhafnck_mcp_http": {
            "type": "http",
            "url": "http://localhost:8000/mcp/",
            "headers": {
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer <VALID_JWT_TOKEN>"
            }
        }
    }
}
```

### Required Environment Variables
```bash
DHAFNCK_AUTH_ENABLED=false  # For testing
DATABASE_TYPE=sqlite
MCP_DB_PATH=/data/dhafnck_mcp.db
```

## Next Steps

1. **Immediate**: Use direct HTTP API testing to validate all tool functionality
2. **Short-term**: Fix MCP protocol implementation on server side
3. **Long-term**: Establish proper MCP connection with Claude Code

## Status
- **MCP Connection**: ❌ Failed (multiple issues)
- **Server Health**: ✅ Running (Docker)
- **API Endpoints**: ✅ Available (auth disabled)
- **Direct Testing**: ✅ Feasible approach

## Test Results Summary

Based on diagnostics:
- ✅ Server is running and healthy
- ❌ MCP `/register` endpoint not found (404)
- ❌ Authentication tokens invalid/expired  
- ❌ Claude Code cannot establish MCP connection
- ✅ Direct HTTP API testing possible with auth disabled

**Recommendation**: Proceed with direct API testing methodology while MCP issues are resolved.