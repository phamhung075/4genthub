# Batch Update All Repository Factories

## Task: Update All Repository Factories to Support ORM

### Objective
Update all repository factory files to check DATABASE_TYPE and return appropriate repository implementation.

### Files to Modify

1. **All Factory Files in**: `/src/fastmcp/task_management/infrastructure/repositories/`
   - `project_repository_factory.py`
   - `subtask_repository_factory.py` 
   - `git_branch_repository_factory.py`
   - `agent_repository_factory.py`
   - `hierarchical_context_repository_factory.py`
   - Any other `*_factory.py` files

### Standard Pattern to Apply
```python
import os
from .sqlite.xxx_repository import SQLiteXxxRepository
from .orm.xxx_repository import ORMXxxRepository

def create_repository(...):
    database_type = os.getenv("DATABASE_TYPE", "sqlite").lower()
    
    if database_type == "postgresql":
        return ORMXxxRepository(...)
    else:
        # Existing SQLite logic
        return SQLiteXxxRepository(...)
```

### Checklist for Each Factory
- [ ] Add import for ORM repository
- [ ] Add DATABASE_TYPE check
- [ ] Return ORM repository for PostgreSQL
- [ ] Maintain backward compatibility for SQLite
- [ ] Update any factory-specific methods

### Testing
Create `test_all_factories.py` to verify:
- All factories create correct repository type
- Both SQLite and PostgreSQL work
- No breaking changes to existing code