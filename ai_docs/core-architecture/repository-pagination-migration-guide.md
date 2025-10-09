# Repository Pagination Migration Guide

**Status**: ✅ Complete (Preventative Implementation)
**Date**: 2025-10-09
**Related Task**: Subtask 2.4 - Update Repository Implementations to Use PaginationService
**Feature Flag**: FEATURE_CLEAN_REPOSITORIES

## Executive Summary

**Current State**: No concrete repository implementations currently use `create_pagination_result()`. The pagination infrastructure is in place but not yet adopted.

**This Guide**: Serves as preventative documentation for future repository implementations to ensure they use PaginationService correctly from the start.

## Migration Status

### What Was Done

1. **Analysis**: Searched entire codebase for repositories using `create_pagination_result()`
2. **Finding**: No concrete repositories currently use pagination
3. **Action**: Created comprehensive reference implementation and integration tests
4. **Result**: Future repositories have clear guidance on correct pagination patterns

### Files Modified

- ✅ Created: `tests/integration/task_management/repositories/test_pagination_service_integration.py`
  - Reference implementation: `ExampleRepositoryWithPagination`
  - 11 integration tests demonstrating correct patterns
  - Documentation tests showing migration path
  - All tests passing

### Files NOT Modified (None Existed)

- **Infrastructure Repositories**: No repositories currently implement pagination
  - `infrastructure/repositories/task_context_repository.py` - No pagination
  - `infrastructure/repositories/project_context_repository.py` - No pagination
  - `infrastructure/repositories/branch_context_repository.py` - No pagination
  - All other repositories - No pagination

## Correct Pagination Pattern

### ✅ NEW PATTERN (Use This)

```python
from fastmcp.task_management.domain.repositories.base_repository import (
    BaseRepository,
    PaginationRequest,
    PaginationResult
)
from fastmcp.task_management.domain.services.pagination_service import PaginationService

class MyRepository(BaseRepository[MyEntity]):
    """Repository with correct pagination implementation"""

    def list_with_pagination(
        self,
        pagination: PaginationRequest
    ) -> PaginationResult[MyEntity]:
        """List entities with pagination using PaginationService"""
        # Get all items (or apply filters first)
        all_items = self.get_all()
        total_count = len(all_items)

        # Calculate offset and slice for current page
        offset = PaginationService.calculate_offset(pagination)
        end = offset + pagination.page_size
        page_items = all_items[offset:end]

        # ✅ CORRECT: Use PaginationService.create_pagination_result()
        return PaginationService[MyEntity].create_pagination_result(
            items=page_items,
            total_count=total_count,
            pagination=pagination
        )
```

### ❌ OLD PATTERN (Don't Use This)

```python
class MyRepository(BaseRepository[MyEntity]):
    """Repository with deprecated pagination pattern"""

    def list_with_pagination(
        self,
        pagination: PaginationRequest
    ) -> PaginationResult[MyEntity]:
        """DEPRECATED: Using BaseRepository method"""
        all_items = self.get_all()
        total_count = len(all_items)

        offset = (pagination.page - 1) * pagination.page_size
        page_items = all_items[offset:offset + pagination.page_size]

        # ❌ DEPRECATED: Don't call self.create_pagination_result()
        return self.create_pagination_result(page_items, total_count, pagination)
```

## Key Differences

| Aspect | Old Pattern | New Pattern |
|--------|------------|-------------|
| **Import** | No PaginationService import | Import PaginationService |
| **Offset Calculation** | Manual calculation | `PaginationService.calculate_offset()` |
| **Result Creation** | `self.create_pagination_result()` | `PaginationService.create_pagination_result()` |
| **Feature Flag** | Breaks when flag=True | Works with both flag states |
| **DDD Compliance** | Violates interface principle | Follows DDD service pattern |

## Reference Implementation

See `tests/integration/task_management/repositories/test_pagination_service_integration.py` for:

