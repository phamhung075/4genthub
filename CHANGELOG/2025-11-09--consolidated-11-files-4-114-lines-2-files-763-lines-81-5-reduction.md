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
