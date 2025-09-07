# MCP Tools Disconnection Issue Report

## Issue Summary
The dhafnck_mcp_http MCP tools are not accessible from Claude Code, despite the Docker container running and the HTTP server being healthy.

## Date: 2025-08-22

## Environment
- Docker containers: Running (dhafnck-mcp-server on port 8000, dhafnck-frontend on port 3800)
- Server health: Healthy (confirmed via curl http://localhost:8000/health)
- MCP Version: 2.1.0
- Authentication: Enabled (dual token system)

## Issue Details

### Symptoms
1. MCP tools like `mcp__dhafnck_mcp_http__manage_project` are not available
2. Error message: "Error: No such tool available: mcp__dhafnck_mcp_http__*"
3. ListMcpResourcesTool returns empty array for dhafnck_mcp_http server
4. Claude Code shows "Failed to reconnect to dhafnck_mcp_http"

### Root Cause Analysis
The issue appears to be related to recent authentication changes:
- Dual token authentication system was implemented
- JWT authentication backend was modified
- MCP entry point was updated with new authentication middleware

### Verification Steps Performed
1. ✅ Docker containers are running
2. ✅ HTTP server is healthy and responding
3. ✅ Server logs show no errors
4. ❌ MCP tools not accessible from Claude Code
5. ❌ MCP server not listed in running MCP processes

## Affected Components
1. `/dhafnck_mcp_main/src/fastmcp/server/mcp_entry_point.py`
2. `/dhafnck_mcp_main/src/fastmcp/auth/mcp_integration/jwt_auth_backend.py`
3. `/dhafnck_mcp_main/src/fastmcp/server/http_server.py`

## Temporary Workaround
Currently, the HTTP API can be accessed directly via curl:
```bash
curl -X POST http://localhost:8000/api/[endpoint] \
  -H "Content-Type: application/json" \
  -d '{"action": "...", ...}'
```

## Fix Recommendations

### 1. MCP Server Connection Issue
The MCP server needs to be properly connected to Claude Code. The issue is that the MCP server is running as an HTTP server but not exposed as an MCP server to Claude Code.

### 2. Authentication Compatibility
The dual token authentication may be interfering with MCP tool registration. The JWT auth backend uses a dummy RSA public key which might cause validation issues.

### 3. Tool Registration
The DDD-compliant tools are registered in the server but may not be exposed properly through the MCP protocol.

## Prompt for Fix in New Chat

### Prompt 1: Fix MCP Server Connection
```
The dhafnck_mcp_http MCP server is not connecting to Claude Code. The Docker container is running on port 8000 and HTTP endpoints are working, but MCP tools are not available in Claude Code.

Current situation:
- Docker container dhafnck-mcp-server is running on port 8000
- HTTP health check returns healthy status
- MCP tools like mcp__dhafnck_mcp_http__manage_project are not available
- Error: "No such tool available: mcp__dhafnck_mcp_http__*"

Files involved:
- dhafnck_mcp_main/src/fastmcp/server/mcp_entry_point.py
- dhafnck_mcp_main/src/fastmcp/server/http_server.py

Please fix the MCP server connection so that MCP tools are available in Claude Code.
```

### Prompt 2: Fix Authentication for MCP Tools
```
The JWT authentication system may be blocking MCP tool registration. Recent changes to dual token authentication might have broken MCP functionality.

Issue details:
- JWT auth backend uses a dummy RSA public key (lines 75-83 in jwt_auth_backend.py)
- Authentication is always enabled (line 324 in mcp_entry_point.py)
- MCP tools are registered but not accessible

Files to check:
- dhafnck_mcp_main/src/fastmcp/auth/mcp_integration/jwt_auth_backend.py
- dhafnck_mcp_main/src/fastmcp/server/mcp_entry_point.py

Please ensure authentication doesn't block MCP tool access while maintaining security.
```

### Prompt 3: Verify Tool Registration
```
DDD-compliant MCP tools are registered in the server but not exposed to Claude Code.

Current implementation:
- Tools registered at line 386-394 in mcp_entry_point.py
- DDDCompliantMCPTools class used for registration
- Server created with enable_task_management=False (line 356)

Please verify that:
1. Tools are properly registered with the FastMCP server
2. Tools are exposed through the MCP protocol
3. Tool names match the expected format (mcp__dhafnck_mcp_http__*)

File: dhafnck_mcp_main/src/fastmcp/server/mcp_entry_point.py
```

## Testing Checklist After Fix
- [ ] MCP tools are available in Claude Code
- [ ] Can create projects using mcp__dhafnck_mcp_http__manage_project
- [ ] Can create tasks using mcp__dhafnck_mcp_http__manage_task
- [ ] Can manage contexts using mcp__dhafnck_mcp_http__manage_context
- [ ] Authentication still works for secured endpoints
- [ ] No regression in HTTP API functionality

## Related Issues
- Dual token authentication implementation
- MCP server stateless HTTP mode
- Docker container health checks

## Status: OPEN
Awaiting fix for MCP tool connection issue.