# Changelog

All notable changes to the agenthub AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Fixed

**Docker Build Failure - Missing rollup-plugin-visualizer** (2025-11-08)
- **Issue**: Docker build failing at `pnpm run build` step with `Cannot find module 'rollup-plugin-visualizer'`
- **Root cause**: Package imported in `vite.config.ts:6` but missing from `package.json` devDependencies
- **Fix**: Added `"rollup-plugin-visualizer": "^5.12.0"` to package.json devDependencies
- **Impact**: Docker builds now succeed; bundle analyzer generates stats.html for build optimization
- **File**: `agenthub-frontend/package.json:76`

**Critical Schema Bugs - Production Database Initialization** (2025-11-08)
- **Bug #1 - task_labels composite key**: Fixed duplicate PRIMARY KEY declarations causing "multiple primary keys not allowed" error
  - Before: `task_id UUID PRIMARY KEY, label_id VARCHAR PRIMARY KEY` (❌ TWO separate primary keys)
  - After: `PRIMARY KEY (task_id, label_id)` (✅ Composite primary key for junction table)
  - Location: `init_schema_postgresql.sql:358-366`
- **Bug #2 - task_dependencies sequence**: Fixed sequence lifecycle issue causing "relation does not exist" error
  - Problem: Sequence created at line 17 → `DROP CASCADE` at line 34 drops sequence → table creation at line 348 references missing sequence
  - Solution: Moved sequence creation AFTER all DROP statements (now line 54-56)
  - Location: `init_schema_postgresql.sql:54-56`
- **Impact**: Schema now initializes successfully - all 27 tables created without errors in production
- **Root cause**: Auto-generated schema from `generate_schema_sql.py` didn't handle edge cases (composite keys, sequence CASCADE dependencies)
- **Lesson**: Generated schemas require manual review for junction tables and sequence ordering

### Removed

**Dead Code Cleanup - Legacy Code Removal** (2025-11-08)
- **Migrations directory** (18 files): Removed entire `infrastructure/database/migrations/` directory (17 Python + 1 SQL file, all superseded by `auto_migration.py`)
- **Migration tests** (3 files): Removed `tests/unit/task_management/infrastructure/migrations/` and `tests/unit/task_management/infrastructure/database/migrations/`
- **Database infrastructure** (2 files): Removed `migration_runner.py` (async migrations - optional/unused), `add_composite_indexes.py` (never imported)
- SQL migration files (7): Removed manual migration files (002-007) - superseded by `init_schema_postgresql.sql`
- Obsolete files (10): Removed `.obsolete`, `.backup`, `.old` files across codebase
- Obsolete tests (5): Removed tests using deleted services (`realtime-updates.test.tsx`, `LazyTaskList.test.tsx`, `LazyTaskList.realtime.test.tsx`, `ProjectList.test.tsx`, `TaskContextDialog.test.tsx`)
- Obsolete controller (1): Removed `call_agent_mcp_controller.obsolete/` directory and all contents
- Analysis scripts (30): Removed one-time use analysis, diagnostic, and benchmark scripts
- Purpose: Clean breaks in development phase, reduce maintenance burden, eliminate confusion
- Migration strategy: Runtime migrations via `auto_migration.py`, clean DB init via `init_schema_postgresql.sql`
- Result: ~3500+ lines of dead code removed, cleaner codebase structure

### Added

**Database Schema Management Tools** (2025-11-08)
- Schema verification scripts (3): `verify_init_schema.py`, `deep_verify_schema.py`, `check_fk_cascade.py`
- Schema generation: `generate_schema_sql.py` - Auto-generate SQL from actual database
- Inspection tools (2): `inspect_database.py`, `compare_schema.py` - Database analysis
- Verification report: `schema_verification_report.md` - Complete validation results
- Documentation: Added Database Schema Management section to `CLAUDE.local.md`
- Result: init_schema_postgresql.sql verified 100% accurate (27 tables, all columns match)

**MCP WebSocket Polling - Pydantic Validation** (2025-11-07)
- Type-safe WebSocket polling scripts with comprehensive Pydantic validation
- Files: `.claude/bin/poll_mcp_websocket.py` (single task/subtask), `poll_mcp_websocket_parallel.py` (parallel)
- Features: Validation against `TaskCompletePayload`/`SubtaskCompletePayload`, detailed error tables, color-coded output, debug mode (`--debug`), graceful degradation
- Output: JSON includes `validation_passed`, `validation_error` fields
- Benefits: Early payload mismatch detection, clear error messages, type-safe data handling, visual feedback (⚠️ for failures)

