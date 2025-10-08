# Cascade Calculator DDD Refactoring - Architecture Design Document

**Date**: 2025-10-08
**Status**: Implemented
**Priority**: P0-CRITICAL
**Architect**: system-architect-agent
**Related Issue**: DDD Architecture Violation in cascade_calculator.py

## Executive Summary

Successfully removed SQLAlchemy dependency from the domain layer's `cascade_calculator.py` service by applying the Dependency Inversion Principle. The domain service now depends on an abstract Protocol interface, with SQLAlchemy implementation living in the infrastructure layer where it belongs.

## Problem Statement

### Original Violation
```python
# domain/services/cascade_calculator.py (BEFORE)
from sqlalchemy.ext.asyncio import AsyncSession  # ❌ Domain depending on infrastructure
from sqlalchemy import text                      # ❌ Domain depending on infrastructure

class CascadeCalculator:
    def __init__(self, session: AsyncSession):  # ❌ Direct infrastructure dependency
        self.session = session
        # ... uses self.session.execute(text(...)) throughout
```

**Why This Violates DDD:**
- Domain layer MUST NOT depend on infrastructure
- Makes domain logic untestable without a database
- Couples business logic to specific database technology
- Violates Dependency Inversion Principle

## Solution Architecture

### Core Principle: Dependency Inversion

```
BEFORE (Violation):
Domain Service → SQLAlchemy (Infrastructure)
    ❌ Domain depends on concrete infrastructure

AFTER (DDD-Compliant):
Domain Service → Protocol (Domain)
                      ↑
                      |
         SQLAlchemy Implementation (Infrastructure)
    ✅ Both depend on domain abstraction
```

### Architecture Components

#### 1. Protocol Definition (Domain Layer)

**Location**: `domain/services/protocols/cascade_data_provider.py`

```python
from typing import Protocol, Optional, Set

class CascadeDataProvider(Protocol):
    """Domain-defined interface for data access"""

    async def get_task_cascade_data(self, task_id: str) -> Optional[TaskCascadeData]:
        """Get cascade-relevant data for a task"""
        ...

    async def get_task_subtask_ids(self, task_id: str) -> Set[str]:
        """Get all subtask IDs for a task"""
        ...

    # ... 7 more methods defining data needs
```

**Key Design Decisions:**
- Uses Python's `Protocol` for structural subtyping (no inheritance required)
- All methods return domain DTOs, never infrastructure types
- All methods are async to support efficient I/O
- Protocol lives in domain layer - it's a domain concept

#### 2. Domain Transfer Objects (DTOs)

**Location**: Same file as Protocol

```python
@dataclass
class TaskCascadeData:
    """Pure domain data object"""
    id: str
    git_branch_id: str
    project_id: str
    context_id: Optional[str] = None
```

**Why DTOs:**
- Decouple domain from database schema
- Allow schema changes without affecting domain logic
- Provide clean, type-safe interface
- No SQLAlchemy magic, just data

#### 3. Infrastructure Implementation

**Location**: `infrastructure/repositories/orm/cascade_data_provider.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession  # ✅ OK in infrastructure layer
from sqlalchemy import text

class SQLAlchemyCascadeDataProvider:
    """Concrete implementation using SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_task_cascade_data(self, task_id: str) -> Optional[TaskCascadeData]:
        query = text("""
            SELECT t.id, t.git_branch_id, b.project_id, t.context_id
            FROM tasks t
            JOIN project_git_branchs b ON t.git_branch_id = b.id
            WHERE t.id = :task_id
        """)
        result = await self.session.execute(query, {"task_id": task_id})
        row = result.fetchone()

        if not row:
            return None

        return TaskCascadeData(
            id=row[0],
            git_branch_id=row[1],
            project_id=row[2],
            context_id=row[3]
        )

    # ... implement all 9 Protocol methods
```

