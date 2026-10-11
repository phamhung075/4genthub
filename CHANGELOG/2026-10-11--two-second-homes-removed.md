## Two second homes removed: the unified context's inert Metadata note, and a dead fixture

### What changed
The reviewer's `f99d10eb` verdict left two non-blocking findings in the mission's "one source of truth / no
dead code" class:

- `fastmcp/task_management/application/services/unified_context_service.go:926` still wrote
  `implementation_notes` into the context's `Metadata` map — an inert second home for a field that lives on
  the entity (`t.ImplementationNotes`, mapped to its own column) and is rendered from it. The write is gone;
  the entity field and its column are untouched. The `metadata` local is still consumed by
  `t.Metadata = zpUCSMap(metadata)`, so nothing was left dangling.
- `fastmcp/task_management/infrastructure/repositories/task_context_repository_test.go:118` carried a dead
  `implementation_notes` entry in `taskCtxRepoTestEntity`'s Metadata literal. Removed.

### Why it is safe to say so
A grep of the whole tree for that Metadata key found no reader that consumes it. The only places that name it
are assertions that the key is **absent** — `task_context_repository_test.go:51-52` and
`server/httpapp/unified_context_notes_pg_test.go:115-117` — so deleting the write and the fixture leaves
those assertions true rather than defeating them. The column path (`context.go`,
`init_schema_postgresql.sql`, `models.go`, `task_context_repository.go:103/165`) is a different home and was
not touched.

### Verified, by the seat that committed it
`gofmt -l` on both files printed nothing; `go build ./...` rc 0; `go vet` on the two packages rc 0; and the
two touched packages, run by this seat with `AGENTHUB_TEST_PG_URL` against the live test PostgreSQL on
55451: `go test -count=1 ./fastmcp/task_management/application/services/
./fastmcp/task_management/infrastructure/repositories/` → **ok 6.442s and ok 364.619s**. The repositories
package is the slow one; the number is quoted as measured rather than as a rounded impression.
