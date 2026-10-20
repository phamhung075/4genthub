# The context factory refuses instead of installing an in-memory mock

Date: 2026-10-19
Task: c1c3540b (`NFR register + three enforcement gates`, gate G1 / INT-01)

## What was wrong

`factories.NewUnifiedContextFacadeFactory` returned a factory in every case. When the session
manager was nil, the repository builder was unwired, or the builder itself failed, it installed
`services.NewMockUnifiedContextService()` — an in-memory store with no database behind it — and
cached that factory as the process-wide singleton. Production then answered context calls from a
store that could never see or write a row, and a database failure looked like a working server.
That is a fallback, which repo rule 1 forbids.

## What changed

- `NewUnifiedContextFacadeFactory` returns `(*UnifiedContextFacadeFactory, error)`: no session
  manager, no repository builder, and a builder error are all returned, with the builder's cause
  wrapped. Only a successful construction is cached as the singleton.
- `UnifiedService` is typed `*services.UnifiedContextService`, so the facade is built directly;
  the "does it implement the interface" runtime check (which existed only to reject the mock) is
  gone, and so is the unused `GetUnifiedContextFacadeFactory` wrapper.
- The three production callers propagate the error: `NewApp` refuses to compose, `newRouteDeps`
  reuses the factory `NewApp` built (it no longer constructs a second one), and
  `NewTaskLifecycleSweeper` returns it with the schedule error's shape.
- `mock_unified_context_service.go` and its test are deleted: nothing in production can reach the
  mock, and its test only pinned the deleted type.

## Verification

- `cd agenthub_go && go build ./...` — clean.
- `go test -count=1 ./...` — 138 packages ok, 0 failures.
- `go test ./fastmcp/task_management/application/factories/...` covers the refusal: nil session
  manager, unwired builder, and a failing builder that carries `database unreachable`.
- `grep -rn MockUnifiedContextService agenthub_go --include=*.go` — no matches.
