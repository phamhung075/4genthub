### Added

**Git Pre-commit Hook for Ruff Formatting + Auto-Staging** (2025-11-12)

Implemented automated code formatting using ruff with one-step auto-staging workflow for seamless developer experience.

**Changes Made**:
- Created `agenthub_main/.pre-commit-config.yaml` - Pre-commit framework configuration
- Configured to run on STAGED files only (default behavior) for auto-staging support
- Created `scripts/git-auto-commit.sh` - Wrapper script for automatic re-staging workflow
- Fixed Pydantic V2 deprecation: `class Config` → `model_config = {"extra": "allow"}`
- Fixed datetime deprecation: `datetime.utcnow()` → `datetime.now(datetime.UTC)`
- Fixed test failure: `Settings._set_project_root()` now updates `model_config["env_file"]`
- Added pytest marks: `regression`, `agent_repository`, `timestamp_bug_fix`
- Fixed pytest warning: `_MockFastAPIClient` → `__MockFastAPIClient`

**Auto-Staging Workflow**:
- **Standard git commit**: Two-step (commit → format → blocked → re-add → commit)
- **Auto-commit script**: One-step (commit → format → auto-re-stage → success)
- Usage: `./scripts/git-auto-commit.sh -m "message"`

**Benefits**:
- ✅ Consistent code formatting across all commits
- ⚡ Fast formatting (only processes staged files)
- 🔒 Enforced in CI/CD via existing `run-static.yml` workflow
- 🎯 One-step workflow with auto-commit script
- 🚫 Prevents unformatted code from being committed
- 🤝 Works locally and in GitHub Actions

**Files Created/Modified**:
- `agenthub_main/.pre-commit-config.yaml:1-30` - Pre-commit configuration (staged files only)
- `scripts/git-auto-commit.sh:1-25` - Auto-staging wrapper script
- `agenthub_main/src/fastmcp/task_management/domain/websocket_protocol.py:340,377-379` - Fixed Pydantic deprecation
- `agenthub_main/src/fastmcp/settings.py:175` - Fixed test failure (model_config sync)
- `agenthub_main/pyproject.toml:153-155,267-268` - Added pytest marks and ruff ignores
- `agenthub_main/src/tests/conftest.py:483,1016` - Fixed mock class naming

**Technical Details**:
- Pre-commit runs on staged files by default (enables auto-staging)
- Removed `pass_filenames: false` and `always_run: true` for default behavior
- Auto-commit script detects "Changes not staged" and re-stages automatically
- Includes hooks: ruff, ruff-format, trailing-whitespace, end-of-file-fixer, check-yaml, check-merge-conflict
- Test fixes: All 9 tests in TestEnvFilePriority now pass
