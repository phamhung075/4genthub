# Template Repository Migration to ORM

## Task: Migrate Template Repository to SQLAlchemy ORM

### Objective
Create an ORM implementation of the Template Repository for managing reusable templates.

### Files to Create/Modify

1. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/template_repository.py`
   - Implement `ORMTemplateRepository` class
   - Handle template content as JSON
   - Support tags as JSON array

2. **Create/Update**: Template repository factory if exists
   - Add DATABASE_TYPE checking
   - Return appropriate repository

### Key Methods to Implement
- `create_template()`
- `get_template()`
- `update_template()`
- `delete_template()`
- `list_templates()`
- `get_templates_by_type()`
- `get_templates_by_category()`
- `search_templates_by_tags()`
- `increment_usage_count()`

### Template Types
- task
- checklist
- workflow

### Testing
Create `test_template_orm.py` to verify:
- Template CRUD operations
- Tag-based search
- Usage tracking
- JSON content storage