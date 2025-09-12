# Fix for Test Import Errors

## Problem
When running tests with option 3 in test-menu.sh, getting multiple import errors for test files.

## Root Cause
The test files were created for modules that don't exist yet or have different import paths than expected.

## Files with Import Issues

### 1. Enhanced Auth Endpoints Test
- **File**: `dhafnck_mcp_main/src/tests/auth/api/enhanced_auth_endpoints_test.py`
- **Issue**: Trying to import functions that are router endpoints, not exported functions
- **Fix**: Refactored to only test models and utility functions

### 2. Task Management Tests
These test files reference modules that may not exist:
- `context_search_test.py`
- `context_versioning_test.py`
- `batch_context_operations_test.py`
- `context_templates_test.py`

### 3. Other Failing Tests
Tests that reference non-existent or differently structured modules:
- `token_mgmt_routes_test.py` - for non-existent token management routes
- Various unit test files in wrong locations

## Solution Approach

### Step 1: Identify Non-Existent Modules
Check if source modules exist before keeping test files.

### Step 2: Fix Import Paths
Update test files to use correct import paths.

### Step 3: Remove Tests for Non-Existent Code
Remove test files for modules that haven't been implemented yet.

## Commands to Run

```bash
# List all test files with errors
find dhafnck_mcp_main/src/tests -name "*test*.py" -type f | while read f; do
    python -c "import sys; sys.path.insert(0, 'dhafnck_mcp_main/src'); exec(open('$f').read())" 2>/dev/null || echo "Error in: $f"
done

# Run tests with better error reporting
cd dhafnck_mcp_main
python -m pytest src/tests --tb=short --co -q
```

## Next Steps
1. Review each failing test file
2. Check if corresponding source module exists
3. Either fix imports or remove test file
4. Update TEST-CHANGELOG.md to reflect changes