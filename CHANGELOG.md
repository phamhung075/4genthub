# Changelog

All notable changes to the agenthub AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Removed

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

### Changed

**AI Documentation Consolidation** (2025-11-09)

**Claude Code Folder** (Phase 1)
- Consolidated 11 files (4,114 lines) → 2 files (763 lines) = 81.5% reduction
- Applied token economy principles: tables over prose, pattern statements, consolidated redundancy
- Created:
  - `hooks-complete-guide.md` (401 lines) - All hook system documentation
  - `tools-and-mcp-reference.md` (362 lines) - Complete tools + MCP reference
- Removed (safe-rm to .obsolete):
  - 8 hook/*.md files: system-guide, reference, logging-architecture, architecture-analysis, logging-structure, message-flow-analysis, dependency-map
  - `tools_list.md`, `hooks-mcp-query-guide.md`
- Files: `.claude/ai_docs/claude-code/hooks-complete-guide.md`, `.claude/ai_docs/claude-code/tools-and-mcp-reference.md`

**API Behavior Folder** (Phase 2, Folder 1/11)
- Consolidated 3 files (476 lines) → 1 file (246 lines) = 48.3% reduction
- Created `api-parameter-handling-complete.md` with quick reference tables, consolidated JSON parsing, boolean/integer coercion
- Removed (safe-rm to .obsolete): `json-parameter-parsing.md`, `parameter-type-conversion-verification.md`, `parameter-type-validation.md`
- Updated `ai_docs/index.json` to reflect consolidation
- File: `ai_docs/api-behavior/api-parameter-handling-complete.md`

**Testing-QA Folder** (Phase 2, Folder 2/11)
- Consolidated 31 files (17,669 lines) → 3 files (887 lines) = 95.0% reduction
- Created:
  - `mcp-tools-validation-complete.md` (235 lines) - All MCP validation reports with historical summary
  - `qa-strategy-planning-complete.md` (283 lines) - Coverage strategies, wave execution plans, improvement roadmap
  - `contract-integration-complete.md` (369 lines) - Layer-to-layer contracts, type comparison matrix, integration coverage
- Removed (safe-rm to .obsolete): 31 dated reports, strategic plans, validation reports, coverage analyses
- Token economy applied: Dated reports → summary tables, redundant content consolidated, pattern statements
- Files: `ai_docs/testing-qa/*-complete.md`

**Setup-Guides Folder** (Phase 2, Folder 3/11)
- Consolidated 6 files (1,418 lines) → 1 file (569 lines) = 59.9% reduction
- Created `complete-setup-guide.md` covering PostgreSQL, Keycloak, email verification, database UI, branch setup
- Removed (safe-rm to .obsolete): `BRANCH_SETUP.md`, `DATABASE_UI_GUIDE.md`, `POSTGRESQL_KEYCLOAK_PRODUCTION.md`, `index.md`, `keycloak-authentication-setup.md`, `keycloak-email-verification-setup.md`
- Unified all setup procedures with quick reference table, troubleshooting, production deployment
- File: `ai_docs/setup-guides/complete-setup-guide.md`

**Authentication Folder** (Phase 2, Folder 4/11)
- Consolidated 12 files (4,695 lines) → 1 file (597 lines) = 87.3% reduction
- Created `complete-authentication-guide.md` covering Keycloak setup, JWT validation, token flow, security, RBAC
- Removed (safe-rm to .obsolete): 12 authentication files including Keycloak setup guides, token security, PostgreSQL integration, service account setup
- Unified auth architecture with flow diagrams, token validation, security best practices, production hardening
- File: `ai_docs/authentication/complete-authentication-guide.md`

**Troubleshooting-Guides Folder** (Phase 2, Folder 5/11)
- Consolidated 14 files (4,662 lines) → 1 file (645 lines) = 86.2% reduction
- Created `complete-troubleshooting-guide.md` with quick diagnostic reference, database/Docker/MCP/WebSocket issues, production deployment troubleshooting
- Removed (safe-rm to .obsolete): 14 troubleshooting files covering database locks, Docker volumes, MCP connection, subtask rendering, label timestamps, production deployment
- Unified with diagnostic commands, emergency procedures, backup/restore guides
- File: `ai_docs/troubleshooting-guides/complete-troubleshooting-guide.md`

**Operations Folder** (Phase 2, Folder 6/11)
- Consolidated 17 files (6,634 lines) → 1 file (706 lines) = 89.4% reduction
- Created `complete-operations-guide.md` covering production deployment (CI/CD, security, rollback), Docker deployment (SSL configs, CapRover, managed PostgreSQL), database migrations (Alembic, SQL, reset), monitoring (metrics, dashboards), performance tuning (PostgreSQL, caching), and Keycloak setup
- Removed (safe-rm to .obsolete): 17 operations files including deployment guides, Docker SSL configurations, migration workflows, monitoring setup, performance optimization, Keycloak integration
- Unified with quick reference commands, environment validation, troubleshooting, emergency procedures
- File: `ai_docs/operations/complete-operations-guide.md`

**API-Integration Folder** (Phase 2, Folder 7/11)
- Consolidated 24 files (13,421 lines) → 2 files (1,010 lines) = 92.5% reduction
- Created:
  - `mcp-tools-api-complete.md` (520 lines) - All 10 MCP tool APIs with parameters, examples, responses: manage_task (30+ params), manage_subtask (progress tracking), manage_project, manage_git_branch, manage_context (4-tier hierarchy), manage_agent, call_agent, manage_connection
  - `mcp-client-integration-complete.md` (490 lines) - Client architecture (TokenManager, RateLimiter, HTTP clients), data contracts, configuration, troubleshooting, label operations, token tracking
- Removed (safe-rm to .obsolete): 24 API integration files (14 main + 10 controllers/) including MCP server architecture, API references, configuration guides, client documentation, controller APIs
- Unified with quick reference tables, parameter validation rules, error handling patterns, advanced features
- Files: `ai_docs/api-integration/mcp-tools-api-complete.md`, `ai_docs/api-integration/mcp-client-integration-complete.md`

**Development-Guides Folder** (Phase 2, Folder 8/11)
- Consolidated 36 files (15,067 lines) → 3 files (1,928 lines) = 87.2% reduction
- Created:
  - `ddd-architecture-complete.md` (607 lines) - Domain layer (entities, value objects, domain services, events), Application layer (facades, use cases, DTOs), Infrastructure layer (repositories, database), Interface layer (MCP controllers), MRO conflict resolution, common patterns
  - `development-workflow-complete.md` (536 lines) - 3-phase professional workflow (Plan → Execute → Review), delegation models (cclaude async, cclaude-wait sync, cclaude-wait-parallel, agent switching), MCP task creation best practices, workflow decision tree
  - `development-infrastructure-complete.md` (785 lines) - Test system (TDD, fixtures, assertions, pytest marks), Docker development (menu system, build configs, hot reload), error handling & logging (exception hierarchy, structured logging, January 2025 fixes), HMR debugging (Vite plugin, WebSocket monitoring), frontend UX patterns (toasts, optimistic updates, error recovery)
- Removed (safe-rm to .obsolete): 36 development guide files including DDD schema, repository architecture, workflow guides, delegation models, Docker system guide, domain events, error handling, event handlers, frontend UX, HMR debugging, test organization, MCP integration, JWT auth, token management, parallel execution, implementation phases
- Unified with quick reference tables, testing patterns, Docker configurations, logging best practices, performance monitoring
- Files: `ai_docs/development-guides/ddd-architecture-complete.md`, `ai_docs/development-guides/development-workflow-complete.md`, `ai_docs/development-guides/development-infrastructure-complete.md`

**UI Patterns Documentation** (Phase 2, Folder 8/11 - Addendum)
- Rewrote `toast-notification-architecture.md` (663 → 381 lines) = 42.5% reduction
- **Documented actual implementation** (not deprecated architecture):
  - Removed references to non-existent `toastEventBus`, `NotificationService`, `WebSocketToastBridge`
  - Documented current architecture: WebSocket v2.0 → `useRealtimeSync` (global dedup) → Toast hooks → Context → UI
  - Key insight: **Components use error toasts only** - WebSocket handles all success notifications (prevents duplicates)
- Applied token economy: Tables over prose (toast types, entity actions, troubleshooting), flow diagrams → sequential text, consolidated deduplication (2s global window in `useRealtimeSync.ts:17-65`)
- File: `ai_docs/development-guides/ui-patterns/toast-notification-architecture.md`

**Architecture-Design Folder** (Phase 2, Folder 9/11)
- Consolidated 2 files (2,023 lines) → 1 file (557 lines) = 72.5% reduction
- Created `product-architecture-complete.md` covering product vision (PRD, user personas, feature requirements), technical architecture (DDD layers, bounded contexts, tech stack), system design (high-level components, layered architecture), frontend/backend architecture, deployment tiers (MVP → Enterprise), security architecture, release roadmap
- Removed (safe-rm to .obsolete): Architecture_Technique.md, PRD.md
- Unified strategic and technical documentation with quick reference tables, scaling tiers, technology stack matrices
- File: `ai_docs/architecture-design/product-architecture-complete.md`

### Fixed

**Session Directory Consolidation** (2025-11-09)
- Fixed fragmented `.claude/data/sessions` directories (14+ locations throughout project)
- Root cause: Hooks used relative paths, creating directories wherever executed
- Solution: Updated to use absolute paths via `get_project_root()` from `utils.env_loader`
- All session data now consolidated to single location: `{project_root}/.claude/data/sessions/`
- Benefits: Consistent session state, hooks can access each other's data, no more scattered directories
- Files: `.claude/hooks/user_prompt_submit.py:411,414`, `.claude/hooks/status_lines/status_line_mcp.py:363`
- **Additional fixes**: Agent context manager and session_start fallback now use absolute paths
  - `.claude/hooks/utils/agent_context_manager.py:20-21` - Runtime context file path
  - `.claude/hooks/session_start.py:2334-2336` - Logs directory fallback path

**GitHub Actions Pipeline** (2025-11-09)
- Updated Python 3.11 → 3.14, replaced Black/isort/flake8 with Ruff (10-100x faster)
- Fixed dependency installation to use `pyproject.toml` instead of missing `requirements.txt`
- Pipeline now passes Code Quality and Test Suite stages
- Files: `.github/workflows/production-deployment.yml:34,88-108,149-154`

**Production Bulk Agent Creation** (2025-11-08)
- Fixed "Create All" button crash (`TypeError: ae is not a function`)
- Root cause: Missing `bulkCreateInstances` export in `useUserAgentInstances` hook
- Files: `src/hooks/useAgentManagement.ts:83,129-149,220,225-233`

**TypeScript Type System** (2025-11-08)
- Eliminated all `as any` casts with proper API contract types
- Created 7 new types: `ApiCreateInstanceInput`, `ApiUpdateInstanceInput`, `ApiInstanceResponse`, `ApiBulkCreateResponse`, `ApiDeleteResponse`, `ToApiInput<T>`, `toApiInput()`
- Fixed `null` vs `undefined` mismatch between frontend and backend
- Benefits: Compile-time safety, full IDE autocomplete, zero type errors
- Files: `src/types/agentTypes.ts:326-425`, `src/services/apiV2.ts:64,987-1075`, `src/hooks/useAgentManagement.ts`, `src/pages/MyAgentsPage.tsx`

**Docker Build** (2025-11-08)
- Added missing `rollup-plugin-visualizer` to `package.json` devDependencies
- Resolves build failure at `pnpm run build` step

**Database Schema** (2025-11-08)
- Fixed `task_labels` composite key (duplicate PRIMARY KEY declarations)
- Fixed `task_dependencies` sequence lifecycle (created before DROP CASCADE)
- All 27 tables now initialize successfully
- File: `init_schema_postgresql.sql:54-56,358-366`

**WebSocket Animations** (2025-11-07)
- Fixed UPDATE operations not triggering animations (race condition: React Query's synchronous `setQueryData` vs async animations)
- Solution: Delayed cache updates (150ms) for UPDATE, matching DELETE pattern
- Files: `useRealtimeSync.ts:576-597,763-811,135-176,398-424`

**WebSocket Subtask Sync** (2025-11-07)

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| 22.22% validation failures | Schema mismatch (timestamps) | Aligned TypeScript types with backend |
| 4× duplicate toasts | Per-hook deduplication | Global toast deduplication map |
| Automatic task update spam | No filtering of system events | Filter `metadata.source === 'system'` |
| Create delays/queuing | `invalidateQueries()` blocking | Removed (WebSocket handles updates) |

- Files: `websocket-protocol.ts:125,135-136,152-153`, `useRealtimeSync.ts:17-19,40-65,145-156,327-332`

**WebSocket Delete Operations** (2025-11-06)
- Backend: `sync_broadcast_project_event()` safety net (ensures completion)
- Frontend: Delayed cache update (600ms) + immediate toast, time-based deduplication (2s window)
- Applied to all entity types: Project, Branch, Task, Subtask
- Files: `project_management_service.py:354-368`, `git_branch_service.py:199-212`, `useRealtimeSync.ts:29-57,276-325`

**WebSocket Protocol v2.0** (2025-11-06)
- Type-safe communication: TypeScript interfaces + Python Pydantic models
- Benefits: Compile-time + runtime validation, self-documenting, IDE autocomplete
- Files: `websocket-protocol.ts` (395 lines), `websocket_protocol.py` (450 lines)
- Docs: `ai_docs/core-architecture/websocket-protocol-migration-guide.md`

**Agent Management** (2025-11-05)
- Fixed read-only validation (AttributeError on private agent edits)
- Fixed non-UUID user ID support (dev environment JWT tokens)
- Files: `agent_management_facade.py:346-353`, `agent_management_routes.py:430,469-474,927-937`

**Test Infrastructure** (2025-11-05)
- Created `__mocks__` directory with `AnimationFactory.ts`, deletion trackers
- Reduced uncaught exceptions 19 → 4 (79% reduction)
- Updated `setupTests.ts` for global service mocking

**Agent Name Display** (2025-11-03)
- Fixed session start hook showing "Agent: unknown"
- Changed field reference from `name` to `agent_name` in `simple_formatter.py:86`

**Claude Hooks** (2025-11-03)
- Updated path references: `scripts/claude-hooks` → `.claude/hooks`
- Fixed `_find_project_root()` traversal logic

### Removed

**Project-Wide Cleanup - Phase 4** (2025-11-09)
- Removed 7 obsolete files from project root directory:
  - 3 hook test files: `not_allowed_test.txt`, `should_be_blocked.txt`, `test_blocking.txt`
  - 2 debug scripts: `debug_context_injector.py`, `toggle_auth.py`
  - 2 old test scripts: `loop-worker_testfix.sh`, `check_tests.sh`
- Verified frontend and scripts directories clean (no obsolete files found)
- **Total cleanup**: 43 obsolete files removed across all phases

**Backend Cleanup - Phase 3** (2025-11-09)
- Removed 27 obsolete files from `agenthub_main` root directory:
  - 6 shell scripts: `start_mcp_server.sh`, `start_mcp_stdio.sh`, `configure_claude_code.sh`, `run_tests_fast.sh`, `fast_test_commands.sh`, `test_coverage_quick.sh`
  - 4 one-time fix scripts: `fix_imports.py`, `fix_imports_v2.py`, `fix_timezone_imports.py`, `fix_value_object_imports.py`
  - 8 test result files: `architecture_test_report.txt`, `full_test_results.txt`, `phase1_analysis.txt`, `test_output.txt`, `test_results*.txt`
  - 3 utility scripts: `add_priority_import.py`, `debug_uuid_conversion.py`, `test_batch_checker.py`
  - 4 coverage files: `coverage.json`, `coverage_final.json`, `full_coverage.json`, `session_coverage.json`
  - 2 error files: `=0.10.2`, `=1.2.2`
- Server now started exclusively via docker menu: `python -m fastmcp.server.mcp_entry_point`
- Kept: `init_database.py`, `run_tests.py`, `email_tokens.db` (actively used)

**Backend Cleanup - Phase 2** (2025-11-09)
- Removed 9 obsolete files from `agenthub_main/src`:
  - 4 `.obsolete` test files (already marked for removal)
  - 5 auth migration files superseded by `auto_migration.py`
- Migration files removed:
  - `fastmcp/auth/infrastructure/migrations/001_create_auth_tables.py`
  - `fastmcp/auth/infrastructure/migrations/002_create_email_tokens_table.py`
  - `fastmcp/auth/infrastructure/migrations/migrator.py`
  - `fastmcp/auth/infrastructure/migrations/__init__.py`
  - `fastmcp/auth/migrations/update_api_tokens_to_orm.py`
- **Note**: Supabase auth files retained - part of active DualAuthMiddleware system

**Backend Cleanup** (2025-11-09)
- Removed 410+ lines of legacy code:
  - `mcp_bridge.py` (248 lines) - Replaced by HTTP FastMCP
  - `verify_user_id_fix.py` (145 lines) - One-time verification script
  - `mock_supabase.py` (17 lines) - Replaced by inline mock
  - `tests/hooks/` - 16 legacy hook test files
  - `examples/` - Empty directory

**Dead Code Cleanup** (2025-11-08)
- Migrations: 18 files superseded by `auto_migration.py` + `init_schema_postgresql.sql`
- Obsolete files: 10 `.obsolete`, `.backup`, `.old` files
- Obsolete tests: 5 test files using deleted services
- Analysis scripts: 30 one-time use diagnostic/benchmark scripts
- WebSocket services: 4 legacy services (~200 lines, ~8KB)
  - `changePoolService`, `toastEventBus`, `WebSocketToastBridge`, `notificationService`
- Total: ~3,700+ lines removed

**Phase 2 Dead Code** (2025-11-04)
- 568 lines: Example tests, unused Keycloak integration, dead API functions, test fixtures
- Fixed duplicate `UseTaskDataOptions`/`UseTaskDataReturn`
- Impact: Single-source-of-truth enforcement, zero breaking changes

**Token Optimization** (2025-11-03)
- Removed EnrichmentService (566 lines, 500-800 tokens per operation)
- Removed hint system infrastructure (1,864 lines, 4,500-7,000 tokens per session)
- Visual indicators: Frontend computes status emojis, progress bars (620-980 tokens saved)

### Added

**Database Schema Tools** (2025-11-08)
- Verification: `verify_init_schema.py`, `deep_verify_schema.py`, `check_fk_cascade.py`
- Generation: `generate_schema_sql.py` - Auto-generate SQL from database
- Inspection: `inspect_database.py`, `compare_schema.py`
- Documentation: Added section to `CLAUDE.local.md`

**MCP WebSocket Polling** (2025-11-07)
- Type-safe polling scripts with Pydantic validation
- Files: `poll_mcp_websocket.py` (single), `poll_mcp_websocket_parallel.py` (parallel)
- Features: Validation against payloads, color-coded output, debug mode, graceful degradation

**System Architecture Docs** (2025-11-07)
- Single source of truth: `ai_docs/core-architecture/agenthub-system-architecture.md` (38KB, ~1500 lines)
- Coverage: Frontend, Backend (DDD/FastMCP), API, MCP, WebSocket v2.0, Auth, Database, Context
- Moved 50+ obsolete docs to `ai_docs/_obsolete_docs/`

**Agent Import System** (2025-11-05)
- Public shared reference model: Imported agents remain public with unique share tokens
- New fields: `is_imported`, `original_creator_id`, `is_read_only`
- Original creator retains edit rights; importers read-only
- Files: `agent_sharing_service.py:188-215`, `agent_management_routes.py:424-436`

**Parallel Execution** (2025-11-04)
- `cclaude-wait-parallel`: WebSocket multiplexer for parallel subtask monitoring
- Features: True parallel execution, live progress table, aggregated JSON results
- Performance: 67% time savings (3×60s tasks: 180s → 60s)
- Docs: `ai_docs/development-guides/cclaude-wait-parallel-guide.md`

**Changelog Skills** (2025-11-03)
- `changelog-updater` skill: 4 files (905 lines, ~14KB)
- SKILL.md (format), EXAMPLES.md (real-world), TEMPLATES.md (copy-paste), VALIDATION.md (quality)
- Auto-discovery when "update changelog" mentioned

**Agent Management System**
- 33 specialized agents (coding, testing, docs, DevOps, security, ML, architecture)
- Agent switching: `call_agent()` loads instructions + transforms role
- Token savings: ~1,200 tokens (70% reduction vs delegation ~4,000 tokens)

**CLI Tools**
- `cclaude` (async): Non-blocking, parallel execution
- `cclaude-wait` (sync): Blocking + JSON results
- `cclaude-wait-parallel`: Parallel subtasks with live progress
- All support task_id and subtask_id delegation

**Documentation System**
- 17 standard folders (kebab-case enforced)
- Auto-generated `index.json` (metadata, hashes, timestamps)
- `_absolute_docs` pattern for file-specific documentation
- `_obsolete_docs` for auto-archival

### Changed

**CHANGELOG Optimization** (2025-11-03)
- Consolidated Unreleased: 331 lines (271KB, ~42k tokens) → 170 lines (6.8KB, ~1k tokens)
- 48.6% fewer lines, 97.5% smaller file, 100% essential information preserved

**MCP Response Optimizations** (2025-11-03)

| Optimization | Savings | Details |
|--------------|---------|---------|
| Minimal search/list results | 96% (40k → 1.5k tokens per 10 results) | 4 fields vs 20+ fields |
| Tool descriptions | 10,600 tokens | Tables, emoji removal, prose compression |
| MinimalResponseSerializer | 6,000-8,000 tokens | No input echo (70-75% per operation) |
| Visual indicators | 620-980 tokens | Frontend computes status/progress |
| Dead code prevention | 4,500-7,000 tokens | Removed hint/enrichment services |
| **TOTAL** | **21,720-26,580 tokens** | **10.9-13.3% of 200k context** |

**Agent Files Optimization** (2025-11-03)
- Rewrote 31 `.claude/agents/*.md` to minimal YAML headers
- 1,878 → 832 lines (55.7% savings, ~2,000-2,500 tokens per file)
- Format: YAML header + MCP init + minimal use case (avg 26 vs 80 lines)

**ai_docs Optimization** (2025-11-03)
- Phase 2 (Core): 4 docs, 68-78% reduction, ~16,500-18,500 tokens saved
- Phase 3 (Guides): 2 docs, 69.8% reduction (4,122→1,209 lines), ~5,800-6,500 tokens saved
- Cumulative: ~24,630-28,130 tokens per session (10-12% of 200k budget)

**Hooks System** (2025-11-03)
- Migrated: `scripts/claude-hooks/` → `.claude/hooks/`
- Updated all path references in validators, protection system, configs

**Architecture**
- ORM model = source of truth (update DB to match ORM, never reverse)
- Test hierarchy: Prompt Input → ORM → Database → Tests → Code
- No backward compatibility in dev phase (clean breaks allowed)
- Dynamic tool enforcement replaces static permissions

---

## [0.0.5] - 2025-09-26

### Added
- Frontend type system consolidation (`src/types/`)
- Documentation system (auto-indexing, `_absolute_docs` pattern)
- File system protection (root restrictions, kebab-case)

### Fixed
- Repository user ID propagation (with_user methods)
- Git branch creation (update → save)

### Changed
- Removed obsolete frontend debug scripts

---

## [0.0.4] - 2025-09-23

### Added
- Dynamic Tool Enforcement v2.0 (permissions from call_agent response)
- Agent system documentation (33 specialized agents)
- MCP task management (4-tier context hierarchy)
- AI-powered task enrichment

### Fixed
- Context system type safety

### Changed
- Major CLAUDE.md update (orchestration, session types, token economy)

---

## [0.0.3] - 2025-09-19

### Added
- Keycloak Integration (JWT auth, auto refresh, RBAC, multi-tenant)
- WebSocket real-time updates (auto-reconnection)
- Frontend performance (lazy loading, virtualization, memoization)

### Fixed
- Docker integration (configs, health checks, startup)
- Database schema (ORM alignment)

### Changed
- Test organization (unit/, integration/, e2e/, performance/)

---

## [0.0.2] - 2025-09-17

### Added
- Context management (4-tier hierarchical inheritance)
- Agent management (33 specialized agents)
- Vision system (AI task enrichment)

### Fixed
- SQLAlchemy session lifecycle
- UUID validation

### Changed
- Domain model refactoring (improved DDD)

---

## [0.0.1] - 2025-09-16

### Added
- Initial setup (FastMCP server, PostgreSQL/SQLite, React frontend)
- Core domain models (Project, Task, GitBranch, Agent, Context)
- Basic MCP tools (CRUD operations)
- Docker development environment

### Fixed
- Initial setup issues (database, env loading, Docker permissions)

---

## Project Information

**Repository**: agenthub AI Agent Orchestration Platform
**Documentation**: ai_docs/ (17 standard folders with auto-generated index.json)
**Key Principles**: Clean code (DRY, SOLID, single source of truth) | ORM = truth source | No backward compatibility in dev phase
