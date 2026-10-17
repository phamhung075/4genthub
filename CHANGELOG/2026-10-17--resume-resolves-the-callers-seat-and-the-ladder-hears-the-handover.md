# Resume resolves the caller's seat, and the ladder hears the handover

## Added

- `fastmcp/task_management/application/services/task_resume_service.go`: `resume` with an absent or empty
  `task_id` resolves the CALLER SEAT's current task instead of refusing: `status = in_progress AND assignee =
  @<seat key>`, ordered `updated_at DESC, id ASC`, limit 1. The seat key is read from the request's actor
  (`services.ActorFromContext`, the same attribution the ledger's writes travel under); it is never a parameter,
  so a seat cannot resume another seat's item by naming it. No actor, an actor that is not a seat, or a seat
  with no in_progress item answers `ErrNoTaskForSeat`, whose text carries the token and the ruling's two fixes
  ("claim a queue item, or pass task_id").
- `fastmcp/task_management/infrastructure/repositories/task_repository.go`: `LatestInProgressByAssignee`
  executes the ruled query as ONE read, in the repository's own user + branch scope.
- `fastmcp/task_management/interface/mcp_controllers/task_mcp_controller`: `task_id` is optional for the
  `resume` action (validation, handler and the tool description agree), and the handler no longer pre-empts the
  service's answer with a generic "task_id is required".

## Changed

- `resumeNextAction` gained the 1/8 ruling's one input: the last handover's `decision` ranks FIRST. `blocked`
  and `escalate` yield `blocked: <blocked_on>` / `escalate: <blocked_on>` above the REJECT branch, because a
  seat that read the rejection and still could not proceed is the more recent fact; a payload written before
  2/8's gate (no `blocked_on`) yields the decision alone rather than a dangling colon. `continue`/`done` add no
  arm, so the deterministic ladder still answers and `last_handover` keeps the seat's own line.

## Verified

- `go test -count=1 ./...` exits 0.
- `task_resume_service_test.go`: the resolution asks for `@<the request's seat>` and produces the same brief as
  an explicit call; no actor, a non-seat actor and a seat without a task all answer `no_task_for_seat` with the
  two fixes; the blocked handover outranks a REJECT verdict; `continue` leaves the ladder alone; `escalate`
  names its row and degrades cleanly without one.
- `task_repository_test.go` (PostgreSQL): the most recently UPDATED in_progress row wins over an older-created
  one, a tie on `updated_at` is broken by id ascending, and another status, seat or tenant is never a
  candidate.
- `fastmcp/server/mcptoolpath/resume_by_seat_tool_path_pg_test.go`: through the real MCP route, the seat's own
  `X-Agenthub-Seat` header resolves its task with no `task_id`; another seat's header and a header-less call
  both answer `no_task_for_seat` and name the two fixes.
