# Context Delegation Async/Await Error Fix

## 🐛 Issue Description

**Error**: `'coroutine' object has no attribute 'get'`

**Location**: `manage_context` tool, specifically in the `delegate` action

**Root Cause**: The `delegate_context` method in `HierarchicalContextService` calls `process_delegation` from `ContextDelegationService`, which is an async method, but doesn't await it properly. This results in a coroutine object being returned instead of the expected dictionary.

## 📍 Error Chain

1. **Controller Level** (`context_mcp_controller.py:763`):
   ```python
   # _handle_delegate_context calls:
   result = self.hierarchy_service.delegate_context(...)  # No await
   ```

2. **Service Level** (`hierarchical_context_service.py:548`):
   ```python
   # delegate_context is sync but calls:
   result = self.delegation_service.process_delegation(...)  # async method, no await!
   ```

3. **Delegation Service** (`context_delegation_service.py:56`):
   ```python
   async def process_delegation(...):  # This is async!
   ```

## 🔧 Fix Implementation

### Option 1: Make delegate_context Async (Breaking Change)

```python
# In HierarchicalContextService
async def delegate_context(self, from_level: str, from_id: str, 
                         to_level: str, data: Dict[str, Any], 
                         reason: str = "Manual delegation") -> Dict[str, Any]:
    # ... validation ...
    
    # FIXED: Properly await async call
    result = await self.delegation_service.process_delegation(
        source_level=from_level,
        source_id=from_id,
        target_level=to_level,
        target_id=target_id,
        delegated_data=data,
        reason=reason
    )
    
    # ... rest of method ...
```

### Option 2: Sync Wrapper with Internal Async Handling (Recommended)

```python
# In HierarchicalContextService
def delegate_context(self, from_level: str, from_id: str,
                   to_level: str, data: Dict[str, Any],
                   reason: str = "Manual delegation") -> Dict[str, Any]:
    """Sync method that handles async delegation internally"""
    
    async def _async_delegate():
        # ... validation ...
        
        # Properly await async call
        result = await self.delegation_service.process_delegation(...)
        
        # ... rest of logic ...
        return result
    
    # Execute async in sync context
    return self._run_async_in_sync(_async_delegate())

def _run_async_in_sync(self, coro):
    """Helper to run async code in sync context"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Handle nested event loop
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)
```

### Controller Update

```python
# In ContextMCPController._handle_delegate_context
async def _handle_delegate_context(self, from_level: str, from_id: str, 
                                 to_level: str, data: Dict[str, Any], 
                                 reason: str) -> Dict[str, Any]:
    try:
        # Check if delegate_context is async
        if asyncio.iscoroutinefunction(self.hierarchy_service.delegate_context):
            result = await self.hierarchy_service.delegate_context(...)
        else:
            # Sync version (with internal async handling)
            result = self.hierarchy_service.delegate_context(...)
        
        # ... handle result ...
```

## 📋 Files Affected

1. **`/src/fastmcp/task_management/application/services/hierarchical_context_service.py`**
   - Add `_run_async_in_sync` helper method
   - Update `delegate_context` to handle async internally

2. **`/src/fastmcp/task_management/interface/controllers/context_mcp_controller.py`**
   - Already async, just needs to handle potential async delegate_context

3. **`/src/fastmcp/task_management/interface/controllers/context_mcp_controller.py:256`**
   - Update `manage_delegation_queue` to properly await async operations

## 🧪 Test Coverage

Created comprehensive tests in:
- `/tests/unit/interface/controllers/test_context_delegation_async_fix.py`
- `/tests/integration/context_delegation_async_fix_implementation.py`

Test cases cover:
1. ✅ Reproducing the original error
2. ✅ Sync wrapper implementation
3. ✅ Async delegate_context fix
4. ✅ Controller handling of both sync/async versions
5. ✅ Delegation queue async operations
6. ✅ Complete integration test

## 🚀 Implementation Steps

1. **Add helper method to HierarchicalContextService**:
   ```python
   def _run_async_in_sync(self, coro):
       # Implementation from fix
   ```

2. **Update delegate_context in HierarchicalContextService**:
   - Wrap async operations in `_async_delegate` inner function
   - Use `_run_async_in_sync` to execute

3. **Update manage_delegation_queue in ContextMCPController**:
   - Properly await all delegation service calls
   - Return consistent response format

4. **Test thoroughly**:
   - Run unit tests
   - Test in real environment
   - Verify no breaking changes

## ✅ Benefits

- Maintains backward compatibility (sync API)
- Properly handles async operations
- No coroutine leaks
- Works in all environments (including Jupyter)
- Clear error handling

## 📊 Impact

- **Low Risk**: Using sync wrapper maintains API compatibility
- **Performance**: Minimal overhead from thread pool when needed
- **Reliability**: Eliminates coroutine attribute errors
- **Maintainability**: Clear async/sync boundary