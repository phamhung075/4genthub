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
