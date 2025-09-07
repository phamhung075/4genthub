# MCP Token Authentication Guide

## Overview

The DhafnckMCP platform now supports JWT Bearer token authentication for MCP connections. This allows you to secure your MCP server and control access using the token management system.

## Quick Start

### 1. Generate an API Token

First, generate an API token through the web interface:

1. Log in to the DhafnckMCP frontend at http://localhost:3800
2. Navigate to **API Tokens** (key icon in the header)
3. Click **Generate Token** tab
4. Configure your token:
   - **Name**: Give your token a descriptive name (e.g., "MCP Client Token")
   - **Scopes**: Select the permissions needed:
     - `execute:mcp` - Required for MCP execution
     - `read:tasks` - Read task data
     - `write:tasks` - Create/modify tasks
     - `read:context` - Read context data
     - `write:context` - Modify context
   - **Expiry**: Set token lifetime (1-365 days)
   - **Rate Limit**: Set requests per hour limit
5. Click **Generate Token**
6. **IMPORTANT**: Copy the token immediately - you won't see it again!

### 2. Configure MCP Client with Bearer Token

Update your MCP client configuration to include the Bearer token in the Authorization header.

#### Cursor Configuration (.cursor/mcp.json)

```json
{
  "mcpServers": {
    "dhafnck_mcp_http": {
      "type": "http",
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
      }
    }
  }
}
```

#### VS Code Configuration

```json
{
  "mcp.servers": {
    "dhafnck_mcp_http": {
      "type": "http",
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Accept": "application/json, text/event-stream",
        "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
      }
    }
  }
}
```

### 3. Server-Side Configuration

The MCP server automatically detects and uses JWT authentication when `JWT_SECRET_KEY` is set.

#### Environment Variables

```bash
# Required for JWT authentication
JWT_SECRET_KEY=your-secret-key-here

# Optional: Control authentication type
MCP_AUTH_TYPE=jwt  # Options: jwt, env, none

# Optional: Require specific scopes
MCP_REQUIRED_SCOPES=mcp:access,execute:mcp
```

#### Docker Configuration

If using Docker, add to your `docker-compose.yml`:

```yaml
services:
  dhafnck-mcp:
    environment:
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - MCP_AUTH_TYPE=jwt
```

## Token Scopes and Permissions

### Available Scopes

| Scope | Description | MCP Permission |
|-------|-------------|----------------|
| `read:tasks` | Read task data | `mcp:read` |
| `write:tasks` | Create/modify tasks | `mcp:write` |
| `read:context` | Read context data | `mcp:read` |
| `write:context` | Modify context data | `mcp:write` |
| `read:agents` | View agent configurations | `mcp:read` |
| `write:agents` | Configure agents | `mcp:write` |
| `execute:mcp` | Execute MCP commands | `mcp:execute` |

**Note:** Administrative privileges (`mcp:admin`) cannot be granted through the UI. Admin access must be configured directly in the database for security reasons.

### Scope Inheritance

- `write:*` scopes include corresponding `read:*` permissions
- All tokens automatically get `mcp:access` for basic connectivity
- Admin scope (when set directly in database) includes all permissions

## Programmatic Token Usage

### Python Client Example

```python
import httpx
import json

# Your API token from the token management system
token = "YOUR_JWT_TOKEN_HERE"

# MCP request headers
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {token}"
}

# Initialize MCP connection
async with httpx.AsyncClient() as client:
    # Send initialization request
    response = await client.post(
        "http://localhost:8000/mcp/initialize",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {}
            },
            "id": 1
        }
    )
    
    print(response.json())
```

### JavaScript/TypeScript Client Example

```typescript
const token = "YOUR_JWT_TOKEN_HERE";

const mcpClient = {
  baseUrl: "http://localhost:8000/mcp/",
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": `Bearer ${token}`
  },
  
  async initialize() {
    const response = await fetch(`${this.baseUrl}initialize`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({
        jsonrpc: "2.0",
        method: "initialize",
        params: {
          protocolVersion: "2025-06-18",
          capabilities: {}
        },
        id: 1
      })
    });
    
    return response.json();
  }
};
```

## Token Management

### Token Rotation

For security, rotate tokens periodically:

```bash
# Using the API
curl -X POST http://localhost:8000/api/v2/tokens/{token_id}/rotate \
  -H "Authorization: Bearer YOUR_USER_TOKEN"
```

