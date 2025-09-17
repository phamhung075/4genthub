# Label and Vision Repositories Migration to ORM

## Task: Migrate Label and Vision Repositories to SQLAlchemy ORM

### Objective
Create ORM implementations for Label and Vision repositories.

### Files to Create/Modify

1. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/label_repository.py`
   - Implement `ORMLabelRepository` class
   - Handle many-to-many relationship with tasks

2. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/vision_repository.py`
   - Implement `ORMVisionRepository` class
   - Note: Check if vision table exists in schema

### Label Repository Methods
- `create_label()`
- `get_label()`
- `update_label()`
- `delete_label()`
- `list_labels()`
- `get_label_by_name()`
- `assign_label_to_task()`
- `remove_label_from_task()`
- `get_tasks_by_label()`

### Vision Repository
- First check if vision table/model exists
- If not, may need to create the model
- Implement basic CRUD operations

### Testing
Create test scripts:
- `test_label_orm.py`
- `test_vision_orm.py` (if applicable)