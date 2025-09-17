# 🔧 Fix: Keycloak User ID Integration with API Tokens

## Problem
API tokens are being created with `user_id: "anonymous"` instead of the actual Keycloak user ID.

## Root Cause
The token creation endpoint (`/api/v2/tokens`) doesn't properly extract the authenticated user information from the Keycloak token.

## Solution

### 1. Update Token Creation Endpoint

Edit `/home/daihungpham/__projects__/agentic-project/agenthub_main/src/fastmcp/server/routes/api_token_routes_postgresql.py`:

```python
# Line 82-84 - Current problematic code:
# Get user ID from request if available
user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None

# REPLACE WITH:
# Extract user ID from Keycloak authentication
user_id = None
if hasattr(request, "state"):
    # Check for Keycloak user info
    if hasattr(request.state, "user"):
        # From Keycloak authentication middleware
        user_info = request.state.user
        user_id = user_info.get("sub") or user_info.get("user_id") or user_info.get("email")
    elif hasattr(request.state, "user_id"):
        # Direct user_id
        user_id = request.state.user_id
    
    # Also check headers for Keycloak token info
    if not user_id and hasattr(request, "headers"):
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Token validation should have populated user info
            pass
```

### 2. Add Authentication Middleware for Token Routes

Create a new middleware to ensure Keycloak user info is available:

```python
# Add to api_token_routes_postgresql.py

from fastmcp.auth.mcp_keycloak_auth import MCPKeycloakAuth

# Initialize Keycloak auth
keycloak_auth = MCPKeycloakAuth()

async def extract_user_from_keycloak(request: Request, call_next):
    """Middleware to extract user info from Keycloak token"""
    auth_header = request.headers.get("authorization", "")
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            # Validate token with Keycloak
            user_info = await keycloak_auth.validate_mcp_token(token)
            if user_info:
                # Store user info in request state
                request.state.user = user_info
                request.state.user_id = (
                    user_info.get("sub") or 
                    user_info.get("user_id") or 
                    user_info.get("email", "anonymous")
                )
        except Exception as e:
            logger.debug(f"Token validation failed: {e}")
            request.state.user_id = "anonymous"
    else:
        request.state.user_id = "anonymous"
    
    response = await call_next(request)
    return response
```

### 3. Update Token Creation to Use Keycloak User

```python
# In create_token function (line 108):
# CHANGE FROM:
user_id=user_id if user_id else "anonymous",

# CHANGE TO:
user_id=user_id if user_id and user_id != "anonymous" else request.state.get("user_id", "anonymous"),
```

### 4. Add User Email to Token Metadata

```python
# Line 109 - Update token metadata to include user email:
token_metadata={
    "user_email": request.state.user.get("email") if hasattr(request.state, "user") else None,
    "created_via": "keycloak_auth" if user_id != "anonymous" else "anonymous",
    "keycloak_roles": request.state.user.get("roles", []) if hasattr(request.state, "user") else []
}
```

## Database Schema Update

Add columns to track Keycloak integration:

```sql
-- Add columns to api_tokens table
ALTER TABLE api_tokens 
ADD COLUMN IF NOT EXISTS user_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS keycloak_sub VARCHAR(255),
ADD COLUMN IF NOT EXISTS created_via VARCHAR(50) DEFAULT 'anonymous';

-- Create index for user queries
CREATE INDEX IF NOT EXISTS idx_api_tokens_user_email ON api_tokens(user_email);
CREATE INDEX IF NOT EXISTS idx_api_tokens_keycloak_sub ON api_tokens(keycloak_sub);
```

## Query Tokens by User

Once fixed, you can query tokens by user:

```sql
-- List all tokens for a specific user
SELECT 
    id,
    name,
    user_id,
    user_email,
    created_at,
    expires_at,
    is_active,
    scopes
FROM api_tokens
WHERE user_email = 'user@example.com'
   OR keycloak_sub = 'keycloak-user-uuid'
ORDER BY created_at DESC;

-- Count tokens per user
SELECT 
    COALESCE(user_email, user_id) as user_identifier,
    COUNT(*) as token_count,
    COUNT(CASE WHEN is_active THEN 1 END) as active_tokens
FROM api_tokens
GROUP BY COALESCE(user_email, user_id)
ORDER BY token_count DESC;
```

## Testing the Fix

1. **Create a token with authentication**:
```bash
# First login to get Keycloak token
KEYCLOAK_TOKEN=$(curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"password"}' \
  | jq -r '.access_token')

# Create API token with Keycloak auth
curl -X POST http://localhost:8001/api/v2/tokens \
  -H "Authorization: Bearer $KEYCLOAK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API Token",
    "scopes": ["read:tasks", "write:tasks"],
    "expires_in_days": 30
  }'
```

2. **Verify in database**:
```sql
SELECT * FROM api_tokens ORDER BY created_at DESC LIMIT 1;
-- Should show actual user_id from Keycloak, not "anonymous"
```

## Alternative: Direct Integration Approach

If the middleware approach doesn't work, directly integrate in the endpoint:

```python
async def create_token_with_auth(request: Request) -> JSONResponse:
    """Create token with Keycloak authentication"""
    
    # Get Keycloak token from header
    auth_header = request.headers.get("authorization", "")
    user_id = "anonymous"
    user_email = None
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            # Validate with Keycloak
            from fastmcp.auth.mcp_keycloak_auth import MCPKeycloakAuth
            keycloak_auth = MCPKeycloakAuth()
            user_info = await keycloak_auth.validate_mcp_token(token)
            
            if user_info and user_info.get("active"):
                user_id = user_info.get("sub", user_info.get("user_id", "anonymous"))
                user_email = user_info.get("email")
        except Exception as e:
            logger.warning(f"Keycloak validation failed: {e}")
    
    # Continue with token creation using extracted user_id...
```

## Benefits After Fix

1. **User-specific token management**: Each user can see only their tokens
2. **Audit trail**: Track which user created which tokens
3. **Security**: Revoke all tokens for a specific user if needed
4. **Compliance**: Better tracking for regulatory requirements
5. **Analytics**: Understand token usage patterns per user

## Monitoring

Add logging to track the fix:

```python
logger.info(f"Creating API token for user: {user_id} (email: {user_email})")
```

Check logs:
```bash
docker logs agenthub-server 2>&1 | grep "Creating API token"
```

## Rollback Plan

If issues occur, revert to anonymous tokens:
```python
user_id = "anonymous"  # Temporary fallback
```

---

This fix ensures that API tokens are properly linked to Keycloak users, enabling user-specific token management and improving security.