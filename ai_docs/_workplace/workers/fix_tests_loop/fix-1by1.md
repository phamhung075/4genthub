# Test Fix Loop - Token-Optimized Guide

## 🚨 GOLDEN RULE
**Code > Tests**: Always fix tests to match current implementation. NEVER modify working code to satisfy outdated tests.

## Objective
Fix failing tests by addressing root causes based on LATEST CODE VERSION, not obsolete test expectations.

---

## Obsolescence Decision Matrix

| Scenario | Test | Code | Action | Priority |
|----------|------|------|--------|----------|
| Test expects removed feature | OBSOLETE | CURRENT | Update/remove test | HIGH |
| Test uses old API format | OBSOLETE | CURRENT | Update test to new API | HIGH |
| Test imports old modules | OBSOLETE | CURRENT | Fix test imports | HIGH |
| Code has actual bug | CURRENT | BROKEN | Fix code bug | HIGH |
| Code is deprecated | CURRENT | OBSOLETE | Remove both | MEDIUM |
| Both work but mismatch | UNCLEAR | UNCLEAR | Check git history | LOW |

### Determining Obsolescence

```bash
# Check modification dates (newer code usually means test is obsolete)
git log -p --follow [source_file_path]
git log -p --follow [test_file_path]
```

**Check**: ai_docs/ for API specs | CHANGELOG.md for breaking changes | Production usage | Dependencies

---

## Step-by-Step Process

### 1. Load Failed Tests
```bash
# View failed tests
echo -e "8\nq" | timeout 10 scripts/test-menu.sh

# See statistics
echo -e "7\nq" | timeout 10 scripts/test-menu.sh
```
Pick FIRST failing test → Note exact file path and test name

### 2. Investigate Root Cause
```bash
# Run specific test (RECOMMENDED)
echo -e "4\n[test_file_path]\nq" | timeout 20 scripts/test-menu.sh

# Or direct pytest
timeout 20 bash -c "cd agenthub_main && python -m pytest [test_file_path]::[test_name] -xvs --tb=long"
```

**EXAMINE CURRENT CODE FIRST** - Not test expectations

| Error Type | Investigation Focus |
|------------|-------------------|
| Import errors | Find module/class in CURRENT codebase |
| Assertion errors | Check if test expects OBSOLETE behavior |
| Type errors | Verify current data types/interfaces |
| Method errors | Check if methods exist in CURRENT implementation |
| Dependency errors | Verify dependencies in LATEST code |

### 3. Fix Root Cause

**Protection Checklist (BEFORE changing anything):**
- [ ] Is current code working in production?
- [ ] Is this just an outdated test expectation?
- [ ] Checked git history (which changed recently)?
- [ ] Looked for other passing tests using same code?
- [ ] Will this break other components?

**Decision Flow:**
```
Test Fails → Code working elsewhere? → YES → UPDATE TEST
                                    → NO → Code changed recently? → YES → UPDATE TEST
                                                                  → NO → Real bug? → YES → FIX CODE (rare)
                                                                                   → NO → UPDATE TEST (default)
```

**Implementation Priority:**
1. Check CURRENT implementation
2. Run obsolescence check
3. **Default: UPDATE TEST, NOT CODE**

| Scenario | Action | Update Changelog |
|----------|--------|------------------|
| Test expects OBSOLETE behavior | Update test → match current | ✅ |
| Missing methods | Check if renamed/moved → Update test | ✅ |
| Import failures | Update imports → current structure | ✅ |
| Assertion failures | Update test data → current API | ✅ |
| Confirmed bug + no dependencies | Fix source code | ⚠️ |

### 4. Verify Fix
```bash
# Re-run specific test
echo -e "4\n[test_file_path]\nq" | timeout 20 scripts/test-menu.sh
```

1. Confirm test passes
2. Run related tests (check no regression)
3. Verify cache updated (`.pytest_cache/test-menu-cache.json`)

### 5. Document & Continue
Log: Test name | Root cause | Fix applied | Verification status → Return to Step 1

---

## Common Mistakes (NEVER DO)

| ❌ WRONG | Why |
|---------|-----|
| Add method because test expects it | Method likely renamed/moved |
| Change return types to match test | Tests should match current API |
| Revert recent code for old tests | Tests need updating |
| Modify schemas for test fixtures | Update fixtures instead |
| Change endpoints for old test URLs | Update test URLs |
| Add deprecated parameters back | Remove from tests |
| Downgrade libraries for test mocks | Update mocks |

**Example:**
```python
# ❌ WRONG: Adding old method for test
def get_user_by_id(self, id):  # Old name
    return self.get_user(id)   # Wrapper for test

# ✅ RIGHT: Update test
# Change: user = service.get_user_by_id(123)
# To: user = service.get_user(123)
```

---

## Command Reference

### test-menu.sh (RECOMMENDED)
```bash
# Run specific test
echo -e "4\n[test_file_path]\nq" | timeout 20 scripts/test-menu.sh

# Run failed tests only
echo -e "2\nq" | timeout 20 scripts/test-menu.sh

# Statistics
echo -e "7\nq" | timeout 10 scripts/test-menu.sh

# View cached tests
echo -e "8\nq" | timeout 10 scripts/test-menu.sh
```

### Direct pytest (Fallback)
```bash
# Single test with timeout
timeout 20 bash -c "cd agenthub_main && python -m pytest [test_path]::[test_name] -xvs"

# Full file
timeout 20 bash -c "cd agenthub_main && python -m pytest [test_path] -xvs"

# With coverage
timeout 60 bash -c "cd agenthub_main && python -m pytest [test_path] --cov=[module] --cov-report=term-missing"
```

### Timeout Strategy
| Operation | Timeout | Use |
|-----------|---------|-----|
| Most operations | 20s | Standard test runs |
| Coverage reports | 60s | Extended analysis |
| Stats/cache viewing | 10s | Quick queries |

### Query JSON Cache
```bash
# Statistics
jq '.statistics' .pytest_cache/test-menu-cache.json

# List failed tests
jq -r '.tests | to_entries[] | select(.value.status == "failed") | .key' .pytest_cache/test-menu-cache.json

# Count failed
jq '[.tests[] | select(.status == "failed")] | length' .pytest_cache/test-menu-cache.json
```

---

## Cache Files
- `.pytest_cache/test-menu-cache.json` - Test status, hashes, statistics (auto-updated by test-menu.sh)
- `.pytest_cache/test-menu-last-run.log` - Last run output

## Common Outdated Test Patterns

| Pattern | Indicates |
|---------|-----------|
| Imports non-existent modules | Outdated imports |
| Calls methods that don't exist | Renamed/removed methods |
| Expects old data formats | API changed |
| Mocks removed/renamed methods | Outdated mocks |
| Hardcoded values don't match defaults | Changed configuration |

---

## Summary Checklist

**DO:**
- ✅ Examine CURRENT code first
- ✅ Update tests for obsolete/removed functionality
- ✅ Fix imports to match current structure
- ✅ Align test data with current API
- ✅ Address root causes based on latest codebase
- ✅ Run tests in isolation
- ✅ Verify no regressions
- ✅ Log all fixes (code vs test)

**DON'T:**
- ❌ Modify working code for outdated tests
- ❌ Add missing methods without checking if renamed
- ❌ Downgrade implementation for old patterns
- ❌ Apply quick patches without understanding
- ❌ Skip verification
- ❌ Fix multiple tests simultaneously
- ❌ Assume test expectations are always correct
