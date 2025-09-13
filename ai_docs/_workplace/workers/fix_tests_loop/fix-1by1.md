# Test Fix Instructions - Step by Step Process

## Objective
Fix all failing tests systematically by addressing root causes, not just symptoms.

## Step-by-Step Process

### Step 1: Load and Analyze Failed Tests
1. Read the `.test_cache/failed_tests.txt` file
2. Pick the FIRST failing test from the list
3. Note the exact file path and test name

### Step 2: Investigate Root Cause
1. Run the specific test in isolation to see the exact error:
   ```bash
   cd dhafnck_mcp_main
   python -m pytest [test_file_path]::[test_name] -xvs --tb=long
   ```
2. Analyze the error message carefully
3. Identify the root cause (not just the symptom):
   - Import errors → Find missing module/class
   - Assertion errors → Understand expected vs actual behavior
   - Type errors → Check data types and interfaces
   - Dependency errors → Verify all dependencies exist

### Step 3: Fix the Root Cause
1. Navigate to the source of the problem (not just the test file)
2. Apply the fix to the SOURCE CODE, not the test
3. If test is outdated, update test to match current implementation
4. Document what was changed and why

### Step 4: Verify the Fix
1. Re-run the specific test to confirm it passes
2. Run related tests in the same module to ensure no regression
3. If test passes, proceed to next step

### Step 5: Update Test Cache
1. Remove the fixed test from `.test_cache/failed_tests.txt`
2. Add the test to `.test_cache/passed_tests.txt`
3. Update test hash in `.test_cache/test_hashes.txt`

### Step 6: Document and Continue
1. Log the fix in a tracking file with:
   - Test name
   - Root cause identified
   - Fix applied
   - Verification status
2. Return to Step 1 with the next failing test

## Important Guidelines

### DO:
- Fix the actual source code that causes test failures
- Address root causes in the implementation
- Update tests only if they're testing deprecated behavior
- Run each test in isolation first
- Verify fixes don't break other tests
- Keep detailed logs of each fix

### DON'T:
- Just modify tests to make them pass
- Apply quick patches without understanding the issue
- Skip verification steps
- Fix multiple tests simultaneously
- Ignore related test failures

## Current Status
- Total failing tests: Check `.test_cache/failed_tests.txt`
- Progress tracking: See fix logs
- Next test to fix: [First line in failed_tests.txt]

## Command Reference
```bash
# Run single test
cd dhafnck_mcp_main && python -m pytest [test_path]::[test_name] -xvs

# Run all tests in a file
cd dhafnck_mcp_main && python -m pytest [test_path] -xvs

# Check test with detailed traceback
cd dhafnck_mcp_main && python -m pytest [test_path]::[test_name] -xvs --tb=long

# Run with coverage
cd dhafnck_mcp_main && python -m pytest [test_path] --cov=[module] --cov-report=term-missing
```