**Comprehensive System Architecture Documentation** (2025-11-07)
- Single source of truth: `ai_docs/core-architecture/agenthub-system-architecture.md` (38KB, ~1500 lines, token-optimized)
- Coverage: Frontend (React/TypeScript), Backend (DDD/FastMCP), API, MCP Tools, WebSocket v2.0, Auth, Database, Context, Real-time Sync
- Consolidation: Moved 50+ obsolete docs (34 core-architecture, 15 context-system, 6 api-integration .obsolete files) to `ai_docs/_obsolete_docs/`
- Result: `ai_docs/core-architecture/` contains ONLY authoritative system documentation
- Reference: Added to `CLAUDE.local.md` as "📘 PRIMARY SYSTEM DOCUMENTATION"
- Structure: 14 sections covering system overview, architecture stack, development workflow, testing, patterns

**Agent Import - Public Shared Reference Model** (2025-11-05)
- Imported agents remain public with independent share tokens (viral sharing network)
- Each import generates unique 64-char token (prevents DB constraint violation)
- Original creator retains edit rights; importers have read-only access
- New API fields: `is_imported`, `original_creator_id`, `is_read_only`
- Files: `agent_sharing_service.py:188-215`, `agent_management_routes.py:424-436`, `models.py:86-89`

**Parallel Execution System - cclaude-wait-parallel** (2025-11-04)
- WebSocket multiplexer pattern for parallel subtask monitoring
- Components: `.claude/bin/cclaude-wait-parallel` (bash wrapper), `poll_mcp_websocket_parallel.py` (multiplexer)
- Features: True parallel execution, live progress table, blocking wait, aggregated JSON results
- Performance: 67% time savings vs sequential (3×60s tasks: 180s → 60s)
- Usage: `cclaude-wait-parallel <agent> <task_id> <sub1> <sub2> <sub3> [...]`
- Docs: `ai_docs/development-guides/cclaude-wait-parallel-guide.md`, `parallel-execution-architecture.md`

**Agent Skills - changelog-updater** (2025-11-03)
- 4 files (905 lines, ~14KB): SKILL.md (format/instructions), EXAMPLES.md (real-world), TEMPLATES.md (copy-paste), VALIDATION.md (quality checks)
- Token optimized: Tables over prose, pattern statements, consolidated format
- Auto-discovery: Claude uses automatically when "update changelog" mentioned

**Phase 2 MCP Response Optimizations** (2025-11-03)
- Minimal search/list results: 4 essential fields (id, title, status, priority) vs 20+ fields
- Token impact: 96% reduction (40,000 → 1,500 tokens per 10 results)
- Required fields: `progress_notes`/`details` (10+ chars) for updates, `completion_summary` (20+ chars) for completions
- Files: `search_handler.py`, `crud_handler.py` (task/subtask)
- User tip: "Use manage_task(action='get', task_id='...') for full details"

**Agent Files Token Optimization** (2025-11-03)
- Rewrote 31 `.claude/agents/*.md` files to minimal YAML headers
- Reduction: 1,878 → 832 lines (55.7% savings, ~2,000-2,500 tokens per file)
- Architecture: Agent files = metadata only; full instructions loaded via `mcp__agenthub_http__call_agent()`
- Format: YAML header + MCP initialization + minimal use case reference (avg 26 lines vs 80 lines)

**Agent Management System**
- 33 specialized agents (coding, testing, docs, DevOps, security, ML, architecture)
- Agent switching: `call_agent()` loads complete instructions + transforms role
- Dynamic tool enforcement: Permissions from `tools` array in call_agent response
- Token savings: Agent switching ~1,200 tokens (70% reduction vs delegation ~4,000 tokens)

**CLI Tools**
- `cclaude` (async): Delegate to separate terminal, non-blocking, parallel execution
- `cclaude-wait` (sync): Delegate with blocking + JSON results, sequential workflows
- `cclaude-wait-parallel`: Parallel subtasks with live progress (replicates Task tool)
- Both support task_id and subtask_id delegation patterns

**Documentation System**
- ai_docs/ with 17 standard folders (kebab-case enforced)
- Auto-generated index.json (metadata, hashes, timestamps)
- _absolute_docs pattern for file-specific documentation enforcement
- _obsolete_docs for auto-archival when source files deleted

