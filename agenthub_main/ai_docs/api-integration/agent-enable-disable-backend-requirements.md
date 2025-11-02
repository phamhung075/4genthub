# Agent Enable/Disable Feature - Backend Requirements

**Date**: 2025-11-02
**Status**: Frontend Complete - Backend Implementation Needed
**Feature**: Agent selection via enable/disable toggle

## Overview

The frontend now supports enabling/disabling specific agent instances to solve the duplicate agent name problem (same name, different creators: default/private/public). Users can select which specific agents they want active for use in call_agent tools.

## Frontend Changes Completed ✅

1. **Type Definitions** (`agenthub-frontend/src/types/agentTypes.ts`):
   - Added `is_enabled: boolean` field to `UserAgentInstance` interface (line 60)
   - Added `is_enabled?: boolean | null` to `UpdateInstanceRequest` interface (line 108)

2. **API Integration** (`agenthub-frontend/src/services/apiV2.ts`):
   - Updated `updateInstance` method parameters to include `is_enabled` (line 1052)

3. **Hook Methods** (`agenthub-frontend/src/hooks/useAgentManagement.ts`):
   - Added `toggleEnabled` method to `useUserAgentInstances` hook (lines 251-273)
   - Returns `Promise<boolean>` indicating success/failure
   - Updates local state after successful API call

4. **UI Components** (`agenthub-frontend/src/pages/MyAgentsPage.tsx`):
   - Added checkbox toggle with loading state (lines 937-951)
   - Added enabled status badge: blue "✓ Enabled" / gray "Disabled" (lines 892-900)
   - Integrated with `toggleEnabled` method for real-time updates
   - Proper error handling and loading states

## Backend Changes Required 🔧

### 1. Database Schema Migration

**Table**: `user_agent_instances`

```sql
-- Add is_enabled column with default TRUE for existing rows
ALTER TABLE user_agent_instances
ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT TRUE;

-- Add index for filtering queries
CREATE INDEX idx_user_agent_instances_enabled
ON user_agent_instances(user_id, is_enabled)
WHERE is_enabled = TRUE;
```

**Migration Script Location**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/migrations/`

**Migration Name**: `add_is_enabled_to_user_agent_instances.py`

### 2. ORM Model Update

**File**: `agenthub_main/src/fastmcp/agent_management/domain/entities/user_agent_instance.py`

```python
class UserAgentInstance:
    """
    User's agent instance entity with customization and selection
    """
    # ... existing fields ...

    is_enabled: bool = True  # Default to enabled for new instances
```

### 3. API Endpoint Updates

**File**: `agenthub_main/src/fastmcp/agent_management/interface/rest/models.py`

Update Pydantic models:

```python
class UpdateInstanceRequest(BaseModel):
    """Request to update agent instance"""
    agent_name: Optional[str] = None
    is_enabled: Optional[bool] = None  # NEW FIELD
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    # ... rest of fields ...
```

**File**: `agenthub_main/src/fastmcp/agent_management/interface/rest/agent_management_routes.py`

Update PUT endpoint handler:

```python
@router.put("/instances/{instance_id}")
async def update_instance(
    instance_id: str,
    request: UpdateInstanceRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update agent instance
    """
    # ... existing code ...

    # Handle is_enabled update
    if request.is_enabled is not None:
        instance.is_enabled = request.is_enabled

    # ... rest of update logic ...
```

### 4. Agent Listing Filter

**File**: `agenthub_main/src/fastmcp/agent_management/domain/repositories/user_agent_instance_repository.py`

Add method to get only enabled instances:

```python
async def get_enabled_instances(self, user_id: str) -> List[UserAgentInstance]:
    """
    Get all enabled agent instances for a user
    Used when populating call_agent tool options
    """
    return await self.session.execute(
        select(UserAgentInstance)
        .where(
            UserAgentInstance.user_id == user_id,
            UserAgentInstance.is_enabled == True
        )
        .order_by(UserAgentInstance.agent_name)
    ).scalars().all()
```

### 5. call_agent Tool Integration

**File**: `agenthub_main/src/fastmcp/server/tools/call_agent_tool.py` (or similar)

Update call_agent logic to filter by enabled status:

```python
async def get_available_agents(user_id: str) -> List[str]:
    """
    Get list of agent names available for call_agent tool
    Only returns enabled agents
    """
    repository = UserAgentInstanceRepository(session)
    enabled_instances = await repository.get_enabled_instances(user_id)

    return [instance.agent_name for instance in enabled_instances]
```

## API Request/Response Examples

### Frontend Request (Update Enabled Status)

```http
PUT /api/v2/agent-management/instances/550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json
Authorization: Bearer <token>

{
  "is_enabled": false
}
```

### Backend Response

```json
{
  "success": true,
  "instance": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "agent_name": "coding-agent",
    "is_enabled": false,
    "visibility": "private",
    "is_customized": false,
    "usage_count": 5,
    "created_at": "2025-11-02T10:00:00Z",
    "updated_at": "2025-11-02T11:45:00Z",
    ...
  },
  "message": "Agent disabled successfully"
}
```

## Testing Checklist

### Backend Tests Required

- [ ] **Unit Tests**:
  - [ ] Test ORM model with is_enabled field
  - [ ] Test update_instance with is_enabled parameter
  - [ ] Test get_enabled_instances repository method

- [ ] **Integration Tests**:
  - [ ] Test PUT endpoint updates is_enabled correctly
  - [ ] Test enabled instances are filtered properly
  - [ ] Test disabled agents don't appear in call_agent options

- [ ] **E2E Tests**:
  - [ ] Test complete flow: enable → call_agent shows agent
  - [ ] Test complete flow: disable → call_agent hides agent
  - [ ] Test multiple users have independent enabled states

### Frontend Tests (Already Passing)

- [x] Type definitions include is_enabled field
- [x] API call includes is_enabled parameter
- [x] Toggle checkbox updates state correctly
- [x] Badge displays correct status
- [x] Loading state prevents multiple clicks

## Migration Strategy

1. **Add Column** with DEFAULT TRUE (all existing agents remain enabled)
2. **Update ORM Models** to include new field
3. **Deploy Backend** with updated endpoints
4. **Test Frontend** integration
5. **Update call_agent Logic** to filter by enabled status
6. **Document** for users in help docs

## Benefits

✅ **Solves Duplicate Agent Problem**: Users can select specific agents when names collide (default vs private vs public from different creators)

✅ **Clean Management**: Non-destructive - disable instead of delete, re-enable anytime

✅ **Better UX**: Clear visual feedback (badges, checkboxes, loading states)

✅ **Performance**: Indexed queries for fast filtering

✅ **Scalability**: Works with large agent collections

## Notes

- Default value is `TRUE` to maintain backward compatibility
- Frontend handles all UI state management
- Backend just needs to persist the boolean flag and filter queries
- No breaking changes to existing functionality