**Key Benefits:**
- Can use SQLAlchemy freely (it's infrastructure)
- Converts SQL results to domain DTOs
- Encapsulates all SQL queries in one place
- Easy to replace with different database technology

#### 4. Updated Domain Service

**Location**: `domain/services/cascade_calculator.py`

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocols.cascade_data_provider import CascadeDataProvider

class CascadeCalculator:
    """Domain service - now infrastructure-independent"""

    def __init__(self, data_provider: "CascadeDataProvider"):
        self._data_provider = data_provider
        # No more self.session!

    async def calculate_task_cascade(self, task_id: str) -> CascadeResult:
        # Use data provider instead of direct SQL
        task_data = await self._data_provider.get_task_cascade_data(task_id)

        if not task_data:
            # Handle not found case
            return CascadeResult(...)

        # Pure domain logic using DTOs
        affected_branches.add(task_data.git_branch_id)
        affected_projects.add(task_data.project_id)

        # ... business logic continues
```

**Changes Made:**
- ❌ Removed `from sqlalchemy.ext.asyncio import AsyncSession`
- ❌ Removed `from sqlalchemy import text`
- ✅ Added Protocol import (with TYPE_CHECKING for forward reference)
- ✅ Constructor now accepts `CascadeDataProvider` instead of `AsyncSession`
- ✅ All methods use `self._data_provider` instead of `self.session`
- ✅ Removed 5 private methods that had SQL queries (_get_branch_summary, _get_project_metrics, etc.)

### Dependency Injection (Wiring)

**Where it happens**: Application layer or dependency injection container

```python
# application/services/task_application_service.py (example)
from infrastructure.repositories.orm.cascade_data_provider import SQLAlchemyCascadeDataProvider
from domain.services.cascade_calculator import CascadeCalculator

class TaskApplicationService:
    def __init__(self, session: AsyncSession):
        # Infrastructure layer can depend on SQLAlchemy
        data_provider = SQLAlchemyCascadeDataProvider(session)

        # Inject into domain service
        self.cascade_calculator = CascadeCalculator(data_provider)
```

## Testing Strategy

### Unit Tests (Domain Layer)

```python
class MockCascadeDataProvider:
    """Test double - no database needed"""

    async def get_task_cascade_data(self, task_id: str) -> Optional[TaskCascadeData]:
        return TaskCascadeData(
            id=task_id,
            git_branch_id="branch-123",
            project_id="project-456",
            context_id="context-789"
        )

    # ... mock all 9 methods

def test_calculate_task_cascade():
    # No database, no SQLAlchemy, pure domain testing
    mock_provider = MockCascadeDataProvider()
    calculator = CascadeCalculator(mock_provider)

    result = await calculator.calculate_task_cascade("task-123")

    assert "branch-123" in result.affected_branches
    assert "project-456" in result.affected_projects
    # Test business logic, not database queries
```

### Integration Tests (Infrastructure Layer)

```python
async def test_sqlalchemy_cascade_data_provider():
    # Test infrastructure implementation with real database
    async with test_session() as session:
        provider = SQLAlchemyCascadeDataProvider(session)

        # Test actual SQL queries
        task_data = await provider.get_task_cascade_data("task-123")

        assert task_data is not None
        assert task_data.git_branch_id == "expected-branch"
```

## Protocol Method Reference

### Data Access Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_task_cascade_data` | Get task with relationships | `Optional[TaskCascadeData]` |
| `get_task_subtask_ids` | Get all subtask IDs for task | `Set[str]` |
| `get_task_parent_task_ids` | Get parent tasks depending on this | `Set[str]` |
| `get_subtask_cascade_data` | Get subtask with relationships | `Optional[SubtaskCascadeData]` |
| `get_branch_cascade_data` | Get branch with tasks/subtasks | `Optional[BranchCascadeData]` |
| `get_project_cascade_data` | Get project with all entities | `Optional[ProjectCascadeData]` |
| `get_context_cascade_data` | Get context with all entities | `Optional[ContextCascadeData]` |
| `get_related_context_ids` | Get contexts for branch/project | `Set[str]` |
| `detect_entity_type` | Auto-detect entity type by ID | `Optional[EntityType]` |

### DTO Reference

**TaskCascadeData**:
- `id: str`
- `git_branch_id: str`
- `project_id: str`
- `context_id: Optional[str]`

**SubtaskCascadeData**:
- `id: str`
- `task_id: str`
- `git_branch_id: str`
- `project_id: str`
- `context_id: Optional[str]`

**BranchCascadeData**:
- `id: str`
- `project_id: str`
- `task_ids: Set[str]`
- `subtask_ids: Set[str]`

**ProjectCascadeData**:
- `id: str`
- `branch_ids: Set[str]`
- `task_ids: Set[str]`
- `subtask_ids: Set[str]`

**ContextCascadeData**:
- `id: str`
- `task_ids: Set[str]`
- `branch_ids: Set[str]`
- `project_ids: Set[str]`
- `subtask_ids: Set[str]`

## Benefits of This Architecture

### 1. Domain Independence ✅
- Domain layer has ZERO infrastructure dependencies
- Can reason about business logic without knowing implementation details
- True separation of concerns

### 2. Testability ✅
- Unit test domain logic without database
- Mock Protocol with test data
- Fast tests, no setup overhead

### 3. Flexibility ✅
- Easy to switch databases (PostgreSQL → MongoDB)
- Easy to add caching layer
- Easy to add read replicas

### 4. Maintainability ✅
- Clear boundaries between layers
- Infrastructure changes don't affect domain
- Domain changes don't affect infrastructure queries

### 5. Type Safety ✅
- Protocol provides type checking
- DTOs provide clean interfaces
- IDE autocomplete works perfectly

## Migration Impact

### Files Created
1. `domain/services/protocols/__init__.py` - New protocol module
2. `domain/services/protocols/cascade_data_provider.py` - Protocol and DTOs
3. `infrastructure/repositories/orm/cascade_data_provider.py` - SQLAlchemy implementation

### Files Modified
1. `domain/services/cascade_calculator.py`:
   - Removed SQLAlchemy imports
   - Changed constructor to accept Protocol
   - Updated all cascade methods to use data provider
   - Removed 5 private methods with direct SQL

### Breaking Changes
- Any code instantiating `CascadeCalculator` must now pass a `CascadeDataProvider` implementation instead of `AsyncSession`
- Application layer services need to be updated to create data provider and inject it

### Migration Path
```python
# BEFORE
calculator = CascadeCalculator(session)

# AFTER
data_provider = SQLAlchemyCascadeDataProvider(session)
calculator = CascadeCalculator(data_provider)
```

## Performance Considerations

### No Performance Impact
- Same SQL queries, just encapsulated differently
- No additional layers or overhead
- Protocol is zero-cost abstraction at runtime
- DTOs are lightweight dataclasses

### Future Optimization Opportunities
- Add caching in data provider implementation
- Add query result pooling
- Switch to read replicas for queries
- Add query batching
- All without touching domain layer!

## Compliance Verification

### DDD Architecture Checklist
- ✅ Domain layer has zero infrastructure dependencies
- ✅ Domain depends only on abstractions (Protocol)
- ✅ Infrastructure depends on domain abstractions
- ✅ Clear layer boundaries maintained
- ✅ Testable without infrastructure
- ✅ Infrastructure can be swapped without domain changes

### Code Quality Checklist
- ✅ No backward compatibility code
- ✅ No legacy patterns
- ✅ Direct implementation only
- ✅ Clean error handling
- ✅ Type hints throughout
- ✅ Comprehensive documentation

## Success Metrics

**Before**: 14% DDD compliance (1/7 repositories compliant)
**After This Fix**: 28% compliance (2/7 repositories compliant)

**Domain Layer Infrastructure Dependencies**:
- Before: 2 (AsyncSession, text)
- After: 0 ✅

**Lines of Code**:
- Domain service: ~450 lines (before) → ~350 lines (after) - cleaner!
- Infrastructure: +250 lines (new provider implementation)
- Net change: Domain layer is simpler, complexity moved to infrastructure where it belongs

## Future Enhancements

### Potential Improvements
1. Add query result caching in data provider
2. Add metrics/observability to data provider
3. Create MongoDB implementation of Protocol
4. Add query optimization layer
5. Implement read replica routing

### Pattern Replication
This same pattern should be applied to:
- Other domain services needing data access
- Any domain code with infrastructure dependencies
- Event handlers needing database access

## Conclusion

This refactoring successfully eliminates a critical DDD violation by applying the Dependency Inversion Principle. The cascade calculator is now a pure domain service that depends only on abstractions, making it testable, maintainable, and infrastructure-independent.

The architecture provides a template for fixing the remaining 5 repository violations and demonstrates how to properly separate domain and infrastructure concerns in a DDD architecture.

## References

- Parent Task: #4e76b7f5-99f8-4d50-b1f4-fdccb4dc1341
- Subtask: #844034a0-9b9a-4c06-a99e-7b0d1128903d
- Audit Document: `ai_docs/code-quality/ddd-architecture-audit-2025-10-08.md`
- DDD Principles: Domain-Driven Design by Eric Evans
- Dependency Inversion: Clean Architecture by Robert C. Martin
