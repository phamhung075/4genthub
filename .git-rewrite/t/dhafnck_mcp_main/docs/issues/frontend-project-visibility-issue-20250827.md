# Frontend Project Visibility Issue - Analysis Report
**Date**: 2025-08-27
**Issue**: Newly created projects not visible in frontend

## Executive Summary
Projects created via MCP tools are successfully stored in Supabase database but are not visible in the frontend. Only the "frontend-visible-project" created on 2025-08-25 is visible. Root cause is a module import error in the context management system preventing proper context creation for new projects.

## Root Cause Analysis

### 1. Primary Issue: Context Module Import Error
- **Finding**: The `manage_context` MCP tool is trying to import `context_application_facade` which doesn't exist
- **Actual Module**: The correct module is `unified_context_facade.py`
- **Impact**: Context creation fails with `ModuleNotFoundError`
- **Evidence**: 
  ```python
  ModuleNotFoundError: No module named 'fastmcp.task_management.application.facades.context_application_facade'
  ```

### 2. Secondary Issue: Missing Global Context
- **Finding**: Projects require a global context parent but none exists
- **Error**: "Cannot create project context without global context"
- **Impact**: Even if module import was fixed, context creation would fail due to missing hierarchy

### 3. Frontend Visibility Dependency
- **Finding**: Frontend only displays projects that have a `project_context` field
- **Evidence**: `frontend-visible-project` has context, new projects don't
- **Impact**: Projects without context are invisible to frontend

## System Configuration Status

### ✅ Working Components:
- Supabase connection configured and healthy
- Database credentials properly set
- Backend server running and healthy
- Frontend server running (though marked unhealthy in Docker)
- Projects successfully creating in database
- Authentication system enabled

### ❌ Broken Components:
- Context management MCP tool module import
- Global context initialization
- Project context auto-creation
- Frontend health check failing

## Affected Projects
1. **test-project-beta-20250827** (ID: 69008dfa-77ed-4ffb-8e22-8b838a96cc22) - Created but invisible
2. **test-project-gamma-20250827** (ID: 0732ac0d-44f7-4de5-8840-36a4882927b4) - Created but invisible
3. Multiple other test projects from previous days - All invisible except one

## Impact Assessment
- **Severity**: HIGH - Core functionality broken
- **User Impact**: Cannot see or work with newly created projects
- **Data Integrity**: Low risk - data is stored correctly, just not accessible
- **System Stability**: Medium risk - frontend marked unhealthy

## Remediation Tasks

### Task 1: Fix Context Module Import Path
**Priority**: CRITICAL
**Type**: Bug Fix
**Description**: Update manage_context MCP tool to import correct module
**Action Required**:
1. Locate the manage_context tool implementation
2. Change import from `context_application_facade` to `unified_context_facade`
3. Update class reference from `ContextApplicationFacade` to `UnifiedContextFacade`
4. Test context operations

### Task 2: Initialize Global Context
**Priority**: HIGH
**Type**: System Initialization
**Description**: Create the global singleton context required for hierarchy
**Action Required**:
1. After fixing module import, create global_singleton context
2. Set up proper global context structure
3. Verify context inheritance chain works

### Task 3: Fix Frontend Health Check
**Priority**: MEDIUM
**Type**: Infrastructure
**Description**: Investigate and fix frontend container health check
**Action Required**:
1. Check frontend health check endpoint
2. Verify frontend can connect to backend
3. Fix any connection or configuration issues

### Task 4: Add Context Auto-Creation
**Priority**: HIGH
**Type**: Enhancement
**Description**: Automatically create context when projects are created
**Action Required**:
1. Modify project creation to include context creation
2. Ensure context hierarchy is maintained
3. Add error handling for context creation failures

### Task 5: Create Migration Script
**Priority**: MEDIUM
**Type**: Data Migration
**Description**: Create contexts for existing projects without them
**Action Required**:
1. Write script to find projects without contexts
2. Create contexts for each project
3. Verify frontend visibility after migration

## Verification Steps

After fixes are applied:
1. Test creating a new project via MCP tools
2. Verify context is created automatically
3. Check frontend shows the new project
4. Test all context operations (create, get, update, delete)
5. Verify context inheritance works (global → project → branch → task)

## Prevention Measures

1. **Add Integration Tests**: Test full project creation including context
2. **Module Import Validation**: Add startup checks for critical modules
3. **Health Check Enhancement**: Include context system in health checks
4. **Documentation Update**: Document context requirements for frontend visibility

## Prompts for Individual Fixes

### Prompt 1: Fix Context Module Import
```
The manage_context MCP tool has a module import error. It's trying to import 'context_application_facade' but the actual module is 'unified_context_facade'. 

Please:
1. Find where manage_context is implemented (likely in mcp tools or interface)
2. Update the import to use UnifiedContextFacade from unified_context_facade
3. Test that context operations work after the fix
```

### Prompt 2: Initialize Global Context
```
The context hierarchy requires a global_singleton context to exist before project contexts can be created.

Please:
1. Use the fixed manage_context tool to create global_singleton
2. Set up proper global context data structure
3. Verify projects can create contexts after global exists
4. Each user have only 1 global context link by user-id
```

### Prompt 3: Fix Frontend Health Check
```
The frontend Docker container shows as unhealthy but is running. 

Please:
1. Check docker logs for dhafnck-frontend container
2. Identify why health check is failing
3. Fix the health check configuration or endpoint
```

### Prompt 4: Add Auto Context Creation
```
Projects created via manage_project don't automatically create contexts, making them invisible to frontend.

Please:
1. Modify project creation in project_application_facade
2. Add automatic context creation after project is saved
3. Handle errors gracefully if context creation fails
```

### Prompt 5: Create Migration Script
```
Existing projects don't have contexts and are invisible in frontend.

Please create a migration script that:
1. Queries all projects from database
2. Checks which ones lack contexts
3. Creates contexts for projects missing them
4. Reports success/failure for each migration
```

## Conclusion

The issue is well-understood and fixable. The primary problem is a simple module naming mismatch that prevents context creation. Once fixed, the system should work as designed. The frontend visibility dependency on project contexts is by design, not a bug.

**Recommended Action**: Start with Task 1 (Fix Module Import) as it unblocks all other tasks.