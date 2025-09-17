# Subtask Repository Migration to ORM

## Task: Migrate Subtask Repository to SQLAlchemy ORM

### Objective
Create an ORM implementation of the Subtask Repository for managing task subtasks.

### Files to Create/Modify

1. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/subtask_repository.py`
   - Implement `ORMSubtaskRepository` class
   - Handle assignees as JSON array
   - Track progress and completion

2. **Update**: `/src/fastmcp/task_management/infrastructure/repositories/subtask_repository_factory.py`
   - Add DATABASE_TYPE checking
   - Return appropriate repository

### Key Methods to Implement
- `create_subtask()`
- `get_subtask()`
- `update_subtask()`
- `delete_subtask()`
- `list_subtasks()`
- `get_subtasks_by_task()`
- `update_progress()`
- `complete_subtask()`
- `get_subtasks_by_assignee()`
- `bulk_update_status()`

### Special Considerations
- Assignees stored as JSON array
- Progress tracking (0-100%)
- Completion timestamps
- Impact on parent task
- Insights found during execution

### Testing
Create `test_subtask_orm.py` to verify:
- Subtask CRUD operations
- Progress updates
- Assignee management
- Relationship with parent tasks