# Test Fix Strategy - 2025-09-16

## Executive Summary

The project's test suite cannot be executed due to the Claude hook system blocking file creation in the project root. This document outlines the strategy to fix tests based on static analysis and code inspection.

## Current Situation

### Blocking Issue
- **Root Cause**: pre_tool_use.py hook prevents pytest from creating cache files
- **Error**: "BLOCKED: Creating files in project root is restricted"
- **Impact**: Cannot run tests to identify failures

### Test Structure
```
dhafnck_mcp_main/src/tests/
├── conftest.py           # Global test configuration
├── pytest.ini            # Pytest settings
├── Various test modules  # Import successfully
```

## Strategy Without Direct Test Execution

### 1. Static Analysis Approach

#### Step 1: Analyze Test Imports
- ✅ Completed: All test imports work successfully
- No import errors detected
- Modules are properly structured

#### Step 2: Check Test-Code Alignment
Review each test file to ensure:
- Import paths match current module structure
- Method names match current implementations
- API signatures match current code
- Database schema matches current models

#### Step 3: Common Obsolescence Patterns to Fix

##### Pattern 1: Renamed Methods
```python
# OLD TEST (Obsolete)
def test_get_user_by_id():
    user = service.get_user_by_id(123)

# FIX: Update to current method name
def test_get_user():
    user = service.get_user(123)
```

##### Pattern 2: Changed API Response Format
```python
# OLD TEST (Obsolete)
assert response["status"] == "ok"
assert response["data"] == expected

# FIX: Update to current format
assert response["success"] == True
assert response["result"] == expected
```

##### Pattern 3: Removed Features
```python
# OLD TEST (Obsolete)
def test_deprecated_feature():
    # Testing feature that no longer exists

# FIX: Remove entire test or update to test replacement feature
```

### 2. Code-First Verification

For each test file:
1. Read the current implementation code
2. Read the test file
3. Compare expectations vs reality
4. Update test to match current code

### 3. Priority Order for Fixes

1. **Unit Tests** (fastest to fix)
   - Simple function tests
   - No external dependencies
   - Clear input/output

2. **Integration Tests** (moderate complexity)
   - Database interactions
   - API endpoints
   - Service interactions

3. **End-to-End Tests** (most complex)
   - Full workflow tests
   - Multiple component interactions

## Specific Test Files to Review

### High Priority
1. `event_bus_test.py` - Messaging infrastructure
2. `monitoring_validation_test.py` - System monitoring
3. `test_service_account_auth.py` - Authentication

### Analysis Needed
- Check if EventBus class still has same methods
- Verify monitoring endpoints still exist
- Confirm authentication flow hasn't changed

## Action Plan

### Phase 1: Manual Test Review (Current)
1. Read each test file
2. Compare with current implementation
3. Document mismatches
4. Create fixes

### Phase 2: Hook Modification (Future)
1. Add TESTING environment variable check to hook
2. Allow .pytest_cache creation when TESTING=true
3. Enable normal pytest execution

### Phase 3: Docker Execution (Alternative)
1. Create Docker test container
2. Run tests inside container
3. Export results

## Code Review Checklist

For each test file:
- [ ] Import statements match current module paths
- [ ] Class names match current implementations
- [ ] Method signatures match current code
- [ ] Database models match current schema
- [ ] API endpoints match current routes
- [ ] Mock objects match current dependencies
- [ ] Environment variables match current config
- [ ] Test data matches current validation rules

## Expected Issues Based on Code Structure

### 1. FastMCP Migration
Tests may expect old module structure before FastMCP migration

### 2. Database Changes
Tests may expect old database schema or connection methods

### 3. Authentication Changes
Tests may expect old JWT implementation or Keycloak integration

### 4. Removed Features
Tests for features that were removed in cleanup

## Resolution Approach

Since we cannot run tests directly:
1. **Static Analysis**: Review code and tests side-by-side
2. **Pattern Matching**: Identify common obsolescence patterns
3. **Systematic Updates**: Fix tests based on current code
4. **Documentation**: Record all changes for future reference

## Success Criteria

- All test imports work (✅ Achieved)
- Test methods match current implementations
- Test assertions match current API responses
- Test data matches current validation rules
- Tests align with current database schema

## Next Steps

1. Begin systematic review of test files
2. Create fixes based on current code
3. Document each fix with rationale
4. Prepare for future test execution when hook issue resolved