# Configuration Tests

## Phase 6: DATABASE_TYPE Validation Tests

### Overview

This directory contains tests for environment configuration validation, specifically focusing on the tightened `DATABASE_TYPE` validation implemented to enforce PostgreSQL-only database support.

### Test Coverage

**File:** `test_database_type_validation.py`

**Total Test Cases:** 16

#### Test Classes

1. **TestDatabaseTypeValidation** (7 tests)
   - Tests valid DATABASE_TYPE values (postgresql, supabase, case-insensitive variants)
   - Tests invalid DATABASE_TYPE rejection (sqlite, mysql, oracle, mongodb, etc.)
   - Tests missing/None DATABASE_TYPE error handling
   - Tests connection detail requirements for postgresql and supabase
   - Tests case-insensitive normalization

2. **TestDatabaseTypeErrorMessages** (3 tests)
   - Validates clear error messages for invalid types
   - Ensures error messages provide migration guidance
   - Verifies no fallback behavior on invalid types

3. **TestDatabaseConfigurationConstructor** (3 tests)
   - Tests validation before connection attempt
   - Verifies singleton pattern preservation
   - Tests reset_instance() state clearing

4. **TestEnvironmentVariableValidation** (3 tests)
   - Tests explicit configuration requirement (no defaults)
   - Tests empty string handling
   - Tests whitespace-only value rejection

### Expected Test Results

#### Should PASS (11 tests)
- All valid DATABASE_TYPE tests (postgresql, supabase, case variants)
- Invalid type rejection tests (sqlite, mysql, etc.)
- Missing DATABASE_TYPE error tests
- Constructor validation tests
- Error message validation tests

#### May FAIL Initially (5 tests)
These tests verify strict requirements and may fail if:
1. `test_postgresql_requires_connection_details` - Connection validation logic differs
2. `test_supabase_requires_connection_details` - Supabase validation logic differs
3. `test_empty_string_treated_as_missing` - Empty string handling logic
4. `test_whitespace_only_rejected` - Whitespace handling in validation
5. Error message exact text matches

### Running the Tests

```bash
# Run all configuration tests
pytest src/tests/unit/task_management/infrastructure/configuration/ -v

# Run only DATABASE_TYPE validation tests
pytest src/tests/unit/task_management/infrastructure/configuration/test_database_type_validation.py -v

# Run specific test class
pytest src/tests/unit/task_management/infrastructure/configuration/test_database_type_validation.py::TestDatabaseTypeValidation -v

# Run with detailed output
pytest src/tests/unit/task_management/infrastructure/configuration/test_database_type_validation.py -v --tb=short
```

### Related Files

- **Source:** `agenthub_main/src/fastmcp/task_management/infrastructure/database/database_config.py`
  - Lines 126-158: DATABASE_TYPE validation logic
  - Lines 145-158: Type validation (only postgresql/supabase allowed)

### Known Issues

**~9 Existing Tests Will Fail** after these validation rules are enforced:
- `test_env_loading.py`: Uses `DATABASE_TYPE='sqlite'` (2 occurrences)
- `test_env_priority_tdd.py`: Uses `DATABASE_TYPE='sqlite'` (1 occurrence)
- `test_env_loading_tdd.py`: Uses `DATABASE_TYPE='sqlite'` (2 occurrences)
- `test_completion_summary_manual.py`: Uses `DATABASE_TYPE='sqlite'` (1 occurrence)
- `test_sqlite_mode.py`: Uses `DATABASE_TYPE='sqlite'` (1 occurrence)
- `conftest_simplified.py`: Uses `DATABASE_TYPE='sqlite'` (3 occurrences)
- `test_database_migrations.py`: Uses `DATABASE_TYPE='sqlite'` (1 occurrence)
- `test_server_startup.py`: Uses `DATABASE_TYPE='sqlite'` (1 occurrence)
- `test_database_init.py`: Uses `DATABASE_TYPE='sqlite'` (1 occurrence)

These files need to be updated to use valid DATABASE_TYPE values or mock the validation appropriately.

### Validation Logic

Current `database_config.py` validation (lines 145-158):

```python
# Validate database type - PostgreSQL only
if self.database_type in ["postgresql", "supabase"]:
    # Get database URL from environment variables
    self.database_url = self._get_secure_database_url()
    if not self.database_url:
        raise ValueError(
            f"Database configuration missing for {self.database_type}.\n"
            "Required environment variables:\n"
            f"{'DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD' if self.database_type == 'postgresql' else 'SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD'}"
        )
else:
    raise ValueError(
        f"Invalid DATABASE_TYPE: {self.database_type}\n"
        "Supported types: 'postgresql' or 'supabase'"
    )
```

### Future Enhancements

1. Add tests for environment variable precedence (.env vs .env.dev)
2. Add tests for connection string construction validation
3. Add tests for pool configuration validation
4. Add integration tests for actual database connections
