# Authentication System Documentation

## Quick Start

The DhafnckMCP platform uses a **dual-token authentication system**:

1. **Supabase Tokens** - For user authentication (Frontend ↔ Backend)
2. **MCP Tokens** - For tool/API authorization (MCP Tools ↔ Backend)

## Key Concepts

### Why Two Token Systems?

- **Separation of Concerns**: User auth vs tool auth
- **Security**: Different signing keys and validation logic
- **Flexibility**: Users can have multiple MCP tokens with different scopes
- **Scalability**: MCP tokens can be used by automated tools without user context

### Token Flow Summary

```
1. User Login → Supabase → JWT Token → Frontend Cookies
2. Frontend Request → Include Supabase Token → Backend Validates
3. Generate MCP Token → Backend Creates JWT → Return to User
4. MCP Tool → Include MCP Token → Backend Validates → Process Request
```

## Documentation Structure

### Architecture Guides
- [Authentication Architecture](../architecture/authentication-architecture.md) - Complete system design
- [Token Flow](../architecture/token-flow.md) - Detailed token lifecycle

### API Documentation
- [Authentication API](../api/authentication.md) - Endpoint reference
- [Token Management API](../api/token-api.md) - Token CRUD operations

### Integration Guides
- [Frontend Auth Integration](../frontend/auth-integration.md) - React/TypeScript setup
- [MCP Tool Integration](../integrations/mcp-tools.md) - Using tokens with tools
- [Supabase Setup](../integrations/supabase.md) - External auth configuration

### Security Documentation
- [Security Best Practices](../security/best-practices.md) - Implementation guidelines
- [Token Security](../security/token-security.md) - Token handling rules

## Quick Reference

### Environment Variables

```bash
# Required for authentication
SUPABASE_URL=https://[project].supabase.co
SUPABASE_ANON_KEY=eyJ...
JWT_SECRET_KEY=your-secret-key
DHAFNCK_AUTH_ENABLED=true
```

### Common Operations

#### User Login (Frontend)
```typescript
const { login } = useAuth();
await login(email, password);
```

#### Generate MCP Token (Frontend)
```typescript
const token = await tokenService.generateToken({
  name: "My Token",
  scopes: ["mcp:read", "mcp:write"],
  expires_in_days: 30
});
```

#### Use MCP Token (MCP Tool)
```bash
curl -H "Authorization: Bearer ${MCP_TOKEN}" \
  http://localhost:8000/api/v2/tasks
```

## Authentication Stack Overview

### Active Components

| Component | Purpose | Location |
|-----------|---------|----------|
| JWT Auth Middleware | Validates tokens | `auth/middleware/jwt_auth_middleware.py` |
| Dual Auth Middleware | Combines auth methods | `auth/middleware/dual_auth_middleware.py` |
| Request Context | Propagates auth state | `auth/middleware/request_context_middleware.py` |
| JWT Bearer Provider | MCP token validation | `server/auth/providers/jwt_bearer.py` |
| Supabase Client | External auth | `auth/supabase_client.py` |

### Removed Components (2025-08-26)

The following were removed in the authentication cleanup:
- FastAPI Auth Bridge (not needed, using Starlette)
- Bearer Env Provider (replaced by JWT)
- Dev Auth Endpoints (security risk)
- Legacy MCP Token Service
- Thread Context Manager (async doesn't need it)
- User Context Middleware (duplicate functionality)

## Token Types

### Supabase Token Structure
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "roles": ["authenticated"],
  "exp": 1234567890
}
```

### MCP Token Structure
```json
{
  "token_id": "tok_abc123",
  "user_id": "user-uuid",
  "scopes": ["mcp:read", "mcp:write"],
  "type": "api_token",
  "exp": 1234567890
}
```

## Available Scopes

| Scope | Description | Operations |
|-------|-------------|------------|
| `mcp:access` | Basic access | Health checks |
| `mcp:read` | Read operations | GET endpoints |
| `mcp:write` | Write operations | POST, PUT, DELETE |
| `mcp:execute` | Execute tools | MCP tool execution |
| `mcp:admin` | Admin operations | User management |

## Security Features

- **JWT Signing**: All tokens cryptographically signed
- **Token Hashing**: MCP tokens stored hashed in database
- **Rate Limiting**: Per-token request limits
- **Expiration**: Automatic token expiry
- **Secure Storage**: httpOnly cookies for browser tokens
- **Scope Validation**: Operation-level permission checks

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "No authentication provided" | Missing token | Check cookies/headers |
| "Token expired" | Past expiry date | Refresh or regenerate |
| "Invalid token" | Bad signature | Verify token format |
| "Insufficient scopes" | Missing permissions | Generate token with required scopes |
| "Rate limit exceeded" | Too many requests | Wait or increase limit |

### Debug Commands

```bash
# Check if auth is enabled
echo $DHAFNCK_AUTH_ENABLED

# Validate JWT token
python -c "import jwt; print(jwt.decode('YOUR_TOKEN', options={'verify_signature': False}))"

# Test authentication
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/health
```

## Migration Guide

### From Single Token to Dual Token System

1. **Update Environment**
   - Add Supabase configuration
   - Set JWT_SECRET_KEY
   - Enable DHAFNCK_AUTH_ENABLED

2. **Update Frontend**
   - Use AuthContext for user auth
   - Use TokenService for MCP tokens
   - Update API calls with proper tokens

3. **Update MCP Tools**
   - Replace user tokens with MCP tokens
   - Request appropriate scopes
   - Handle rate limiting

## Best Practices

1. **Token Security**
   - Never log or expose tokens
   - Store securely (cookies/env vars)
   - Rotate tokens regularly
   - Use minimal required scopes

2. **Error Handling**
   - Handle 401 with token refresh
   - Provide clear error messages
   - Log authentication failures
   - Monitor for suspicious activity

3. **Performance**
   - Cache token validations
   - Use database indexes
   - Implement request batching
   - Monitor token usage patterns

## Getting Help

- Check [Authentication Architecture](../architecture/authentication-architecture.md) for design details
- Review [Token Flow](../architecture/token-flow.md) for step-by-step processes
- See [Security Best Practices](../security/best-practices.md) for implementation guidelines
- File issues at [GitHub Issues](https://github.com/your-repo/issues)

## Related Documentation

- [API Authentication](../api/authentication.md)
- [Frontend Integration](../frontend/auth-integration.md)
- [Supabase Setup](../integrations/supabase.md)
- [Security Guidelines](../security/best-practices.md)