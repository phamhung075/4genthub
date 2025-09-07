# Frontend JWT Token Audience Analysis

## Overview

This document analyzes how the frontend generates and sends JWT tokens, specifically focusing on the audience claim issue where the backend expects `audience='mcp-server'` but receives tokens with different audience values from Supabase.

## Current Token Flow

### 1. Frontend Authentication Process

The frontend uses Supabase authentication through the following flow:

1. **User Login**: `AuthContext.tsx` calls `/auth/supabase/signin`
2. **Supabase Token Generation**: Backend calls Supabase Auth API
3. **Token Storage**: Tokens stored in cookies (`access_token`, `refresh_token`)
4. **API Requests**: `useAuthenticatedFetch.ts` adds `Authorization: Bearer <token>` header

### 2. Token Structure Analysis

Based on the codebase analysis, here's what we know about token structures:

#### Supabase Tokens (from `debug_generate_supabase_token.py`)
```json
{
  "aud": "authenticated",           // ❌ NOT 'mcp-server'
  "sub": "user-id",
  "email": "user@example.com",
  "iss": "https://[project].supabase.co/auth/v1",
  "exp": 1234567890,
  "iat": 1234567890,
  "role": "authenticated",
  "user_metadata": {
    "username": "testuser",
    "email": "user@example.com"
  }
}
```

#### Expected Backend Format (from JWT auth backend)
```json
{
  "aud": "mcp-server",             // ✅ Required by backend
  "sub": "user-id",
  "email": "user@example.com",
  "type": "access" or "api_token"
}
```

## Root Cause Analysis

### Issue 1: Audience Mismatch
- **Supabase tokens**: Use `"aud": "authenticated"`
- **Backend expects**: `"aud": "mcp-server"`
- **Location**: JWT validation in `jwt_auth_backend.py:70` sets `audience = "mcp-server"`

### Issue 2: Token Type Missing
- **Supabase tokens**: No `type` field
- **Backend expects**: `type` field for token type identification
- **Workaround**: Backend adds `"type": "supabase_access"` in `jwt_auth_backend.py:172`

## Current Workarounds in Place

### Dual Authentication System
The backend already implements a dual authentication system in `jwt_auth_backend.py`:

1. **Local JWT Validation**: Tries local JWT secret first
2. **Supabase JWT Validation**: Falls back to Supabase JWT secret with permissive options:

```python
payload = pyjwt.decode(
    token,
    supabase_jwt_secret,
    algorithms=["HS256"],
    options={
        "verify_signature": True,  # ✅ Validates signature
        "verify_aud": False,       # ✅ Ignores audience mismatch
        "verify_iss": False,       # ✅ Ignores issuer
        "verify_exp": False,       # ❌ Should verify expiration
        "verify_iat": False,       # ✅ Ignores issued at
        "verify_nbf": False,       # ✅ Ignores not before
    }
)
```

## Frontend Token Usage Patterns

### 1. Authentication Context (`AuthContext.tsx`)

```typescript
// Login process
const response = await fetch(`${API_BASE_URL}/auth/supabase/signin`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password }),
});

const data = await response.json();
// Receives Supabase tokens with "aud": "authenticated"
setTokens({
  access_token: data.access_token,
  refresh_token: data.refresh_token
});
```

### 2. API Requests (`useAuthenticatedFetch.ts`)

```typescript
// All API requests include:
fetchOptions.headers = {
  ...fetchOptions.headers,
  'Authorization': `Bearer ${tokens.access_token}`,
};
```

### 3. Token Service (`tokenService.ts`)

```typescript
// Token management operations use authenticated fetch
const response = await authenticatedFetch('/api/v2/tokens', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(request),
});
```

## Impact Assessment

### ✅ Currently Working
- Authentication flow works due to dual auth system
- Token validation succeeds with Supabase secret
- User context extraction works
- API requests succeed

### ⚠️ Potential Issues
- **Security**: `verify_exp: False` disables expiration checking
- **Consistency**: Different token formats cause confusion
- **Debugging**: Harder to trace which auth system validated token
- **Future**: Adding stricter validation might break existing flow

## Token Claims Comparison

| Claim | Supabase Token | Expected Backend | Impact |
|-------|----------------|------------------|---------|
| `aud` | `"authenticated"` | `"mcp-server"` | ❌ Handled by `verify_aud: False` |
| `sub` | ✅ User ID | ✅ User ID | ✅ Compatible |
| `email` | ✅ Present | ✅ Required | ✅ Compatible |
| `type` | ❌ Missing | ✅ Required | ⚠️ Added by backend |
| `exp` | ✅ Present | ✅ Expected | ⚠️ Not verified |
| `iat` | ✅ Present | ✅ Expected | ✅ Compatible |
| `iss` | Supabase URL | Not enforced | ✅ Ignored |
| `role` | `"authenticated"` | Not used | ✅ Ignored |

## Recommendations

### Option 1: Fix Backend Validation (Recommended)
Enable proper token validation while maintaining compatibility:

```python
# In jwt_auth_backend.py, enable expiration checking
options={
    "verify_signature": True,
    "verify_aud": False,       # Keep disabled for Supabase
    "verify_iss": False,
    "verify_exp": True,        # ✅ Enable expiration checking
    "verify_iat": False,
    "verify_nbf": False,
}
```

### Option 2: Frontend Token Transformation
Add middleware to transform Supabase tokens before sending to backend:

```typescript
// In useAuthenticatedFetch.ts
const transformSupabaseToken = (supabaseToken: string): string => {
  // Decode, modify audience, re-encode
  // This would require JWT manipulation on frontend
};
```

### Option 3: Backend Token Translation
Create endpoint that exchanges Supabase tokens for backend-compatible tokens:

```python
@router.post("/auth/exchange-token")
async def exchange_supabase_token(supabase_token: str):
    # Validate Supabase token
    # Generate new token with correct audience
    # Return backend-compatible token
```

## Testing Commands

### Test Current Token Flow
```bash
# Get token from frontend cookies
token="your-supabase-token-here"

# Test API call
curl -X GET "http://localhost:8000/api/v2/tasks/" \
  -H "Authorization: Bearer $token" \
  -v
```

### Decode Token Contents
```python
import jwt
token = "your-token-here"
decoded = jwt.decode(token, options={"verify_signature": False})
print(f"Audience: {decoded.get('aud')}")
print(f"Subject: {decoded.get('sub')}")
print(f"Email: {decoded.get('email')}")
print(f"Type: {decoded.get('type', 'NOT_SET')}")
```

## Conclusion

The frontend correctly generates and sends Supabase JWT tokens, but there's an audience claim mismatch. The backend's dual authentication system with permissive Supabase validation currently handles this, but should be improved to enable proper token expiration checking while maintaining compatibility.

The root issue is architectural: mixing Supabase's standard audience claim (`"authenticated"`) with the backend's expected custom audience (`"mcp-server"`). The current workaround is functional but could be more secure.