### Removed

**Dead Code Cleanup - Compatibility Shims & Duplicate Implementations** (2025-11-10)

Removed 4 dead code items (6 total files, ~650 lines) including compatibility layers, unused wrappers, and duplicate implementations no longer used anywhere in codebase.

**Infrastructure Layer** (`agenthub_main/src/fastmcp/task_management/infrastructure/`)
- Removed `orm/` directory (2 files, ~450 bytes)
  - Pure re-export shims from when models moved to `database/`
  - 0 import references found across entire codebase
  - Actual models at: `infrastructure/database/models.py` (750 lines, actively used)
- Removed `mock_repository_factory_wrapper.py` (55 lines)
  - Wrapper to import from test fixtures with fallback
  - 0 import references - never adopted by consumers
  - Infrastructure `mock_repository_factory.py` is actively used by 5 test files
- Files: `infrastructure/orm.obsolete/`, `mock_repository_factory_wrapper.py.obsolete`

**Domain Layer** (`agenthub_main/src/fastmcp/task_management/domain/`)
- Removed `models/` directory (2 files, ~360 bytes)
  - Compatibility layer for `ContextLevel` enum
  - 0 import references found across entire codebase
  - Actual location: `domain/value_objects/context_enums.py` (actively imported by 20+ files)
- Files: `domain/models.obsolete/`

**Test Fixtures** (`agenthub_main/src/tests/fixtures/mocks/repositories/`)
- Removed `mock_repository_factory.py` (594 lines)
  - Orphaned duplicate of infrastructure implementation (464 lines)
  - Only imported by dead wrapper (which was never used)
  - All tests import from infrastructure version
- Files: `mock_repository_factory.py.obsolete`

**Impact**
- Lines removed: ~650 lines of dead code
- Codebase clarity: Single source of truth for each entity
- Import paths: No confusing multiple paths to same code
- Maintenance: Fewer files to understand/maintain
- Pattern detection: Identified wrapper/duplicate implementation anti-patterns
- Verification: Import tests pass ✅
- Recovery: Reversible via `.obsolete` naming pattern

**Details**: See `ai_docs/reports-status/dead-code-cleanup-2025-11-10.md`

---

**Scripts Directory Cleanup** (2025-11-09)

**Backend Scripts** (`agenthub_main/scripts/`)
- Marked 51 obsolete scripts with `.obsolete` extension (reversible pattern)
- Categories removed:
  - Migration scripts (5 files) - Replaced by `init_database.py`
  - One-off fix scripts (12 files) - Historical bug fixes no longer needed
  - Duplicate auth check scripts (9 files) - Consolidated to `jwt-authentication-verification.py`
  - Cleanup/migration utilities (11 files) - One-time scripts
  - Duplicate setup scripts (9 files) - Consolidated to 2 essential scripts
  - Output/result files (4 files) - Should not be in version control
  - Clean code validation folder (1 folder) - One-time validation scripts
- Reduction: 144 → 96 active scripts (33% reduction)
- Files: `agenthub_main/scripts/**/*.obsolete`

**Root Scripts** (`scripts/`)
- Marked 6 obsolete scripts with `.obsolete` extension
- Categories removed:
  - Migration scripts (1 file) - `migrate-database.sh` replaced by `init_database.py`
  - One-off verification (1 file) - `verify_duplicate_project_enhancement.py`
  - Old deployment scripts (2 files) - Replaced by `scripts/deployment/` folder
  - Obsolete utilities (1 file) - `create_hook_proxies.py` hook workaround
  - Output files (1 file) - `schema_verification_report.md` should not be in git
- Reduction: 34 → 28 active scripts (18% reduction)
- Active scripts: 10 Python + 18 Shell = 28 total
- Files: `scripts/**/*.obsolete`

**Total Cleanup**
- Combined reduction: 178 → 124 active scripts (30% reduction)
- Total obsolete files marked: 57 files
- Reversible: `mv file.obsolete file` to restore any file
- Permanent delete: `find . -name "*.obsolete" -delete`
- Updated: `agenthub_main/scripts/README.md` with cleanup history
