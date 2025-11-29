# agenthub Project - Local AI Agent Rules
DATABASE agenthub | rolname = 'agenthub_user'

## About This File
This file (`CLAUDE.local.md`) contains **local, environment-specific rules** for AI agents working on this project. It is NOT checked into version control and complements the main `CLAUDE.md` file.

| File | Purpose | Version Control |
|------|---------|----------------|
| **CLAUDE.md** | Main AI agent instructions (shared across team) | ✅ Checked in |
| **CLAUDE.local.md** | Local environment rules and overrides | ❌ NOT checked in |

**Quick Dev Commands:**
- Restart after code change: `echo "R" | ./docker-system/docker-menu.sh`
- Server entry point: `fastmcp.server.mcp_entry_point`
- Docker menu rebuild: `./docker-system/docker-menu.sh` → option R
- Run tests: `./scripts/test-menu.sh` or `python scripts/run-tests.py`
- Database schema verification: `python scripts/verify_init_schema.py`

**Critical Principles:**
- Keycloak is source of truth for user authentication
- ORM model is source of truth (update DB to match ORM, not reverse)
- Frontend type declarations → consolidate to `agenthub-frontend/src/types`
- Development phase = break anything that needs breaking (no legacy users)

---

## 🚨 AGENTHUB-SPECIFIC: Test Fixing Priority

**ORM Locations:**
- **ORM Models**: `agenthub_main/src/fastmcp/task_management/domain/entities/*.py`
- **Tests**: `agenthub_main/src/tests/`
- **Rule**: ORM entity definitions = SOURCE OF TRUTH

**Common Test Scenarios:**
1. **Character Limits** → Check ORM model's `max_length` field (e.g., Task.py: max_description_length=2000)
2. **UUID Validation** → Check `domain/value_objects` for UUID rules
3. **Context Hierarchy** → Check `domain/entities` for inheritance rules
4. **Agent Assignment** → Check minimum agent requirements in domain

**Remember**: We're in DEVELOPMENT phase - break anything, make clean changes, no migration concerns. When in doubt: **ORM model > test assertions**

---

## 📋 TEST FIXING PRIORITY - SOURCE OF TRUTH HIERARCHY

```
1. PROMPT INPUT (User requirements) ↓
2. ORM MODEL (Domain definitions) ↓
3. DATABASE (Actual structure) ↓
4. TESTS (Verify behavior) ↓
5. CODE (Implementation)
```

**When Test Fails - Decision Process**:
1. Check ORM model definition (e.g., `max_length=2000`)
2. If code doesn't match ORM → Fix code to match ORM model
3. If test doesn't match ORM → Update test to match ORM model
4. Never add compatibility code to support both old and new
5. Make clean breaks - change directly, no transition period

### Decision Tree:
```
┌─────────────────────┐
│   Test Failed?      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Check ORM Model Definition       │
│ (e.g., max_length=2000)         │
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ Does Code Match ORM Model?       │
└────┬─────────────────────┬───────┘
     │ NO                  │ YES
     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐
│ FIX THE CODE    │  │ FIX THE TEST    │
│ to match ORM    │  │ to match ORM    │
└─────────────────┘  └─────────────────┘
```

### CORRECT Test Fixing Examples:

#### ❌ WRONG - Changing test to match broken code:
```python
# Test expects 1000 char limit (per original spec)
with pytest.raises(ValueError, match="cannot exceed 1000"):
    # Developer wrongly changes to 2000 to make test pass
    # THIS IS BACKWARD COMPATIBILITY - DON'T DO THIS!
```

#### ✅ RIGHT - Fixing code to match ORM model:
```python
# 1. Check ORM model: max_length=2000
# 2. Fix code validation to match: if len(text) > 2000
# 3. Update test to match ORM: "cannot exceed 2000"
# Test now correctly validates against ORM model
```

---

## 🏗️ System Architecture

### Project Structure
| Path | Purpose | Port |
|------|---------|------|
| `agenthub-frontend/` | React/TypeScript frontend | 3800 |
| `agenthub_main/src/` | Python/FastMCP/DDD backend | 8000 |
| `agenthub_main/src/tests/` | Test files (unit, integration, e2e, performance) | - |
| `00_RESOURCES/*` | Reference materials only (IGNORE) | - |
| `00_RULES/*` | Legacy rules (use CLAUDE.md instead) | - |

