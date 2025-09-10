# End-to-End Testing Guidelines

## 1. Overview
Describe E2E testing strategies, tools, and workflows for DhafnckMCP.

**Example:**
- "E2E tests simulate real user flows using Cypress."

## 2. Tools and Frameworks
- List recommended tools (e.g., Cypress, Playwright, Selenium).

| Tool       | Purpose           |
|------------|------------------|
| Cypress    | E2E browser tests |
| Playwright | Cross-browser E2E|

## 3. E2E Test Workflows
- Simulate user journeys across the system
- Test critical paths (login, task creation, etc.)

**Example Workflow:**
- "User signs up, logs in, and creates a new task."

## 4. Environment Setup
- Use dedicated E2E environments
- Reset state before each test run

## 5. Success Criteria
- All critical user flows are tested
- E2E tests are stable and repeatable

## 6. Validation Checklist
- [ ] Tools and frameworks are listed
- [ ] E2E workflows are described
- [ ] Example workflow is included
- [ ] Environment setup is specified
- [ ] Success criteria are documented

## 7. MCP Tool API Protocol: JSON-RPC 2.0 Envelope Required

All E2E tests that interact with MCP tool endpoints (e.g., `/mcp/tool/manage_task`, `/mcp/tool/manage_agent`, etc.) **must** send requests using the JSON-RPC 2.0 protocol envelope. Directly sending a dict as the payload (e.g., `{ "action": "list" }`) will result in a 400 error due to missing required fields.

**Required JSON-RPC 2.0 Envelope Example:**

```json
{
  "jsonrpc": "2.0",
  "method": "manage_task",
  "params": { "action": "list", "project_id": "default_project" },
  "id": "test-manage-task"
}
```

- `jsonrpc`: Always "2.0"
- `method`: The tool name (e.g., "manage_task")
- `params`: The original tool arguments
- `id`: Any unique string or number for the request

**Incorrect (will fail):**
```json
{ "action": "list", "project_id": "default_project" }
```

**Correct (will succeed):**
```json
{
  "jsonrpc": "2.0",
  "method": "manage_task",
  "params": { "action": "list", "project_id": "default_project" },
  "id": "test-manage-task"
}
```

This applies to all tool endpoints. See E2E test code for working examples.

> **Note:** The `MCP-Protocol-Version` header must be set to a supported version (e.g., `2025-06-18`) in all client and test requests. Using an unsupported version (such as `1.0`) will result in a 400 error. In frontend code, set this header in your API helper (e.g., `api.ts`). In tests, set it in your test header helper.

## 8. Updated Context System (January 2025)

The context system has been unified under the `manage_context` tool:
- **Deprecated**: `manage_context` is no longer used
- **Use**: `manage_context` for all context operations (create, update, resolve, delegate)
- **Auto-creation**: Contexts are automatically created when creating projects, branches, and tasks
- **Parameter flexibility**: Boolean parameters accept string values ("true", "false", "yes", "no")
- **Array parameters**: Accept JSON strings, comma-separated values, or arrays

**Example Context Test:**
```json
{
  "jsonrpc": "2.0",
  "method": "manage_context",
  "params": {
    "action": "create",
    "level": "task",
    "context_id": "task-123",
    "data": {"title": "Test Task", "status": "in_progress"}
  },
  "id": "test-context-create"
}
```

---
*This document follows the DhafnckMCP PRD template. Update as E2E testing practices evolve.* 