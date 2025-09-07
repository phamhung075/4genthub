# MCP Tools Fix Prompts - 2025-08-26

## Overview
This document contains specific, detailed prompts for fixing each issue identified during MCP tools testing. Each prompt can be used in a new chat session to address the specific issue.

---

## Fix Prompt 1: Add User ID Parameter to Git Branch Management

**Use this prompt to fix the git branch management authentication issue:**

```
I need help fixing the manage_git_branch tool in dhafnck_mcp_http. The tool currently requires user authentication but doesn't accept user_id as a parameter.

Current situation:
1. When calling manage_git_branch without user_id, it returns: "Git branch facade creation requires user authentication. No user ID was provided."
2. When trying to pass user_id parameter, it returns: "Unexpected keyword argument" validation error

The issue is in:
- dhafnck_mcp_main/src/fastmcp/task_management/interface/consolidated_mcp_tools.py (or ddd_compliant_mcp_tools.py)
- The manage_git_branch function definition

Please:
1. Add user_id as an optional parameter to the manage_git_branch function
2. Pass it through to the GitBranchApplicationFacade
3. Ensure it follows the same pattern as manage_project which already accepts user_id
4. Update the function signature and parameter schema

The fix should allow this to work:
mcp__dhafnck_mcp_http__manage_git_branch(
    action="create",
    project_id="project-id",
    git_branch_name="feature/test",
    user_id="test-user-001"
)
```

---

## Fix Prompt 2: Fix Global Context Creation UUID Issue

**Use this prompt to fix the global context UUID handling:**

```
I need help fixing the global context creation in manage_context tool. The global context uses "global_singleton" as its identifier but the system is trying to parse it as a UUID.

Current error when creating global context:
- context_id="global_singleton" returns: "badly formed hexadecimal UUID string"

The issue is likely in:
- dhafnck_mcp_main/src/fastmcp/task_management/application/facades/context_application_facade.py
- The _handle_global_singleton method or context_id validation

Please:
1. Ensure "global_singleton" is properly converted to the singleton UUID (00000000-0000-0000-0000-000000000001)
2. Fix the context creation to handle this special case before UUID validation
3. Update any validation logic that's preventing this conversion

The fix should allow this to work:
mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="global",
    context_id="global_singleton",
    data={"organization": "Test"},
    user_id="test-user-001"
)
```

---

## Fix Prompt 3: Add User Authentication to Task Management

**Use this prompt to fix task management authentication:**

```
I need help adding user authentication support to the manage_task tool. Currently it requires authentication but provides no way to pass user credentials.

Current error: "Task context resolution requires user authentication. No user ID was provided."

The issue is in:
- dhafnck_mcp_main/src/fastmcp/task_management/interface/consolidated_mcp_tools.py
- The manage_task function definition
- dhafnck_mcp_main/src/fastmcp/task_management/application/facades/task_application_facade.py

Please:
1. Add user_id as an optional parameter to manage_task function (like manage_project has)
2. Pass user_id through to TaskApplicationFacade methods
3. Update TaskApplicationFacade to use the user_id for authentication
4. Ensure the parameter is properly documented in the schema

The fix should allow this to work:
mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id="branch-id",
    title="Test Task",
    user_id="test-user-001"
)
```

---

## Fix Prompt 4: Fix Context Hierarchy Initialization

**Use this prompt to fix the context hierarchy dependency issue:**

```
I need help fixing the context hierarchy initialization. Project contexts require global context to exist, but global context creation is failing.

Current issues:
1. Global context creation fails with UUID error (see Fix Prompt 2)
2. Project context creation fails with: "Global context is required before creating project contexts"
3. There's no way to bootstrap the context hierarchy

The issue is in:
- dhafnck_mcp_main/src/fastmcp/task_management/domain/services/context_service.py
- The validation logic for context creation

Please:
1. Allow project context creation even if global doesn't exist (auto-create global)
2. OR provide a bootstrap method that creates the hierarchy
3. OR relax the requirement and make global context optional
4. Document the proper initialization sequence

The system should handle this gracefully:
- If global doesn't exist when creating project context, either auto-create it or proceed without it
- Provide clear initialization instructions in the documentation
```

---

