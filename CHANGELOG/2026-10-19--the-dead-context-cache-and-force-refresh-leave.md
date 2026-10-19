# The never-wired context cache and `force_refresh` leave the code (T6 gate)

T6 was held on PERF-02's citation: `unified_context_facade_factory.go` built a
`ContextCacheService` with a nil repository and no searcher, so every `GetContext` missed the
cache and every `InvalidateContext` was a no-op, while the `force_refresh` argument was threaded
from the MCP tool, the REST routes, the facade, the service and the use cases down to a bool that
nothing read. Both leave the code; the resolve path is live reads only.

## What changed

- `fastmcp/task_management/application/services/context_cache_service.go` and its test are
  deleted; the facade factory no longer constructs it, and `UnifiedContextService.GetContext`
  reads through `fetchContextEntries` with no cache probe and no invalidation.
- `force_refresh` is gone from `manage_context`'s input schema, description and handler, from
  `GET /api/v2/contexts/{level}/{context_id}` and `POST .../resolve` (the query parameter was
  parsed and discarded), from `ContextAPIController.GetContext`/`ResolveContext`,
  `UnifiedContextFacade`, `UnifiedContextService`, `TaskContextSyncService`, the batch use case
  and the MCP controller, so every call site loses the dead bool rather than keeping a shim.
- `tools_golden.json` and `agenthub-frontend/src/docs/apiReference.ts` are regenerated from the
  new surface (the latter by `go run ./cmd/apirefgen`), and the tools doc no longer lists the
  parameter.
- `context_cache_optimizer.go` stays: it is never wired either, but it is not part of the chain
  PERF-02 cites and no caller changed.

## Verification

- `cd agenthub_go && go build ./...` clean; `go vet ./...` clean; `gofmt -l .` empty.
- `cd agenthub_go && go test ./... -count=1` green, whole module.
- The wire tools/list test (`TestMCPToolsListMatchesGolden`) passes against the regenerated
  golden, so `manage_context` publishes no `force_refresh`; the route tests assert the GET and
  resolve handlers take no such parameter.
