## The subtask route carries a progress note, and one shape for an empty details

Rows `qitem-20261011005109-a9cf974e31f368d7` and `qitem-20261011005300-01e49bd73e28d338`. Both are wire
parity between the subtask route and the tool that share a use case.

### The route could not write a progress note at all, silently

`PUT /api/v2/subtasks/{id}` built its `update_data` from title, description, status and
`progress_percentage` only (`routes/subtask_routes.go`), so `ProgressNotes` stayed nil, the use case's
`subtask.AppendProgress` (`update_subtask.go:101`) was never reached from that path, and a client on the
HTTP API got **200 and no progress** while a client on `manage_subtask` got one. Nothing anywhere said
the two paths differed.

The route now accepts `progress_notes` and the routes layer sets the key the facade reads - the same key
the MCP handler sets (`crud_handler.go:179`), so both paths reach the same use case. The parameter stays
optional: a request that does not mention it builds exactly the `update_data` it built before, and there
is a case for that as well as for the key order, because the key order is what the existing port case
pins.

### One meaning, one shape

The task path renders `details` from the dict its facade builds and serves the **empty string** for a task
with no history. The subtask path built its DTO from `progress_history` and `subtaskDetails` answered
**nil** for an empty history, so the same meaning had two shapes on the wire - `""` on one route and null
on the other. Both are falsy to a presence-guarded read, which is why the reviewer filed it as a nit rather
than a defect, and neither is falsy to a caller that tests `=== ''`: absent-or-null reads as "not loaded"
and `""` reads as "none". `subtaskDetails` now serves the empty string for an empty history, which is the
task's shape; a history with entries is joined exactly as before.

**An existing case pinned the old shape and its expectation is changed rather than routed around:**
`dto_test.go`'s `TestSubtaskDTOservesDetailsFromItsOwnProgressHistory` asserted `details = nil` and "a
subtask with no progress serves details as null". It now asserts the empty string on the DTO and on the
wire (`ModelDump`), and its comment says why. That is the only assertion this change flips.

### Verified
- `cd agenthub_go && GOCACHE=.gocache TMPDIR=.gotmp go test -count=1 ./fastmcp/types/ ./fastmcp/server/routes/`
  -> both `ok`. The routes case that proves the carry is `TestPortUpdateSubtaskKeyOrder`
  (`[title, status, progress_percentage, progress_notes]`) with `TestPortUpdateSubtaskWithoutProgressNotesKeepsTheOldKeys`.
- `go test -count=1 ./fastmcp/server/... ./fastmcp/task_management/...` -> no failures.
- `gofmt -l` over the changed files: nothing. `go build ./...` clean. `go vet` on the three changed
  packages: clean.
- Before the fix, the shape case was red on `details = nil` while the populated join stayed green, and the
  key-order case did not compile without the new parameter - both reds are the change's own.

### What could NOT be verified, and why
The full REST chain to the row's proof - post a note through `PUT /api/v2/subtasks/{id}` and read
`subtasks.progress_history` back - could not be driven in-process. Measured, not assumed: a real
`NewApp` over a throwaway database answers `{"detail":"Task <id> not found"}` for a task seeded under both
the token's raw subject and the id `domain.ValidateUserID` maps it to, because the subtask controller
resolves the parent task through `facadeService.GetTaskFacade(nil, nil, &userID).GetTask(...)`, which
cannot see a task created by a plain insert in a branch. So the carry is proven at the routes layer, where
the row located the defect, and the landing half is covered by the tool path's own PostgreSQL case, which
already exercises the same use case. The attempt also turned up two things worth someone's attention:

1. **One subtask request is resolved by two different user ids.** The subtask row is looked up with the
   caller's raw token subject (`getTaskIDFromSubtask` -> `NewORMSubtaskRepository(&userID)`), while the
   parent task goes through a facade that maps the subject through `domain.ValidateUserID`. For a real
   Keycloak subject those coincide because it is already a UUID; for any other subject the two routes
   disagree about who the caller is. Reported rather than changed, because it is an authorization
   question and it is not what either row asked for.
2. **The subtask facade comes from a process-global provider**
   (`services.RepositoryProviderService{}.GetInstance()`), so a second throwaway database in one test
   process leaves the first subtask request answering `sql: database is closed`.

### What this does NOT do
It does not fix the second nit in `qitem-...005300` - the 422 refusal body whose `input` field is always
null where FastAPI echoes the offending body. The reviewer routed that one to the P6 parity work, and this
entry carries it there rather than settling it here. No assertion was loosened, no case deleted, and
`progress_notes` remains opt-in rather than defaulted.
