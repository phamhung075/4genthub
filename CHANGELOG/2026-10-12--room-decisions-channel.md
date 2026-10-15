# The room decision channel: one room's asks, and the human's click on them

Date: 2026-10-12
Scope: `agenthub_go/fastmcp/room_decisions` (new), `agenthub_go/fastmcp/server/httpapp/room_decisions_mount.go` (new), `fastmcp/server/httpapp/app.go`, the three DDL homes

## Summary
Two routes under the room family's own prefix:

- `GET /api/v2/rooms/{room}/decisions` - the asks mirrored up for the CALLER in that room, in the shape the panel renders.
- `POST /api/v2/rooms/{room}/decisions/{id}/answer` - one click per call, answered as `{state, answers, complete}`.

`{room}` is the SLUG, and the caller is the tenant. The read resolves the room through the room family's visible read (so a shared room is readable) and then scopes the rows to the CALLER's own id, never the room owner's: a viewer of a shared room reads an empty list rather than somebody else's asks. The write resolves the room through the strict owner-scoped read, so a caller who merely shares the room is refused `not-the-asked-human` (403) instead of answering for another human, and a caller with no relationship to the room gets the same 404 an unknown room gets.

`RoomDecisionService` owns the contract, the mount owns the transport. A click is validated in one order - unknown decision, then an exact replay, then unknown question, then unknown option, then not-pending - and every refusal carries the contract's own token. The replay step before the state check is what makes a retried click after the ask was completed answer from the stored row instead of `state-answered`. The ask's door ports the daemon's closed limits (`domain/questions`): 1-4 questions, 2-4 options each, a 75-character option label, a 500-character question, a token-shaped id, plus the summary and detail bounds and the credential scan, so a malformed ask is refused before any row exists.

The response bodies are not wrapped in `success`: the answer mirrors the daemon's `RecordHumanAnswerResult` and the read mirrors the panel, so a client that knows one side of this channel knows the other.

Registering the two routes changes the committed API reference the frontend imports, so that artefact is regenerated in the same commit: `go run ./cmd/apirefgen` adds exactly these two entries to `agenthub-frontend/src/docs/apiReference.ts` and touches nothing else. Both carry an empty `handler`, which the producer documents as its answer for a mount that registers a closure rather than a named function.

## The DDL sits in three homes, and one parity guard holds them together
`room_decisions` is declared in the runtime schema, in the checked-in DDL the deploy applies, and in the ORM struct that is the source of truth. Constraints: `ck_room_decisions_state`, `uq_room_decisions_user_qitem` (one ask per owner per routed item, so a redrive cannot ask the human twice) and `uq_room_decisions_idempotency_key`; the create's `ON CONFLICT ("idempotency_key") DO NOTHING` plus read-back makes the mirror durable-first. A package test compares the three homes without a database.

## Tests
From `agenthub_go`, with `AGENTHUB_TEST_PG_URL` set to a throwaway cluster's URL (`tools/testpg/start.sh`) and the same value as `SEAT_TEST_DATABASE_URL` and `TEST_DATABASE_URL`:

- `gofmt -l` over the tracked `.go` files, from `agenthub_go`: no output.
- `go build ./...` and `go vet ./...`: exit 0.
- `go test -count=1 ./fastmcp/room_decisions/...`: ok.
- `go test -count=1 -v ./fastmcp/server/httpapp/ -run TestRoomDecision`: exit 0, 8 cases PASS, the three DB-backed acceptance cases at 2.46-2.78s (they ran, not skipped).
- `go test -count=1 ./fastmcp/seat_management/...` with the DB env: ok, including `TestEnsureSeatColumnsExistOnOldSchema`, the old-schema upgrade case.
- `go test -count=1 ./internal/apiref/`: ok, after the regeneration above.
- `go test -count=1 ./...`: 141 packages ok on the run made before the regeneration, whose two reds were the missing artefact entries above and `TestSeatMessageRepositoryIntegration` - a pre-existing flake this change does not touch (`TEST-CHANGELOG.md` records its mechanism and the measurement).

See `TEST-CHANGELOG.md` for what each case proves and for the two defects the first DB-backed run exposed.

## Not run / limits
- Pushing, deploying, `POST /api/v2/seat-types/seed` and the re-pin stay the owner's.
- The ask's route (`POST .../decisions`) does not exist yet, so `RoomDecisionService.Create` is reachable only from tests; a redrive is proven at the SQL level and by the service test, not through a route.
- The DB-backed cases SKIP without `AGENTHUB_TEST_PG_URL`, loudly: they are not proof unless they run.
- `resolved`/`superseded` and `answered_at` on the daemon's report-back are not written by this channel, which only records clicks.
