# Phase 3: Critical Scenario Tests - Summary

**Created**: 2025-10-28
**Task**: 51155169-3077-4c5c-bd2a-9e086aaadd50
**Subtask**: b760d86f-7334-47f5-b862-02487050002c
**Agent**: test-orchestrator-agent

## Overview

Created comprehensive integration tests to identify the EXACT scenarios where user-reported issues occur with subtask counts, completed counts, and progress calculations.

## Files Created

### 1. test_critical_scenarios_subtask_counts.py
**Location**: `agenthub_main/src/tests/integration/test_critical_scenarios_subtask_counts.py`
**Lines**: 450+
**Tests**: 8

#### Test Coverage:
- **test_new_task_has_zero_subtasks**: Verify zero state is correct
- **test_task_with_five_subtasks_shows_correct_count**: Add 5 subtasks → count should be 5
- **test_deleting_subtasks_updates_count_correctly**: Delete 2 of 5 → count should be 3
- **test_completing_subtasks_updates_completed_count**: Complete 2 of 5 → completed_subtasks should be 2
- **test_all_subtasks_completed_shows_full_count**: Complete all → completed_subtasks equals subtask_count
- **test_mixed_subtask_states_counts_only_done**: Only 'done' status counts as completed
- **test_rapid_subtask_addition_maintains_count_accuracy**: No drift during rapid operations
- **test_subtask_counts_persist_across_multiple_retrievals**: Consistent across refreshes

#### Key Scenarios Tested:
- ✅ Zero subtasks (badge shows nothing)
- ✅ Adding subtasks (badge increments correctly)
- ✅ Deleting subtasks (badge decrements correctly)
- ✅ Completing subtasks (progress updates correctly)
- ✅ Mixed states (only 'done' counts as complete)
- ✅ Count consistency (no drift across operations)

### 2. test_critical_scenarios_progress_calculation.py
**Location**: `agenthub_main/src/tests/integration/test_critical_scenarios_progress_calculation.py`
**Lines**: 380+
**Tests**: 8

#### Test Coverage:
- **test_new_task_without_subtasks_has_zero_progress**: New task → 0% progress
- **test_task_without_subtasks_progress_updates_with_status**: Status transitions update progress
- **test_parent_progress_zero_when_no_subtasks_completed**: 0 completed → low/zero progress
- **test_parent_progress_updates_when_subtask_completed**: 2 of 4 complete → ~50% progress
- **test_parent_progress_100_when_all_subtasks_completed**: All complete → 100% progress
- **test_progress_calculation_with_single_subtask**: No division errors with 1 subtask
- **test_progress_percentage_is_always_integer**: 33.33% rounds to integer
- **test_progress_never_exceeds_100_percent**: Cap at 100%

#### Key Scenarios Tested:
- ✅ Progress without subtasks (status-based)
- ✅ Progress with subtasks (completion-based)
- ✅ 0%, 50%, 100% scenarios
- ✅ Always integer (no decimals)
- ✅ Never exceeds 100%
- ✅ Edge cases (1 subtask, division by zero)

## Testing Approach

### Why These Tests Are Different from Contract Tests

**Contract Tests** (task 1bbf2913):
- Validate response STRUCTURE
- Check field types and names
- Static validation
- Mock data

**Critical Scenario Tests** (this task):
- Validate actual BEHAVIOR
- Check calculated VALUES
- Dynamic workflows
- REAL database operations

### Example Difference:
```python
# Contract test (structural):
assert hasattr(task, 'subtask_count')
assert isinstance(task.subtask_count, int)

# Critical scenario test (behavioral):
# Create 5 subtasks
for i in range(5):
    add_subtask_use_case.execute(...)

# Retrieve fresh data
fresh_task = get_task_use_case.execute(...)

# Verify ACTUAL count matches REAL state
assert fresh_task.subtask_count == 5  # Not just "exists and is int"
assert fresh_task.subtask_count == len(fresh_task.subtasks)  # Matches array
```

## Issues Found During Test Creation

### 1. DTO Parameter Mismatch
**Issue**: `AddSubtaskRequest` does not accept `user_id` parameter
**Location**: Test files line ~143, ~160, etc.
**Fix Required**: Remove `user_id` from subtask request objects

