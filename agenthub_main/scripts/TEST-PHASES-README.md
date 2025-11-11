# Test Phase Scripts - Parallel Execution Guide

## Overview

This directory contains scripts to run the remaining test phases in parallel sessions. Each phase targets specific test failure categories from the original 102 failures.

## Progress Summary

| Phase | Status | Tests Fixed | Description |
|-------|--------|-------------|-------------|
| **Phase 1** | ✅ Complete | 9 tests | TaskResponse.from_domain() signature changes |
| **Phase 2** | ✅ Complete | 13 tests | Computed property assertions |
| **Phase 3** | ✅ Complete | 3 tests | WebSocket metadata & business logic |
| **Phase 4** | ✅ Complete | 12 tests | Agent controller workflow guidance |
| **Phase 5A** | ✅ Complete | 26 tests | Repository session injection |
| **TOTAL FIXED** | | **63 tests** | **61.8% of original 102 failures** |

## Remaining Phases

### Phase 5B: Repository Errors (~47 errors)
**Script:** `./scripts/test-phase-5b-repository-errors.sh`
**Target:** Repository tests with import/dependency errors
**Common Issues:**
- Import errors for moved/renamed classes
- Missing mock dependencies
- Changed method signatures
- Updated repository interfaces

### Phase 6: Environment Configuration (~9 failures)
**Script:** `./scripts/test-phase-6-environment-config.sh`
**Target:** DATABASE_TYPE validation and environment config
**Common Issues:**
- DATABASE_TYPE enum validation tightened
- Invalid DATABASE_TYPE values in tests
- Environment variable validation changes
- Configuration class constructor updates

### Phase 7: Miscellaneous (~9+ failures)
**Script:** `./scripts/test-phase-7-misc.sh`
**Target:** Remaining edge cases and miscellaneous failures
**Common Issues:**
- Edge case handling updates
- API response format changes
- Validation rule updates
- Domain event changes

## Usage

### Run Individual Phases

```bash
# From agenthub_main directory

# Phase 5B - Repository Errors
./scripts/test-phase-5b-repository-errors.sh

# Phase 6 - Environment Config
./scripts/test-phase-6-environment-config.sh

# Phase 7 - Miscellaneous
./scripts/test-phase-7-misc.sh
```

### Run All Remaining Phases Sequentially

```bash
./scripts/test-all-remaining-phases.sh
```

### Parallel Execution (Recommended)

Open 3 terminal sessions and run one phase in each:

**Session 1:**
```bash
cd /home/daihu/__projects__/4genthub/agenthub_main
./scripts/test-phase-5b-repository-errors.sh
```

**Session 2:**
```bash
cd /home/daihu/__projects__/4genthub/agenthub_main
./scripts/test-phase-6-environment-config.sh
```

**Session 3:**
```bash
cd /home/daihu/__projects__/4genthub/agenthub_main
./scripts/test-phase-7-misc.sh
```

## Output Files

Each script saves detailed results to `/tmp/`:
- `/tmp/phase5b-results.txt` - Repository error details
- `/tmp/phase6-results.txt` - Environment config details
- `/tmp/phase7-results.txt` - Miscellaneous test details

## Workflow After Running Scripts

1. **Review Output:** Check the terminal output for failure patterns
2. **Analyze Results:** Examine the `/tmp/phase*.txt` files for detailed errors
3. **Fix Tests:** Apply fixes following the SOURCE OF TRUTH hierarchy:
   ```
   User Requirements → ORM Model → Database → Tests → Code
   ```
4. **Commit Per Phase:** Create separate commits for each phase:
   ```bash
   git add <modified-files>
   git commit -m "test: fix Phase X failures (N tests)"
   git push
   ```

## Common Fix Patterns

### Session Injection (Already Fixed in 5A)
```python
# OLD (broken)
with patch('...get_session'): repo = Repo()

# NEW (working)
mock_session = Mock()
repo = Repo(session=mock_session)
```

### Signature Updates
```python
# Check implementation for new parameters
# Update test assertions to match current signature
```

### Property Changes
```python
# OLD (writable field)
task.subtask_count = 5

# NEW (computed property)
# subtask_count computed from len(task.subtasks)
```

## Tips for Parallel Work

1. **No Conflicts:** Each phase targets different test files, so no merge conflicts
2. **Independent Fixes:** Phases can be fixed in any order
3. **Quick Wins:** Phase 6 (environment config) is likely the quickest
4. **Commit Often:** Commit after fixing each phase for clean history

## SOURCE OF TRUTH Reminder

Always follow this hierarchy when tests fail:
1. **Check ORM Model** - The domain entity definition is authoritative
2. **Update Code** - Make code match ORM model
3. **Update Tests** - Make tests match current implementation
4. **Never add compatibility code** - Clean breaks are preferred in development

## Questions?

If you encounter issues:
1. Check the error pattern in `/tmp/phase*.txt`
2. Search for similar fixes in git history: `git log --grep="test:"`
3. Refer to CLAUDE.local.md for test fixing guidelines
