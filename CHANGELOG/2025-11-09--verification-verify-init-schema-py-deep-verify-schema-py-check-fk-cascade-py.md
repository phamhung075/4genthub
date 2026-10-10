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
