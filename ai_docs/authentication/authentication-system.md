# Authentication System Architecture

## Overview
The agenthub platform implements a comprehensive JWT-based authentication system that supports multiple token types, flexible validation, and seamless integration with MCP protocol and frontend applications.

## Core Components

### 1. JWT Service (`jwt_service.py`)
Central service for token generation and validation with enhanced flexibility.

#### Key Features
- **Multi-format support**: Accepts both `access` and `api_token` types
- **Flexible user identification**: Checks both `sub` and `user_id` fields
- **Graceful degradation**: Allows certain format variations for compatibility
- **Comprehensive validation**: Verifies signature, expiration, and claims

#### Token Structure
```python
{
    "sub": "user-id",           # Standard JWT subject
    "user_id": "user-id",        # Alternative user ID field
    "type": "access",            # Token type (access/api_token)
    "scopes": ["execute:mcp"],  # Permission scopes
    "exp": 1234567890,          # Expiration timestamp
    "iat": 1234567890,          # Issued at timestamp
    "token_id": "tok_xxx"       # Optional token identifier
}
```

### 2. JWT Auth Backend (`jwt_auth_backend.py`)
MCP integration layer for authentication.

#### Responsibilities
- Extract and validate tokens from requests
- Create MCP-compatible user objects
- Handle authentication failures gracefully
- Support multiple token formats

#### Authentication Flow
```python
1. Extract token from Authorization header
2. Validate token with JWT service
3. Extract user information (sub or user_id)
4. Create AccessToken for MCP
5. Return authenticated user context
```

### 3. HTTP Server Integration (`http_server.py`)
Middleware integration for request authentication.

#### Token Verifier
Custom verifier that bridges JWT authentication with MCP protocol:
```python
class TokenVerifier:
    def verify_token(self, token: str) -> Optional[AccessToken]:
        # Detect provider type
        # Handle JWT middleware
        # Create AccessToken with proper fields
        # Return authenticated context
```

#### Defensive Programming
- Checks for attribute existence before access
- Handles missing middleware gracefully
- Provides fallback for undefined methods

### 4. Token Management Routes (`token_routes.py`)
RESTful API for token lifecycle management.

#### Endpoints
- `POST /api/tokens/generate` - Create new token
- `GET /api/tokens` - List user tokens
- `GET /api/tokens/{token_id}` - Get token details
- `POST /api/tokens/{token_id}/revoke` - Revoke token
- `POST /api/tokens/{token_id}/refresh` - Refresh token
- `DELETE /api/tokens/{token_id}` - Delete token

#### Metadata Handling Fix
```python
# Fixed validation error with SQLAlchemy MetaData
"metadata": token.token_metadata if isinstance(token.token_metadata, dict) else {}
```

## Token Types

### 1. Access Tokens
- **Purpose**: Short-lived tokens for API access
- **Duration**: 24 hours default
- **Use Case**: Regular API operations

### 2. API Tokens
- **Purpose**: Long-lived tokens for integration
- **Duration**: 30+ days
- **Use Case**: MCP clients, CI/CD, automation

### 3. Refresh Tokens
- **Purpose**: Token renewal without re-authentication
- **Duration**: 7 days
- **Use Case**: Seamless token rotation

## Scope System

### Available Scopes
```python
SCOPES = [
    "read:tasks",      # View tasks
    "write:tasks",     # Create/update tasks
    "read:context",    # View context
    "write:context",   # Update context
    "read:agents",     # View agents
    "write:agents",    # Configure agents
    "execute:mcp",     # Execute MCP tools
    "admin:system"     # System administration
]
```

### Scope Validation
- Token must have required scope for endpoint
- Hierarchical scope inheritance
- Default scopes for new tokens

## Security Features

### 1. Token Security
- **HS256 signing**: HMAC with SHA-256
- **Secret rotation**: Support for key rotation
- **Expiration enforcement**: Automatic token expiry
- **Revocation support**: Immediate token invalidation

### 2. Request Security
- **Bearer token format**: Industry standard
- **HTTPS enforcement**: In production
- **CORS configuration**: Controlled cross-origin access
- **Rate limiting**: Prevent abuse

