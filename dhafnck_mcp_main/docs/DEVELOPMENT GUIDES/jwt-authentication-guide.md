# JWT Authentication Guide

## Overview

The DhafnckMCP platform uses Keycloak for authentication with JWT tokens. This guide consolidates all JWT authentication information into a single comprehensive resource.

## Current Architecture (as of 2025-09-02)

### Authentication Flow
1. **Keycloak Authentication**: Primary authentication provider
2. **Local JWT Tokens**: Generated for frontend session management
3. **No MVP Mode**: System requires authentication - no fallback users

### Key Changes from Previous Versions
- ✅ **Removed**: MVP mode and hardcoded user IDs
- ✅ **Removed**: Dual authentication system
- ✅ **Simplified**: Single authentication flow through Keycloak
- ✅ **Required**: All operations require valid JWT tokens

## Configuration

### Environment Variables
```env
# Keycloak Configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=your-client-id
KEYCLOAK_CLIENT_SECRET=your-client-secret

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key  # Must match SUPABASE_JWT_SECRET if used
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Database Configuration
DATABASE_TYPE=postgresql  # Default for local development
```

### JWT Token Structure
```json
{
  "sub": "user-uuid-from-keycloak",
  "exp": 1234567890,
  "iat": 1234567890,
  "aud": "dhafnck-mcp",
  "iss": "keycloak"
}
```

## Implementation Details

### Token Extraction Service
Located at: `src/fastmcp/task_management/interface/mcp_controllers/auth_helper/services/token_extraction_service.py`

```python
class TokenExtractionService:
    """Extracts user information from JWT tokens"""
    
    def extract_user_id_from_token(self, token: str) -> Optional[str]:
        """Extract user ID from JWT token"""
        # Decodes token and returns 'sub' claim
```

### Authentication Service
Located at: `src/fastmcp/task_management/interface/mcp_controllers/auth_helper/services/authentication_service.py`

```python
class AuthenticationService:
    """Handles authentication for MCP operations"""
    
    def get_authenticated_user_id(self, params: dict) -> Optional[str]:
        """Get user ID from authentication context"""
        # No fallbacks - returns None if no valid token
```

## Testing Authentication

### Unit Tests
```bash
# Run authentication tests
pytest dhafnck_mcp_main/src/tests/auth/test_token_extraction.py -v
```

### Manual Testing
1. Start Keycloak server
2. Configure realm and client
3. Generate token through Keycloak
4. Use token in API requests

### Test Coverage
- ✅ Token extraction from headers
- ✅ Token validation
- ✅ User ID extraction
- ✅ Token expiration handling
- ✅ Invalid token rejection

## Troubleshooting

### Common Issues

#### Issue: "No user ID was provided"
**Cause**: Missing or invalid JWT token
**Solution**: Ensure valid token is included in request headers

#### Issue: JWT Secret Mismatch
**Cause**: JWT_SECRET_KEY doesn't match expected value
**Solution**: Verify JWT_SECRET_KEY matches across all services

#### Issue: Token Expired
**Cause**: JWT token has expired
**Solution**: Refresh token or re-authenticate through Keycloak

### Debug Logging
Enable debug logging to troubleshoot authentication issues:
```python
import logging
logging.getLogger('dhafnck.auth').setLevel(logging.DEBUG)
```

## Migration from Previous Versions

### From MVP Mode (Pre-2025-09-02)
1. Remove all hardcoded user IDs
2. Remove MVP_MODE environment variables
3. Implement proper JWT token handling
4. Update all API calls to include authentication

### From Dual Authentication
1. Remove Supabase authentication code
2. Update to use Keycloak-only flow
3. Simplify token validation logic

## Security Best Practices

1. **Never hardcode tokens**: Always use environment variables
2. **Rotate secrets regularly**: Update JWT_SECRET_KEY periodically
3. **Use HTTPS in production**: Protect tokens in transit
4. **Validate token expiration**: Check exp claim
5. **Log authentication failures**: Monitor for security issues

## API Integration

### Required Headers
```http
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

### Example Request
```python
import requests

headers = {
    'Authorization': f'Bearer {jwt_token}',
    'Content-Type': 'application/json'
}

response = requests.post(
    'http://localhost:8000/mcp',
    headers=headers,
    json=payload
)
```

## References

- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [JWT.io](https://jwt.io/) - JWT debugger
- [RFC 7519](https://tools.ietf.org/html/rfc7519) - JWT specification

---

**Last Updated**: 2025-09-02
**Status**: Current and Accurate