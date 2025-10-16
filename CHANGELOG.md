# Changelog

All notable changes to the agenthub AI Agent Orchestration Platform.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) | Versioning: [Semantic](https://semver.org/spec/v2.0.0.html)

## [Unreleased]

### Changed

- **Docker Build Performance** (2025-10-16): Consolidated ENV declarations across all Dockerfiles for faster builds and better cache utilization
- **Python 3.14 Upgrade** (2025-10-15): System-wide upgrade from 3.12.3 to 3.14.0 with compatibility fixes and DRY cleanup (removed redundant requirements.txt, fixed Pydantic field definitions, created hooks fix script)
- **Workflow Guidance UX** (2025-10-12): Refactored all guidance modules (task, subtask, git_branch) to show "next action" examples instead of redundant creation examples

### Maintenance

- **Authentication Documentation Consolidation** (2025-10-16): Completed Phase 1 & 2 of authentication/ folder cleanup. Created comprehensive `complete-authentication-system.md` (57KB, 10 sections) consolidating 3 duplicate files with 70% overlap: authentication-system.md (35% unique Keycloak integration), authentication-system-current.md (15% unique current implementation), MCP_TOKEN_AUTHENTICATION.md (20% unique MCP token flow). New document includes Python 3.14.0 compatibility, DDD Phase 8 patterns, specific file references with line numbers, and enhanced troubleshooting guide. Archived obsolete files to `_archived_2025-10-16/`. Folder reduced from 17 to 15 files while consolidating all authentication knowledge into single authoritative source
- **Core Architecture Review** (2025-10-16): Completed comprehensive 6-phase review of core-architecture/ folder. Generated detailed 27-page report identifying critical issues: index.md claims 6 files but 36 exist (500% discrepancy), 6 database-timestamp files with 85% overlap, 4 MCP injection files with 80% overlap. Report provides consolidation plan (36→14 files, 61% reduction) and update strategy for Python 3.14, DDD Phase 8, and Dynamic Tool Enforcement v2.0. Report: `ai_docs/reports-status/core-architecture-review-20251016.md`
- **Documentation Quality Cleanup** (2025-10-16): Implemented aggressive documentation curation to keep only valuable AI knowledge. Created mark-obsolete-docs.py script following principle "AI docs should be curated, not cluttered". Marked 124 low-value files with .obsolete extension: 102 historical test iteration summaries (testing-qa/), 19 old status reports (reports-status/), 1 temp workspace results file, 2 obsolete absolute docs. Reduced active documentation from 473 to 347 files (27% reduction) while maintaining 100% of valuable knowledge. Updated index.json: 347 files across 32 directories
- **Documentation Architecture Audit** (2025-10-16): Phase 2 complete - Created audit-architecture-accuracy.py script to scan 470 documentation files for outdated architecture references. Generated comprehensive report with 2,872 issues found: 96 outdated patterns (25 old Python versions, 59 old context patterns), 2,776 files with missing modern coverage (381 missing Python 3.14, 380 missing React 19/Vite 7, 361 missing Event System), and 63 architecture gaps. Report saved to `ai_docs/reports-status/architecture-accuracy-audit-20251016.md` with prioritized update strategy
- **Documentation Obsolete Detection** (2025-10-16): Created cleanup-obsolete-docs.py script to automatically detect and archive obsolete documentation. Moved 3 obsolete docs to `_obsolete_docs/20251016/` (claude-hooks-pre-tool-use.py.md, scripts/f_index.md, scripts/test-doc-system.sh.md). Initial cleanup pass before quality curation

### Added

- **Week 1 Performance Tests** (2025-10-11): Baseline test suite with 3x improvement targets (150ms → 50ms), metrics collector with JSON/CSV export, comprehensive documentation
- **UUID Validation Cache** (2025-10-11): Added LRU cache with monitoring (2.5x speedup, 10k entries, cache hit rate logging every 1000 calls)
- **Event System** (2025-10-11): EventQueue (thread-safe FIFO, 10k capacity), EventWorker (background thread with retry logic and DLQ), EventBus refactoring (non-blocking publish with feature flag)
- **Performance Fix Plan** (2025-10-11): Comprehensive 3-week roadmap to fix 3-5x degradation (150ms → <30ms target) with technology recommendations and cost analysis

### Fixed

- **PostgreSQL 18 Docker Volume** (2025-10-16): Fixed WSL2 overlay filesystem mounting error after upgrade from PostgreSQL 15 to 18. Root cause: stale overlayfs directory reference. Solution: removed corrupted `docker_postgres-data` volume and recreated using docker-menu.sh option B with proper environment loading. Container now running successfully on postgres:18-alpine
- **Projects List API** (2025-10-13): Fixed BranchDTO validation errors in list_projects endpoint (added required project_id and git_branch_name fields)

### Completed

- **Phase 8 DDD Refactoring** (2025-10-11): Completed entire 8-phase initiative - removed 3 feature flags, eliminated 3 legacy components, 8,314 tests passing, 100% DDD compliance achieved

### Removed

- **Backward Compatibility Cleanup** (2025-10-11): Removed SimpleMultiAgentAdapter, deprecated task_events.py, removed domain orchestrator (preserved core DDD adapters)
- **FEATURE_APPLICATION_ORCHESTRATOR Flag** (2025-10-11): Removed feature flag, deprecated legacy domain orchestrator, simplified orchestrator router to always use application layer

---

## Previous Phases & Fixes

### Phase 5-7: Event System & Repository Refactoring (2025-10-09 to 2025-10-10)

- **Phase 5**: Event bus integration (21 handlers), domain event handlers (task/agent/project), events standardization (BaseDomainEvent pattern)
- **Phase 5.2-5.4**: Enum consolidation (moved 7 enum files to value_objects), removed domain/enums and domain/models directories
- **Timestamp Tests Fix** (2025-10-10): Added value object support to UnifiedUUID.process_bind_param()
- **BaseTimestampRepository Fix** (2025-10-10): Fixed MRO chain issues by manual mixin initialization
- **Event Handler Registration Fix** (2025-10-10): Fixed startup failures, updated event names, fixed EventStore imports

### Phase 4: Value Objects & ID Consolidation (2025-10-09)

- **Phase 4.5-4.7**: Created EntityId abstract base (eliminated ~200 lines duplication), unified SubtaskId with TaskId, consolidated TemplateId
- **Phase 4**: Created immutable value objects (ProjectId, AgentId, GitBranchId), migrated 3 entities from string IDs, all 996 tests passing

### Phase 3: Application Layer (2025-10-09)

- **Orchestrator Migration**: Moved multi-aggregate orchestration from domain to application layer with feature flag system for zero-downtime migration

### Documentation & Architecture (2025-10-08 to 2025-10-09)

- **PRD & Architecture Sync** (2025-10-08): Added FR008_WebSocket_Real_Time_System with v2.0 implementation, 160+ line WEBSOCKET_REAL_TIME_ARCHITECTURE section
- **Hook Logging Architecture** (2025-10-09): Comprehensive guide for Claude hooks logging system
- **MCP Context Debug Logging** (2025-10-09): Added conditional debug logging controlled by APP_LOG_LEVEL=DEBUG
- **Session Start Logging Migration** (2025-10-09): Converted print() to Python logging module with persistent output

### DDD Architecture Compliance (2025-10-08 to 2025-10-09)

- **Repository Fixes**: Git Branch (renamed conversion methods), Label (added _entity_to_model_dict), Task (proper entity conversion)
- **Cascade Calculator DDD Refactoring**: Removed SQLAlchemy from domain service, created CascadeDataProvider Protocol with infrastructure implementation
- **BaseRepository Clean Architecture** (2025-10-09): Removed concrete pagination from interface using FEATURE_CLEAN_REPOSITORIES flag

### UI/UX & Real-time Updates (2025-09-30 to 2025-10-08)

- **Real-time Task Updates** (2025-10-08): TaskDetailsDialog auto-refreshes via WebSocket with "Updated" badge
- **MCP Tool Enhancement** (2025-10-08): Added delete action to manage_project for complete CRUD
- **WebSocket Improvements** (2025-10-08): Fixed subtask filter, removed redundant branch filtering, added task deletion tracking, enhanced changePoolService
- **Global Context Dialog** (2025-09-30): JSON tree with smart Expand/Collapse All functionality
- **Task UI Enhancements** (2025-09-30): Copy buttons for task ID/name, standardized animations, LazySubtaskList improvements

### Security & Repository Fixes (2025-10-08)

- **Security**: Added apply_user_filter() to search_agents()
- **Repository**: Fixed MRO conflicts (Project/Agent), added with_user() to GitBranch, fixed unsafe .lower() on None values

### Frontend Architecture (2025-09-29 to 2025-09-30)

- **API Response Models** (2025-09-30): 40+ Pydantic DTOs in fastmcp/types/ with comprehensive refactoring guide
- **Custom Hooks** (2025-09-29): useTaskFilters, useTaskGrouping (18 tests), useTaskData, useTaskWebSocket (300+ line simplification)

### Test Suite & Fixes (2025-09-29 to 2025-10-01)

- **Test Suite Excellence** (2025-10-01): 379/406 tests passing (93.3%), zero failures across 42 iterations
- **Test Fixes** (2025-09-29): Docker integration test, cache false positives, session hook branch detection

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
- **Dynamic Tool Enforcement v2.0**: Revolutionary static → dynamic permissions from call_agent response
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
**License**: MIT
**Python**: 3.14+ | **Node**: 18+
**Database**: SQLite (dev) / PostgreSQL (prod)
**Architecture**: Domain-Driven Design (DDD)
