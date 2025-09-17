# Remove Direct SQLite Dependencies

## Task: Remove Direct SQLite3 Imports and Connection Pool

### Objective
Replace all direct SQLite3 usage with SQLAlchemy ORM to support multiple databases.

### Files to Modify

1. **Replace SQLite Connection Pool**
   - File: `/src/fastmcp/task_management/infrastructure/database/connection_pool.py`
   - Action: Delete or replace with SQLAlchemy session management
   - Update all files that import from connection_pool

2. **Update Base Repository**
   - File: `/src/fastmcp/task_management/infrastructure/repositories/sqlite/base_repository.py`
   - Action: Create a compatibility layer or migrate to use BaseORMRepository
   - Ensure backward compatibility during transition

3. **Remove Direct sqlite3 Imports**
   Search and replace in these files:
   - Controllers that use sqlite3 directly
   - Service classes with database connections
   - Utility functions using sqlite3

### Migration Strategy
1. Create compatibility wrappers where needed
2. Use SQLAlchemy's raw SQL execution for complex queries
3. Gradually phase out SQLite-specific code

### Key Changes
- Replace `sqlite3.connect()` with SQLAlchemy sessions
- Replace `cursor.execute()` with `session.execute()`
- Replace `sqlite3.Row` with SQLAlchemy result mapping
- Update error handling from sqlite3 exceptions to SQLAlchemy exceptions

### Testing
- Ensure all existing tests pass
- Add tests for PostgreSQL compatibility
- Verify no performance regression