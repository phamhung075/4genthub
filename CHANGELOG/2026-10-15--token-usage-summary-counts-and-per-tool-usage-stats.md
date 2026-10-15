## 2026-10-15 - Token Usage Summary shows its counts, and counts each MCP tool

### Fixed
- `agenthub_go/fastmcp/server/routes/token_router.go`: `usage_count` and `rate_limit` were read with a plain `int` assertion, but the `api_tokens` INTEGER columns arrive as `int64`. Every token therefore answered `usage_count: 0` and `rate_limit: null` although `last_used_at` moved. `trIntPtr` now reads both.

### Added
- `agenthub_go/fastmcp/task_management/infrastructure/repositories/token_repository.go`: `RecordOperation` adds one to `usage_stats[operation]` in a single SQL statement (jsonb round trip), so concurrent calls do not lose counts.
- `agenthub_go/fastmcp/server/httpapp/mcp_routes.go`, `app.go`: every authenticated MCP `tools/call` is counted on the API token that made it, keyed `<tool>.<action>` (for example `manage_task.create`) or the bare tool name. The Usage Summary's "Operation Types", "Most Used" and "Operation Breakdown" read these keys. A failure is swallowed; a count never refuses a call.

### Testing
- `go test ./server/...` passes; `TestTokenResponseFromMapKeepsInt64Counters`, `TestRecordToolCallKeysByToolAndAction`.
- `TestTokenRepoRecordOperationCountsPerOperation` passes against the throwaway PostgreSQL (`tools/testpg`).
- Counts begin when this is deployed; earlier calls were never recorded.