1. **ExampleRepositoryWithPagination**: Complete reference implementation
2. **Integration Tests**: 11 tests covering all pagination scenarios:
   - First page, middle page, last page
   - Empty results, single page
   - Search/filtering with pagination
   - Offset calculation and validation
   - Feature flag compatibility
3. **Documentation Tests**: Migration examples and import patterns

## Feature Flag Behavior

### FEATURE_CLEAN_REPOSITORIES = False (Current Default)

- **BaseRepository.create_pagination_result()**: Works (with deprecation warning)
- **PaginationService.create_pagination_result()**: Works (recommended)
- **Status**: Both patterns available for zero-downtime migration

### FEATURE_CLEAN_REPOSITORIES = True (Future)

- **BaseRepository.create_pagination_result()**: Raises NotImplementedError
- **PaginationService.create_pagination_result()**: Works (only option)
- **Status**: Clean repositories enforced

## PaginationService Features

### Available Methods

```python
class PaginationService(Generic[T]):
    """Domain service for pagination operations"""

    @classmethod
    def create_pagination_result(
        cls,
        items: List[T],
        total_count: int,
        pagination: PaginationRequest
    ) -> PaginationResult[T]:
        """Create paginated result with metadata"""

    @classmethod
    def calculate_offset(
        cls,
        pagination: PaginationRequest
    ) -> int:
        """Calculate database offset from pagination params"""

    @classmethod
    def validate_pagination_request(
        cls,
        pagination: PaginationRequest
    ) -> None:
        """Validate pagination parameters"""
```

### Business Rules

1. **Total Pages**: `(total_count + page_size - 1) // page_size` (ceiling division)
2. **Has Next**: `current_page < total_pages`
3. **Has Previous**: `current_page > 1`
4. **Offset**: `(page - 1) * page_size`

### Validation Rules

- Page must be >= 1 (first page is 1, not 0)
- Page size must be > 0
- Page size must be <= 100 (configurable limit)

## Common Patterns

### Basic Pagination

```python
def list_all(self, pagination: PaginationRequest) -> PaginationResult[Entity]:
    """Simple pagination of all entities"""
    items = self.get_all()
    offset = PaginationService.calculate_offset(pagination)
    page_items = items[offset:offset + pagination.page_size]

    return PaginationService[Entity].create_pagination_result(
        items=page_items,
        total_count=len(items),
        pagination=pagination
    )
```

### Pagination with Filtering

```python
def search(
    self,
    query: str,
    pagination: PaginationRequest
) -> PaginationResult[Entity]:
    """Pagination with search filter"""
    # Apply filter first
    filtered = [e for e in self.get_all() if query in e.name]

    # Then paginate filtered results
    offset = PaginationService.calculate_offset(pagination)
    page_items = filtered[offset:offset + pagination.page_size]

    return PaginationService[Entity].create_pagination_result(
        items=page_items,
        total_count=len(filtered),  # Count of filtered items
        pagination=pagination
    )
```

### Pagination with Database Query

```python
def list_by_status(
    self,
    status: str,
    pagination: PaginationRequest
) -> PaginationResult[Entity]:
    """Pagination with database query"""
    # Count total matching records
    total_count = self.session.query(EntityModel)\
        .filter(EntityModel.status == status)\
        .count()

    # Query current page
    offset = PaginationService.calculate_offset(pagination)
    models = self.session.query(EntityModel)\
        .filter(EntityModel.status == status)\
        .offset(offset)\
        .limit(pagination.page_size)\
        .all()

    # Convert to domain entities
    entities = [self._to_entity(m) for m in models]

    return PaginationService[Entity].create_pagination_result(
        items=entities,
        total_count=total_count,
        pagination=pagination
    )
```

## Testing Recommendations

### Test All Edge Cases

