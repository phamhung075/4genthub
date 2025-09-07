# Agent Assignment Name Resolution Fix

## Problem Statement
The `manage_git_branch` action with `assign_agent` was failing when using `@agent_name` format (e.g., `@coding_agent`). The system only accepted UUID format, causing PostgreSQL UUID validation errors when agent names were passed.

## Error Symptoms
```
PostgreSQL UUID validation fails when using:
- agent_id="@coding_agent"
- agent_id="coding_agent"
```

## Root Cause
The controller's `_resolve_agent_identifier` method was returning agent names (with or without @ prefix) directly instead of resolving them to valid UUIDs. The downstream `assign_agent_to_tree` method expected valid UUIDs for database operations.

## Solution Implemented

### 1. Added Agent Name Lookup (agent_repository.py)
Created a new method `find_by_name` to look up agents by their name:
```python
def find_by_name(self, name: str) -> Optional[Agent]:
    """Find an agent by its name."""
    clean_name = name.lstrip('@')
    agent = self.get_by_field("name", clean_name)
    if agent:
        return agent
    # Also try with @ prefix
    agent = self.get_by_field("name", f"@{clean_name}")
    return agent
```

### 2. Enhanced Agent Resolution (git_branch_mcp_controller.py)
Updated `_resolve_agent_identifier` to:
1. Check if input is already a valid UUID → return as-is
2. If it's a name, look up existing agent by name → return UUID if found
3. If agent doesn't exist, generate deterministic UUID and return special format `uuid:name` for auto-registration

```python
def _resolve_agent_identifier(self, project_id: str, agent_identifier: str) -> str:
    # Check if UUID
    if uuid_pattern.match(agent_identifier):
        return agent_identifier
    
    # Look up by name
    agent_name = agent_identifier.lstrip('@')
    agent = agent_repo.find_by_name(agent_name)
    if agent:
        return agent.id
    
    # Generate UUID for auto-registration
    namespace_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, project_id)
    agent_uuid = str(uuid.uuid5(namespace_uuid, agent_name))
    return f"{agent_uuid}:{agent_name}"  # Special format preserves name
```

### 3. Updated Auto-Registration (agent_repository.py)
Enhanced `assign_agent_to_tree` to parse the special `uuid:name` format:
```python
def assign_agent_to_tree(self, project_id: str, agent_id: str, git_branch_id: str):
    # Parse special format
    actual_agent_id = agent_id
    agent_name = None
    
    if ':' in agent_id:
        parts = agent_id.split(':', 1)
        actual_agent_id = parts[0]
        agent_name = parts[1]
    
    # Use parsed values for auto-registration
```

## Supported Formats
After this fix, the system now accepts:
1. **UUID format**: `"2d3727cf-6915-4b54-be8d-4a5a0311ca03"`
2. **Agent name with @**: `"@coding_agent"`  
3. **Agent name without @**: `"coding_agent"`

## Benefits
- **Backward Compatibility**: Existing UUID-based calls continue to work
- **User-Friendly**: AI agents can use intuitive names like `@coding_agent`
- **Auto-Registration**: New agents are automatically registered with proper names
- **Deterministic UUIDs**: Same agent name always generates the same UUID within a project

## Test Coverage
Created comprehensive tests in:
- `tests/test_agent_assignment_fix.py` - Unit tests for each component
- `tests/test_agent_assignment_integration.py` - Integration tests for end-to-end flow

All tests pass successfully, confirming the fix works for all supported formats.

## Usage Examples

### Using Agent Name
```python
manage_git_branch(
    action="assign_agent",
    project_id="proj-123",
    git_branch_id="branch-456",
    agent_id="@coding_agent"  # Works now!
)
```

### Using UUID (Still Works)
```python
manage_git_branch(
    action="assign_agent", 
    project_id="proj-123",
    git_branch_id="branch-456",
    agent_id="2d3727cf-6915-4b54-be8d-4a5a0311ca03"
)
```

### Without @ Prefix  
```python
manage_git_branch(
    action="assign_agent",
    project_id="proj-123",
    git_branch_id="branch-456",
    agent_id="coding_agent"  # Also works!
)
```

## Files Modified
1. `/src/fastmcp/task_management/infrastructure/repositories/orm/agent_repository.py`
   - Added `find_by_name` method
   - Enhanced `assign_agent_to_tree` to handle special format

2. `/src/fastmcp/task_management/interface/controllers/git_branch_mcp_controller.py`
   - Updated `_resolve_agent_identifier` for name resolution

## Implementation Date
2025-08-08