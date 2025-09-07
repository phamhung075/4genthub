# Context Hierarchy Validation & Repository Fixes

## Issue Summary

The context hierarchy validation system had two critical issues that prevented project context creation in dual authentication scenarios:

### Issue 1: Context Hierarchy Validator Not Using User-Scoped Repositories Properly
- **Problem**: `ContextHierarchyValidator._validate_project_requirements()` was performing manual user-specific lookups instead of trusting user-scoped repositories
- **Symptom**: Project context creation failed with "Global context is required before creating project contexts" even when global context existed for the user
- **Root Cause**: Validator tried to construct user-specific IDs manually instead of using the already user-scoped repository methods

### Issue 2: Project Context Repository Data Mapping Issues
- **Problem**: Multiple field mapping issues in `ProjectContextRepository`
- **Symptoms**: Database constraint violations, incorrect parameter passing to entities
- **Root Causes**:
  1. Repository tried to use non-existent `context_data` field instead of `data` field
  2. Missing `id` field assignment causing primary key constraint violations
  3. Incorrect entity parameter mapping (passing `context_data` to ProjectContext which doesn't accept it)

## Solutions Applied

### Fix 1: Updated Context Hierarchy Validator (Lines 56-108)

**File**: `dhafnck_mcp_main/src/fastmcp/task_management/application/services/context_hierarchy_validator.py`

**Changes**:
- Removed manual user-specific ID construction
- Use user-scoped repository directly via `.get("global_singleton")` method
- Fall back to `.list()` method if direct get fails
- Trust that repositories are already properly user-scoped

**Key Code Change**:
```python
# OLD: Manual user-specific lookups
if self.user_id:
    user_global_id = f"{GLOBAL_SINGLETON_UUID}_{self.user_id}"
    global_context = self.global_repo.get(user_global_id)

# NEW: Trust user-scoped repository
global_context = self.global_repo.get("global_singleton")
if not global_context:
    global_contexts = self.global_repo.list()
    if global_contexts and len(global_contexts) > 0:
        global_context = global_contexts[0]
```

### Fix 2: Updated Project Context Repository (Multiple Locations)

**File**: `dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/repositories/project_context_repository_user_scoped.py`

**Changes**:

1. **Database Field Mapping** (Lines 100, 132, 194):
   ```python
   # OLD: Using non-existent field
   context_data=context_data
   db_model.context_data = context_data
   
   # NEW: Using correct field
   data=context_data
   db_model.data = context_data
   ```

2. **Primary Key Assignment** (Line 99):
   ```python
   # OLD: Missing id field
   db_model = ProjectContextModel(
       project_id=project_id,
       data=context_data,
       ...
   )
   
   # NEW: Setting both id and project_id
   db_model = ProjectContextModel(
       id=project_id,  # Primary key
       project_id=project_id,
       data=context_data,
       ...
   )
   ```

3. **Entity Construction** (Lines 129-134):
   ```python
   # OLD: Incorrect parameters
   entity = ProjectContext(
       id=str(uuid.uuid4()),
       project_id=project_id,
       context_data=context_data  # Invalid parameter
   )
   
   # NEW: Correct parameters
   entity = ProjectContext(
       id=project_id,
       project_name=context_data.get("project_name", f"Project-{project_id}"),
       project_settings=context_data.get("project_settings", {}),
       metadata=context_data.get("metadata", {})
   )
   ```

4. **Entity-to-Database Mapping** (Lines 377, 384):
   ```python
   # OLD: Using non-existent field and wrong ID field
   context_data = db_model.context_data or {}
   return ProjectContext(id=db_model.project_id, ...)
   
   # NEW: Using correct fields
   context_data = db_model.data or {}
   return ProjectContext(id=db_model.id, ...)
   ```

## Testing

Created comprehensive test coverage in:
- `src/tests/integration/test_context_dual_auth_hierarchy_fix.py`
- `docs/troubleshooting-guides/context-hierarchy-dual-auth-fix-demo.py`

**Test Results**:
- ✅ Global context creation works for users
- ✅ Project context creation now works when global context exists
- ✅ User isolation maintained (users can't see each other's contexts)
- ✅ Auto-creation feature works (system creates missing parent contexts)
- ✅ Hierarchy validation properly detects missing contexts

## Impact

This fix resolves the dual authentication issue where:
- JWT authentication was working correctly
- Global contexts could be created and retrieved
- BUT project context creation was failing due to validation logic not recognizing existing global contexts

With this fix:
- Context hierarchy validation works correctly with user-scoped repositories
- Project contexts can be created when global contexts exist
- Repository data mapping is consistent with database schema
- Database constraints are properly satisfied

## Files Modified

1. `dhafnck_mcp_main/src/fastmcp/task_management/application/services/context_hierarchy_validator.py`
2. `dhafnck_mcp_main/src/fastmcp/task_management/infrastructure/repositories/project_context_repository_user_scoped.py`

## Verification

Run the demonstration script:
```bash
cd dhafnck_mcp_main
python docs/troubleshooting-guides/context-hierarchy-dual-auth-fix-demo.py
```

Expected output: All tests pass, showing that context hierarchy validation and project context creation work correctly with dual authentication.