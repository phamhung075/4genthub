# MCP Registration System Documentation

## Overview
The DhafnckMCP server implements a comprehensive registration system for MCP (Model Context Protocol) clients, including Claude Desktop and other compatible clients.

## Architecture

### Registration Endpoint
- **URL**: `/register`
- **Method**: POST
- **Purpose**: Establishes client sessions and provides server capability information

### Alternative Paths
The server supports multiple registration paths for compatibility:
- `/register` - Primary endpoint
- `/api/register` - API-style path
- `/mcp/register` - MCP-specific path

## Registration Flow

### 1. Client Registration Request
```json
POST /register
Content-Type: application/json

{
  "client_info": {
    "name": "Claude Desktop",
    "version": "1.0.0"
  },
  "capabilities": {
    "tools": true,
    "resources": true,
    "prompts": true
  }
}
```

### 2. Server Registration Response
```json
{
  "success": true,
  "session_id": "uuid-v4-session-id",
  "server": {
    "name": "dhafnck-mcp-server",
    "version": "2.1.0",
    "protocol_version": "2024-11-05"
  },
  "endpoints": {
    "mcp": "http://localhost:8000/mcp/",
    "initialize": "http://localhost:8000/mcp/initialize",
    "tools": "http://localhost:8000/mcp/tools/list",
    "health": "http://localhost:8000/health"
  },
  "transport": "streamable-http",
  "authentication": {
    "required": true,
    "type": "Bearer",
    "header": "Authorization",
    "format": "Bearer YOUR_JWT_TOKEN_HERE"
  },
  "capabilities": {
    "tools": true,
    "resources": true,
    "prompts": true,
    "logging": true,
    "progress": true
  },
  "instructions": {
    "next_step": "Initialize connection at /mcp/initialize endpoint",
    "authentication": "Include JWT token in Authorization header",
    "protocol": "Use MCP protocol for all subsequent requests"
  }
}
```

## Session Management

### Active Sessions
- Sessions are tracked in memory (development) or Redis (production)
- Each session has a unique UUID identifier
- Sessions track client information and last activity time

### Session Cleanup
- Expired sessions (>1 hour inactive) are automatically cleaned
- Clients can explicitly unregister using `/unregister` endpoint

## Authentication Integration

### JWT Token Requirements
After registration, clients must authenticate using JWT tokens:

1. **Token Format**: Bearer token in Authorization header
2. **Required Scopes**: `execute:mcp` for MCP protocol access
3. **Token Types**: Accepts both `access` and `api_token` types
4. **User ID Fields**: Checks both `sub` and `user_id` fields

### Token Generation
```python
import jwt
from datetime import datetime, timedelta

payload = {
    'sub': 'user-id',
    'user_id': 'user-id',
    'type': 'access',
    'scopes': ['execute:mcp'],
    'exp': datetime.utcnow() + timedelta(hours=24),
    'iat': datetime.utcnow()
}

token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
```

## MCP Protocol Flow

### Complete Connection Sequence

1. **Registration** (Optional)
   ```
   POST /register → Get server info and session ID
   ```

2. **MCP Initialization** (Required)
   ```
   POST /mcp/
   Authorization: Bearer <token>
   
   {
     "jsonrpc": "2.0",
     "method": "initialize",
     "params": {
       "protocolVersion": "2024-11-05",
       "capabilities": {},
       "clientInfo": {
         "name": "client-name",
         "version": "1.0"
       }
     },
     "id": 1
   }
   ```

3. **Tool Discovery**
   ```
   POST /mcp/
   Authorization: Bearer <token>
   
   {
     "jsonrpc": "2.0",
     "method": "tools/list",
     "params": {},
     "id": 2
   }
   ```

4. **Tool Execution**
   ```
   POST /mcp/
   Authorization: Bearer <token>
   
   {
     "jsonrpc": "2.0",
     "method": "tools/call",
     "params": {
       "name": "manage_task",
       "arguments": {
         "action": "list"
       }
     },
     "id": 3
   }
   ```

## Client Configuration

### Claude Desktop (.mcp.json)
```json
{
  "mcpServers": {
    "dhafnck_mcp_http": {
      "type": "http",
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer <JWT_TOKEN>"
      }
    }
  }
}
```

### MCP Bridge (stdio to HTTP)
For stdio-based clients, use the MCP bridge:
```json
{
  "mcpServers": {
    "dhafnck_mcp": {
      "command": "python",
      "args": ["src/mcp_bridge.py"],
      "transport": "stdio"
    }
  }
}
```

## Debugging

### Registration Endpoint Testing
```bash
# Test registration
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -H "User-Agent: Claude-Desktop/1.0" \
  -d '{"client_info": {"name": "test", "version": "1.0"}}'

# List active registrations
curl http://localhost:8000/registrations
```

### Common Issues

1. **404 on /register**
   - Ensure Docker container is running with latest code
   - Check that registration routes are imported in http_server.py

2. **Authentication Failures**
   - Verify JWT token hasn't expired
   - Ensure token has `execute:mcp` scope
   - Check JWT secret matches between token and server

3. **Connection Refused**
   - Verify Docker container is running: `docker ps`
   - Check server health: `curl http://localhost:8000/health`
   - Ensure port 8000 is not blocked

### Log Files
- **Bridge logs**: `/tmp/mcp_bridge.log`
- **Server logs**: `docker logs dhafnck-mcp-server`

## Security Considerations

1. **Token Security**
   - Never expose JWT tokens in logs or error messages
   - Use short-lived tokens in production
   - Rotate JWT secrets regularly

2. **CORS Headers**
   - Registration endpoints include permissive CORS for development
   - Restrict origins in production deployment

3. **Session Management**
   - Implement proper session timeout
   - Clean up inactive sessions
   - Use persistent storage (Redis) in production

## Implementation Details

### File Structure
```
src/fastmcp/server/routes/
├── mcp_registration_routes.py  # Registration endpoints
├── mcp_redirect_routes.py      # Legacy redirect handlers
└── token_routes.py             # Token management
```

### Key Components

1. **Registration Handler** (`register_client`)
   - Validates client information
   - Generates session ID
   - Returns server capabilities
   - Stores session for tracking

2. **Session Storage** (`active_registrations`)
   - In-memory dictionary (development)
   - Redis integration ready for production
   - Tracks client metadata and activity

3. **CORS Support** (`handle_options`)
   - Handles preflight requests
   - Enables cross-origin access
   - Required for browser-based clients

## Future Enhancements

1. **Persistent Sessions**
   - Redis or database storage
   - Session recovery after restart
   - Multi-server support

2. **Enhanced Authentication**
   - OAuth2 flow support
   - API key authentication
   - Role-based access control

3. **Metrics and Monitoring**
   - Registration success/failure rates
   - Active session counts
   - Client version tracking

4. **Rate Limiting**
   - Per-client rate limits
   - DDoS protection
   - Fair usage policies