### 4-Tier Context Hierarchy
```
GLOBAL (per-user) → PROJECT → BRANCH → TASK
```
- Each level inherits from parent | UUID-based identification | Auto-creation on demand | Multi-tenant isolation

### Tech Stack
| Component | Technology | Details |
|-----------|-----------|---------|
| **Backend** | Python, FastMCP, SQLAlchemy | DDD patterns (Domain/Application/Infrastructure/Interface layers) |
| **Frontend** | React, TypeScript, Tailwind CSS | Vite build, shadcn/ui components |
| **Database** | PostgreSQL (dev), SQLite fallback | Path: `/data/agenthub.db` (Docker volume) |
| **Auth** | Keycloak + JWT tokens | Source of truth for user identity |
| **Container** | Docker + docker-compose | PostgreSQL Local (recommended for dev) |
| **MCP** | 15+ tool categories | 32 specialized agents |

### Local URLs & Paths
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3800
- **Database**: `/data/agenthub.db` (Docker volume)
- **Documentation**: `ai_docs/`
- **Environment**: `.env` file in project root
- **Docker Menu**: `docker-system/docker-menu.sh`

### Security Guidelines
- **Authentication**: Keycloak is source of truth for all user identity
- **Credentials**: NEVER expose passwords - all in `.env` file only
- **Token Handling**: JWT tokens expire and refresh automatically
- **Multi-tenant**: Each user's data completely isolated
- **Audit Trails**: All operations logged for compliance

---

## 📚 Documentation Architecture

### Core Principle
> **AI documentation should be curated, not cluttered.** Every document must provide clear value - teaching architecture, solving problems, or guiding decisions. Anything else degrades AI performance.

### ai_docs Structure (17 Standard Folders)
```
ai_docs/
├── _absolute_docs/          # File-specific docs (marks importance)
├── _obsolete_docs/          # Auto-archived when source deleted
├── index.json               # Auto-generated index (by hooks)
├── api-integration/         # API docs
├── authentication/          # Auth system docs
├── claude-code/             # Claude Code specific
├── context-system/          # Context management
├── core-architecture/       # System architecture
├── development-guides/      # Developer resources
├── issues/                  # Issue tracking
├── keycloak/                # Keycloak integration
├── migration-guides/        # Version migrations
├── operations/              # Deployment & config
├── reports-status/          # Status reports
├── setup-guides/            # Setup instructions
├── testing-qa/              # Testing docs
└── troubleshooting-guides/  # Problem resolution
```

### Key Features for AI Agents

**1. Fast Context Access**
- **index.json**: Machine-readable index with metadata, hashes, timestamps
- **Automatic updates**: Hooks update index.json when docs change
- **Quick lookup**: Find relevant documentation via index

**2. Selective Documentation Enforcement**
- **_absolute_docs pattern**: `ai_docs/_absolute_docs/path/to/file.ext.md` documents `/path/to/file.ext`
- **Smart blocking**: Only blocks modifications if documentation exists
- **Session tracking**: 2-hour sessions prevent workflow disruption
- **f_index.md**: Mark entire folders as important

**3. Automatic Management**
- **Post-tool hook**: Updates index.json after ai_docs changes
- **Obsolete tracking**: Moves docs to _obsolete_docs when source deleted
- **Warning system**: Non-blocking warnings for missing documentation

### Documentation Rules

| Rule | Description |
|------|-------------|
| **Test files** | Must be in `agenthub_main/src/tests/` only |
| **Document files** | Must be in `ai_docs/` (except 5 allowed root files) |
| **Kebab-case folders** | All ai_docs subfolders use lowercase-with-dashes |
| **Root .md files** | ONLY 5 allowed: README.md, CHANGELOG.md, TEST-CHANGELOG.md, CLAUDE.md, CLAUDE.local.md |
| **Index files** | Auto-generated index.json (not index.md) |

---

## 🔒 Essential Rules & File System Protection

