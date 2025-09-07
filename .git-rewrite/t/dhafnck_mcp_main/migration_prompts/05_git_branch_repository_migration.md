# Git Branch Repository Migration to ORM

## Task: Migrate Git Branch (Project Task Tree) Repository to SQLAlchemy ORM

### Objective
Create an ORM implementation of the Git Branch Repository for managing project branches/task trees.

### Files to Create/Modify

1. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/git_branch_repository.py`
   - Implement `ORMGitBranchRepository` class
   - Use ProjectTaskTree model
   - Handle relationships with projects and tasks

2. **Update**: `/src/fastmcp/task_management/infrastructure/repositories/git_branch_repository_factory.py`
   - Add ORM support
   - Check DATABASE_TYPE

### Key Methods to Implement
- `create_git_branch()`
- `get_git_branch()`
- `update_git_branch()`
- `delete_git_branch()`
- `list_git_branchs()`
- `get_branches_by_project()`
- `assign_agent_to_branch()`
- `update_task_counts()`
- `get_branch_statistics()`

### Relationships
- Many-to-one with Project
- One-to-many with Tasks
- Track task counts (total and completed)

### Testing
Create `test_git_branch_orm.py` to verify:
- Branch creation and management
- Agent assignment
- Task count updates
- Project relationships