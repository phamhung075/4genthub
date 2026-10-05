# End-to-End Testing Guidelines

## 1. Overview
Describe E2E testing strategies, tools, and workflows for agenthub.

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

All E2E tests that interact with MCP **must** POST a JSON-RPC 2.0 request to the single MCP endpoint, `POST /mcp` (`handleJSONRPC`, `agenthub_go/fastmcp/server/httpapp/mcp_routes.go:55`). There is no `/mcp/tool/<name>` route: the tool is named inside the `tools/call` request. Posting a bare tool payload (e.g., `{ "action": "list" }`) fails because it is not a JSON-RPC request. (`GET /mcp` is the SSE transport, `mcpSSEHandler`, `mcp_routes.go:116`.)

**Required JSON-RPC 2.0 Envelope Example:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "manage_task",
    "arguments": { "action": "list", "project_id": "default_project" }
  },
  "id": "test-manage-task"
}
```

- `jsonrpc`: Always "2.0"
- `method`: Always `"tools/call"` to invoke a tool. The other JSON-RPC methods are the protocol layer, not tools: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `resources/list`, `prompts/list`
- `params`: `{ "name": <tool name>, "arguments": <original tool arguments> }`
- `id`: Any unique string or number for the request

**Incorrect (will fail):**
```json
{ "action": "list", "project_id": "default_project" }
```

**Correct (will succeed):**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "manage_task",
    "arguments": { "action": "list", "project_id": "default_project" }
  },
  "id": "test-manage-task"
}
```

This applies to every tool call on `POST /mcp`. See E2E test code for working examples.

> **Note:** The Go server does not reject requests based on protocol version. `initialize` reports `"protocolVersion": "2024-11-05"` (`mcp_routes.go:160`); the `MCP-Protocol-Version` header is used only by the dual-auth middleware to classify a request as MCP (`agenthub_go/fastmcp/auth/middleware/dual_auth_middleware.go:69`).

## 8. Updated Context System (January 2025)

The context system is unified under the live `manage_context` tool:
- **Use**: `manage_context` for all context operations (create, update, resolve, delegate)
- **Auto-creation**: Contexts are automatically created when creating projects, branches, and tasks
- **Parameter flexibility**: Boolean parameters accept string values ("true", "false", "yes", "no")
- **Array parameters**: Accept JSON strings, comma-separated values, or arrays

**Example Context Test:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "manage_context",
    "arguments": {
      "action": "create",
      "level": "task",
      "context_id": "task-123",
      "data": {"title": "Test Task", "status": "in_progress"}
    }
  },
  "id": "test-context-create"
}
```

---
*This document follows the agenthub PRD template. Update as E2E testing practices evolve.*
