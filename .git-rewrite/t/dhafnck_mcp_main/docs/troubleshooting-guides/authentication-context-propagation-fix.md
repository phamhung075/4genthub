# Authentication Context Propagation Fix

## Problem Statement

**Issue**: JWT tokens were successfully validated by `DualAuthMiddleware` but MCP request handlers were returning 401 "Authentication required" errors.

**Root Cause**: The authentication context was not propagating from `DualAuthMiddleware` to MCP request handlers. While JWT validation succeeded and `request.state.user_id` was correctly set, the `auth_helper.py` functions used by MCP controllers could not access this authentication information.

**Impact**: All MCP operations requiring authentication failed despite valid JWT tokens, making the system unusable for authenticated users.

## Solution Overview

Implemented `RequestContextMiddleware` using Python's `contextvars` module to capture authentication context from `DualAuthMiddleware` and make it accessible throughout the request lifecycle.

### Authentication Flow (Before Fix)
```
1. HTTP Request with JWT token
2. DualAuthMiddleware validates JWT ✅
3. DualAuthMiddleware sets request.state.user_id ✅
4. MCP Handler calls auth_helper.get_authenticated_user_id()
5. auth_helper.py cannot access request.state ❌
6. Returns 401 "Authentication required" ❌
```

### Authentication Flow (After Fix)
```
1. HTTP Request with JWT token
2. DualAuthMiddleware validates JWT ✅
3. DualAuthMiddleware sets request.state.user_id ✅
4. RequestContextMiddleware captures auth context to contextvars ✅
5. MCP Handler calls auth_helper.get_authenticated_user_id()
6. auth_helper.py reads from contextvars ✅
7. Returns authenticated user_id ✅
```

## Implementation Details

### 1. RequestContextMiddleware

**File**: `src/fastmcp/auth/middleware/request_context_middleware.py`

**Key Features**:
- Thread-safe context storage using Python `contextvars`
- Captures authentication context after `DualAuthMiddleware` processes JWT tokens
- Provides helper functions for accessing authentication data
- Automatic context cleanup to prevent memory leaks
- Comprehensive error handling and logging

**Context Variables**:
```python
_current_user_id: ContextVar[Optional[str]]
_current_user_email: ContextVar[Optional[str]] 
_current_auth_method: ContextVar[Optional[str]]
_current_auth_info: ContextVar[Optional[Dict[str, Any]]]
_request_authenticated: ContextVar[bool]
```

**Helper Functions**:
```python
get_current_user_id() -> Optional[str]
get_current_user_email() -> Optional[str]
get_current_auth_method() -> Optional[str]
is_request_authenticated() -> bool
get_authentication_context() -> Dict[str, Any]
```

### 2. Updated auth_helper.py

**File**: `src/fastmcp/task_management/interface/controllers/auth_helper.py`

**Key Changes**:
- Added priority-based authentication source lookup
- Integrated `RequestContextMiddleware` context variables as Priority 1
- Maintained backward compatibility with existing authentication methods
- Enhanced logging for debugging authentication issues

**Priority Chain**:
1. **Provided user_id** (explicit parameter)
2. **RequestContextMiddleware** context variables (NEW - highest priority)
3. **Legacy request state** (existing method)
4. **Custom user context** middleware
5. **MCP authentication** context

### 3. Middleware Ordering Fix

**File**: `src/fastmcp/server/mcp_entry_point.py`

**Critical Fix**: Corrected middleware execution order

**Before** (Incorrect):
```python
# Wrong order - RequestContext ran before DualAuth
middleware_stack.append(Middleware(RequestContextMiddleware))
middleware_stack.append(Middleware(DualAuthMiddleware))
```

**After** (Correct):
```python
# Correct order - DualAuth runs first, then RequestContext
middleware_stack.append(Middleware(DualAuthMiddleware))      # Executes FIRST
middleware_stack.append(Middleware(RequestContextMiddleware))  # Executes SECOND
```

