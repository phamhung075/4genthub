# Unified Context System Migration Guide

## Overview

This guide provides step-by-step instructions for migrating from the legacy dual context system to the new unified context management system. The migration eliminates redundancy, fixes integration issues, and provides a clean, maintainable architecture.

## Pre-Migration Checklist

### Current System Assessment
- [ ] Identify all usage of `manage_context` and `manage_context`
- [ ] Document current context data structures
- [ ] Backup existing context data
- [ ] Review integration points in controllers and services

### Environment Preparation
- [ ] Update development environment
- [ ] Install required dependencies
- [ ] Run existing tests to establish baseline
- [ ] Create migration branch

## Migration Steps

### Phase 1: Implementation of Unified System

#### 1.1 Create Unified Components

**UnifiedContextService**
```python
# Location: src/fastmcp/task_management/application/services/unified_context_service.py
class UnifiedContextService:
    """Single service for all context operations"""
    
    async def create_context(self, level: str, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create context at specified level"""
        
    async def get_context(self, level: str, context_id: str, include_inherited: bool = False) -> Dict[str, Any]:
        """Get context with optional inheritance"""
        
    async def update_context(self, level: str, context_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing context"""
        
    async def resolve_context(self, level: str, context_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Resolve context with full inheritance chain"""
        
    async def delegate_context(self, level: str, context_id: str, delegate_to: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate context data to higher level"""
```

**UnifiedContextController**
```python
# Location: src/fastmcp/task_management/interface/controllers/unified_context_controller.py
class UnifiedContextController:
    """Single MCP controller for all context operations"""
    
    async def handle_context_operation(self, action: str, **kwargs) -> Dict[str, Any]:
        """Route all context operations to unified service"""
```

#### 1.2 Update Database Models

**Remove Legacy Model**
```python
# Remove from models.py
class HierarchicalContext(Base):  # DELETE THIS CLASS
    __tablename__ = 'hierarchical_contexts'
    # ... (remove entire class definition)
```

**Keep Granular Models**
```python
# Keep these in models.py
class GlobalContext(Base):
    __tablename__ = 'global_contexts'
    
class ProjectContext(Base):
    __tablename__ = 'project_contexts'
    
class BranchContext(Base):
    __tablename__ = 'branch_contexts'
    
class TaskContext(Base):
    __tablename__ = 'task_contexts'
```

### Phase 2: API Migration

#### 2.1 Parameter Mapping

**Old Dual System → New Unified System**

| Old `manage_context` | Old `manage_context` | New `manage_context` (Unified) |
|---------------------|-----------------------------------|-------------------------------|
| `task_id` | `context_id` | `context_id` |
| `user_id` | `user_id` | `user_id` |
| `project_id` | `project_id` | `project_id` |
| `data_title` | `data.title` | `data.title` |
| `data_description` | `data.description` | `data.description` |
| N/A | `level` | `level` |
| N/A | `force_refresh` | `force_refresh` |

#### 2.2 Action Mapping

| Old Actions | New Unified Actions |
|-------------|-------------------|
| `create` | `create` |
| `get` | `get` |
| `update` | `update` |
| `delete` | `delete` |
| `resolve` | `resolve` |
| `delegate` | `delegate` |
| `add_insight` | `add_insight` |
| `add_progress` | `add_progress` |

### Phase 3: Code Migration Patterns

#### 3.1 Controller Updates

**Before (Dual System)**
```python
# Old way - using both tools
context_result = await manage_context(
    action="create",
    task_id=task_id,
    data_title="Task Context"
)

hierarchical_result = await manage_context(
    action="create",
    level="task",
    context_id=task_id,
    data={"title": "Task Context"}
)
```

**After (Unified System)**
```python
# New way - single tool
context_result = await manage_context(
    action="create",
    level="task",
    context_id=task_id,
    data={"title": "Task Context"}
)
```

#### 3.2 Service Integration

**Before (Dual System)**
```python
# Old way - multiple services
from ..services.context_service import ContextService
from ..services.hierarchical_context_service import HierarchicalContextService

context_service = ContextService()
hierarchical_service = HierarchicalContextService()

# Use both services...
```

**After (Unified System)**
```python
# New way - single service
from ..services.unified_context_service import UnifiedContextService

unified_service = UnifiedContextService()

# Use single service for all operations
```

#### 3.3 Repository Updates

**Before (Dual System)**
```python
# Old way - multiple repositories
from ..repositories.context_repository import ContextRepository
from ..repositories.hierarchical_context_repository import HierarchicalContextRepository
```

**After (Unified System)**
```python
# New way - single repository
from ..repositories.unified_context_repository import UnifiedContextRepository
```

### Phase 4: Test Migration

#### 4.1 Test Pattern Updates

**Before (Dual System Tests)**
```python
# Old test pattern
def test_dual_context_creation():
    # Test manage_context
    result1 = manage_context(action="create", task_id="test")
    
    # Test manage_context
    result2 = manage_context(action="create", level="task", context_id="test")
    
    # Verify both work
    assert result1["success"] and result2["success"]
```

