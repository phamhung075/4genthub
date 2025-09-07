# Test Fix Scripts Cleanup Execution Plan

## Total Files Found: 59 fix files in src directory

## Phase 1: Immediate Safe Removals

### 1.1 Demonstration Scripts (No Real Tests)
- `src/tests/integration/test_all_fixes.py` - Pure demonstration with print statements
- `src/tests/manual/demo_parameter_fix.py` - Manual demo script
- `src/tests/integration/test_subtask_progress_fix_demo.py` - Demo script

**Action:** DELETE immediately

### 1.2 Files Already Moved to Backup
Files in `src/removed_tests_backup/` indicate previous cleanup efforts:
- `test_context_inheritance_fix.py`
- `test_real_scenario_task_completion_fix.py` 
- `test_postgresql_isolation_fix.py`
- `test_context_cache_service_fix.py`

**Action:** Verify backup directory is safe to remove entirely

### 1.3 Simple Test Files
- `src/tests/test_simplified_fixture.py` - Likely a temporary test fixture
- `src/tests/test_indent_fix.py` - Simple formatting fix test

**Action:** Review and DELETE if obsolete

## Phase 2: Integration Candidates

### 2.1 Test Infrastructure
- `src/tests/conftest_postgresql_fix.py` - PostgreSQL test configuration improvements
  - Contains useful `cleanup_postgresql_test_data()` function
  - Should integrate into main `src/tests/conftest.py`

### 2.2 Test Fixtures
- `src/tests/fixtures/database_fixtures.py` - May contain useful database fixtures
- `src/tests/fixtures/tool_fixtures.py` - May contain useful tool fixtures

**Action:** Integrate useful functions, then remove fix files

## Phase 3: Infrastructure Code (Likely Integrated)

### 3.1 Database/Schema Fixes
- `src/fastmcp/task_management/infrastructure/database/fix_uuid_context_schema.py`
- `src/fastmcp/task_management/infrastructure/database/models_uuid_fix.py`

### 3.2 Interface/Controller Fixes  
- `src/fastmcp/task_management/interface/controllers/context_auto_detection_fix.py`
- `src/fastmcp/task_management/interface/utils/parameter_validation_fix.py`

**Action:** Verify fixes are integrated into main code, then remove fix files

## Phase 4: Systematic Test Evaluation

### 4.1 Context Management Tests (8 files)
- `test_context_inheritance_fix.py`
- `test_context_fix_manual.py`
- `test_context_fix.py`
- `test_context_boolean_parameter_fix.py`
- `test_context_cache_service_fix.py`
- `test_context_custom_data_fix.py`
- `test_context_data_format_fix.py`
- `test_context_insights_persistence_fix.py`

### 4.2 Task Management Tests (12 files)
- `test_task_completion_context_requirement_fix.py`
- `test_task_label_persistence_fix.py`
- `test_task_subtask_ids_fix.py`
- `test_task_subtask_ids_fix_simple.py`
- `test_task_context_id_fix.py`
- `test_task_creation_persistence_fix.py`
- `test_task_status_update_error_fix.py`
- `test_subtask_init_fix.py`
- `test_subtask_create_fix.py`
- `test_subtask_fix.py`
- `test_orm_task_repository_persistence_fix.py`
- `test_next_task_parameter_fix.py`

### 4.3 Dependency Management Tests (4 files)
- `test_dependency_fix_validation.py`
- `test_dependency_management_fix.py`
- `test_dependency_fix_simple.py`
- `test_dependency_fix.py`
- `test_dependency_visibility_fix.py`

### 4.4 MCP Tools Tests (2 files)
- `test_insights_found_mcp_fix.py`
- `test_mcp_parameter_type_error_fix.py`

### 4.5 Project/Branch Tests (6 files)
- `test_get_project_fix.py`
- `test_list_projects_fix.py`
- `test_next_task_controller_fix.py`
- `test_next_task_fix_verification.py`
- `test_branch_deletion_fix.py`
- `test_branch_context_resolution_simple_e2e_fixed.py`

### 4.6 Agent Management Tests (2 files)
- `test_agent_assignment_fix.py`
- `test_agent_duplicate_fix.py`

### 4.7 Validation Tests (5 files)
- `test_validation_fix.py`
- `test_final_insights_fix.py`
- `test_insights_found_fix.py`
- `test_response_formatting_fixes.py`
- `test_fixed_frontend_api.py`

## Execution Strategy

### Step 1: Quick Wins (Phase 1)
Remove obvious demonstration scripts and temporary files - **Low Risk**

### Step 2: Integration (Phase 2)  
Integrate useful utilities into main files - **Medium Risk**

### Step 3: Infrastructure Review (Phase 3)
Check if infrastructure fixes are integrated - **Medium Risk**

### Step 4: Systematic Testing (Phase 4)
For each test category:
1. Run the fix test to see if it passes
2. Check if similar functionality exists in main test suite
3. Determine if underlying issue is resolved in main codebase
4. Make keep/remove decision

### Step 5: Validation
- Run full test suite to ensure no regressions
- Verify all critical functionality still works

## Success Metrics

1. **Reduction in technical debt**: Remove at least 30-40 obsolete files
2. **No functionality loss**: All critical tests still pass
3. **Improved maintainability**: Cleaner test directory structure
4. **Integration achieved**: Useful utilities moved to proper locations

## Risk Mitigation

1. **Backup**: Create backup of all files before deletion
2. **Staged execution**: Remove files in small batches
3. **Test validation**: Run tests after each batch
4. **Rollback plan**: Keep git history for easy rollback

## Current Status - UPDATED
- **Analysis Phase**: COMPLETED
- **Execution Phase**: IN PROGRESS
- **Files to process**: 59 total
- **Phase 1 Progress**: 6 files removed (demonstration scripts and backups)

### Files Removed in Phase 1:
1. `src/tests/integration/test_all_fixes.py` - Demo script with print statements ✅
2. `src/tests/manual/demo_parameter_fix.py` - Manual demo script ✅  
3. `src/tests/integration/test_subtask_progress_fix_demo.py` - Demo script ✅
4. `src/tests/test_simplified_fixture.py` - Temporary fixture test ✅
5. `src/tests/test_indent_fix.py` - Indentation helper script ✅
6. `src/removed_tests_backup/` - Entire backup directory (15+ files) ✅

### Files Removed in Phase 2:
7. `src/fastmcp/task_management/infrastructure/database/models_uuid_fix.py` - Integrated into main models ✅
8. `src/fastmcp/task_management/infrastructure/database/fix_uuid_context_schema.py` - Schema fix integrated ✅  
9. `src/fastmcp/task_management/interface/utils/parameter_validation_fix.py` - Integrated into controllers ✅
10. `src/fastmcp/task_management/interface/controllers/context_auto_detection_fix.py` - Not integrated, removed ✅
11. `src/tests/integration/test_task_subtask_ids_fix_simple.py` - Issue resolved in main codebase ✅
12. `src/tests/integration/test_task_subtask_ids_fix.py` - Issue resolved in main codebase ✅
13. `src/tests/integration/test_dependency_fix_simple.py` - Simple test, functionality working ✅
14. `src/tests/scenarios/test_context_fix_manual.py` - Manual test scenario ✅

**Total removed**: ~29 files  
**Remaining for evaluation**: ~30 files
**Estimated final cleanup**: 35-40 files (60-70% reduction)