# Agent Assignment Name Resolution

## Overview

The agent assignment functionality in DhafnckMCP has been enhanced to support user-friendly agent names in addition to UUIDs, making it easier for users to assign agents to git branches without needing to remember complex identifiers.

## Supported Agent Identifier Formats

### 1. UUID Format (Existing)
```python
# Valid UUID - preserved as-is
manage_git_branch(
    action="assign_agent",
    project_id="project-123",
    git_branch_id="branch-456", 
    agent_id="2d3727cf-6915-4b54-be8d-4a5a0311ca03"
)
```

### 2. Prefixed Agent Names (New)
```python
# Agent name with @ prefix - preserved as-is
manage_git_branch(
    action="assign_agent", 
    project_id="project-123",
    git_branch_id="branch-456",
    agent_id="@coding_agent"
)
```

### 3. Unprefixed Agent Names (New)
```python
# Agent name without @ prefix - automatically adds @
manage_git_branch(
    action="assign_agent",
    project_id="project-123", 
    git_branch_id="branch-456",
    agent_id="coding_agent"  # Becomes "@coding_agent"
)
```

## Implementation Details

### Agent Identifier Resolution Logic

The `_resolve_agent_identifier` method in `GitBranchMCPController` handles the resolution:

1. **UUID Detection**: Uses regex to identify valid UUID format (case-insensitive)
2. **Prefix Handling**: Preserves existing @ prefixes
3. **Auto-Prefixing**: Adds @ prefix to unprefixed names
4. **Error Handling**: Returns input as-is if resolution fails

### Auto-Registration

When an agent is assigned using a name (with or without @), the system:

1. **Checks Existence**: Looks for existing agent with that identifier
2. **Auto-Registers**: If not found, automatically registers the agent
3. **Assigns**: Proceeds with assignment using the resolved identifier

## Usage Examples

### Basic Assignment
```python
# All of these work and are equivalent:
manage_git_branch(action="assign_agent", agent_id="coding_agent")
manage_git_branch(action="assign_agent", agent_id="@coding_agent")

# UUID still works as before:
manage_git_branch(action="assign_agent", agent_id="a1b2c3d4-...")
```

### Branch Name Support
```python
# Can use branch name instead of branch ID
manage_git_branch(
    action="assign_agent",
    project_id="project-123",
    git_branch_name="feature/user-auth",  # Instead of git_branch_id
    agent_id="@security_agent"
)
```

### Unassignment
```python
# Unassignment supports the same formats
manage_git_branch(
    action="unassign_agent",
    project_id="project-123",
    git_branch_id="branch-456",
    agent_id="coding_agent"  # Resolved to "@coding_agent"
)
```

## Response Format

The enhanced response includes both original and resolved identifiers:

```json
{
  "success": true,
  "action": "assign_agent",
  "agent_id": "@coding_agent",           // Resolved identifier
  "original_agent_id": "coding_agent",   // What user provided
  "git_branch_id": "branch-456",
  "git_branch_name": "feature/auth", 
  "workflow_guidance": { ... }
}
```

## Error Handling

### Invalid Branch
```json
{
  "success": false,
  "error": "Git branch not found: non-existent-branch",
  "error_code": "BRANCH_NOT_FOUND"
}
```

### Missing Parameters
```json
{
  "success": false, 
  "error": "Missing required field: agent_id",
  "error_code": "MISSING_FIELD"
}
```

## Edge Cases

### Special Characters
The system preserves special characters in agent names:
- `agent-with-dashes` → `@agent-with-dashes`
- `agent_with_underscores` → `@agent_with_underscores` 
- `agent.with.dots` → `@agent.with.dots`

### Case Sensitivity
Agent names are case-sensitive:
- `Agent` → `@Agent`
- `agent` → `@agent`
- `AGENT` → `@AGENT`

### Malformed UUIDs
Invalid UUIDs are treated as agent names:
- `2d3727cf-6915-4b54-be8d` → `@2d3727cf-6915-4b54-be8d`

## Backward Compatibility

This enhancement is fully backward compatible:
- Existing UUID-based assignments continue to work unchanged
- No breaking changes to API or response formats
- All existing functionality preserved

## Testing

### Unit Tests
- `test_agent_identifier_resolution.py` - 10 comprehensive tests covering all formats and edge cases
- Tests UUID detection, prefix handling, special characters, error handling

### Integration Tests  
- `test_agent_assignment_mcp_integration.py` - End-to-end testing via MCP interface
- Tests real assignment scenarios with various agent formats

## Performance Impact

- Minimal overhead: Single regex check for UUID detection
- O(1) string operations for prefix handling
- No database queries during resolution (only during assignment)

## Files Modified

1. **GitBranchMCPController** (`git_branch_mcp_controller.py`)
   - Added `_resolve_agent_identifier()` method
   - Updated `_handle_assign_agent()` and `_handle_unassign_agent()`
   - Enhanced response tracking

2. **Tests**
   - `test_agent_identifier_resolution.py` - Unit tests
   - `test_agent_assignment_mcp_integration.py` - Integration tests

## Future Enhancements

### Potential Improvements
1. **Agent Name Validation**: Add validation rules for agent names
2. **Agent Lookup**: Support lookup by partial name matching
3. **Agent Suggestions**: Provide suggestions for typos in agent names
4. **Bulk Operations**: Support assigning multiple agents at once

### Configuration Options
Future versions could add configuration for:
- Custom prefix characters (beyond @)
- Agent name formatting rules
- Auto-registration policies

## Migration Notes

No migration required - this is a feature enhancement with full backward compatibility.

## Related Documentation

- [Agent Management Guide](../api-reference.md#agent-management)
- [Git Branch Operations](../api-reference.md#git-branch-management)
- [Error Handling](../troubleshooting/error-codes.md)