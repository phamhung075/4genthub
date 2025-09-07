# Hierarchical Context Repository Migration to ORM

## Task: Migrate Hierarchical Context Repository to SQLAlchemy ORM

### Objective
Create an ORM implementation of the Hierarchical Context Repository, which is critical for the context management system.

### Files to Create/Modify

1. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/hierarchical_context_repository.py`
   - Implement `ORMHierarchicalContextRepository` class
   - Handle JSON fields for patterns, architectures, constraints, etc.
   - Implement context inheritance logic
   - Support context delegation

2. **Update**: `/src/fastmcp/task_management/infrastructure/repositories/hierarchical_context_repository_factory.py`
   - Add DATABASE_TYPE checking
   - Return appropriate repository implementation

### Special Considerations
- The context system uses complex JSON fields
- Must maintain parent-child relationships
- Support for context merging and inheritance
- Handle version tracking

### Key Methods to Implement
- `create_context()`
- `get_context()`
- `update_context()`
- `resolve_context()` - with inheritance
- `delegate_context()`
- `get_context_hierarchy()`
- `merge_contexts()`
- `search_contexts()`

### JSON Field Handling
Use SQLAlchemy's JSON column type which works with both:
- PostgreSQL: Native JSONB
- SQLite: JSON stored as TEXT

### Testing
Create `test_hierarchical_context_orm.py` to verify:
- Context creation at all levels (global, project, task)
- Context inheritance resolution
- JSON data storage and retrieval
- Context delegation between levels