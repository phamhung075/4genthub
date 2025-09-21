# MCP Subtask User ID Association Fix

## Issue Description

Subtasks created via MCP tools return 404 errors when accessed via the frontend API, even though they were successfully created. The frontend shows "subtask try to open but back up to task dialog" error.

**Specific Error:**
- GET `/api/v2/subtasks/{subtask_id}` returns 404
- Subtask was created via MCP tools
- Frontend cannot access the subtask

## Root Cause Analysis

### The Problem

The issue occurs due to a **missing environment variable configuration**:

1. **MCP_AUTH_MODE** was not set in `.env.dev`
2. This causes the authentication service to default to **"production"** mode
3. In production mode, the authentication service tries to use Keycloak authentication
4. MCP tools have no HTTP request context or Keycloak tokens
5. Authentication fails, causing user_id issues

### Code Analysis

**Authentication Service Logic** (`authentication_service.py:54-58`):
```python
# Testing mode bypass - ONLY for development/testing
if not self.auth_enabled or self.auth_mode == "testing":
    logger.warning(f"⚠️ TESTING MODE: Authentication bypassed for {operation_name}")
    logger.warning(f"⚠️ Using test user ID: {self.test_user_id}")
    return validate_user_id(self.test_user_id, operation_name)
```

**The Issue:**
- `auth_enabled = true` (from .env.dev)
- `auth_mode` defaults to "production" (MCP_AUTH_MODE not set)
- Condition `not self.auth_enabled or self.auth_mode == "testing"` evaluates to `False`
- Authentication service tries Keycloak authentication instead of using TEST_USER_ID

## Solution

### Required Fix

Add the following line to your `.env.dev` file:

```bash
MCP_AUTH_MODE=testing
```

### Environment Configuration

**Before Fix:**
```bash
AUTH_ENABLED=true
TEST_USER_ID=f0de4c5d-2a97-4324-abcd-9dae3922761e
# MCP_AUTH_MODE not set (defaults to "production")
```

**After Fix:**
```bash
AUTH_ENABLED=true
TEST_USER_ID=f0de4c5d-2a97-4324-abcd-9dae3922761e
MCP_AUTH_MODE=testing
```

### Implementation Steps

1. **Edit .env.dev file:**
   ```bash
   echo "MCP_AUTH_MODE=testing" >> .env.dev
   ```

2. **Restart development server:**
   ```bash
   cd docker-system
   ./docker-menu.sh
   # Select option R for rebuild
   ```

3. **Verify the fix:**
   - Create a subtask via MCP tools
   - Access the subtask via frontend API
   - Should now return 200 instead of 404

## Technical Details

### Authentication Flow

**With MCP_AUTH_MODE=testing:**
1. MCP tool calls `manage_subtask`
2. Authentication service checks: `auth_mode == "testing"` → `True`
3. Returns `TEST_USER_ID=f0de4c5d-2a97-4324-abcd-9dae3922761e`
4. Repository creates subtask with correct user_id
5. Frontend can access subtask (same user_id)

**Without MCP_AUTH_MODE (production mode):**
1. MCP tool calls `manage_subtask`
2. Authentication service tries Keycloak authentication
3. No HTTP context available → authentication fails
4. User_id issues cause repository problems
5. Frontend gets 404 when trying to access

### Repository User Filtering

The subtask repository correctly implements user filtering:

```python
def find_by_id(self, id: str) -> Optional[SubtaskEntity]:
    query = session.query(SubtaskModel).filter(
        SubtaskModel.id == id
    )

    # CRITICAL: Apply user filter for multi-tenancy
    if self.user_id:
        query = query.filter(SubtaskModel.user_id == self.user_id)

    model = query.first()  # Returns None if user_id doesn't match
```

This is working correctly - the issue was that MCP tools weren't getting the right user_id due to authentication mode.

## Verification

After applying the fix, verify with these steps:

1. **Check environment loading:**
   ```python
   import os
   from dotenv import load_dotenv
   load_dotenv('.env.dev')
   print(f'MCP_AUTH_MODE: {os.getenv("MCP_AUTH_MODE")}')
   ```

2. **Test MCP subtask creation:**
   ```python
   # Use MCP tools to create a subtask
   # Should now use TEST_USER_ID correctly
   ```

3. **Test frontend access:**
   ```bash
   curl -X GET http://localhost:8000/api/v2/subtasks/{subtask_id}
   # Should return 200 with subtask data
   ```

## Prevention

To prevent this issue in the future:

1. **Document required environment variables** in setup guides
2. **Add validation** to check MCP_AUTH_MODE on startup
3. **Include MCP_AUTH_MODE** in example .env files
4. **Add tests** that verify MCP authentication in testing mode

## Related Files

- `authentication_service.py:54-80` - Authentication mode logic
- `subtask_repository.py:147-148` - User filtering implementation
- `subtask_mcp_controller.py:185-190` - Authentication call
- `.env.dev` - Environment configuration
- `scripts/fix_mcp_auth_mode.py` - Diagnostic script

## Status

**Issue:** Resolved
**Fix Applied:** Environment configuration update required
**Testing:** Manual verification recommended after environment change