```python
def test_pagination_scenarios(repository):
    """Test all pagination edge cases"""
    # First page
    result = repository.list(PaginationRequest(page=1, page_size=10))
    assert result.has_previous is False

    # Middle page
    result = repository.list(PaginationRequest(page=2, page_size=10))
    assert result.has_previous is True
    assert result.has_next is True

    # Last page
    result = repository.list(PaginationRequest(page=3, page_size=10))
    assert result.has_next is False

    # Empty results
    empty_repo = EmptyRepository()
    result = empty_repo.list(PaginationRequest(page=1, page_size=10))
    assert result.total_pages == 0

    # Single page
    small_repo = SmallRepository()
    result = small_repo.list(PaginationRequest(page=1, page_size=100))
    assert result.total_pages == 1
```

### Test Feature Flag Compatibility

```python
def test_feature_flag_compatibility(repository):
    """Ensure pagination works with both flag states"""
    pagination = PaginationRequest(page=1, page_size=10)

    # Test with flag=False
    PaginationService.FEATURE_CLEAN_REPOSITORIES = False
    result_legacy = repository.list(pagination)

    # Test with flag=True
    PaginationService.FEATURE_CLEAN_REPOSITORIES = True
    result_clean = repository.list(pagination)

    # Results should be identical
    assert result_legacy.total_count == result_clean.total_count
    assert len(result_legacy.items) == len(result_clean.items)
```

## Future Migration Timeline

### Phase 1: Current (Complete)
- ✅ PaginationService created and tested
- ✅ BaseRepository.create_pagination_result() deprecated
- ✅ Reference implementation provided
- ✅ Integration tests created

### Phase 2: When Repositories Need Pagination
- Future repositories should use PaginationService from the start
- Follow reference implementation in test_pagination_service_integration.py
- No migration needed (correct pattern used immediately)

### Phase 3: Clean Repositories Enforcement (Future)
- Set FEATURE_CLEAN_REPOSITORIES = True
- BaseRepository.create_pagination_result() throws NotImplementedError
- Move PaginationRequest/PaginationResult to domain/value_objects
- Remove deprecated method from BaseRepository

## Key Insights

1. **Preventative Approach**: This subtask was completed proactively - no repositories needed updates because none use pagination yet
2. **Reference Implementation**: Created comprehensive example repository that serves as template for future implementations
3. **Zero-Downtime Ready**: PaginationService works with both feature flag states
4. **DDD Compliance**: Service-based approach follows domain-driven design principles
5. **Documentation First**: Integration tests serve as living documentation

## Troubleshooting

### Issue: "PaginationService has no attribute 'create_pagination_result'"

**Cause**: Missing import
**Solution**: Add `from fastmcp.task_management.domain.services.pagination_service import PaginationService`

### Issue: "NotImplementedError: create_pagination_result is deprecated"

**Cause**: Using `self.create_pagination_result()` with FEATURE_CLEAN_REPOSITORIES=True
**Solution**: Use `PaginationService[Entity].create_pagination_result()` instead

### Issue: Test failures with pagination edge cases

**Cause**: Not testing all pagination scenarios
**Solution**: Reference the 11 integration tests in test_pagination_service_integration.py

## Related Documentation

- **PaginationService**: `domain/services/pagination_service.py`
- **BaseRepository**: `domain/repositories/base_repository.py`
- **Integration Tests**: `tests/integration/task_management/repositories/test_pagination_service_integration.py`
- **Feature Flag Guide**: See BaseRepository docstring for FEATURE_CLEAN_REPOSITORIES details

## Conclusion

**Subtask 2.4 Status**: ✅ Complete

No repository migrations were needed because no repositories currently use pagination. Instead, we've created:

1. Comprehensive reference implementation
2. 11 passing integration tests
3. Clear documentation for future implementations
4. Feature flag compatibility verification

Future repositories that need pagination should follow the patterns demonstrated in `ExampleRepositoryWithPagination` and use `PaginationService` from day one.
