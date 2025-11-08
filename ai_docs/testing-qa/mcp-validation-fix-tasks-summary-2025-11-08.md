# MCP Validation Fix Tasks - Complete Structure
**Date**: 2025-11-08
**Status**: All tasks created and delegated to agents
**Total Tasks**: 5 main tasks, 13 subtasks

---

## Task Overview

All tasks include **TDD (Test-Driven Development)**, **Test Updates**, and **Dead Code Removal** subtasks.

---

## Task #1: Fix Status Badge Real-time Updates 🔴 HIGH PRIORITY

**Task ID**: `1beafdf3-3948-44e4-a13d-b28a7881db0b`
**Assigned to**: coding-agent (Terminal tab open)
**Priority**: High
**Labels**: bug, frontend, websocket, real-time-sync

### Main Issue
Task completion status badge not updating in real-time when task is completed via MCP tools.

### Subtasks (3)

| ID | Title | Priority | Type |
|----|-------|----------|------|
| `4f74a802-c18f...` | TDD: Write tests for task completion status badge updates | High | TDD |
| `f848b192-ccd0...` | Update existing tests after status badge fix implementation | High | Test Update |
| `6ef3632e-3859...` | Remove dead code from WebSocket handling and task components | Medium | Cleanup |

### Expected Outcomes
1. ✅ Failing tests written first (TDD approach)
2. ✅ Fix implemented: WebSocket payload includes "status": "done"
3. ✅ All existing tests updated and passing
4. ✅ Dead code removed from useRealtimeSync.ts and LazyTaskListRefactored.tsx

---

## Task #2: Fix Agent Name Display 🟡 MEDIUM PRIORITY

**Task ID**: `dbf47340-6932-45d8-a147-06e03ffeb2a8`
**Assigned to**: coding-agent (Terminal tab open)
**Priority**: Medium
**Labels**: bug, frontend, real-time-sync, ui-display

### Main Issue
Agent names not displaying on task/subtask rows after adding dependencies.

### Subtasks (3)

| ID | Title | Priority | Type |
|----|-------|----------|------|
| `0516b1c2-db0d...` | TDD: Write tests for agent name display after dependency operations | Medium | TDD |
| `0c60be50-b0df...` | Update existing tests after agent display fix | Medium | Test Update |
| `b7005be1-56d5...` | Remove dead code from task/subtask row components | Low | Cleanup |

### Expected Outcomes
1. ✅ Failing tests written for agent display scenarios
2. ✅ Fix implemented: Agent names appear in real-time after dependency changes
3. ✅ Component tests updated for assignee data flow
4. ✅ Dead code removed from row components

---

## Task #3: Enhance Duplicate Project Error 🟢 LOW PRIORITY

**Task ID**: `ad37a2b6-b974-4f4d-a75d-454f5c1a30a1`
**Assigned to**: coding-agent (Terminal tab open)
**Priority**: Low
**Labels**: enhancement, backend, ux, error-handling

### Main Issue
Duplicate project name error could be more helpful with suggested actions.

### Subtasks (3)

| ID | Title | Priority | Type |
|----|-------|----------|------|
| `6c7b46ec-b8a4...` | TDD: Write tests for enhanced duplicate project error response | Low | TDD |
| `2f79d78d-3819...` | Update existing project facade tests after error enhancement | Low | Test Update |
| `44887d11-955a...` | Remove dead code from project application facade | Low | Cleanup |

### Expected Outcomes
1. ✅ Tests verify enhanced error format with suggested_actions
2. ✅ Error response includes error_code, suggested_actions, hint
3. ✅ Project facade tests updated for new format
4. ✅ Dead code removed from error handling

---

## Task #4: Update manage_task Documentation 🟡 MEDIUM PRIORITY

**Task ID**: `8c8a9b09-d324-44d4-aded-f844734994a2`
**Assigned to**: documentation-agent (Terminal tab open)
**Priority**: Medium
**Labels**: documentation, api-docs, validation

### Main Issue
Tool description doesn't clearly highlight 'details' parameter requirement.

### Subtasks (2)

| ID | Title | Priority | Type |
|----|-------|----------|------|
| `fdd9730f-76b0...` | Validate: Test manage_task tool with updated documentation | Medium | Validation |
| `96047434-4b78...` | Review and remove dead code from tool schema definitions | Low | Cleanup |

### Expected Outcomes
1. ✅ Parameter description highlights REQUIRED status
2. ✅ Usage notes explain validation requirements
3. ✅ Examples show correct and incorrect usage
4. ✅ Validation tests confirm docs match error messages
5. ✅ Obsolete documentation removed

---

## Task #5: Update manage_subtask Documentation 🟡 MEDIUM PRIORITY

**Task ID**: `b29733b5-56e6-4442-a2c7-8a8dabe8e9f8`
**Assigned to**: documentation-agent (Terminal tab open)
**Priority**: Medium
**Labels**: documentation, api-docs, validation

### Main Issue
Tool description doesn't clearly highlight 'progress_notes' MANDATORY requirement.

### Subtasks (2)

| ID | Title | Priority | Type |
|----|-------|----------|------|
| `af17318e-e9bd...` | Validate: Test manage_subtask tool with updated documentation | Medium | Validation |
| `e9965ad1-5fb4...` | Review and remove dead code from subtask tool schema | Low | Cleanup |