### 3. Validation Layers
```python
1. HTTP layer - Bearer token extraction
2. JWT layer - Signature and claims validation
3. Scope layer - Permission verification
4. Business layer - Resource access control
```

## Integration Points

### 1. Frontend Integration
```javascript
// Using token in frontend
const response = await fetch('/api/resource', {
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    }
});
```

### 2. MCP Client Integration
```json
{
  "mcpServers": {
    "agenthub": {
      "type": "http",
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

### 3. Docker Environment
```dockerfile
ENV JWT_SECRET_KEY=${JWT_SECRET_KEY}
ENV JWT_ALGORITHM=HS256
ENV JWT_EXPIRATION_MINUTES=1440
```

## Recent Fixes

### 1. Token Type Compatibility (2025-08-20)
**Problem**: Frontend generates `api_token` type, backend expects `access`
**Solution**: Modified JWT service to accept both types
```python
if token_type != expected_type:
    if expected_type == "access" and token_type == "api_token":
        logger.debug("Accepting api_token type for access token")
```

### 2. User ID Field Flexibility (2025-08-20)
**Problem**: Tokens use different user ID fields
**Solution**: Check both `sub` and `user_id` fields
```python
user_id = payload.get("sub") or payload.get("user_id")
```

### 3. Metadata Validation Error (2025-08-20)
**Problem**: SQLAlchemy MetaData object causing Pydantic validation errors
**Solution**: Type checking before serialization
```python
"metadata": token.token_metadata if isinstance(token.token_metadata, dict) else {}
```

### 4. Middleware Attribute Errors (2025-08-20)
**Problem**: JWTAuthMiddleware missing expected attributes
**Solution**: Defensive attribute checking
```python
getattr(auth, 'required_scopes', None) or []
```

## Configuration

### Environment Variables
```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440  # 24 hours
JWT_REFRESH_EXPIRATION_DAYS=7

# Authentication Settings
AUTH_ENABLED=true
AUTH_REQUIRED_ENDPOINTS=/api/*,/mcp/*
AUTH_OPTIONAL_ENDPOINTS=/health,/register
```

### Docker Secrets
```yaml
secrets:
  jwt_secret:
    external: true
    
services:
  mcp-server:
    secrets:
      - jwt_secret
    environment:
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret
```

## Testing Authentication

### 1. Generate Test Token
```python
import jwt
from datetime import datetime, timedelta

secret = 'your-secret-key'
payload = {
    'sub': 'test-user',
    'type': 'access',
    'scopes': ['execute:mcp'],
    'exp': datetime.utcnow() + timedelta(hours=24)
}

token = jwt.encode(payload, secret, algorithm='HS256')
```

### 2. Validate Token
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/me
```

### 3. Test MCP Access
```bash
curl -X POST http://localhost:8000/mcp/ \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Monitoring

### Key Metrics
- Token generation rate
- Authentication success/failure ratio
- Token expiration events
- Invalid token attempts
- Scope violation attempts

### Log Points
```python
# Successful authentication
logger.info(f"User {user_id} authenticated successfully")

# Failed authentication
logger.warning(f"Authentication failed: {error}")

# Token operations
logger.info(f"Token {token_id} generated for user {user_id}")
logger.info(f"Token {token_id} revoked")
```

## Best Practices

### 1. Token Management
- Use short-lived access tokens
- Implement token refresh mechanism
- Revoke tokens on logout
- Monitor token usage

### 2. Security
- Never log token values
- Use environment variables for secrets
- Rotate secrets regularly
- Implement rate limiting

### 3. Error Handling
- Return generic error messages
- Log detailed errors internally
- Handle edge cases gracefully
- Provide clear authentication headers

## Future Enhancements

### 1. OAuth2 Support
- GitHub OAuth integration
- Google OAuth integration
- SAML support for enterprise

### 2. Advanced Security
- Multi-factor authentication
- Device fingerprinting
- Anomaly detection
- IP allowlisting

### 3. Token Features
- Token families for related services
- Delegated tokens with reduced scope
- Time-bound tokens for specific operations
- Token templates for common use cases