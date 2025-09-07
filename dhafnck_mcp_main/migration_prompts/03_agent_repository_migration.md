# Agent Repository Migration to ORM

## Task: Migrate Agent Repository to SQLAlchemy ORM

### Objective
Create an ORM implementation of the Agent Repository for managing AI agents in the system.

### Files to Create/Modify

1. **Create**: `/src/fastmcp/task_management/infrastructure/repositories/orm/agent_repository.py`
   - Implement `ORMAgentRepository` class
   - Handle agent capabilities (JSON array)
   - Manage agent availability and status

2. **Update**: `/src/fastmcp/task_management/infrastructure/repositories/agent_repository_factory.py`
   - Add ORM support with DATABASE_TYPE checking
   - Maintain backward compatibility

### Key Methods to Implement
- `create_agent()`
- `get_agent()`
- `update_agent()`
- `delete_agent()`
- `list_agents()`
- `get_available_agents()`
- `update_agent_status()`
- `get_agents_by_capability()`
- `update_availability_score()`

### Special Features
- Agent capabilities stored as JSON array
- Availability scoring system
- Last active timestamp tracking
- Agent metadata support

### Testing
Create `test_agent_orm.py` to verify:
- Agent CRUD operations
- Capability-based queries
- Availability updates
- Status management