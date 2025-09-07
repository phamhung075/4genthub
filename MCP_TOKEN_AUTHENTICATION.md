# MCP Token-Based Authentication Architecture

## Overview
The DhafnckMCP server uses **token-based authentication** for secure access control. This means:
- **CORS can be fully open** (`*`) since security is handled by tokens
- **Any Claude Code instance** can connect from any location
- **Tokens are generated from the frontend** after user authentication
- **Each request must include a valid token** to access MCP tools

## Security Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Claude Code    │────▶│   MCP Server    │◀────│    Frontend     │
│  (Any PC)       │     │  (Token Auth)   │     │  (Token Gen)    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │                        │
        │  1. Request           │                        │
        │  + Bearer Token       │                        │
        │                       │                        │
        └──────────────────────▶│                        │
                                │  2. Validate Token     │
                                │                        │
                                │◀───────────────────────┘
                                │  3. Generate Token
                                │  (After Login)
```

## How It Works

### 1. User Authentication (Frontend)
```javascript
// User logs in via frontend
const response = await fetch('/api/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});
const { token } = await response.json();
```

### 2. Token Generation (Backend)
```python
# Backend generates MCP token after successful authentication
mcp_token = generate_mcp_token(user_id, permissions)
return {"token": mcp_token, "expires_in": 86400}
```

### 3. Claude Code Configuration
```json
{
  "mcpServers": {
    "dhafnck-mcp": {
      "url": "https://dhafnck-mcp-backend.92.5.226.7.nip.io/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN_HERE"
      }
    }
  }
}
```

### 4. MCP Server Validation
```python
# Every request is validated
def validate_request(request):
    token = extract_bearer_token(request.headers)
    if not token:
        raise Unauthorized("No token provided")
    
    user_data = validate_token(token)
    if not user_data:
        raise Unauthorized("Invalid token")
    
    return process_mcp_request(request, user_data)
```

## CORS Configuration

Since security is handled by tokens, CORS can be fully open:

### Backend Environment Variables
```bash
# Allow all origins - security via tokens
CORS_ORIGINS=*

# Token authentication settings
AUTH_ENABLED=true
AUTH_PROVIDER=local  # or keycloak
JWT_SECRET_KEY=your-secret-key-here
TOKEN_EXPIRY=86400  # 24 hours
```

### Why CORS Can Be Open

1. **Token Required**: Every MCP request must include a valid Bearer token
2. **Token Validation**: Server validates token before processing any request
3. **User Context**: Token contains user ID and permissions
4. **Expiration**: Tokens expire after set time (default 24 hours)
5. **Revocation**: Tokens can be revoked server-side if needed

## Token Lifecycle

### Generation Flow
```
Frontend Login → Backend Auth → Generate Token → Return to Frontend → Share with Claude Code
```

### Usage Flow
```
Claude Code → Include Token in Headers → MCP Server → Validate Token → Process Request
```

### Expiration Flow
```
Token Expires → Request Fails → User Re-authenticates → New Token Generated
```

## Security Benefits

### ✅ Advantages of Token-Based Auth

1. **Stateless**: Server doesn't need to maintain session state
2. **Scalable**: Works across multiple servers/instances
3. **Flexible**: Claude Code can run from any location
4. **Secure**: Tokens can include encrypted user data and permissions
5. **Auditable**: Every request can be traced to a specific user/token

### 🔒 Security Best Practices

1. **Use HTTPS**: Always use HTTPS in production to protect tokens in transit
2. **Short Expiry**: Keep token expiry times reasonable (24-48 hours)
3. **Secure Storage**: Store tokens securely in Claude Code configuration
4. **Rotate Keys**: Regularly rotate JWT_SECRET_KEY
5. **Monitor Usage**: Log and monitor token usage for anomalies

## Implementation Details

### Token Structure (JWT)
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": "user-123",
    "email": "user@example.com",
    "permissions": ["mcp.tools.use", "mcp.resources.read"],
    "iat": 1703001600,
    "exp": 1703088000
  },
  "signature": "..."
}
```

### Token Validation Middleware
```python
class TokenAuthMiddleware:
    async def __call__(self, request):
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"error": "No token provided"}, 401)
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate token
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            request.state.user_id = payload["user_id"]
            request.state.permissions = payload.get("permissions", [])
        except jwt.ExpiredSignatureError:
            return JSONResponse({"error": "Token expired"}, 401)
        except jwt.InvalidTokenError:
            return JSONResponse({"error": "Invalid token"}, 401)
        
        # Continue processing
        return await call_next(request)
```

## Claude Code Setup

### 1. Get Token from Frontend
1. Log in to the frontend application
2. Go to Token Management page
3. Generate a new MCP token
4. Copy the token

### 2. Configure Claude Code
Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "dhafnck-mcp": {
      "url": "https://your-mcp-server.com/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### 3. Test Connection
```bash
# Test with curl
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     -X POST https://your-mcp-server.com/mcp \
     -d '{"method": "list_tools"}'
```

## Troubleshooting

### "Unauthorized" Error
- **Cause**: Missing or invalid token
- **Fix**: Generate new token from frontend

### "Token Expired" Error
- **Cause**: Token has exceeded expiry time
- **Fix**: Generate new token from frontend

### "CORS Error" (Should not happen)
- **Cause**: CORS_ORIGINS not set to `*`
- **Fix**: Set `CORS_ORIGINS=*` in backend environment

## Summary

The DhafnckMCP server uses **token-based authentication** which means:

1. **CORS is open** (`*`) - Any origin can make requests
2. **Security via tokens** - Every request must have valid token
3. **Tokens from frontend** - Users authenticate and get tokens
4. **Claude Code ready** - Works from any PC with valid token
5. **No CORS restrictions needed** - Token validation provides security

This architecture provides maximum flexibility for Claude Code access while maintaining security through token authentication.