# Branch Context Auto-Detection of project_id

## Issue
When creating a branch context in the hierarchical context system, users were required to manually provide the `project_id` even though the branch entity already knows which project it belongs to. This created unnecessary friction and potential for errors.

## Solution
Implemented automatic detection of `project_id` from the git branch entity when creating branch contexts.

## Implementation Details

### 1. UnifiedContextService Enhancement
Added auto-detection logic in `create_context` method:
- When creating a branch context without `project_id` in data
- Attempts to fetch the git branch entity using the branch_id
- Extracts the project_id from the branch entity
- Adds it to the context data before validation

### 2. Support for Both Sync and Async Repositories
The implementation handles both synchronous and asynchronous git branch repositories:
- Checks if repository has sync `get()` method
- Falls back to async `find_by_id()` with event loop if needed

### 3. Graceful Fallback
If auto-detection fails:
- Logs debug message but doesn't fail the operation
- Continues with normal validation
- User gets helpful error message explaining auto-detection capability

### 4. Updated Error Messages
The hierarchy validator now provides enhanced guidance:
- Explains that project_id can be auto-detected for existing branches
- Shows examples both with and without explicit project_id
- Clarifies when auto-detection applies

## Usage Examples

### Before (Manual project_id Required)
```python
# User had to know and provide project_id
manage_context(
    action="create",
    level="branch",
    context_id="branch-uuid-123",
    data={
        "project_id": "project-uuid-456",  # Required manually
        "git_branch_name": "feature/my-feature"
    }
)
```

### After (Auto-Detection)
```python
# For existing branches, project_id is auto-detected
manage_context(
    action="create", 
    level="branch",
    context_id="branch-uuid-123",
    data={
        "git_branch_name": "feature/my-feature"
        # project_id auto-detected from branch entity!
    }
)

# Explicit project_id still works (takes precedence)
manage_context(
    action="create",
    level="branch", 
    context_id="branch-uuid-123",
    data={
        "project_id": "project-uuid-456",  # Optional, overrides auto-detection
        "git_branch_name": "feature/my-feature"
    }
)
```

## Benefits
1. **Reduced Friction**: Users don't need to look up project_id for existing branches
2. **Fewer Errors**: Eliminates incorrect project_id assignments
3. **Backward Compatible**: Explicit project_id still works and takes precedence
4. **Graceful Degradation**: Falls back to validation errors if auto-detection fails

## Test Coverage
Comprehensive unit tests added in `test_branch_context_auto_detect_project_id.py`:
- Auto-detection with sync repository
- Auto-detection with async repository  
- Explicit project_id skips auto-detection
- Graceful handling of auto-detection failures
- Updated error message validation

All tests passing ✅