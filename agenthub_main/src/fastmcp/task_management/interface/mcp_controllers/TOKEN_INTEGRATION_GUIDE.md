# Token Consumption Integration Guide for MCP Controllers

## Overview

This guide explains how to integrate token consumption into MCP controllers using the `TokenConsumptionHelper` class.

## Quick Integration Pattern

### Step 1: Import the Helper

```python
from ..token_consumption_helper import TokenConsumptionHelper
```

### Step 2: Initialize in Constructor

```python
class YourMCPController:
    def __init__(self, facade_service):
        self.facade_service = facade_service
        # Initialize token helper with database session
        self.token_helper = TokenConsumptionHelper(session=self._get_session())
```

### Step 3: Add Token Consumption to Operations

**Pattern A: Manual consumption with error handling**

```python
async def create_something(self, user_id=None, **kwargs):
    # Consume tokens BEFORE the operation
    success, error_response = await self.token_helper.consume_tokens(
        operation="create_something",
        user_id=user_id
    )

    if not success:
        # Return error response (402 for insufficient tokens)
        return error_response

    # Proceed with actual operation
    result = await self.facade.create_something(**kwargs)

    # Add token info to response
    token_info = await self.token_helper.get_token_info(
        operation="create_something",
        user_id=user_id
    )
    result["token_info"] = token_info

    return result
```

**Pattern B: One-step consumption and info addition**

```python
async def create_something(self, user_id=None, **kwargs):
    # Execute the operation
    result = await self.facade.create_something(**kwargs)

    # Consume tokens and add info in one step
    success, final_response = await self.token_helper.consume_and_add_info(
        operation="create_something",
        response=result,
        user_id=user_id
    )

    if not success:
        # Rollback operation if needed
        await self.facade.rollback_create_something(result["id"])
        return final_response  # Error response

    return final_response  # Success with token_info
```

**Pattern C: Using standalone function (no class instance)**

```python
from ..token_consumption_helper import consume_tokens_for_operation

async def simple_operation(self, user_id=None):
    # Quick consumption without helper instance
    success, error_response = await consume_tokens_for_operation(
        session=self._get_session(),
        operation="simple_operation",
        user_id=user_id
    )

    if not success:
        return error_response

    # Proceed with operation
    return await self.facade.do_something()
```

## Complete Example: Project Controller Integration

```python
"""
Project MCP Controller with Token Consumption
"""

import logging
from typing import Optional, Dict, Any
from ..token_consumption_helper import TokenConsumptionHelper

logger = logging.getLogger(__name__)


class ProjectMCPController:
    def __init__(self, facade_service):
        self.facade_service = facade_service
        # Initialize token helper
        self.token_helper = TokenConsumptionHelper(
            session=facade_service.get_session()
        )
        logger.info("ProjectMCPController initialized with token consumption")

    async def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new project (costs 10 tokens)

        Args:
            name: Project name
            description: Project description
            user_id: User identifier (extracted from auth if not provided)

        Returns:
            Project creation result with token_info
        """
        # Step 1: Consume tokens BEFORE creating project
        success, error_response = await self.token_helper.consume_tokens(
            operation="create_project",
            user_id=user_id
        )

        if not success:
            logger.warning(f"Token consumption failed for create_project: {error_response}")
            return error_response

        # Step 2: Execute the actual operation
        try:
            result = await self.facade_service.create_project(
                name=name,
                description=description
            )

            # Step 3: Add token info to successful response
            token_info = await self.token_helper.get_token_info(
                operation="create_project",
                user_id=user_id
            )
            result["token_info"] = token_info

            logger.info(f"Project created successfully, consumed {token_info['consumed']} tokens")
            return result

        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "PROJECT_CREATION_FAILED"
            }

    async def list_projects(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List all projects (costs 1 token)

        This is a cheap read operation.
        """
        # Consume tokens (only 1 token for list operations)
        success, error_response = await self.token_helper.consume_tokens(
            operation="list_projects",
            user_id=user_id
        )

        if not success:
            return error_response

        # Execute operation
        result = await self.facade_service.list_projects()

        # Add token info
        token_info = await self.token_helper.get_token_info(
            operation="list_projects",
            user_id=user_id
        )
        result["token_info"] = token_info

        return result

    async def delete_project(
        self,
        project_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a project (costs 5 tokens)
        """
        # Consume tokens
        success, error_response = await self.token_helper.consume_tokens(
            operation="delete_project",
            user_id=user_id
        )

        if not success:
            return error_response

        # Execute deletion
        result = await self.facade_service.delete_project(project_id)

        # Add token info
        token_info = await self.token_helper.get_token_info(
            operation="delete_project",
            user_id=user_id
        )
        result["token_info"] = token_info

        return result
```