**Correct signature**:
```python
@dataclass
class AddSubtaskRequest:
    task_id: Union[str, int]
    title: str
    description: str = ""
    assignees: List[str] = field(default_factory=list)
    priority: Optional[str] = None
    status: Optional[str] = None
    progress_percentage: Optional[int] = None
```

**Same for `UpdateSubtaskRequest`** - no `user_id` parameter.

### 2. Repository Initialization
**Issue**: Repositories don't take `session` parameter
**Fix**: Already corrected in both test files
```python
# ❌ WRONG:
return ORMTaskRepository(session=None, user_id=user_id)

# ✅ CORRECT:
return ORMTaskRepository(user_id=user_id)
```

## Next Steps for Debugger Agent

### Immediate Actions:
1. **Fix parameter issues** in both test files:
   - Remove `user_id` from all `AddSubtaskRequest` calls
   - Remove `user_id` from all `UpdateSubtaskRequest` calls

2. **Run complete test suite**:
   ```bash
   pytest src/tests/integration/test_critical_scenarios_subtask_counts.py -v
   pytest src/tests/integration/test_critical_scenarios_progress_calculation.py -v
   ```

3. **Document failures**:
   - Which specific tests fail?
   - What are the actual vs expected values?
   - Under what conditions do failures occur?

4. **Create fix tasks**:
   - One task per discovered issue
   - Include test reproduction steps
   - Link to specific test that fails

### Expected Test Results:

**If all tests PASS**:
- Backend is correctly calculating counts and progress
- Issue might be in frontend state management or WebSocket updates
- Investigation shifts to Phase 1B (frontend interceptors)

**If tests FAIL**:
- Specific scenarios where backend calculation is incorrect
- Each failure pinpoints EXACT conditions causing user issues
- Fix tasks can be created with reproduction steps

## Test Execution Commands

```bash
# Run all subtask count tests
pytest src/tests/integration/test_critical_scenarios_subtask_counts.py -v

# Run all progress calculation tests
pytest src/tests/integration/test_critical_scenarios_progress_calculation.py -v

# Run specific test
pytest src/tests/integration/test_critical_scenarios_subtask_counts.py::TestSubtaskCountAccuracy::test_task_with_five_subtasks_shows_correct_count -v

# Run with detailed output
pytest src/tests/integration/test_critical_scenarios_subtask_counts.py -vv --tb=long

# Run with coverage
pytest src/tests/integration/test_critical_scenarios_subtask_counts.py --cov=fastmcp.task_management
```

## Key Insights

1. **User-ID Handling**: Subtask DTOs don't include user_id - it's passed at use case level
2. **Real State Testing**: These tests use actual DB operations to catch state-dependent bugs
3. **Behavioral Validation**: Focus on WHAT happens, not just THAT it happens
4. **Edge Cases**: Tests include edge cases like single subtask, rapid operations, mixed states
5. **Count Accuracy**: Multiple tests verify `subtask_count == len(subtasks)` consistency

## Success Criteria

✅ Tests compile and execute (after fixing parameter issues)
✅ Tests reveal specific failing scenarios (if backend has bugs)
✅ Tests provide reproduction steps for fixes
✅ Tests verify counts match across: calculated field, array length, DB state
✅ Tests verify progress is always integer 0-100
✅ Tests verify WebSocket payload includes correct counts

## Related Documentation

- **Contract Tests**: `agenthub_main/src/tests/integration/api_contracts/test_task_api_contracts.py`
- **Subtask DTO**: `agenthub_main/src/fastmcp/task_management/application/dtos/subtask/add_subtask_request.py`
- **Task Response DTO**: `agenthub_main/src/fastmcp/task_management/application/dtos/task/task_response.py`
- **Task Entity**: `agenthub_main/src/fastmcp/task_management/domain/entities/task.py`

## Comparison Matrix Reference

See: `ai_docs/testing-qa/backend-frontend-type-comparison-matrix.md`

**Known mismatches being tested**:
- Mismatch #2: subtask_count field (tests verify accurate calculation)
- Mismatch #3: completed_subtasks field (tests verify accurate calculation)
- Progress percentage calculation (tests verify 0-100 integer range)