**After (Unified System Tests)**
```python
# New test pattern
def test_unified_context_creation():
    # Test single manage_context
    result = manage_context(
        action="create",
        level="task", 
        context_id="test",
        data={"title": "Test Context"}
    )
    
    # Verify unified system works
    assert result["success"]
```

#### 4.2 Mock Updates

**Before (Dual System Mocks)**
```python
# Old mocking pattern
@patch('module.ContextService')
@patch('module.HierarchicalContextService')
def test_with_mocks(mock_hierarchical, mock_context):
    # Setup both mocks
    mock_context.return_value = Mock()
    mock_hierarchical.return_value = Mock()
```

**After (Unified System Mocks)**
```python
# New mocking pattern
@patch('module.UnifiedContextService')
def test_with_unified_mock(mock_unified):
    # Setup single mock
    mock_unified.return_value = Mock()
```

## Data Migration

### Context Data Transformation

#### 4.1 Legacy Data Export
```python
# Export existing context data
legacy_contexts = session.query(HierarchicalContext).all()
for context in legacy_contexts:
    # Transform to new format
    new_data = {
        "level": context.level,
        "context_id": context.context_id,
        "data": {
            "title": context.title,
            "description": context.description,
            "metadata": context.metadata
        }
    }
    # Store for migration
```

#### 4.2 New System Import
```python
# Import to unified system
unified_service = UnifiedContextService()
for data in migration_data:
    await unified_service.create_context(
        level=data["level"],
        context_id=data["context_id"],
        data=data["data"]
    )
```

## Validation and Testing

### 4.1 Migration Validation
```python
# Validate migration success
def validate_migration():
    # Check all contexts migrated
    old_count = session.query(HierarchicalContext).count()
    new_count = unified_service.get_context_count()
    
    assert new_count >= old_count, "Migration incomplete"
    
    # Check functionality
    test_result = unified_service.get_context("task", "test-task-id")
    assert test_result["success"], "Unified system not working"
```

### 4.2 Integration Testing
```python
# Test complete workflow
def test_task_completion_workflow():
    # Create task context
    context_result = manage_context(
        action="create",
        level="task",
        context_id="workflow-test",
        data={"title": "Workflow Test"}
    )
    
    # Complete task (should work now)
    task_result = manage_task(
        action="complete",
        task_id="workflow-test",
        completion_summary="Test completed successfully"
    )
    
    assert context_result["success"] and task_result["success"]
```

## Rollback Plan

### Emergency Rollback
If issues arise during migration:

1. **Restore Database Backup**
   ```bash
   # Restore pre-migration database
   cp database_backup.db database.db
   ```

2. **Revert Code Changes**
   ```bash
   # Revert to pre-migration commit
   git checkout pre-migration-commit
   ```

3. **Restore Legacy Controllers**
   ```python
   # Re-enable legacy controllers
   # Uncomment legacy imports and registrations
   ```

### Gradual Rollback
For partial rollback:

1. **Disable Unified System**
   ```python
   # In ddd_compliant_mcp_tools.py
   USE_UNIFIED_CONTEXT = False  # Switch back to legacy
   ```

2. **Re-enable Legacy Tools**
   ```python
   # Re-register legacy tools
   mcp.tool("manage_context_legacy")
   mcp.tool("manage_context_legacy")
   ```

## Post-Migration Cleanup

### 4.1 Remove Legacy Code
```python
# Delete legacy files
# - context_mcp_controller.py
# - hierarchical_context_facade_factory.py
# - hierarchical_context_repository.py
```

### 4.2 Update Documentation
- [ ] Update API documentation
- [ ] Update integration guides
- [ ] Update test documentation
- [ ] Update troubleshooting guides

## Troubleshooting

### Common Issues

#### Issue: "Context not found" errors
**Solution**: Verify context_id mapping in migration

#### Issue: Import errors for legacy modules
**Solution**: Update all imports to use unified modules

#### Issue: Parameter validation errors
**Solution**: Update parameter structure to unified format

#### Issue: Test failures
**Solution**: Update test mocks and assertions

### Verification Commands
```bash
# Test unified system
python -m pytest tests/test_unified_context.py -v

# Test integration
python -m pytest tests/integration/test_task_completion.py -v

# Test imports
python -c "from fastmcp.task_management.interface.controllers.unified_context_controller import UnifiedContextController; print('✅ Imports OK')"
```

## Success Criteria

### Migration Complete When:
- [ ] All legacy context tools removed
- [ ] Single `manage_context` tool handles all operations
- [ ] Task completion works reliably
- [ ] All tests pass
- [ ] No import errors
- [ ] Performance maintained or improved

### Quality Gates:
- [ ] Code coverage ≥ 90%
- [ ] All integration tests pass
- [ ] No critical linting errors
- [ ] Documentation updated
- [ ] Performance benchmarks met

---

**Migration Support**: Contact the development team for assistance with complex migration scenarios or issues not covered in this guide.

*Guide Version: 1.0*
*Last Updated: 2024-01-19* 