# Test Suite Action Plan - Iteration 42
Date: Sun Sep 14 08:12:00 CEST 2025

## 🎯 Objective
Complete test suite stabilization by running all tests, identifying failures, and systematically fixing remaining issues.

## 📋 Immediate Actions (Priority 1)

### 1. Enable Test Execution
**Problem**: Hooks blocking pytest from creating temporary files
**Solutions**:
```bash
# Option A: Use test-menu.sh (recommended)
cd /home/daihungpham/__projects__/agentic-project
scripts/test-menu.sh
# Select option 3 (Run All Tests)

# Option B: Run tests from dhafnck_mcp_main directory
cd dhafnck_mcp_main
python -m pytest src/tests/ -xvs --tb=short

# Option C: Temporarily disable hooks (if authorized)
# Comment out hook in .claude/hooks/pre_tool_use.py
```

### 2. Run Comprehensive Test Discovery
```bash
# Discover all tests and check for import errors
cd dhafnck_mcp_main
python -m pytest src/tests/ --collect-only -q

# Count total tests
python -m pytest src/tests/ --collect-only -q | grep "<" | wc -l
```

## 📊 Systematic Test Execution Plan

### Phase 1: Quick Assessment (30 minutes)
1. **Run cached passed tests** to verify they still pass
   ```bash
   echo -e "1\nq" | timeout 120 scripts/test-menu.sh
   ```

2. **Check for import errors**
   ```bash
   cd dhafnck_mcp_main
   python -m pytest src/tests/ --collect-only --tb=short
   ```

3. **Identify quick wins**
   - Tests failing due to simple import errors
   - Missing timezone imports
   - Incorrect assertion methods

### Phase 2: Category-Based Testing (2 hours)

#### A. Unit Tests (Priority)
```bash
# Run all unit tests
cd dhafnck_mcp_main
python -m pytest src/tests/unit/ -xvs --tb=short

# By subdomain:
python -m pytest src/tests/unit/auth/ -xvs
python -m pytest src/tests/unit/task_management/ -xvs
python -m pytest src/tests/unit/mcp_controllers/ -xvs
python -m pytest src/tests/unit/connection_management/ -xvs
```

#### B. Integration Tests
```bash
python -m pytest src/tests/integration/ -xvs --tb=short
```

#### C. E2E Tests
```bash
python -m pytest src/tests/e2e/ -xvs --tb=short
```

### Phase 3: Fix Remaining Issues (4-8 hours)

#### Priority Order:
1. **Import/Module Errors** - Prevent test collection
2. **Infrastructure Issues** - Affect multiple tests
3. **Business Logic Failures** - Individual test failures
4. **Assertion Errors** - Test expectation mismatches

#### Fix Strategy:
```python
# For each failing test:
1. Run in isolation
2. Identify root cause
3. Check if code or test needs update
4. Apply fix
5. Verify fix
6. Update cache
7. Document in CHANGELOG.md
```

## 🔧 Common Fix Patterns

### 1. Mock Spec Issues
```python
# If seeing "Cannot spec a Mock object"
# Use the create_mock_with_spec helper:
def create_mock_with_spec(spec_class):
    if (hasattr(spec_class, '_mock_name') or
        hasattr(spec_class, '_spec_class')):
        return Mock()
    return Mock(spec=spec_class)
```

### 2. Timezone Issues
```python
# Add at top of test file:
from datetime import datetime, timezone

# Replace:
datetime.now()
# With:
datetime.now(timezone.utc)
```

### 3. AsyncMock Assertions
```python
# Replace:
mock.assert_called_once()
# With:
assert mock.call_count == 1
```

### 4. Import Path Issues
```python
# Check actual import location in implementation
# Patch where it's used, not where it's defined
@patch('module.where.used.ClassName')
```

## 📈 Progress Tracking

### Metrics to Monitor:
- Total tests discovered
- Tests passing
- Tests failing
- Tests skipped
- Test execution time
- Coverage percentage

### Update Test Cache:
```bash
# After each test run, cache will auto-update
# Manual verification:
cat .test_cache/stats.txt
wc -l .test_cache/passed_tests.txt
wc -l .test_cache/failed_tests.txt
```

## 🚀 Optimization Strategies

### 1. Parallel Execution
```bash
# Run tests in parallel for speed
python -m pytest src/tests/ -n auto
```

### 2. Fail Fast
```bash
# Stop at first failure for quick iteration
python -m pytest src/tests/ -x
```

### 3. Rerun Failed Only
```bash
# Use test-menu.sh option 2
echo -e "2\nq" | scripts/test-menu.sh
```

## 📝 Documentation Requirements

### For Each Fix Session:
1. **Update CHANGELOG.md**
   ```markdown
   ### Fixed
   - [Test] Fixed X tests in file.py - description of issue
   ```

2. **Update TEST-CHANGELOG.md**
   ```markdown
   ## Session N - Date
   ### Tests Fixed
   - file_test.py: Issue and resolution
   ```

3. **Create Iteration Summary**
   ```markdown
   ai_docs/testing-qa/iteration-N-summary.md
   ```

## 🎯 Success Criteria

### Short Term (Today):
- [ ] All tests can be collected without import errors
- [ ] 80%+ of unit tests passing
- [ ] Critical auth and task management tests passing
- [ ] Test cache accurately reflects current state

### Medium Term (This Week):
- [ ] 95%+ of all tests passing
- [ ] No infrastructure-level failures
- [ ] All Mock spec issues resolved
- [ ] Comprehensive test documentation

### Long Term (This Month):
- [ ] 100% test pass rate
- [ ] Automated CI/CD integration
- [ ] Test coverage > 80%
- [ ] Performance benchmarks established

## 🔄 Continuous Improvement

### Daily Routine:
1. Morning: Run full test suite
2. Identify new failures
3. Fix systematically
4. Document changes
5. Evening: Verify all fixes

### Weekly Review:
- Analyze test trends
- Identify flaky tests
- Improve test performance
- Update test documentation

## 🚨 Troubleshooting Guide

### If Tests Won't Run:
1. Check Python environment
2. Verify dependencies installed
3. Check for hook interference
4. Try different directory
5. Use virtual environment

### If Mass Failures:
1. Check for environment issues
2. Verify database connection
3. Check for missing migrations
4. Review recent code changes
5. Check Python version compatibility

### If Fixes Don't Stick:
1. Verify fix is in correct location
2. Check for multiple test files with same issue
3. Ensure cache is updating
4. Look for test interdependencies
5. Check for race conditions

## 📞 Escalation Path

### When to Seek Help:
- Infrastructure-level blocks
- Mass test failures (>50%)
- Environment-specific issues
- Hook or permission problems
- CI/CD integration issues

### Information to Provide:
- Error messages and stack traces
- Test command used
- Environment details
- Recent changes made
- Cache status

## ✅ Completion Checklist

- [ ] Test execution environment working
- [ ] All tests discovered successfully
- [ ] Import errors resolved
- [ ] Unit tests passing (>95%)
- [ ] Integration tests passing (>90%)
- [ ] E2E tests passing (>85%)
- [ ] Test cache updated
- [ ] Documentation complete
- [ ] CHANGELOG.md updated
- [ ] TEST-CHANGELOG.md updated

## 🎉 Definition of Done

The test suite improvement initiative will be complete when:
1. All tests can be executed without infrastructure issues
2. 95%+ pass rate achieved across all categories
3. Test execution time < 5 minutes for full suite
4. Documentation is comprehensive and current
5. CI/CD pipeline is green
6. Test cache is optimized and accurate