## Fix Prompt 5: Standardize Authentication Across All Tools

**Use this prompt for comprehensive authentication standardization:**

```
I need help standardizing authentication across all MCP tools. Currently there's inconsistent handling of user authentication.

Current situation:
- manage_project: Accepts user_id parameter ✓
- manage_git_branch: Requires auth but doesn't accept user_id ✗
- manage_task: Requires auth but doesn't accept user_id ✗
- manage_subtask: Unknown (couldn't test due to task creation failure)
- manage_context: Accepts user_id parameter ✓

Please implement a comprehensive fix:

1. Add user_id as an optional parameter to ALL management tools:
   - manage_git_branch
   - manage_task
   - manage_subtask
   - manage_agent
   - manage_rule
   - manage_compliance
   - manage_connection

2. Standardize the parameter definition:
   - Name: user_id
   - Type: Optional[str]
   - Default: None (with fallback to session/token auth if available)
   - Description: "User identifier for authentication and audit trails"

3. Update all ApplicationFacade classes to:
   - Accept user_id parameter
   - Use it for authentication
   - Fall back to other auth methods if not provided
   - Provide clear error messages when auth is missing

4. Update tool documentation to clearly indicate:
   - Which operations require authentication
   - How to provide authentication
   - What happens if authentication is missing

This should be implemented consistently across:
- dhafnck_mcp_main/src/fastmcp/task_management/interface/consolidated_mcp_tools.py
- All ApplicationFacade classes in dhafnck_mcp_main/src/fastmcp/task_management/application/facades/
```

---

## Fix Prompt 6: Create Integration Tests

**Use this prompt to create comprehensive integration tests:**

```
I need help creating integration tests to verify all MCP tools work correctly with authentication.

Please create a comprehensive test file that:

1. Tests project management with authentication:
   - Create, get, list, update, delete projects
   - Health checks and context creation

2. Tests git branch management with authentication:
   - Create, list, update branches
   - Agent assignment to branches

3. Tests task management with authentication:
   - Create tasks on different branches
   - Update, search, add dependencies
   - Complete tasks

4. Tests subtask management:
   - Create subtasks for tasks
   - Update progress
   - Complete subtasks

5. Tests context hierarchy:
   - Create global context
   - Create project context
   - Create branch context
   - Create task context
   - Verify inheritance

6. Tests error cases:
   - Missing authentication
   - Invalid parameters
   - Non-existent resources

Create the test file at:
dhafnck_mcp_main/src/tests/integration/test_mcp_tools_authentication.py

Include proper setup/teardown and use pytest fixtures for test data.
```

---

## Usage Instructions

1. **For each issue**, copy the corresponding fix prompt into a new chat session
2. **Provide context** by mentioning this test was run on 2025-08-26
3. **Reference the issue documentation** at: `dhafnck_mcp_main/docs/issues/mcp-tools-testing-issues-2025-08-26.md`
4. **Test the fix** after implementation using the test cases provided
5. **Update documentation** after fixes are applied

## Priority Order

1. **Critical**: Fix Prompts 1, 3 (Git Branch and Task authentication)
2. **High**: Fix Prompt 2, 4 (Global context and hierarchy)
3. **Medium**: Fix Prompt 5 (Standardization)
4. **Low**: Fix Prompt 6 (Integration tests)

## Verification

After applying fixes, run this test sequence:
```python
# 1. Create project with auth
project = mcp__dhafnck_mcp_http__manage_project(
    action="create", 
    name="test-fixed",
    user_id="test-user"
)

# 2. Create branch with auth
branch = mcp__dhafnck_mcp_http__manage_git_branch(
    action="create",
    project_id=project["project"]["id"],
    git_branch_name="feature/test",
    user_id="test-user"
)

# 3. Create task with auth
task = mcp__dhafnck_mcp_http__manage_task(
    action="create",
    git_branch_id=branch["git_branch"]["id"],
    title="Test Task",
    user_id="test-user"
)

# 4. Create context hierarchy
global_ctx = mcp__dhafnck_mcp_http__manage_context(
    action="create",
    level="global",
    context_id="global_singleton",
    data={"test": "data"},
    user_id="test-user"
)

# If all succeed, authentication is fixed!
```