### Changelog Updates (CRITICAL)
**MANDATORY**: AI agents MUST update CHANGELOG.md when making ANY project changes
- Add new features → `### Added`
- Document fixes → `### Fixed`
- Breaking changes → `### Changed`
- Follow [Keep a Changelog](https://keepachangelog.com/) format
- Include file paths modified/created
- Describe impact and testing performed

**CHANGELOG LOCATION RULES**:
- **Root CHANGELOG.md**: Project-wide changes (`/home/daihu/__projects__/4genthub/CHANGELOG.md`)
- **Frontend CHANGELOG.md**: Frontend-only changes (`agenthub-frontend/CHANGELOG.md`)
- **NEVER** create CHANGELOG.md in other subdirectories
- **NEVER** add changelog entries to CLAUDE.local.md

### Context Management
- Use `manage_context` (unified context operations with delegation/inheritance)
- ~~`manage_hierarchical_context`~~ is deprecated
- Always use `git_branch_id` (UUID), not branch names

### Database Modes
- **Docker/Local Dev**: Docker database (`/data/agenthub.db`)
- **Test Mode**: Isolated test database (`agenthub_test.db`)
- **Rebuild**: Required to view code changes in container

### File System Protection (Auto-Enforced by Hooks)

#### Root Directory Restrictions
- **NO file creation in root** (except files in `.allowed_root_files`)
- **NO folder creation in root** (all folders should already exist)
- **Allowed root files**: README.md, CHANGELOG.md, TEST-CHANGELOG.md, CLAUDE.md, CLAUDE.local.md

#### File Type Restrictions
| File Type | Allowed Location | Notes |
|-----------|-----------------|-------|
| **.md files** | `ai_docs/` | Except 5 allowed root files |
| **Test files** | Directories in `.valid_test_paths` | `agenthub_main/src/tests/` |
| **.sh scripts** | `scripts/` or `docker-system/` | No scripts in root |
| **.venv** | `agenthub_main/.venv` | Only ONE .venv allowed |
| **logs/** | Project root | Only ONE logs folder |
| **.env* files** | Cannot be read/created | Security protection |

#### ai_docs Folder Rules
- **Kebab-case required**: lowercase-with-dashes (e.g., `api-integration`, `setup-guides`)
- **Exempt folders**: `_absolute_docs`, `_obsolete_docs` (can use underscores)
- **NO uppercase folders** (except legacy being migrated)

### Hook System Files (Auto-Enforcement)
Located in `.claude/hooks/`:
- **pre_tool_use.py**: Enforces file system protection rules
- **post_tool_use.py**: Updates documentation index
- **utils/session_tracker.py**: Manages 2-hour work sessions
- **utils/docs_indexer.py**: Generates/maintains index.json
- **utils/env_loader.py**: Loads environment variables safely
- **status_lines/status_line.py**: Displays environment paths

### Configuration Files
- **.allowed_root_files**: Files allowed in project root
- **.valid_test_paths**: Directories where test files can be created

---

## 💻 Git Commit Guidelines

Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/):

**Format**: `<type>[optional scope]: <description>`

| Type | Purpose | Example |
|------|---------|---------|
| `feat:` | New feature | `feat(auth): add JWT token validation` |
| `fix:` | Bug fix | `fix(ui): resolve login form validation error` |
| `ai_docs:` | Documentation | `ai_docs: update API documentation` |
| `style:` | Code style | `style(frontend): format components` |
| `refactor:` | Code refactoring | `refactor(backend): simplify auth flow` |
| `test:` | Tests | `test: add unit tests for context management` |
| `chore:` | Maintenance | `chore: update dependencies` |

---

## 🎯 AI Workflow Best Practices

### MANDATORY Behaviors
1. ✅ **UPDATE CHANGELOG.md** for ALL project changes (NOT CLAUDE.local.md)
2. ✅ **CHECK ai_docs/index.json** for existing documentation before creating
3. ✅ **FOLLOW DDD patterns** in codebase
4. ✅ **TEST code examples** before documenting
5. ✅ **USE existing libraries** - check package.json/requirements first
6. ✅ **FOLLOW existing conventions** and patterns
7. ✅ **UPDATE TEST-CHANGELOG.md** when modifying test files

### NEVER Do
- ❌ Create files unless absolutely necessary
- ❌ Create test files, scripts, or documents in project root
- ❌ Proactively create documentation (only when requested)
- ❌ Add backward/legacy code (ALWAYS clean code)
- ❌ Add changelog entries to CLAUDE.local.md

### Quick Reference Commands
```bash
# Update documentation index manually
python .claude/hooks/utils/docs_indexer.py

# Check allowed root files
cat .allowed_root_files

# Check valid test paths
cat .valid_test_paths

# View documentation structure
ls -la ai_docs/_absolute_docs/
ls -la ai_docs/_obsolete_docs/

# Docker rebuild after code changes
echo "R" | ./docker-system/docker-menu.sh
```

---

## 📋 System Behaviors & Gotchas
- **Boolean parameters**: Accept "true", "1", "yes", "on"
- **Array parameters**: Accept JSON strings, comma-separated, or arrays
- **Task completion**: Auto-creates context if missing (working as designed)
- **Docker restart**: Required to view code changes in dev mode
- **PostgreSQL**: Must be running for dev environment
- **Tests**: Run before committing (use appropriate test category)

---

## 🗄️ Database Schema Management

**Schema File**: `agenthub_main/src/fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql`

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/verify_init_schema.py` | Verify SQL file matches database (tables + columns) | After database changes or ORM updates |
| `scripts/deep_verify_schema.py` | Deep verification (types, constraints, FKs) | Before production deployment |
| `scripts/check_fk_cascade.py` | Check foreign key CASCADE behavior | Verify architectural compliance |
| `scripts/generate_schema_sql.py` | Regenerate SQL from actual database | After ORM model changes |

**Quick Commands**:
```bash
# Verify schema matches database
python scripts/verify_init_schema.py

# Deep verification with types/constraints
python scripts/deep_verify_schema.py

# Regenerate SQL file from current database
python scripts/generate_schema_sql.py
```

**Critical Architecture Note**:
- Database uses **NO CASCADE** on all foreign keys (intentional DDD design)
- Application layer handles all cascading deletions via domain events
- Business logic stays in code, not database triggers

---

## 🔗 Additional Resources

**📘 PRIMARY SYSTEM DOCUMENTATION**: `ai_docs/core-architecture/agenthub-system-architecture.md`
- **Complete Technical Reference**: Single source of truth for entire system architecture
- **Covers**: Frontend (React/TypeScript), Backend (DDD/FastMCP), API Layer, MCP Tools, WebSocket v2.0, Auth, Database, Context Management, Real-time Sync
- **Use For**: Understanding system flow, debugging issues, implementing new features, onboarding
- **Status**: ✅ Validated 2025-11-07 | 100% comprehensive | Token-optimized

**Other Resources**:
- **Comprehensive Rules**: See CLAUDE.md for complete agent switching, MCP tasks, and delegation models
- **Vision System**: Refer to CLAUDE.md for workflow guidance and progress tracking details
- **Agent Library**: 32 specialized agents documented in CLAUDE.md
- **Troubleshooter**: Use Task tool to launch Claude Code troubleshooter agent when needed
---

## 🔧 WebSocket Protocol v2.0 - Comprehensive Fix (2025-11-07) - ✅ RESOLVED

**📄 Complete Documentation**: `ai_docs/reports-status/websocket-v2-comprehensive-fix-2025-11-07.md`

### Critical Issues Fixed

| Issue | Impact | Status |
|-------|--------|--------|
| **WebSocket crashes after first message** | CRITICAL - UI freezes, no updates | ✅ Fixed - Error handling in useRealtimeSync.ts |
| **Timestamp validation failures** | Frontend validation breaks | ✅ Fixed - Backend payloads updated |
| **Duplicate toast notifications** | UX - 2 toasts per operation | ✅ Fixed - WebSocket = single source |
| **DELETE operations don't update UI** | Cache sync broken | ✅ Fixed - Dual cache update |
| **1000+ LOC dead code** | Maintenance burden | ✅ Removed - Legacy services deleted |

### Key Files Modified
- `useRealtimeSync.ts` - Try-catch wrapper, dual cache updates, toast deduplication
- `websocket_protocol.py` - Timestamp fields (SubtaskCreatePayload, SubtaskUpdatePayload, SubtaskCompletePayload)
- `subtask_application_facade.py` - Payload construction (lines 341-350, 466-475, 802-812)
- `LazySubtaskListRefactored.tsx` - Removed duplicate toasts, cleaned debug logs
- `LazyTaskListRefactored.tsx` - Removed component-level success toasts

### Testing Verified
- TDD Tests: 7 comprehensive tests (all PASS)
- Manual Workflow: CREATE → UPDATE → COMPLETE → DELETE (all working)
- Animation Timing: CREATE 500ms, UPDATE/DELETE 150ms (WebSocketAnimationService.ts:261-366)

---

##  Key Learning:
When modifying Python backend code, always restart the backend process to load changes.
Python caches imported modules in memory, so file edits alone aren't sufficient—the process must be killed and restarted to pick up new code.