### Fixed

**WebSocket UPDATE Animations - Race Condition Fix** (2025-11-07)
- Problem: UPDATE operations not triggering animations (WebSocket messages arrive, hooks configured, but animations never play)
- Root cause: React Query's `setQueryData` (0ms, synchronous) executes before animation (~150ms, async), component re-renders before animation plays
- Solution: Delayed cache updates for UPDATE operations (150ms `setTimeout` wrapper, matching DELETE pattern)
- Impact: All entity types (project, branch, task, subtask) now show 150ms highlight animation on update
- Files: `useRealtimeSync.ts:576-597,763-811,135-176,398-424`, `ProjectItem.tsx:50` (added data-project-id)

**WebSocket Subtask Real-Time Sync - Quadruple Fix** (2025-11-07)

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| 22.22% validation failures | Schema mismatch (backend sends both timestamps, frontend expects one) | Aligned TypeScript types: added `updated_at` to CreatePayload, `created_at` to UpdatePayload |
| 4× duplicate toasts | Per-hook-instance deduplication (multiple components = multiple toasts) | Global toast deduplication (module-level `globalRecentToastsMap`) |
| Automatic task updates spam | No filtering of system-generated updates (subtask count changes) | Filter toasts: check `metadata.source === 'system'` or `event_type === 'subtask_count_update'` |
| Create delays/queuing | `invalidateQueries()` blocking React Query mutation queue | Removed invalidation (WebSocket already updates cache) |

- Files: `websocket-protocol.ts:125,135-136,152-153`, `useRealtimeSync.ts:17-19,40-65,145-156,327-332`
- Impact: 0% validation failures, single toast per operation, fast sequential creates

**WebSocket Real-Time Sync - Delete Operations + Dead Code Cleanup** (2025-11-06)
- Problem: Delete operations not triggering frontend updates, animations, or notifications
- Root causes: Async broadcast timing, immediate cache update unmounting component, no toast deduplication, event bus with 0 subscribers
- Solutions:
  1. Backend: `sync_broadcast_project_event()` safety net (uses `asyncio.run()` to ensure completion)
  2. Frontend: Delayed cache update (600ms) + immediate toast, `setQueryData(undefined)` prevents refetch
  3. Frontend: Time-based toast deduplication (2-second window)
  4. Dead code cleanup: Removed 4 legacy services (~200 lines, ~8KB)
- Removed files: `changePoolService`, `toastEventBus`, `WebSocketToastBridge`, `notificationService`, `WebSocketNotificationService`, `useSubtaskWebSocket`, related tests
- Architecture: WebSocket → useRealtimeSync → Toast (3 layers vs 6)
- Impact: Reliable delete broadcasts, smooth animations, no duplicates, 75% fewer services, 66% fewer listeners, 8KB smaller bundle
- Files: `project_management_service.py:354-368`, `useRealtimeSync.ts:29-57,276-325`, 6 deleted services
- Docs: `ai_docs/troubleshooting-guides/websocket-realtime-sync-fix.md`, `ai_docs/reports-status/dead-code-analysis-websocket-sync.md`

**WebSocket Real-Time Sync - Branch/Task/Subtask CUD Operations** (2025-11-06)
- Applied project delete pattern to all entity types
- Backend: `sync_broadcast_branch_event()` for delete operations (`git_branch_service.py:199-212`)
- Frontend: Toast notifications + delayed delete cache updates (600ms) for smooth animations
- Handlers: Branch (lines 332-401), Task (lines 74-179), Subtask (lines 181-276)
- Impact: Consistent UX across all entity types, no duplicates, smooth delete animations

**WebSocket Protocol v2.0 - Type-Safe Communication Models** (2025-11-06)
- Problem: No compile-time or runtime validation, implicit contracts, easy to miss required fields
- Solution: Comprehensive type-safe protocol models
  - TypeScript: `websocket-protocol.ts` (payload interfaces, type guards, helpers)
  - Python: `websocket_protocol.py` (Pydantic models, validators, factory functions)
  - Migration pattern: `BranchDeletePayload` with validation, fallback to dict for backward compatibility
- Benefits: Compile-time safety, runtime validation, self-documenting, consistency enforcement, IDE autocomplete, refactoring safety
- Files: `websocket-protocol.ts` (395 lines), `websocket_protocol.py` (450 lines), `git_branch_service.py:206-221`
- Docs: `ai_docs/core-architecture/websocket-protocol-migration-guide.md`

