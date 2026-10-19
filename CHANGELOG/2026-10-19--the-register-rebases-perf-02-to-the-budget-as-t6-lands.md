# The register rebases PERF-02 to the budget as T6 lands

T6 landed at `d45aa05d`: the never-wired `ContextCacheService` and its test, the `CacheService`
field and default, `invalidateChildCaches`, the factory wiring and the `force_refresh` argument left
the surface end to end (MCP schema, description and handler, HTTP routes, controller, facades,
service, batch use case, regenerated `apiReference.ts`). The `context_inheritance_cache` table and
the branch-delete `DELETE` (`git_branch_repository.go:457`) stay, as the ruling said.

PERF-02's requirement was "served from a cache, not a query per level". The cache never existed on
the read path, so the row is rebased to its provenance: a context read/resolution under the 5 ms
budget (`NFR-analysis-2026-10-19.md:41`) with the inheritance merge in memory. Status is PARTIAL -
the merge is in memory and the benchmark measures it, but nothing fails when the budget is exceeded.

## What changed

- `nfr-register.md`: PERF-02's requirement, enforcement and verification are rebased; the
  measurement is re-taken at the landed commit (`BenchmarkResolveContext`, 18.5-26.3 us/op over three
  runs - architect two, lead one - 25881-25882 B/op, 212 allocs/op, i7-12700F) and the row cites the live lines
  (`unified_context_service.go:315`, `:1173`). T6 moves from "Open gates this register expects" to
  "Gates this task landed". Q5's historical citation is attributed to `695e4232`, the commit the
  construction lived at, and the rebase is pinned to `d45aa05d`. INT-01's factory anchor moves
  `:71` -> `:69` because the same commit shifted the nil-session check.
- `G3-drop-classification.md`: re-derived at `d45aa05d`. The deleted `context_cache_service.go`
  row leaves the marker table; four moved rows are re-keyed
  (`unified_context_service.go:551`, `batch_context_operations.go:260`, `task_repository.go:2234`,
  `task_event_controller.go:76`); the sweep block now prints the run's own numbers
  (candidates=91, markers=45, non-markers=46). `scripts/G3-DROP-CLASSIFY.py` exits 0.
- `mcp-tools-api-complete.md` needed no edit: `d45aa05d` already removed the `force_refresh` row
  from `manage_context`'s parameter table and no other cache mention remains in the doc.
- MAINT-01's citation moves `routes_mount.go:381` -> `:382`: `:381` is the `GET <base>/` list
  route, `:382` is `GET <base>/legacy/tokens`, the surface the row names. The anchor was already
  off by one at `d9c165ae`; the row's status word is untouched.

## Verification

- `python3 scripts/G3-DROP-CLASSIFY.py` -> exit 0, output identical to the block in the report.
- `cd agenthub_go && go test ./fastmcp/task_management/application/services -bench
  BenchmarkResolveContext -benchmem -run '^$'` three times at `d45aa05d` (architect two:
  `18.5-18.7 us/op`, `25881 B/op`; lead one: `26285 ns/op`, `25882 B/op`) -> `18.5-26.3 us/op`,
  `25881-25882 B/op`, `212 allocs/op`, all under the 5 ms budget.
- Every `file:` anchor in the edited rows opened at `d45aa05d`: `:315` is `GetContext`, `:1173` is
  `resolveInheritanceSync`, `:69` is the nil-session check, `:457` is the branch-delete `DELETE`,
  `:382` is `GET <base>/legacy/tokens`.
- Diff is documentation only: two `ai_docs/` files plus this entry.
