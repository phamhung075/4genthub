# JWT Authentication State Propagation Fix

**Date**: 2025-08-25  
**Issue**: JWT tokens validated successfully but MCP's RequireAuthMiddleware returns 401 "invalid_token"  
**Status**: ✅ RESOLVED

## Problem Summary

The JWT authentication system was experiencing a paradox where:
- ✅ JWT tokens were being validated successfully 
- ✅ AccessToken objects were being created
- ✅ User context was being set in ContextVar
- ❌ BUT `scope["user"]` was not being set with `AuthenticatedUser` instance
- ❌ MCP's `RequireAuthMiddleware` was rejecting requests with 401 "invalid_token"

## Root Cause

**The Issue**: `JWTAuthBackend` inherited from `BearerAuthProvider` (FastMCP's class) instead of implementing MCP's `TokenVerifier` protocol correctly.

**The Authentication Flow Problem**:
```
1. Starlette's AuthenticationMiddleware calls BearerAuthBackend.authenticate()
2. BearerAuthBackend.authenticate() calls TokenVerifierAdapter.verify_token()  
3. TokenVerifierAdapter.verify_token() calls JWTAuthBackend.load_access_token()
4. BearerAuthBackend.authenticate() should return (AuthCredentials, AuthenticatedUser)
5. Starlette sets these in scope["auth"] and scope["user"] 
6. RequireAuthMiddleware checks scope["user"] for AuthenticatedUser ❌ FAILED HERE
```

**The Missing Link**: Our `JWTAuthBackend` wasn't properly implementing the `TokenVerifier` protocol that MCP's authentication middleware expected.

## Solution

### 1. Fixed JWTAuthBackend Integration (jwt_auth_backend.py)

**Before**:
```python
class JWTAuthBackend(BearerAuthProvider):  # ❌ Wrong base class
    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        # Implementation...
```

**After**:
```python  
class JWTAuthBackend(TokenVerifier):  # ✅ Correct protocol
    async def verify_token(self, token: str) -> Optional[AccessToken]:
        # Same implementation, different method name
        
    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        # Backward compatibility wrapper
        return await self.verify_token(token)
```

### 2. Updated TokenVerifierAdapter (http_server.py)

**Before**:
```python
async def verify_token(self, token: str) -> AccessToken | None:
    # Handle OAuth providers
    if hasattr(self.provider, 'load_access_token'):
        return await self.provider.load_access_token(token)
```

**After**:
```python
async def verify_token(self, token: str) -> AccessToken | None:
    # Handle JWT auth backends (MCP TokenVerifier protocol) ✅ FIRST
    if hasattr(self.provider, 'verify_token'):
        return await self.provider.verify_token(token)
    
    # Handle OAuth providers (FastMCP's OAuthProvider)
    elif hasattr(self.provider, 'load_access_token'):
        return await self.provider.load_access_token(token)
```

### 3. Fixed Role Mapping Issue

**Problem**: UserRole enums were being converted to strings like `"UserRole.DEVELOPER"` instead of `"developer"`.

**Before**:
```python
roles=[str(role) for role in user.roles]  # ❌ "UserRole.DEVELOPER"
```

**After**:
```python
# Extract role names from UserRole enums
role_names = []
for role in user.roles:
    if hasattr(role, 'value'):
        role_names.append(role.value.lower())  # ✅ "developer" 
    else:
        # Handle string roles or other formats
        role_str = str(role).lower()
        if role_str.startswith('userrole.'):
            role_str = role_str.replace('userrole.', '')
        role_names.append(role_str)
```

### 4. Updated UserContextMiddleware Integration

**Before**: Middleware tried to validate tokens itself
**After**: Middleware relies on MCP's authentication pipeline and extracts user context from `request.user`

## The Complete Fixed Flow

```
1. Request with "Authorization: Bearer <jwt_token>"
2. Starlette's AuthenticationMiddleware 
3. → BearerAuthBackend.authenticate()
4.   → TokenVerifierAdapter.verify_token() 
5.     → JWTAuthBackend.verify_token() ✅ 
6.   ← Returns AccessToken
7. ← Returns (AuthCredentials, AuthenticatedUser)
8. Starlette sets scope["user"] = AuthenticatedUser ✅
9. RequireAuthMiddleware checks scope["user"] ✅ PASSES
10. UserContextMiddleware extracts user context from request.user ✅
11. Request reaches protected endpoint ✅
```

## Test Coverage

Added comprehensive integration tests in `test_auth_flow_integration.py`:

- ✅ JWT token verification works
- ✅ BearerAuthBackend creates AuthenticatedUser correctly  
- ✅ RequireAuthMiddleware passes with authenticated user
- ✅ Complete authentication flow works end-to-end
- ✅ Error cases properly rejected

## Key Files Modified

1. **`jwt_auth_backend.py`** - Changed inheritance, added verify_token method
2. **`http_server.py`** - Updated TokenVerifierAdapter to check verify_token first  
3. **`user_context_middleware.py`** - Updated to work with MCP auth flow
4. **`test_auth_flow_integration.py`** - Added comprehensive test coverage

## Verification

Run the integration tests to verify the fix:

```bash
python -m pytest dhafnck_mcp_main/src/tests/auth/mcp_integration/test_auth_flow_integration.py -v
```

## Result

- ✅ JWT authentication now properly integrates with MCP's middleware stack
- ✅ RequireAuthMiddleware correctly identifies authenticated users
- ✅ User context propagation works correctly
- ✅ Role-based scope mapping functions properly
- ✅ Both local and Supabase JWT tokens are supported

The authentication state propagation issue is now resolved, and the JWT authentication system works seamlessly with MCP's authentication architecture.