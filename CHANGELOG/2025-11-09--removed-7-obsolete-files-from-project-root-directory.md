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
