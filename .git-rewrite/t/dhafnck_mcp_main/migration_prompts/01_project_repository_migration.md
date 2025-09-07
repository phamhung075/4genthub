# Project Repository Migration to ORM

## Task: Migrate Project Repository to SQLAlchemy ORM

### Objective
Create an ORM implementation of the Project Repository using SQLAlchemy, similar to the Task Repository implementation.

### Files to Create/Modify

1. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/project_repository.py`
   - Implement `ORMProjectRepository` class extending `BaseORMRepository`
   - Convert between SQLAlchemy Project model and domain entities
   - Implement all methods from `domain/repositories/project_repository.py`

2. **Update**: `/src/fastmcp/task_management/infrastructure/repositories/project_repository_factory.py`
   - Add import for `ORMProjectRepository`
   - Check `DATABASE_TYPE` environment variable
   - Return ORM repository when PostgreSQL is configured

### Reference Implementation
Use `/src/fastmcp/task_management/infrastructure/repositories/orm/task_repository.py` as a reference for:
- Repository structure
- Entity conversion methods
- Transaction handling
- Error handling patterns

### Key Methods to Implement
- `create_project()`
- `get_project()`
- `update_project()`
- `delete_project()`
- `list_projects()`
- `get_project_by_name()`
- `search_projects()`
- `get_project_statistics()`

### Testing
Create a test script: `test_project_orm.py` to verify:
- Project creation with PostgreSQL
- Project retrieval and updates
- Relationship with git branches
- Search functionality