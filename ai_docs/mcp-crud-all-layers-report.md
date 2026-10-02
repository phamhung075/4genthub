# MCP CRUD All Layers Test Report

**Date**: 2026-10-02 20:58:58 UTC
**Target**: `https://api.4genthub.com/mcp` (Go FastMCP Production)
**Run ID**: `b96687`
**User ID**: `f0de4c5d-2a97-4324-abcd-9dae3922761e`

## Summary

- **Total Tests**: 40
- **Passed**: 37 (92.5%)
- **Failed**: 3 (7.5%)

## Detailed Results by Layer

| Layer | Action | Description | Status | Latency | Details |
| :--- | :--- | :--- | :---: | :---: | :--- |
| Projects | `create` | Create Project 1 (crud-p1-b96687) | ✅ PASS | 0.11s |  |
| Projects | `create` | Create Project 2 (crud-p2-b96687) | ✅ PASS | 0.104s |  |
| Projects | `get` | Get Project 1 (f019699a-33d7-4c01-bfbc-404d2693fdfa) | ✅ PASS | 0.096s |  |
| Projects | `list` | List all projects | ✅ PASS | 0.105s |  |
| Projects | `update` | Update Project 1 (f019699a-33d7-4c01-bfbc-404d2693fdfa) | ✅ PASS | 0.105s |  |
| Projects | `health_check` | Health Check Project 1 (f019699a-33d7-4c01-bfbc-404d2693fdfa) | ✅ PASS | 0.095s |  |
| Projects | `set_context` | Set Context for Project 1 (f019699a-33d7-4c01-bfbc-404d2693fdfa) | ✅ PASS | 0.102s |  |
| Projects | `delete` | Delete Project 2 (cdf0ed1d-d886-48a1-94a2-d61394cbf045) | ✅ PASS | 0.104s |  |
| Branches | `create` | Create Branch 1 (branch-1-b96687) | ✅ PASS | 0.11s |  |
| Branches | `create` | Create Branch 2 (branch-2-b96687) | ✅ PASS | 0.104s |  |
| Branches | `get` | Get Branch 1 (ee76d1ac-9fcd-421c-8bdc-58a2a276ebbb) | ✅ PASS | 0.102s |  |
| Branches | `list` | List Branches for Project 1 (f019699a-33d7-4c01-bfbc-404d2693fdfa) | ✅ PASS | 0.096s |  |
| Branches | `update` | Update Branch 1 (ee76d1ac-9fcd-421c-8bdc-58a2a276ebbb) | ✅ PASS | 0.104s |  |
| Agents | `register` | Register Agent (tester-agent-b96687) | ✅ PASS | 0.105s |  |
| Branches | `assign_agent` | Assign Agent tester-agent-b96687 to Branch 1 | ✅ PASS | 0.093s |  |
| Branches | `set_context` | Set Context for Branch 1 (ee76d1ac-9fcd-421c-8bdc-58a2a276ebbb) | ✅ PASS | 0.106s |  |
| Tasks (B1) | `create` | Create Task 1A | ✅ PASS | 0.117s |  |
| Tasks (B1) | `create` | Create Task 1B | ✅ PASS | 0.123s |  |
| Tasks (B1) | `update` | Update Task 1A to in_progress | ✅ PASS | 0.113s |  |
| Tasks (B1) | `get` | Get Task 1A (00d7c302-1291-4a77-96d9-f413c6735a40) | ✅ PASS | 0.128s |  |
| Tasks (B1) | `list` | List Tasks on Branch 1 | ✅ PASS | 0.099s |  |
| Tasks (B1) | `search` | Search Tasks for 'Core Implementation' | ✅ PASS | 0.104s |  |
| Tasks (B1) | `next` | Get Next Task on Branch 1 | ✅ PASS | 0.107s |  |
| Tasks (B1) | `add_dependency` | Add Dependency (1B depends on 1A) | ✅ PASS | 0.102s |  |
| Tasks (B1) | `assign_agent` | Assign coding-agent to Task 1A | ✅ PASS | 0.102s |  |
| Tasks (B2) | `create` | Create Task 2A | ✅ PASS | 0.13s |  |
| Tasks (B2) | `create` | Create Task 2B | ✅ PASS | 0.123s |  |
| Tasks (B2) | `update` | Update Task 2A | ✅ PASS | 0.11s |  |
| Tasks (B2) | `get` | Get Task 2A | ✅ PASS | 0.135s |  |
| Tasks (B2) | `list` | List Tasks on Branch 2 | ✅ PASS | 0.096s |  |
| Tasks (B2) | `search` | Search Tasks on Branch 2 | ✅ PASS | 0.101s |  |
| Tasks (B2) | `next` | Get Next Task on Branch 2 | ✅ PASS | 0.107s |  |
| Tasks (B2) | `add_dependency` | Add Dependency on Branch 2 | ✅ PASS | 0.1s |  |
| Tasks (B2) | `assign_agent` | Assign agent to Task 2A | ✅ PASS | 0.111s |  |
| Branches | `delete` | Delete Branch 2 (66075e6d-1066-4d47-a9aa-d69b1b902404) | ✅ PASS | 0.106s |  |
| Subtasks | `create` | Create Subtask 1A-1 | ❌ FAIL | 0.101s | `{"message": "Subtask operation failed: Failed to get subtask...` |
| Subtasks | `create` | Create Subtask 1A-2 | ❌ FAIL | 0.102s | `{"message": "Subtask operation failed: Failed to get subtask...` |
| Subtasks | `list` | List Subtasks for Task 1A | ❌ FAIL | 0.098s | `{"message": "Subtask operation failed: Failed to get subtask...` |
| Tasks (B1) | `complete` | Complete Task 1A | ✅ PASS | 0.143s |  |
| Cleanup | `delete` | Clean up Project 1 (f019699a-33d7-4c01-bfbc-404d2693fdfa) | ✅ PASS | 0.116s |  |