**Why This Matters**: Starlette middleware executes in reverse order of addition. `RequestContextMiddleware` needs to run AFTER `DualAuthMiddleware` to capture the authentication context that was just set.

## Technical Requirements Fulfilled

✅ **Thread-safe context storage** - Using Python `contextvars`
✅ **Integration with DualAuthMiddleware** - Captures `request.state` set by DualAuth
✅ **Backward compatibility** - Maintains existing authentication methods as fallbacks
✅ **Proper cleanup** - Context variables auto-clear between requests
✅ **Comprehensive error handling** - Graceful degradation when context unavailable
✅ **Proper middleware ordering** - DualAuth → RequestContext → Application

## Testing

### Test Files Added

1. **`test_request_context_middleware.py`**
   - Tests middleware initialization and context capture
   - Verifies context variable isolation between requests
   - Tests error handling and cleanup

2. **`test_auth_helper_request_context_integration.py`**
   - Tests auth_helper integration with new context variables
   - Verifies priority chain and fallback behavior
   - Tests backward compatibility

3. **`test_authentication_context_propagation.py`**
   - End-to-end integration tests
   - Simulates complete authentication flow
   - Verifies concurrent request isolation

### Key Test Scenarios

- ✅ JWT validation → Context capture → MCP handler success
- ✅ Context isolation between concurrent requests
- ✅ Fallback to legacy methods when new context unavailable
- ✅ Proper error handling when authentication fails
- ✅ Middleware ordering verification

## Verification Steps

To verify the fix is working:

1. **Start the server** with authentication enabled
2. **Obtain a JWT token** from the frontend authentication system
3. **Make an MCP request** with the JWT token in Authorization header
4. **Verify success** - Should return authenticated response, not 401

### Example Request
```bash
curl -X POST http://localhost:8000/mcp/manage_task \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "list", "user_id": null}'
```

**Expected**: Success response with user's tasks
**Before Fix**: 401 "Authentication required"

## Impact

### Before Fix
- ❌ All MCP operations failed with 401 errors despite valid JWT tokens
- ❌ Authentication system appeared broken to users
- ❌ System unusable for authenticated operations

### After Fix
- ✅ MCP operations work correctly with JWT tokens
- ✅ No more 401 errors for authenticated requests
- ✅ Seamless authentication experience
- ✅ Proper user isolation and security

## Files Modified

| File | Type | Description |
|------|------|-------------|
| `src/fastmcp/auth/middleware/request_context_middleware.py` | NEW | Core authentication context propagation middleware |
| `src/fastmcp/task_management/interface/controllers/auth_helper.py` | MODIFIED | Added context variable integration with priority chain |
| `src/fastmcp/server/mcp_entry_point.py` | MODIFIED | Fixed middleware ordering (DualAuth → RequestContext) |
| `src/fastmcp/auth/middleware/__init__.py` | MODIFIED | Added exports for new middleware and helpers |

## Configuration

No configuration changes required. The fix is automatically active when:
- Authentication is enabled (`DHAFNCK_AUTH_ENABLED=true`)
- JWT tokens are configured properly
- Server runs in HTTP mode (`--transport=streamable-http`)

## Monitoring and Debugging

Enhanced logging added for debugging authentication issues:

```
🔍 REQUEST_CONTEXT: Processing request POST /mcp/manage_task
✅ REQUEST_CONTEXT: Captured auth context - user_id=user-123, auth_method=local_jwt
🆕 Trying RequestContextMiddleware context variables...
✅ Got user_id from RequestContextMiddleware: user-123
```

## Related Issues

This fix resolves the core authentication context propagation issue. Related authentication fixes:
- Global context user isolation (separate issue)
- JWT secret key configuration (separate issue)  
- Supabase authentication integration (working correctly)

## Conclusion

The `RequestContextMiddleware` solution provides a robust, thread-safe mechanism for propagating authentication context from JWT validation to MCP request handlers. The implementation maintains backward compatibility while solving the critical authentication failure issue.

**Status**: ✅ **RESOLVED** - JWT authentication now works correctly for all MCP operations.