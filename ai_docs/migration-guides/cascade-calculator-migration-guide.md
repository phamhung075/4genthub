# Cascade Calculator Migration Guide

**Date**: 2025-10-08
**Breaking Change**: Yes
**Impact**: Application layer services using CascadeCalculator

## Overview

The `CascadeCalculator` domain service has been refactored to follow DDD principles by removing direct SQLAlchemy dependencies. Any code instantiating `CascadeCalculator` must be updated to use the new Protocol-based injection pattern.

## What Changed

### Before (Old Pattern)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from domain.services.cascade_calculator import CascadeCalculator

# Direct injection of SQLAlchemy session
calculator = CascadeCalculator(session)
```

### After (New Pattern)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.repositories.orm.cascade_data_provider import SQLAlchemyCascadeDataProvider
from domain.services.cascade_calculator import CascadeCalculator

# Create data provider first
data_provider = SQLAlchemyCascadeDataProvider(session)

# Inject data provider into domain service
calculator = CascadeCalculator(data_provider)
```

## Migration Steps

### Step 1: Add New Import
```python
from infrastructure.repositories.orm.cascade_data_provider import SQLAlchemyCascadeDataProvider
```

### Step 2: Update Instantiation
```python
# OLD
calculator = CascadeCalculator(session)

# NEW
data_provider = SQLAlchemyCascadeDataProvider(session)
calculator = CascadeCalculator(data_provider)
```

### Step 3: Test
- Verify all cascade calculations still work correctly
- Check performance (should be identical)
- Ensure no errors in logs

## Files That May Need Updates

Search for all instantiations of `CascadeCalculator`:

```bash
grep -r "CascadeCalculator(" agenthub_main/src/fastmcp/task_management/application/
```

Typical locations:
- `application/services/*_application_service.py`
- `application/use_cases/*.py`
- `interface/mcp/controllers/*.py` (if directly using)

## Example: Application Service Update

### Before
```python
# application/services/task_application_service.py
class TaskApplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cascade_calculator = CascadeCalculator(session)  # OLD
```

### After
```python
# application/services/task_application_service.py
from infrastructure.repositories.orm.cascade_data_provider import SQLAlchemyCascadeDataProvider

class TaskApplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session

        # Create and inject data provider
        cascade_data_provider = SQLAlchemyCascadeDataProvider(session)
        self.cascade_calculator = CascadeCalculator(cascade_data_provider)  # NEW
```

## Testing Your Changes

### Unit Test Changes (if applicable)

**Before**:
```python
async def test_cascade_calculator():
    async with test_session() as session:
        calculator = CascadeCalculator(session)
        result = await calculator.calculate_cascade("task-123")
```

**After - Option 1** (Use real data provider):
```python
from infrastructure.repositories.orm.cascade_data_provider import SQLAlchemyCascadeDataProvider

async def test_cascade_calculator():
    async with test_session() as session:
        data_provider = SQLAlchemyCascadeDataProvider(session)
        calculator = CascadeCalculator(data_provider)
        result = await calculator.calculate_cascade("task-123")
```

**After - Option 2** (Use mock for pure unit tests):
```python
class MockCascadeDataProvider:
    async def get_task_cascade_data(self, task_id: str):
        return TaskCascadeData(
            id=task_id,
            git_branch_id="branch-1",
            project_id="project-1"
        )
    # ... implement other methods

async def test_cascade_calculator():
    mock_provider = MockCascadeDataProvider()
    calculator = CascadeCalculator(mock_provider)
    result = await calculator.calculate_cascade("task-123")
    # Test domain logic without database!
```

## Benefits of New Pattern

### 1. Testability
```python
# Can now mock data provider without needing a database
mock_provider = MockCascadeDataProvider()
calculator = CascadeCalculator(mock_provider)
```

### 2. Flexibility
```python
# Easy to switch implementations
mongo_provider = MongoDBCascadeDataProvider(mongo_client)
calculator = CascadeCalculator(mongo_provider)

# Easy to add caching
cached_provider = CachedCascadeDataProvider(base_provider)
calculator = CascadeCalculator(cached_provider)
```

### 3. Clean Architecture
- Domain layer no longer knows about SQLAlchemy
- Infrastructure details isolated in provider
- Clear separation of concerns

## Performance Impact

**None.** The same SQL queries are executed, just through a cleaner abstraction.

- Before: Direct SQLAlchemy execution
- After: SQLAlchemy execution through provider
- Runtime overhead: Zero (Protocol is compile-time only)

## Rollback Plan

If issues arise during migration:

1. Revert the changes to `cascade_calculator.py`
2. Remove the new Protocol and data provider files
3. Restore old direct SQLAlchemy usage

## Verification Checklist

After migration, verify:

- [ ] All cascade calculations work correctly
- [ ] Performance is unchanged (< 50ms requirement still met)
- [ ] No SQLAlchemy errors in logs
- [ ] All affected tests pass
- [ ] Application layer services instantiate correctly

## Common Issues

### Issue 1: Missing Import
**Error**: `NameError: name 'SQLAlchemyCascadeDataProvider' is not defined`

**Solution**: Add import:
```python
from infrastructure.repositories.orm.cascade_data_provider import SQLAlchemyCascadeDataProvider
```

### Issue 2: Wrong Parameter Type
**Error**: `TypeError: CascadeCalculator.__init__() argument 'data_provider' must be CascadeDataProvider`

**Solution**: Pass data provider instance, not session:
```python
# WRONG
calculator = CascadeCalculator(session)

# RIGHT
data_provider = SQLAlchemyCascadeDataProvider(session)
calculator = CascadeCalculator(data_provider)
```

### Issue 3: Circular Import
**Error**: `ImportError: cannot import name 'CascadeDataProvider'`

**Solution**: Use TYPE_CHECKING for forward references in domain layer:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocols.cascade_data_provider import CascadeDataProvider
```

## Questions?

For questions or issues during migration:
- See architecture doc: `ai_docs/core-architecture/cascade-calculator-ddd-refactoring.md`
- Check task: #844034a0-9b9a-4c06-a99e-7b0d1128903d
- Review parent task: #4e76b7f5-99f8-4d50-b1f4-fdccb4dc1341

## Next Steps

After completing this migration:
1. Update CHANGELOG.md
2. Run full test suite
3. Deploy to dev environment
4. Monitor for any issues
5. Apply same pattern to remaining repository violations
