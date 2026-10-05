# MCP CRUD All Layers Test Report

**Date**: 2026-10-02 21:16:58 UTC
**Target**: `https://api.4genthub.com/mcp` (Go FastMCP Production)
**Run ID**: `d7492b`
**User ID**: `f0de4c5d-2a97-4324-abcd-9dae3922761e`

## Summary

- **Total Tests**: 50
- **Passed**: 50 (100.0%)
- **Failed**: 0 (0.0%)

## Detailed Results by Layer

| Layer | Action | Description | Status | Latency | Details |
| :--- | :--- | :--- | :---: | :---: | :--- |
| Projects | `create` | Create Project 1 (crud-p1-d7492b) | ✅ PASS | 0.122s |  |
| Projects | `create` | Create Project 2 (crud-p2-d7492b) | ✅ PASS | 0.104s |  |
| Projects | `get` | Get Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.097s |  |
| Projects | `list` | List all projects | ✅ PASS | 0.097s |  |
| Projects | `update` | Update Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.104s |  |
| Projects | `health_check` | Health Check Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.092s |  |
| Projects | `set_context` | Set Context for Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.101s |  |
| Projects | `delete` | Delete Project 2 (a49cb4bc-0401-4cfc-95ee-37a65b58e75f) | ✅ PASS | 0.107s |  |
| Branches | `create` | Create Branch 1 (branch-1-d7492b) | ✅ PASS | 0.104s |  |
| Branches | `create` | Create Branch 2 (branch-2-d7492b) | ✅ PASS | 0.099s |  |
| Branches | `get` | Get Branch 1 (82bfd817-cc31-4537-9862-f73a3be95ba7) | ✅ PASS | 0.101s |  |
| Branches | `list` | List Branches for Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.097s |  |
| Branches | `update` | Update Branch 1 (82bfd817-cc31-4537-9862-f73a3be95ba7) | ✅ PASS | 0.096s |  |
| Agents | `register` | Register Agent (tester-agent-d7492b) | ✅ PASS | 0.107s |  |
| Branches | `assign_agent` | Assign Agent tester-agent-d7492b to Branch 1 | ✅ PASS | 0.102s |  |
| Branches | `set_context` | Set Context for Branch 1 (82bfd817-cc31-4537-9862-f73a3be95ba7) | ✅ PASS | 0.107s |  |
| Tasks (B1) | `create` | Create Task 1A | ✅ PASS | 0.138s |  |
| Tasks (B1) | `create` | Create Task 1B | ✅ PASS | 0.124s |  |
| Tasks (B1) | `update` | Update Task 1A to in_progress | ✅ PASS | 0.103s |  |
| Tasks (B1) | `get` | Get Task 1A (c92db6cd-ff2d-4648-a9f6-b9b8af38b325) | ✅ PASS | 0.133s |  |
| Tasks (B1) | `list` | List Tasks on Branch 1 | ✅ PASS | 0.096s |  |
| Tasks (B1) | `search` | Search Tasks for 'Core Implementation' | ✅ PASS | 0.106s |  |
| Tasks (B1) | `next` | Get Next Task on Branch 1 | ✅ PASS | 0.116s |  |
| Tasks (B1) | `add_dependency` | Add Dependency (1B depends on 1A) | ✅ PASS | 0.102s |  |
| Tasks (B1) | `assign_agent` | Assign coding-agent to Task 1A | ✅ PASS | 0.103s |  |
| Tasks (B2) | `create` | Create Task 2A | ✅ PASS | 0.123s |  |
| Tasks (B2) | `create` | Create Task 2B | ✅ PASS | 0.123s |  |
| Tasks (B2) | `update` | Update Task 2A | ✅ PASS | 0.107s |  |
| Tasks (B2) | `get` | Get Task 2A | ✅ PASS | 0.129s |  |
| Tasks (B2) | `list` | List Tasks on Branch 2 | ✅ PASS | 0.105s |  |
| Tasks (B2) | `search` | Search Tasks on Branch 2 | ✅ PASS | 0.107s |  |
| Tasks (B2) | `next` | Get Next Task on Branch 2 | ✅ PASS | 0.107s |  |
| Tasks (B2) | `add_dependency` | Add Dependency on Branch 2 | ✅ PASS | 0.098s |  |
| Tasks (B2) | `assign_agent` | Assign agent to Task 2A | ✅ PASS | 0.108s |  |
| Branches | `delete` | Delete Branch 2 (fb29040a-2a2b-43e2-ba20-078f681420dc) | ✅ PASS | 0.111s |  |
| Subtasks | `create` | Create Subtask 1A-1 | ✅ PASS | 0.11s |  |
| Subtasks | `create` | Create Subtask 1A-2 | ✅ PASS | 0.109s |  |
| Subtasks | `list` | List Subtasks for Task 1A | ✅ PASS | 0.098s |  |
| Subtasks | `get` | Get Subtask 1A-1 | ✅ PASS | 0.106s |  |
| Subtasks | `update` | Update Subtask 1A-1 | ✅ PASS | 0.116s |  |
| Subtasks | `complete` | Complete Subtask 1A-1 | ✅ PASS | 0.112s |  |
| Subtasks | `complete` | Complete Subtask 1A-2 | ✅ PASS | 0.112s |  |
| Tasks (B1) | `complete` | Complete Task 1A | ✅ PASS | 0.15s |  |
| Context | `get` | Get Context for Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.098s |  |
| Context | `update` | Update Context for Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.104s |  |
| Context | `list` | List Project Contexts | ✅ PASS | 0.12s |  |
| Agents | `get` | Get Agent (cf526cf9-3d08-4c26-b71d-19357fecd1ef) | ✅ PASS | 0.105s |  |
| Agents | `list` | List Agents for Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.102s |  |
| Agents | `unregister` | Unregister Agent (cf526cf9-3d08-4c26-b71d-19357fecd1ef) | ✅ PASS | 0.093s |  |
| Cleanup | `delete` | Clean up Project 1 (ab9abf0b-a3e4-4ee9-9a14-dc8725c94831) | ✅ PASS | 0.114s |  |

## Issues & Fix Prompts

🎉 **No issues found! All CRUD operations across all layers succeeded.**
