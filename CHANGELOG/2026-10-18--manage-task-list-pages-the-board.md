# `manage_task list` pages the board, and a one-row page is still a list

The enumeration defect (board task `0a30dd7e`): `offset` was echoed into `pagination` and never
bound into SQL, the page length was reported as `pagination.total`, and the live path hardcoded
offset 0 - so page 2 was page 1 and no seat could enumerate the board. The same run also turned up a
second shape defect: a page carrying ONE row answered `"tasks": {...}` instead of `[{...}]`.

## Fixed

- `agenthub_go/fastmcp/task_management/application/facades/task_application_facade.go`: the
  performance branch - which is the LIVE list path, because `IsPerformanceMode()` is
  unconditionally true - forwarded `offset := 0` to `ListTasksMinimal` on every call. It now passes
  `request.Offset`. It also reports `total` from a count (`CountTasksMinimal`, new on
  `TaskMinimalLister` and implemented by `ORMTaskRepository` and `SupabaseOptimizedRepository`), so a
  page's total is the count of the filtered set. A request with an explicit `sort_by`/`sort_order`
  falls through to the full path, because the minimal lister has one fixed ordering and silently
  replacing the caller's is the same class of lie.
- `infrastructure/repositories/task_repository.go`: `FindByCriteria` takes
  `repositories.ListQuery{Limit, Offset, SortBy, SortOrder}`, binds `OFFSET`, and builds `ORDER BY`
  from a whitelist (`updated_at`, `created_at`, `priority`, `status`, `title`; asc/desc) with
  `"id" ASC` as a tiebreaker - without it, two rows sharing `updated_at` can swap between queries and
  an offset page returns one row twice and misses another. An unsupported ordering is an ERROR, never
  a silent fallback. `CountByCriteria` counts through the SAME WHERE clause (`taskRepoCriteriaWhere`),
  so the page and its total cannot disagree. Search gained `offset` plus the same tiebreaker.
- `handlers/search_handler.go`: `list` passes offset/sort into `ListTasksRequest` and reports
  `pagination.total` from the facade's count with `has_more = offset+len(page) < total`; `search`
  carries offset and now publishes its own `pagination` block.
- `application/services/response_optimizer.go`: `FlattenStructure` no longer rewrites a
  single-element list as its element. A one-row page's `tasks` is a list, as every caller parses it.
- `application/dtos/task`: `ListTasksRequest` gained `Offset`/`SortBy`/`SortOrder`,
  `SearchTasksRequest` gained `Offset`, `TaskListResponse` gained `Total` (and `CountTasks` now
  answers that total rather than the length of an unbounded read).

## Tests

- `TestTaskRepoListPagingHasNoOverlap` (real Postgres): five rows, limit 2 at offsets 0/2/4 - no row
  on two pages, all five reached, `CountByCriteria` = 5, the oldest row is the last page under the
  default order and the FIRST row under `created_at ASC`, and an unknown `sort_by` errors. Red before
  the fix (offset unbound), green after.
- `TestTaskRepoSearch` gained the search half: the same query at offset 0 and offset 1 returns
  different rows.
- `TestMCPListPagingPagesThroughTheBoard` (`fastmcp/server/httpapp`, real Postgres, real `POST /mcp`):
  `tools/call manage_task {action:list, limit:2, offset:0|2|4}` returns three pages whose union is the
  five seeded rows with no overlap, `pagination.total` 5, `has_more` true/true/false, and
  `sort_by=created_at&sort_order=asc` returns the oldest row first. This is the endpoint-level proof:
  before the fix pages 1 and 2 returned the same ids.
- `TestListTasksPerformancePathForwardsOffsetAndTotal` pins the live branch (offset 40 reaches the
  lister, one count call, `total` 137) and the fall-through rule.
- `TestResponseOptimizer_KeepsSingleElementLists`: a one-element `tasks` stays a list, nested too.
- `TestTaskSearchHandlerAdapterKwargs` now asserts the offset/sort REACH the request (not just the
  echo) and that `pagination.total` is the facade's count.

## Verification

- `gofmt -l fastmcp/`: empty; `go vet ./fastmcp/...`: clean; `go build ./...`: ok.
- `go test ./fastmcp/task_management/... ./fastmcp/server/httpapp/`: pass.
- `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55432/postgres` (from
  `bash tools/testpg/start.sh`) for the database cases.
