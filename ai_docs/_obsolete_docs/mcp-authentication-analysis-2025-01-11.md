# MCP Authentication Analysis Report
**Date**: 2025-01-11  
**Status**: Analysis Complete

## Executive Summary
The MCP auto-injection system implementation is complete but not working due to authentication mismatch. The MCP tools in Claude use a different authentication path than what the hooks are attempting.

## Key Findings

### 1. Server Configuration
- **Running Server**: FastMCP on port 8000 (`fastmcp.server.mcp_entry_point`)
- **Auth Status**: `auth_enabled: false` (confirmed via health endpoint)
- **Server Type**: DhafnckMCP v2.1.0 with task management

### 2. How MCP Tools in Claude Work
- **Token Source**: `.mcp.json` file contains JWT token
- **Connection Type**: HTTP with headers:
  - `Authorization: Bearer <token>`
  - `Accept: application/json, text/event-stream`
- **Endpoint**: Configured as `http://localhost:8000/mcp` in `.mcp.json`

### 3. Authentication Flow Issues

#### Current Hook Implementation:
1. Reads token from `.mcp.json` ✅
2. Tries to authenticate with token ✅
3. Gets "Invalid token" error ❌

#### Why It Fails:
- The server has `auth_enabled: false` but still validates tokens
- The token in `.mcp.json` might be expired (issued: 2025-01-06, expires: 2025-02-05)
- The endpoints expected by hooks don't match server implementation

### 4. Server Endpoint Analysis

#### Available Endpoints (from code):
- `/health` - Works, no auth required
- `/mcp/manage_task` - Returns 404
- `/mcp/manage_context` - Returns 404
- `/api/v2/tasks/` - Returns "Invalid token"

#### The Problem:
The FastMCP server running is NOT the same as `mcp_http_server.py`. It's a different implementation that doesn't expose the expected REST endpoints.

## Solution Paths

### Option 1: Use JSON-RPC Protocol (Recommended)
The FastMCP server expects JSON-RPC protocol, not REST:
```python
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "manage_task",
        "arguments": {"action": "list", "status": "todo"}
    },
    "id": 1
}
```

### Option 2: Bypass Authentication
Since `auth_enabled: false`, create a direct query method without token validation.

### Option 3: Generate Fresh Token
Use the MCP token generation endpoint to create a new valid token.

## Implementation Status

### ✅ Completed:
1. Hook infrastructure (`session_start.py`)
2. MCP client with token management (`mcp_client.py`)
3. Fallback strategies and caching
4. Context injection framework

### ❌ Blocked:
1. Actual task retrieval (authentication mismatch)
2. Task injection into Claude context
3. End-to-end testing

## Next Steps

1. **Immediate Fix**: Update `mcp_client.py` to use JSON-RPC protocol
2. **Test**: Verify task retrieval works without authentication
3. **Deploy**: Enable auto-injection in sessions
4. **Monitor**: Track injection success rate

## Technical Details

### Current Server Process:
```bash
/home/daihungpham/__projects__/agentic-project/dhafnck_mcp_main/.venv/bin/python \
  -m fastmcp.server.mcp_entry_point
```

### Token from .mcp.json:
- **Type**: JWT (HS256)
- **Issued**: 2025-01-06 (1757338252)
- **Expires**: 2025-02-05 (1759930252)
- **Subject**: f0de4c5d-2a97-4324-abcd-9dae3922761e
- **Scopes**: Full MCP access (projects, tasks, contexts, agents)

### Environment Detection:
The server checks `AUTH_ENABLED` environment variable:
- If `false`: No authentication required
- If `true`: Requires valid JWT token

## Conclusion

The MCP auto-injection system is **architecturally complete** but needs to match the actual server's authentication mechanism. Since the server has authentication disabled (`auth_enabled: false`), the simplest solution is to bypass token validation entirely for local development.