## Token Costs Reference

Default costs for operations (defined in `auth/config/token_costs.py`):

### Project Operations
- `create_project`: 10 tokens
- `update_project`: 5 tokens
- `delete_project`: 5 tokens
- `list_projects`: 1 token
- `get_project`: 1 token

### Branch Operations
- `create_branch`: 5 tokens
- `update_branch`: 3 tokens
- `delete_branch`: 3 tokens
- `list_branches`: 1 token

### Task Operations
- `create_task`: 5 tokens
- `update_task`: 3 tokens
- `complete_task`: 3 tokens
- `list_tasks`: 1 token

### Agent Operations
- `call_agent`: 20 tokens (most expensive - AI operation)
- `register_agent`: 5 tokens
- `assign_agent`: 3 tokens

### Free Operations
- `login`: 0 tokens
- `register`: 0 tokens
- `get_balance`: 0 tokens

## Custom Token Costs

For operations requiring custom costs:

```python
# Override default cost with custom amount
success, error = await self.token_helper.consume_tokens(
    operation="special_operation",
    user_id=user_id,
    custom_cost=15  # Use 15 tokens instead of default
)
```

## Error Handling

The helper returns standardized error responses:

### Insufficient Tokens Error (402)
```json
{
  "success": false,
  "error": "Insufficient tokens. Required: 10, Available: 5",
  "error_code": "INSUFFICIENT_TOKENS",
  "status_code": 402,
  "operation": "create_project"
}
```

### Token System Error
```json
{
  "success": false,
  "error": "Token consumption error: ...",
  "error_code": "TOKEN_SYSTEM_ERROR",
  "operation": "create_project"
}
```

## Response Format

Successful operations include `token_info`:

```json
{
  "success": true,
  "project": { ... },
  "token_info": {
    "consumed": 10,
    "remaining_balance": 9990,
    "operation": "create_project"
  }
}
```

## Authentication

The helper automatically extracts `user_id` from:
1. Provided `user_id` parameter (if given)
2. JWT token from Authorization header (via `get_authenticated_user_id()`)

No need to manually extract user_id in most cases.

## Testing

Mock the token helper in your tests:

```python
from unittest.mock import AsyncMock, patch

async def test_create_project_insufficient_tokens():
    # Mock token consumption to fail
    with patch.object(TokenConsumptionHelper, 'consume_tokens') as mock_consume:
        mock_consume.return_value = (False, {
            "success": False,
            "error": "Insufficient tokens",
            "error_code": "INSUFFICIENT_TOKENS"
        })

        controller = ProjectMCPController(facade_service)
        result = await controller.create_project(name="Test")

        assert result["success"] is False
        assert result["error_code"] == "INSUFFICIENT_TOKENS"
```

## Migration Checklist

For each MCP controller:

- [ ] Import `TokenConsumptionHelper`
- [ ] Initialize helper in `__init__` with database session
- [ ] Add token consumption to ALL operations (except free ones)
- [ ] Handle error responses (return immediately if consumption fails)
- [ ] Add `token_info` to successful responses
- [ ] Update tests to handle token consumption
- [ ] Update controller documentation

## Controllers to Update

1. ✅ **token_consumption_helper.py** - Helper created
2. ⏳ **project_mcp_controller** - 9 operations
3. ⏳ **git_branch_mcp_controller** - 10 operations
4. ⏳ **task_mcp_controller** - 10 operations
5. ⏳ **subtask_mcp_controller** - 6 operations
6. ⏳ **agent_mcp_controller** - 9 operations
7. ⏳ **call_agent_mcp_controller** - 1 operation (call_agent)
8. ⏳ **unified_context_controller** - 9 operations
9. ⏳ **enhanced_dependency_controller** - 2 operations

**Total**: ~56 operations to integrate

## Performance Considerations

- Token helper uses lazy-loading for service initialization
- Database session reuse prevents connection overhead
- Auto-creation of balances only happens once per user
- Free operations (cost=0) skip database operations entirely

## Support

For issues or questions:
- Check `token_consumption_service.py` for service logic
- Check `token_costs.py` for operation costs
- Check logs for detailed token consumption tracking