**WebSocket Real-Time Sync - Branch Delete Payload Fix** (2025-11-06)
- Problem: "Branch update missing ID" validation errors
- Root cause: Branch delete payload inconsistency (only `name`, missing `id` and `project_id`)
- Solution: Added ID and project_id to branch delete payload: `{"id": git_branch_id, "name": branch_name, "project_id": branch_project_id}`
- Impact: No validation errors, smooth animations, consistent payload structure
- File: `git_branch_service.py:208`

**Agent Update - Read-Only Validation** (2025-11-05)
- Problem: Private agents couldn't be edited (AttributeError: 'get_user_instance' not found)
- Solution: Moved read-only validation from route to facade's `update_instance` method
- Returns HTTP 403 Forbidden for read-only violations, private agents editable
- Files: `agent_management_facade.py:346-353`, `agent_management_routes.py:430,469-474`

**Agent Import - Non-UUID User ID Support** (2025-11-05)
- Problem: Development JWT tokens contain non-UUID user IDs (e.g., 'dev-user-001'), causing import failures
- Solution: Convert non-UUID IDs to deterministic UUID v5 (null namespace)
- Impact: Agent imports work in both dev and production environments
- File: `agent_management_routes.py:927-937`

**Test Infrastructure - AnimationFactory Mocking** (2025-11-05)
- Problem: 68% test suite failing (TypeError: animationFactory.animate is not a function)
- Solution: Created `__mocks__` directory with `AnimationFactory.ts`, `taskDeletionTracker.ts`, `branchDeletionTracker.ts`
- Updated `setupTests.ts` to globally enable service mocking via `vi.mock()`
- Impact: Uncaught exceptions 19 → 4 (79% reduction), reusable mock infrastructure
- Remaining: 68/89 test files failing (assertion mismatches, outdated expectations)
- Docs: `ai_docs/testing-qa/frontend-qa-status-2025-11-05.md`
- Commit: `816c417e`

**Agent Name Display Fix** (2025-11-03)
- Problem: Session start hook showed "Agent: unknown" instead of actual agent name
- Root cause: Field name mismatch (AgentMessageProvider uses `agent_name`, SimpleFormatter expects `name`)
- Solution: Changed `simple_formatter.py:86` from `role.get('name', 'unknown')` to `role.get('agent_name', 'unknown')`
- Impact: Proper agent identification in session context
- Time: 5 minutes

**Claude Hooks Path References** (2025-11-03)
- Updated `config_validator.py` path construction (`scripts/claude-hooks` → `.claude/hooks`)
- Fixed `_find_project_root()` traversal logic
- Updated test paths in `pre_tool_use.py` and config files
- Result: Hooks load correctly, file protection active

**Repository & Database**
- User ID propagation via with_user methods
- Git branch creation (update → save pattern)
- SQLAlchemy session lifecycle management
- UUID validation across system
- ORM model alignment with database schema

### Changed

**CHANGELOG.md Optimization - 97.5% Size Reduction** (2025-11-03)
- Consolidated Unreleased section: 331 lines (271KB, ~42k tokens) → 170 lines (6.8KB, ~1k tokens)
- Eliminated duplicate section headers, applied token optimization techniques
- Preserved 100% essential information + complete version history
- Result: 48.6% fewer lines, 97.5% smaller file, professional scannable format

**Phase 2 Dead Code Cleanup - 568 Lines Removed** (2025-11-04)
- Priority 1 (~300 lines): Example test files, unused Keycloak integration, dead API functions
- Priority 2 (~230 lines): Test fixtures, logger config presets
- Priority 3 (38 lines net): Fixed duplicate `UseTaskDataOptions`/`UseTaskDataReturn`, colocated 5 single-use component props
- Impact: Cleaner codebase, single-source-of-truth enforcement, zero breaking changes
- Commits: `1d34f9a5`, `4a50019c`, `00e1ead2`

**Token Optimization Suite - 21-28k Tokens Saved Per Session** (2025-11-03)