### Token Revocation

Revoke compromised tokens immediately:

```bash
curl -X DELETE http://localhost:8000/api/v2/tokens/{token_id} \
  -H "Authorization: Bearer YOUR_USER_TOKEN"
```

### Token Validation

Test if a token is valid:

```bash
curl -X POST http://localhost:8000/api/v2/tokens/validate \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Security Best Practices

1. **Never commit tokens to version control**
   - Use environment variables or secure vaults
   - Add token files to `.gitignore`

2. **Use minimal scopes**
   - Only grant permissions actually needed
   - Create separate tokens for different purposes

3. **Set appropriate expiration**
   - Short-lived tokens (7-30 days) for development
   - Longer tokens (90-365 days) for production with rotation

4. **Monitor token usage**
   - Check usage statistics in the token management UI
   - Set up alerts for unusual activity

5. **Rotate tokens regularly**
   - Implement automated rotation for production
   - Rotate immediately if compromise suspected

## Troubleshooting

### Common Issues

#### "401 Unauthorized" Error
- **Cause**: Invalid or expired token
- **Solution**: Generate a new token or check token expiration

#### "403 Forbidden" Error
- **Cause**: Token lacks required scopes
- **Solution**: Generate token with appropriate scopes

#### "Token not found in database"
- **Cause**: Token was revoked or deleted
- **Solution**: Generate a new token

#### Connection Refused
- **Cause**: MCP server not running or wrong port
- **Solution**: Check server status and configuration

### Debug Mode

Enable debug logging to troubleshoot authentication:

```bash
# Server side
export APP_DEBUG=true
export LOG_LEVEL=DEBUG

# Check logs
docker logs dhafnck-mcp-server
```

### Testing Authentication

Test your token configuration:

```bash
# Test with curl
curl -X POST http://localhost:8000/mcp/initialize \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-06-18"},"id":1}'
```

Expected response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "tools": {},
      "resources": {}
    }
  },
  "id": 1
}
```

## Migration Guide

### From No Authentication

1. Generate API tokens for all clients
2. Update client configurations with Bearer tokens
3. Enable JWT authentication on server
4. Test all connections

### From Environment Variable Bearer Token

1. Generate JWT tokens to replace static tokens
2. Update `MCP_AUTH_TYPE` from `env` to `jwt`
3. Update client configurations with new tokens
4. Remove old `MCP_BEARER_TOKEN` environment variable

## Advanced Configuration

### Custom Token Validation

Extend the `JWTBearerAuthProvider` for custom validation:

```python
from fastmcp.server.auth.providers.jwt_bearer import JWTBearerAuthProvider

class CustomJWTProvider(JWTBearerAuthProvider):
    async def load_access_token(self, token: str):
        # Add custom validation logic
        result = await super().load_access_token(token)
        
        if result:
            # Additional checks
            if not self.check_ip_whitelist(result.metadata):
                return None
        
        return result
```

### Multi-Tenant Configuration

Support multiple organizations with audience claims:

```python
# Server configuration
auth = JWTBearerAuthProvider(
    audience=["org1.example.com", "org2.example.com"],
    required_scopes=["mcp:access"]
)

# Token generation includes audience
token_data = {
    "aud": "org1.example.com",
    "sub": user_id,
    "scopes": ["execute:mcp"]
}
```

## API Reference

### Token Endpoints

- `POST /api/v2/tokens/` - Generate new token
- `GET /api/v2/tokens/` - List user's tokens
- `GET /api/v2/tokens/{id}` - Get token details
- `DELETE /api/v2/tokens/{id}` - Revoke token
- `PATCH /api/v2/tokens/{id}` - Update token
- `POST /api/v2/tokens/{id}/rotate` - Rotate token
- `POST /api/v2/tokens/validate` - Validate token
- `GET /api/v2/tokens/{id}/usage` - Get usage statistics

### MCP Endpoints (Protected)

All MCP endpoints require valid Bearer token when authentication is enabled:

- `POST /mcp/initialize` - Initialize MCP session
- `POST /mcp/` - Send MCP messages
- `GET /mcp/sse` - Server-sent events stream

## Support

For issues or questions:
- Check the [troubleshooting guide](#troubleshooting)
- Review server logs: `docker logs dhafnck-mcp-server`
- Open an issue on GitHub
- Contact support with token ID (never share the actual token)