### Expected Outcomes
1. ✅ Parameter descriptions highlight MANDATORY requirements
2. ✅ Usage notes explain update/complete requirements
3. ✅ Examples show both failing and succeeding cases
4. ✅ Validation tests confirm docs accuracy
5. ✅ Redundant documentation removed

---

## TDD Workflow for All Tasks

### 1. Test-Driven Development (TDD)
```
1. Write failing test (Red)
   ↓
2. Implement minimal fix (Green)
   ↓
3. Refactor and optimize (Refactor)
   ↓
4. Update existing tests (Validation)
   ↓
5. Remove dead code (Cleanup)
```

### 2. Test Categories

| Task Type | Test Location | Test Type |
|-----------|--------------|-----------|
| Frontend bugs | `agenthub-frontend/src/tests/` | Unit + Integration |
| Backend enhancements | `agenthub_main/src/tests/` | Unit + Integration |
| WebSocket | Both frontend & backend | Integration + E2E |
| Documentation | Validation scripts | Functional |

### 3. Dead Code Removal Checklist

For each file modified:
- ✅ Remove unused imports
- ✅ Delete commented-out code
- ✅ Remove debug console.logs
- ✅ Clean up obsolete event handlers
- ✅ Consolidate duplicate utilities
- ✅ Remove deprecated parameters

---

## Agent Execution Status

### Active Agent Sessions (5)

| Agent | Tasks | Status | Terminal |
|-------|-------|--------|----------|
| **coding-agent** (1) | Status badge fix | 🔄 Running | Tab 1 |
| **coding-agent** (2) | Agent display fix | 🔄 Running | Tab 2 |
| **coding-agent** (3) | Duplicate error enhancement | 🔄 Running | Tab 3 |
| **documentation-agent** (1) | manage_task docs | 🔄 Running | Tab 4 |
| **documentation-agent** (2) | manage_subtask docs | 🔄 Running | Tab 5 |

### Agent Workflow

Each agent will:
1. **Read task context** from MCP
2. **Work through subtasks sequentially**:
   - TDD: Write failing tests first
   - Implementation: Fix the issue
   - Test Update: Update existing tests
   - Cleanup: Remove dead code
3. **Update progress** in MCP as each subtask completes
4. **Complete parent task** when all subtasks done

---

## Monitoring Progress

### Check Task Status
```bash
# List all tasks on main branch
manage_task(action="list", git_branch_id="8f3bc2ca-9947...")

# Get specific task details
manage_task(action="get", task_id="1beafdf3-3948...")

# List subtasks
manage_subtask(action="list", task_id="1beafdf3-3948...")
```

### Expected Timeline

| Priority | Estimated Completion | Tasks |
|----------|---------------------|-------|
| 🔴 High | 2-3 hours | Status badge fix |
| 🟡 Medium | 1.5-2 hours each | Agent display, Documentation tasks |
| 🟢 Low | 30-60 minutes | Duplicate error enhancement |

**Total Estimated Time**: 4-6 hours (parallel execution)

---

## Validation Criteria

### For Coding Tasks
- ✅ TDD tests written and initially failing
- ✅ Implementation makes tests pass
- ✅ All existing tests still passing
- ✅ Dead code removed
- ✅ Code follows DRY/SOLID principles
- ✅ No console errors or warnings

### For Documentation Tasks
- ✅ Required fields clearly marked as MANDATORY
- ✅ Examples show both correct and incorrect usage
- ✅ Validation tests confirm docs match actual behavior
- ✅ Obsolete documentation removed
- ✅ Consistent formatting and terminology

---

## Files Expected to Change

### Frontend (coding-agent tasks 1 & 2)
- `agenthub-frontend/src/hooks/useRealtimeSync.ts`
- `agenthub-frontend/src/components/LazyTaskListRefactored.tsx`
- `agenthub-frontend/src/components/task/TaskStatusBadge.tsx` (possibly)
- `agenthub-frontend/src/tests/...` (new test files)

### Backend (coding-agent task 3)
- `agenthub_main/src/fastmcp/task_management/application/facades/project_application_facade.py`
- `agenthub_main/src/fastmcp/task_management/application/facades/task_application_facade.py`
- `agenthub_main/src/tests/...` (updated test files)

### Documentation (documentation-agent tasks 4 & 5)
- Tool schema definitions for `mcp__agenthub_http__manage_task`
- Tool schema definitions for `mcp__agenthub_http__manage_subtask`
- Validation test scripts

---

## Success Metrics

1. **Backend**: All 31 MCP tool actions still passing validation
2. **Frontend**: Real-time updates working for all operations
3. **Tests**: 100% of tests passing (old + new)
4. **Code Quality**: Dead code removed, clean codebase
5. **Documentation**: Clear, accurate tool descriptions

---

## Next Steps After Agent Completion

1. **Review Changes**: Check all modified files
2. **Run Full Test Suite**: Ensure nothing broken
3. **Manual Testing**: Verify real-time updates in UI
4. **Create Pull Request**: If on feature branch
5. **Update CHANGELOG.md**: Document all changes

---

**Report Generated**: 2025-11-08 18:10 UTC
**Generated By**: Claude (master-orchestrator-agent)
**Structure**: 5 main tasks → 13 subtasks → TDD + Tests + Cleanup
**Status**: All tasks delegated, agents working in parallel