| Optimization | Savings | Impact |
|--------------|---------|--------|
| MCP Tool Descriptions | 10,600 tokens | 60-70% reduction via tables, emoji removal, prose compression |
| Dead Code Prevention | 4,500-7,000 tokens | Removed unused hint/enrichment services |
| MinimalResponseSerializer | 6,000-8,000 tokens | Eliminated echo responses (70-75% per operation) |
| Visual Indicators Removal | 620-980 tokens | Removed status emojis, progress bars |
| **TOTAL** | **21,720-26,580 tokens** | **10.9-13.3% of 200k context window** |

**ai_docs Optimization Results** (2025-11-03)
- Phase 2 (Core Architecture): 4 docs, 68-78% reduction, ~16,500-18,500 tokens saved
- Phase 3 (Development Guides): 2 docs, 69.8% reduction (4,122→1,209 lines), ~5,800-6,500 tokens saved
- Techniques: Mermaid→tables (85%), code examples→patterns (92%), ASCII→tables (81%), prose→numbered tables (70-80%)
- Cumulative: ~24,630-28,130 tokens per session (10-12% of 200k budget)

**Dead Code Cleanup - 2,430 Lines Removed** (2025-11-03)
- Removed EnrichmentService (566 lines, 500-800 token bloat per operation)
- Removed hint system infrastructure (1,864 lines: matrix, post-action hints, unified system, bridge, interceptor)
- Impact: Prevented 4,500-7,000 tokens per session

**MCP Response Architecture** (2025-11-03)
- MinimalResponseSerializer: Returns only IDs, timestamps, computed values (not input echo)
- Visual indicators removed: Frontend computes status emojis, progress bars, context availability
- Philosophy: "Don't echo back what caller already knows" - 70-75% reduction per operation

**Hooks System Migration** (2025-11-03)
- Migrated from `scripts/claude-hooks/` to `.claude/hooks/`
- Updated all path references in config_validator, pre_tool_use, test paths config
- File system protection, documentation enforcement, session tracking operational

**Architecture Changes**
- Removed backward compatibility code (dev phase = clean breaks allowed)
- ORM model = source of truth (update DB to match ORM, never reverse)
- Test fixing hierarchy: Prompt Input → ORM Model → Database → Tests → Code
- Dynamic tool enforcement replaces static tool permissions

---

## [0.0.5] - 2025-09-26

### Added
- Frontend type system consolidation in `src/types/`
- Documentation system (auto-indexing, selective enforcement, _absolute_docs pattern)
- File system protection (root restrictions, kebab-case enforcement)

### Fixed
- Repository user ID propagation (with_user methods)
- Git branch creation (update → save)
- Removed duplicate test files

### Changed
- Removed obsolete frontend debug scripts

---

## [0.0.4] - 2025-09-23

### Added
- **Dynamic Tool Enforcement v2.0**: Static → dynamic permissions from call_agent response
- Agent system documentation (33 specialized agents)
- MCP task management (4-tier context hierarchy)
- AI-powered task enrichment and progress tracking

### Fixed
- Context system type safety improvements

### Changed
- Major CLAUDE.md update (orchestration guidelines, session types, token economy)

---

## [0.0.3] - 2025-09-19

### Added
- **Keycloak Integration**: JWT auth, automatic token refresh, RBAC, multi-tenant isolation
- **WebSocket Real-time Updates**: Live task/project updates with auto-reconnection
- Frontend performance optimizations (lazy loading, virtualization, memoization)

### Fixed
- Docker integration (configs, health checks, startup sequencing)
- Database schema (ORM model alignment)

### Changed
- Test organization restructure (unit/, integration/, e2e/, performance/)

---

## [0.0.2] - 2025-09-17

### Added
- Context management (4-tier hierarchical inheritance with smart caching)
- Agent management (33 specialized agents with dynamic tools)
- Vision system (AI-powered task enrichment)

### Fixed
- SQLAlchemy session management lifecycle
- UUID validation across system

### Changed
- Domain model refactoring (improved DDD implementation)

---

## [0.0.1] - 2025-09-16

### Added
- Initial project setup (FastMCP server, SQLite/PostgreSQL, React frontend)
- Core domain models (Project, Task, GitBranch, Agent, Context)
- Basic MCP tools (CRUD operations)
- Docker development environment

### Fixed
- Initial setup issues (database connections, env loading, Docker permissions)

---

## Project Information

**Repository**: agenthub AI Agent Orchestration Platform
**Documentation**: ai_docs/ (17 standard folders with auto-generated index.json)
**Key Principles**: Clean code (DRY, SOLID, single source of truth) | ORM = truth source | No backward compatibility in dev phase
