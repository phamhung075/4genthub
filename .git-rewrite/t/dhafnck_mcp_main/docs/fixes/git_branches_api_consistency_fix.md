# Git Branches API Consistency Fix

## Problem Description

After the ORM migration, git branches were not appearing in the frontend project list. The issue was that the backend API responses were using inconsistent field names for git branches:

- **Backend was returning**: `git_branchs` and `git_branchs_count`
- **Frontend was expecting**: `git_branchs` and `git_branchs_count`

This mismatch prevented the frontend from accessing git branch data, causing git branches to not appear in the project list.

## Root Cause Analysis

The domain entity `Project` uses the field name `git_branchs` internally (line 56 in `project.py`):
```python
git_branchs: Dict[str, GitBranch] = field(default_factory=dict)
```

However, the frontend's TypeScript interface expects `git_branchs`:
```typescript
export interface Project {
    id: string;
    name: string;
    description: string;
    git_branchs: Record<string, Branch>;  // Expected: git_branchs
}
```

Several use cases and services were directly exposing the internal field name `git_branchs` instead of translating it to the expected API field name `git_branchs`.

## Files Fixed

### 1. GetProjectUseCase (`get_project.py`)
**Line 32**: Changed API response field name
```python
# Before:
"git_branchs": {
    ...
}

# After: 
"git_branchs": {
    ...
}
```

### 2. ListProjectsUseCase (`list_projects.py`)
**Line 26**: Changed count field name
```python
# Before:
"git_branchs_count": len(project.git_branchs),

# After:
"git_branchs_count": len(project.git_branchs),
```

### 3. GitBranchApplicationService (`git_branch_application_service.py`)
**Line 113**: Changed response field name
```python
# Before:
"git_branchs": branch_list,

# After:
"git_branchs": branch_list,
```

### 4. ProjectHealthCheckUseCase (`project_health_check.py`)
**Line 103**: Changed count field name
```python
# Before:
"git_branchs_count": len(project.git_branchs),

# After:
"git_branchs_count": len(project.git_branchs),
```

### 5. CreateProjectUseCase (`create_project.py`)
**Line 131**: Changed response field name
```python
# Before:
"git_branchs": list(project.git_branchs.keys()),

# After:
"git_branchs": list(project.git_branchs.keys()),
```

### 6. GitBranchService (`git_branch_service.py`)
**Line 62**: Changed response field name
```python
# Before:
return {"success": True, "git_branchs": [branch.to_dict() for branch in project.git_branchs.values()]}

# After:
return {"success": True, "git_branchs": [branch.to_dict() for branch in project.git_branchs.values()]}
```

### 7. GitBranchApplicationFacade (`git_branch_application_facade.py`)
**Lines 269, 297**: Changed response field names (2 occurrences)
```python
# Before:
"git_branchs": git_branchs,

# After:
"git_branchs": git_branchs,
```

## Key Design Decision

**Internal vs External Field Names**: 
- The domain entity continues to use `git_branchs` internally (this maintains consistency within the domain layer)
- Only the API response layer translates this to `git_branchs` for frontend compatibility
- This follows the principle of keeping domain logic separate from API contracts

## Testing

Created comprehensive tests to ensure API consistency:

1. **`test_get_project_fix.py`**: Verifies GetProject returns `git_branchs`
2. **`test_list_projects_fix.py`**: Verifies ListProjects returns `git_branchs_count`
3. **`test_git_branchs_api_consistency.py`**: Comprehensive test suite covering all API endpoints

All tests verify that:
- The correct field names (`git_branchs`, `git_branchs_count`) are present in responses
- The incorrect field names (`git_branchs`, `git_branchs_count`) are NOT present in responses
- The data structure and content remain correct

## Impact

This fix resolves the frontend issue where git branches were not appearing in the project list. The frontend can now:

1. **List Projects**: See git branch counts for each project
2. **View Project Details**: Access full git branch information
3. **Navigate Branches**: Select and work with specific git branches
4. **Create Branches**: Add new git branches to projects

## Backwards Compatibility

This change is **breaking** for any API clients expecting the old field names (`git_branchs`). However:
- The internal domain model remains unchanged
- The fix aligns with the existing frontend expectations
- No database schema changes were required

## Verification

To verify the fix works:

1. **Backend Tests**: Run the test suite
   ```bash
   python -m pytest src/tests/integration/test_git_branchs_api_consistency.py -v
   ```

2. **Frontend Integration**: Check that git branches now appear in the project list UI

3. **API Testing**: Use tools like Postman to verify API responses contain `git_branchs` fields

## Related Issues

This fix addresses the core issue preventing git branches from appearing in the frontend after the ORM migration. It ensures consistent API field naming between backend and frontend components.