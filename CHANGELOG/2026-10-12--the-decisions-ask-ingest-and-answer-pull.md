# The decisions channel, machine side: the ask goes up and the answers come back

Date: 2026-10-12
Scope: `agenthub_go/fastmcp/room_decisions` (service, repository contract, ORM), `agenthub_go/fastmcp/server/httpapp/room_decisions_mount.go`, the three DDL homes, `agenthub_go/fastmcp/seat_management/infrastructure/database/ensure_seat_columns.go`, `agenthub-frontend/src/docs/apiReference.ts`

## Summary
Four routes under `/api/v2/openrig/decisions`, the machine half of the room decision channel whose panel half S1 shipped:

- `POST /api/v2/openrig/decisions` - the daemon mirrors one ask up. The body names the rig and may name the room; the room resolves inside the CALLER's tenant, and a slug that resolves to nothing is the pinned 404. The response is `{success, created, decision}`, where `created` is true only for the call that stored the row and false when an earlier attempt already had - and a `created:false` always carries the row.
- `GET /api/v2/openrig/decisions/answers?rig=&after=&limit=` - the pull the daemon drives: that rig's `answered`, un-acked rows, oldest first, each with the room's SLUG beside it.
- `POST /api/v2/openrig/decisions/{id}/ack` - the delivery record. `applied` also resolves the row; `dropped` records the ack and leaves the state alone. Both outcomes make the answer final, so a dropped answer is never handed out again.
- `POST /api/v2/openrig/decisions/{id}/state` - the daemon's state push, the only way a row becomes `superseded` or `closed`. The cloud never resolves a decision on its own: only the daemon's own report does, which is what makes a stale panel answer a refusal rather than a second application.

## The cursor is a keyset over answered_at, and the ack is the delivery record
The pull pages `(answered_at, id)` ascending and renders the position as `<RFC3339Nano>|<uuid>` - the shipped message pull's own format and separator, so one daemon-side parser serves both - and the cursor is opaque by contract. Minting it from the ask's `created_at` would be a keyset over the wrong key: that is the shipped message store's column, and nothing in this repository ordered by `answered_at` before this change.

The ack, not the cursor, is what stops a row being delivered twice: `acked_at IS NULL` is the delivery half of the filter and `state = 'answered'` the work half, both in the SQL, so a resumed pull can neither repeat a delivered row nor skip one. The pull is scoped to one rig because the ack is destructive - a daemon that pulled another rig's answers could not apply them, and its ack would close a decision nobody applied.

## The dedupe tuple is the episode, and the key's value is enforced
`room_decisions` carries ONE unique constraint, `uq_room_decisions_user_qitem UNIQUE (user_id, qitem_id)`, and the ingest's `ON CONFLICT` names exactly that tuple, because that is the tuple its loser path reads back. `idempotency_key` is a stored value whose value is DERIVED from the routed item - `agenthub:decision:<qitem_id>`, the string the daemon already mints for the ask it mirrors - and the service enforces that derivation at the door: a body whose key names another item is refused as `400 {"detail":"idempotency_key must be agenthub:decision:<qitem_id>"}`, before anything is stored. So the stored value is always the derived one, and a reader hunting a row by it finds it rather than finding a row whose key lies about which item it is.

The key is NOT unique, though: a UNIQUE key on its own is GLOBAL, so one routed item asked about by two tenants makes the second tenant's insert no-op and then reads that key back inside that tenant's scope, where the row is not - one tenant's ask swallowed by another tenant's key, and the human never asked. With the same tuple on both sides that state is unreachable, and a create that somehow stores nothing and finds nothing is an error, so the route answers 500 rather than a success carrying no decision.

## The new column reaches an existing database
`acked_at` is registered in `ensure_seat_columns.go` together with its index, which is the path an EXISTING database takes at boot: `CREATE TABLE IF NOT EXISTS` never adds a column to a table that already exists, and S1's `room_decisions` predates the delivery marker. The register's index is now described by its own column list, because this index is composite (the pull filters one machine's answered, unacked rows) and an index over the column alone would be a different object wearing the same name.

## The two envelopes
`{"detail":…}` for a 400/404/409/500 refusal, and the `{success:false,error}` envelope for the ONE refusal that has its own - a credential found in a free-text field, the rule `seat_feedback_mount.go` already follows. A 422 is not a repo-wide envelope, and this channel does not generalise it: the answer route's own 422s stay detail bodies like their neighbours elsewhere in the tree.

## The API reference is regenerated
Four routes change the committed artefact the frontend imports, so `go run ./cmd/apirefgen` writes the four new entries into `agenthub-frontend/src/docs/apiReference.ts` in the same commit and touches nothing else.

## Tests
From `agenthub_go`, with `AGENTHUB_TEST_PG_URL` and `SEAT_TEST_DATABASE_URL` set to a throwaway cluster's URL (`tools/testpg/start.sh`). The DB-backed cases SKIP loudly without it, and a skip is not a pass:

- `gofmt -l` over the touched packages; `go build ./...`; `go vet ./...`.
- `go test -count=1 -run TestRoomDecision -v ./fastmcp/server/httpapp/` - the route's contract cases and the five DB-backed acceptance cases.
- `go test -count=1 ./fastmcp/room_decisions/...`
- `go test -count=1 ./fastmcp/seat_management/... ./fastmcp/task_management/infrastructure/database/` - the DDL parity guards, the baseline-versus-registry guard, and the old-schema upgrade case.
- `go test -count=1 ./...` - the whole module.

See `TEST-CHANGELOG.md` for what each case proves and for the two defects the work exposed.

## Not run / limits
- Pushing, deploying, `POST /api/v2/openrig/seat-types/seed` and the re-pin stay the owner's.
- The daemon half that would drive these routes is its own task, so nothing outside tests consumes the pull yet.
- The DB-backed cases need a PostgreSQL, and the checked-in workflow provides none.
