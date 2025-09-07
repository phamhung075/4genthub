# Database Schema Mismatch Issue - Context Tables

## Issue Date
2025-01-13

## Severity
**CRITICAL** - System unable to connect to Supabase database

## Summary
Complete database schema mismatch between SQLAlchemy ORM models and actual Supabase database structure, causing system-wide connection failures and preventing all context operations.

## Symptoms
1. **Primary Error**: "column branch_contexts.parent_project_context_id does not exist"
2. **Secondary Errors**: 
   - "Could not initialize target column for ForeignKey 'project_contexts.id'"
   - "Could not determine join condition between parent/child tables"
3. **Impact**: Complete inability to use Supabase cloud database

## Root Cause Analysis

### 1. Schema Mismatches
The ORM models were completely out of sync with the actual database:

| Table | Expected (ORM) | Actual (Database) | Issue |
|-------|---------------|-------------------|-------|
| global_contexts | id: String | id: VARCHAR(255) | Type mismatch |
| project_contexts | project_id (PK) | id (PK) | Wrong primary key |
| branch_contexts | parent_project_context_id | (doesn't exist) | Non-existent column |
| task_contexts | task_id (PK) | id (PK) | Wrong primary key |

### 2. Foreign Key Type Conflicts
- global_contexts had VARCHAR(255) ID
- Other tables expected UUID foreign keys
- PostgreSQL couldn't create relationships between VARCHAR and UUID

### 3. Docker Caching
- Docker containers cached old Python code
- Rebuilds didn't pick up model changes
- Python __pycache__ files persisted

## Solution Implemented

### Phase 1: Schema Discovery
Used SQL introspection to discover actual database structure:
```python
inspector = inspect(engine)
for table in ['global_contexts', 'project_contexts', 'branch_contexts', 'task_contexts']:
    columns = inspector.get_columns(table)
    # Analyzed actual column types and names
```

### Phase 2: ORM Model Updates
Updated all context models to match database exactly:
```python
class BranchContext(Base):
    __tablename__ = "branch_contexts"
    
    # Changed to match actual database
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    branch_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ...)
    # Removed non-existent parent_project_context_id
    parent_project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ...)
```

### Phase 3: Database Recreation
When type conflicts persisted, recreated all tables with consistent UUID types:
```sql
DROP TABLE IF EXISTS task_contexts CASCADE;
DROP TABLE IF EXISTS branch_contexts CASCADE;
DROP TABLE IF EXISTS project_contexts CASCADE;
DROP TABLE IF EXISTS global_contexts CASCADE;

CREATE TABLE global_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID,
    ...
);
-- Recreated all tables with UUID for ALL id fields
```

### Phase 4: Docker Rebuild Enhancement
Enhanced docker-menu.sh to ensure clean rebuilds:
```bash
force_complete_rebuild() {
    # Stop and remove containers
    docker stop $(docker ps -aq --filter "name=dhafnck")
    docker rm $(docker ps -aq --filter "name=dhafnck")
    
    # Remove images
    docker rmi $(docker images -q --filter "reference=*dhafnck*") -f
    
    # Clear Python cache
    find ../dhafnck_mcp_main -type d -name "__pycache__" -exec rm -rf {} +
}
```

## Files Modified

### ORM Models
- `src/fastmcp/task_management/infrastructure/database/models.py`
  - GlobalContext: Changed id to UUID
  - ProjectContext: Changed primary key to id
  - BranchContext: Added id as primary key, removed parent_project_context_id
  - TaskContext: Added id as primary key
  - All models: Added explicit primaryjoin for relationships

### Repository Layer
- `src/fastmcp/task_management/infrastructure/repositories/branch_context_repository.py`
  - Updated to use correct column names

### Docker Build System
- `docker-system/docker-menu.sh`
  - Added force_complete_rebuild() function
  - Added Python cache clearing
  - Added option 10 for complete rebuild

### Database Scripts
- `/tmp/recreate_tables.py` - Script to recreate all context tables
- `/tmp/check_global.py` - Schema inspection script
- `/tmp/test_connection.py` - Connection test script

## Prevention Measures

### 1. Schema Validation
Need to add startup schema validation:
```python
def validate_schema_on_startup():
    """Validate ORM models match database schema"""
    inspector = inspect(engine)
    for model in [GlobalContext, ProjectContext, BranchContext, TaskContext]:
        db_columns = inspector.get_columns(model.__tablename__)
        model_columns = model.__table__.columns
        # Compare and validate
```

### 2. Migration System
Implement proper database migrations:
- Use Alembic for schema versioning
- Track all schema changes
- Automatic migration on startup

### 3. Docker Build Improvements
- Always clear Python cache in Dockerfile
- Add build verification step
- Include schema validation in health checks

### 4. Testing
- Add integration tests for all context operations
- Test against both SQLite and PostgreSQL
- Validate foreign key relationships

## Lessons Learned

1. **Schema Synchronization Critical**: ORM models MUST match database exactly
2. **Type Consistency Required**: All related ID fields must use same type (UUID)
3. **Docker Caching Dangerous**: Python cache can hide code changes
4. **Introspection Valuable**: SQL introspection quickly reveals mismatches
5. **Explicit Relationships**: SQLAlchemy needs explicit primaryjoin when ambiguous

## Related Issues
- Task count synchronization (#task-count-sync)
- Agent auto-registration duplicates (#agent-registration)
- Context inheritance chain (#context-inheritance)

## Status
**RESOLVED** - All context tables recreated with consistent UUID types, ORM models updated, Docker rebuild process enhanced.

## Follow-up Actions
1. ✅ Update CHANGELOG.md
2. ✅ Create this issue documentation
3. ⏳ Run full test suite
4. ⏳ Add schema validation on startup
5. ⏳ Implement migration system
6. ⏳ Add integration tests for context operations