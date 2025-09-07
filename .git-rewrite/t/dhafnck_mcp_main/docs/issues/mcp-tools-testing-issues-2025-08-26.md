# MCP Tools Testing Issues Report - 2025-08-26

## Executive Summary
Comprehensive testing of dhafnck_mcp_http tools revealed several critical authentication and parameter issues that prevent proper functionality across multiple management systems.

## Testing Environment
- **Date**: 2025-08-26
- **Tester**: AI Agent (test-user-001)
- **System**: dhafnck_mcp_http MCP server
- **Test Scope**: Project, Git Branch, Task, Subtask, and Context Management

## Issues Identified

### Issue 1: User Authentication Required But Not Documented
**Severity**: Critical
**Affected Tools**: 
- `manage_project`
- `manage_git_branch`
- `manage_task`

**Problem Description**:
All management tools require `user_id` parameter for authentication but this requirement is not clearly documented in tool descriptions or parameter specifications.

**Error Messages**:
```
Operation requires user authentication. No user ID was provided.
Git branch facade creation requires user authentication. No user ID was provided.
Task context resolution requires user authentication. No user ID was provided.
```

**Impact**: Cannot perform any operations without providing user_id parameter.

**Test Case**:
```python
# Fails
mcp__dhafnck_mcp_http__manage_project(action="create", name="test-project")

# Works
mcp__dhafnck_mcp_http__manage_project(action="create", name="test-project", user_id="test-user-001")
```

---

### Issue 2: Git Branch Management User ID Parameter Not Accepted
**Severity**: Critical
**Affected Tool**: `manage_git_branch`

**Problem Description**:
The `manage_git_branch` tool requires user authentication but does not accept `user_id` as a parameter, creating an impossible situation where authentication is required but cannot be provided.

**Error Messages**:
```
# Without user_id:
"Git branch facade creation requires user authentication. No user ID was provided."

# With user_id:
"1 validation error for call[manage_git_branch]
user_id
  Unexpected keyword argument [type=unexpected_keyword_argument, input_value='test-user-001', input_type=str]"
```

**Impact**: Cannot create, update, or list git branches.

---

### Issue 3: Global Context Creation Fails
**Severity**: High
**Affected Tool**: `manage_context`

**Problem Description**:
Creating global context fails with UUID format error when using the documented "global_singleton" identifier.

**Error Messages**:
```
"badly formed hexadecimal UUID string"
```

**Test Case**:
```python
# Fails
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="global",
    context_id="global_singleton",
    data={"organization": "Test"}
)
```

**Impact**: Cannot initialize global context, which blocks creation of project contexts.

---

### Issue 4: Project Context Requires Non-Existent Global Context
**Severity**: High
**Affected Tool**: `manage_context`

**Problem Description**:
Project context creation requires global context to exist first, but global context cannot be created due to Issue #3.

**Error Messages**:
```
"Global context is required before creating project contexts"
```

**Impact**: Cannot create any context hierarchy, blocking context management functionality.

---

### Issue 5: Task Management Authentication Not Configurable
**Severity**: Critical
**Affected Tool**: `manage_task`

**Problem Description**:
Task management requires authentication but doesn't provide a way to pass user credentials through the tool interface. The `assignees` parameter is for task assignment, not authentication.

**Error Messages**:
```
"Task context resolution requires user authentication. No user ID was provided."
```

**Test Case**:
```python
# All attempts fail
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Task title",
    assignees="test-user-001"  # This is for assignment, not auth
)
```

**Impact**: Cannot create, update, or manage tasks.

---

## Summary of Blocked Functionality

Due to the authentication and parameter issues, the following operations are completely blocked:

1. **Git Branch Management**: Cannot create, list, or manage branches
2. **Task Management**: Cannot create, update, or manage tasks
3. **Subtask Management**: Cannot test (depends on task creation)
4. **Context Hierarchy**: Cannot create proper context hierarchy
5. **Task Dependencies**: Cannot test (depends on task creation)
6. **Task Completion**: Cannot test (depends on task creation)

## Successful Operations

The following operations worked correctly when proper authentication was provided:

1. **Project Creation**: Works with user_id parameter
2. **Project Get**: Works with user_id parameter
3. **Project List**: Works with user_id parameter
4. **Project Update**: Works with user_id parameter
5. **Project Health Check**: Works with user_id parameter

## Recommendations

1. **Immediate Actions**:
   - Fix `manage_git_branch` to accept user_id parameter
   - Fix `manage_task` to accept user_id or implement proper authentication flow
   - Fix global context creation to handle "global_singleton" properly

2. **Documentation Updates**:
   - Clearly document authentication requirements for all tools
   - Add user_id to required parameters where needed
   - Provide examples showing proper authentication

3. **API Design Improvements**:
   - Consider implementing session-based authentication
   - Standardize authentication across all tools
   - Provide clear error messages indicating missing authentication

## Test Coverage Achieved

- ✅ Project Management: 80% (missing context creation)
- ❌ Git Branch Management: 0% (blocked by auth issue)
- ❌ Task Management: 0% (blocked by auth issue)
- ❌ Subtask Management: 0% (blocked by task creation)
- ❌ Context Management: 10% (blocked by global context issue)
- ❌ Dependency Management: 0% (blocked by task creation)

## Next Steps

1. Fix authentication issues in the backend
2. Update tool parameter definitions
3. Re-run comprehensive tests
4. Create integration tests to prevent regression