## Issues & Fix Prompts

### Issue 1: Subtasks - `create` failed

- **Action**: `create`
- **Layer**: Subtasks
- **Description**: Create Subtask 1A-1
- **Error Output**: ```json
{
  "message": "Subtask operation failed: Failed to get subtask facade: task facade does not implement GetTask",
  "code": "OPERATION_FAILED",
  "operation": "create",
  "timestamp": "2026-10-02T20:58:57.950125+00:00"
}
```

#### Fix Prompt:
```text
Fix the Subtasks `create` handler in the Go FastMCP server.
Operation 'create' failed with error:
{
  "message": "Subtask operation failed: Failed to get subtask facade: task facade does not implement GetTask",
  "code": "OPERATION_FAILED",
  "operation": "create",
  "timestamp": "2026-10-02T20:58:57.950125+00:00"
}
Ensure that parameters and interface implementations match the expected domain contract.
```

### Issue 2: Subtasks - `create` failed

- **Action**: `create`
- **Layer**: Subtasks
- **Description**: Create Subtask 1A-2
- **Error Output**: ```json
{
  "message": "Subtask operation failed: Failed to get subtask facade: task facade does not implement GetTask",
  "code": "OPERATION_FAILED",
  "operation": "create",
  "timestamp": "2026-10-02T20:58:58.052317+00:00"
}
```

#### Fix Prompt:
```text
Fix the Subtasks `create` handler in the Go FastMCP server.
Operation 'create' failed with error:
{
  "message": "Subtask operation failed: Failed to get subtask facade: task facade does not implement GetTask",
  "code": "OPERATION_FAILED",
  "operation": "create",
  "timestamp": "2026-10-02T20:58:58.052317+00:00"
}
Ensure that parameters and interface implementations match the expected domain contract.
```

### Issue 3: Subtasks - `list` failed

- **Action**: `list`
- **Layer**: Subtasks
- **Description**: List Subtasks for Task 1A
- **Error Output**: ```json
{
  "message": "Subtask operation failed: Failed to get subtask facade: task facade does not implement GetTask",
  "code": "OPERATION_FAILED",
  "operation": "list",
  "timestamp": "2026-10-02T20:58:58.151964+00:00"
}
```

#### Fix Prompt:
```text
Fix the Subtasks `list` handler in the Go FastMCP server.
Operation 'list' failed with error:
{
  "message": "Subtask operation failed: Failed to get subtask facade: task facade does not implement GetTask",
  "code": "OPERATION_FAILED",
  "operation": "list",
  "timestamp": "2026-10-02T20:58:58.151964+00:00"
}
Ensure that parameters and interface implementations match the expected domain contract.
```
