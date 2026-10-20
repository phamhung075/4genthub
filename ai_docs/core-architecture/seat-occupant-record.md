# The seat occupant record

Architect ruling, 2026-10-20. jev=2026-10-20T19:01:34Z (lead tier, option A: persist the record).
Design task `84e06ad1`; the build is task `35431928` (@go-dev). Measured against hub `76b0d84d`
(`0f48cda3` plus the INT-03 cascade commit, which touched the auth and task contexts only).

## 1. Decision

Every stored change of a seat's occupant (runtime, model) writes one append-only row of
`seat_occupant_changes`, inside the SAME transaction that overwrites the `seats` row, carrying the
seven record columns **actor, at, seat, from_runtime, from_model, to_runtime, to_model**. One route
reads a seat's rows newest first:
`GET /api/v2/rooms/{room}/seats/{seat}/occupant-history`.

The transient WebSocket frame keeps its current job and gains no duty. No compatibility code: the
store method's signature grows one parameter and every caller is migrated in the one change.

## 2. Context, measured

- The write call site is `SetOccupant` at `agenthub_go/fastmcp/seat_management/application/services/seat_admin_service.go:103`
  (the function's declaration is at `:105`, its store call at `:124`), reached by
  `PUT /api/v2/rooms/{room}/seats/{seat}/occupant` (`seat_admin_mount.go:356` → `handleSetSeatOccupant`, `:1155`)
  and by the MCP action `manage_seat set_occupant` (`manage_seat_controller.go:67`).
- It reaches `seat_repository.go:87-88`, one statement:
  `UPDATE "seats" SET "runtime" = $1, "model" = $2, "updated_at" = $3 WHERE "user_id" = $4 AND "id" = $5`.
  The row is overwritten in place; the previous values are gone.
- `GetDBSession` (`base_orm_repository.go:94`) is `SessionManager.WithSession`
  (`session_manager.go:150-186`): BEGIN, run, COMMIT, roll back on any error. **The overwrite already
  runs in its own transaction**, so the record needs no new seam — it is one more statement in the
  same closure.
- Nothing durable records the event: no history table, no row, and no log line — unlike
  `handleSetSeatPermissionPolicy` (`seat_admin_mount.go:1182`) and `handleSetSeatPin` (`:1206`), which
  both `log.Printf("[SEAT] user %s …")`.
- The only emission is transient: the route's `seatMutation("seat", "updated", …)` wrapper
  (`seat_admin_mount.go:446-465`) calls `routes.BroadcastDataChange` (`websocket_routes.go:417-421`)
  after a 2xx. The frame carries `entity=seat`, `action=updated`, `{id:"<room>/<seat_key>",room,seat_key}`
  and the actor's id — **never the runtime or model**, and nothing persists it for a connected client.
  `TestSeatAdminSetOccupantEmitsOneFrame` (`seat_admin_mount_test.go:527`) pins that shape.
- No resolve happens at switch time, so no `resolved_seats` row appears either, and the daemon-side pin
  holds a snapshot hash and path only.
- After a change nobody can answer who switched the seat, when, or from what to what.
- Rulings this design must not break: a blank field never clears a field (owner ruling 2026-10-05,
  `seat_admin_service.go:112-123`); the type-default inheritance is CREATE-only; and a running seat
  never changes live (`ai_docs/operations/syncing-seats-with-the-cloud.md:87`) — the row records the
  stored occupant the **next** launch reads, not a switch of a live seat.

## 3. Options

- **A — a seat-owned append-only table written in the overwrite's transaction.** Fits every table in
  this bounded context (`seat_feedback`, `seat_links`, `seat_status` are all `seat_*`), the entity model
  carries no history, and the read route mirrors `handleListSeatLinks`. Cost: one table and the six
  DDL/registry files §11 lists.
- **B — two columns on `seats` (`runtime_changed_by`, `runtime_changed_at`).** Cheapest DDL, but records
  only the LAST change: the before/after pair — the whole question — is still lost, and a read route can
  return one row, not a history. Fails the acceptance.
- **C — reuse an existing ledger.** `task_events` (`0001_baseline.sql:442-462`) and
  `task_audit_records` (`:468-485`) already exist, but both are task-owned: `task_events.task_id`
  is a foreign key and `task_audit_records` needs a `task_id` with a CHECK vocabulary of
  `('escalated','blocked','pruned')`. A seat event would have to invent a task id and widen the
  task vocabulary — one bounded context writing another's table, which no other seat path does.
- **D — a log line per change**, matching the permission-policy and pin handlers. One line of code, no
  table. But a log is not addressable: it cannot be read for one seat, and it dies with the process's
  stdout. It does not answer the question.

## 4. Recommendation

**A.** It is the only option whose answer survives a second change, and it costs one statement inside a
transaction that already exists. Choose **B** instead only if the ask narrows to "who last touched this
seat"; choose **D** only if the ask narrows to observability. Add the log line that C/D's spirit asks
for as well — one `log.Printf("[SEAT] user %s switched %s/%s from %s/%s to %s/%s")` beside the other two
handlers — because a log is cheap and the durable row is what the route reads.

## 5. The record schema

```sql
-- Table: seat_occupant_changes
-- One stored switch of a seat's occupant. Append-only: a row exists exactly when a change was made,
-- and nothing rewrites it. The seat's current values live on seats; this is the trail behind them.
CREATE TABLE IF NOT EXISTS seat_occupant_changes (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    seat_id UUID NOT NULL REFERENCES seats (id) ON DELETE CASCADE,
    actor TEXT NOT NULL,
    at TIMESTAMP WITH TIME ZONE NOT NULL,
    from_runtime TEXT NOT NULL,
    from_model TEXT NOT NULL,
    to_runtime TEXT NOT NULL,
    to_model TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_seat_occupant_changes_seat ON seat_occupant_changes (user_id, seat_id, at DESC);
```

The seven record columns and their meaning:

| Column | Type | Meaning |
| --- | --- | --- |
| `actor` | `TEXT NOT NULL` | the authenticated caller's user id — the actor, never a request field |
| `at` | `TIMESTAMP WITH TIME ZONE NOT NULL` | the instant of the change: the SAME `time.Now().UTC()` written to `seats.updated_at` |
| `seat` (`seat_id`) | `UUID NOT NULL` | the seat changed; FK to `seats(id)` |
| `from_runtime` | `TEXT NOT NULL` | the runtime being replaced, read under the row lock |
| `from_model` | `TEXT NOT NULL` | the model being replaced |
| `to_runtime` | `TEXT NOT NULL` | the runtime stored by this change |
| `to_model` | `TEXT NOT NULL` | the model stored by this change |

`id` and `user_id` are the key and the tenant column every table in this schema carries
(`user_id` is the owner whose rows these are — `seats.user_id`, so a team viewer reads through
`seatAdminScope`). One index serves the only read there is: one seat's rows, newest first.

The cascade is deliberate and is the INT-03 ruling applied, not an exception to it
(`CHANGELOG/2026-10-19--four-cascades-move-to-the-application.md`): **a child that cannot outlive its
one parent keeps the database cascade.** An occupant row has exactly one parent, the seat, and cannot
outlive it. The seat context's older children (`seat_links`, `resolved_seats`) are deleted explicitly by
`SeatDeletionService.RemoveSeat` (`room_deletion_service.go:121`, `:127`) because they predate that
ruling; they are not a precedent for a new table, and copying them would add a call, a fake method and a
test for a delete the database already enforces.

No CHECK: `runtime` and `model` are validated by `repositories.ValidateOccupant` before the write
(`seat_admin_service.go:121`), and a CHECK duplicating a Go list is a second source of truth. No
`updated_at`: a row is never updated.

## 6. The write path

Actor identity is the authenticated caller. In `SetOccupant` it is the `userID` argument, which the
handler fills from `userID(u)` (`seat_admin_mount.go:1164`) and the MCP controller from its
authenticated `uid` (`manage_seat_controller.go:67`). It cannot come from the body:
`decodeSeatAdminBody` uses `DisallowUnknownFields` (`seat_admin_mount.go:532-540`), so an `actor` key in
the PUT is a 400, not a field. The two ids are passed separately because they answer different
questions — whose rows these are, and who acted — and a later team-writer changes only the second.

`ORMSeatRepository.UpdateOccupant` grows one parameter and does all three statements in one
`GetDBSession` closure, which is one transaction:

```go
func (r *ORMSeatRepository) UpdateOccupant(ctx context.Context, userID, seatID, runtime, model, actor string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		// The previous values are read UNDER THE ROW LOCK, not taken from the service's earlier
		// read: two switches that interleave would otherwise both record the same from_* pair.
		var fromRuntime, fromModel string
		if err := s.QueryRowContext(ctx,
			`SELECT "runtime", "model" FROM "seats" WHERE "user_id" = $1 AND "id" = $2 FOR UPDATE`,
			userID, id).Scan(&fromRuntime, &fromModel); err != nil {
			return err
		}
		if fromRuntime == runtime && fromModel == model {
			return nil // nothing changed: no UPDATE, no record
		}
		at := time.Now().UTC()
		if _, err := s.ExecContext(ctx,
			`UPDATE "seats" SET "runtime" = $1, "model" = $2, "updated_at" = $3 WHERE "user_id" = $4 AND "id" = $5`,
			runtime, model, at, userID, id); err != nil {
			return err
		}
		_, err := s.ExecContext(ctx,
			`INSERT INTO "seat_occupant_changes" ("id", "user_id", "seat_id", "actor", "at", "from_runtime", "from_model", "to_runtime", "to_model") `+
				`VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
			value_objects.NewUUIDv4(), userID, id, actor, at, fromRuntime, fromModel, runtime, model)
		return err
	})
}
```

Rules this encodes, each of which a test below pins:

1. **Atomic.** The INSERT fails ⇒ `WithSession` rolls back the UPDATE ⇒ the seat is unchanged and the
   caller gets an error. A seat can never be switched without its record.
2. **The record is what the seats row says.** `from_*` comes from the locked row, not from the
   service's `FindSeat` read, so the trail cannot disagree with the row it describes.
3. **A no-op is not a change.** Both values equal the stored ones ⇒ no UPDATE (so `updated_at` does not
   move), no row. An idempotent retry leaves one row, not two.
4. **One clock.** `at` is the same instant as `seats.updated_at`.
5. **The row vanishes under the write** (a concurrent `RemoveSeat`): `Scan` returns `sql.ErrNoRows`,
   the transaction rolls back, and the route answers 500 instead of reporting a successful switch of a
   seat that no longer exists. Today the UPDATE silently matches 0 rows.
6. **Blank-field inheritance already happened** in `SetOccupant` before this call, so `to_*` is the
   effective value, and a runtime-only PUT records `from_model == to_model`.

`Create` (`seat_repository.go:32-41`) records nothing: creating a seat is not a change, and the service
already refuses to validate a created seat's occupant through this path. Permission-policy and pin
changes are out of scope — the same table can grow a `kind` later if the owner asks, which is the
change that would make this a general seat-change trail instead of an occupant trail.

## 7. The read surface

```
GET /api/v2/rooms/{room}/seats/{seat}/occupant-history
→ 200 {"success": true, "changes": [
     {"actor":"user-1","at":"2026-10-20T19:01:34Z",
      "from_runtime":"claude-code","from_model":"sonnet",
      "to_runtime":"codex","to_model":"gpt-5.1"}
   ]}
```

- Newest first (`ORDER BY "at" DESC`), no paging and no limit: a seat's occupant changes are human
  actions, and a cap would hide exactly the oldest ones.
- **Who may read:** the same caller who may read the seat today. The handler is
  `handleListSeatLinks` (`seat_admin_mount.go:1573-1600`) with the collection swapped: visible room
  (`seatAdminVisibleRoom`, `:561`), then `seatAdminScope` (`:578`) — the caller's own id, or the room
  owner's when the caller is a viewer on the room's team — then the seat, then the rows.
  `actor` is a user id the reader can already see in seat admin, and this route shows no seat data the
  seats list does not.
- Registered beside the other seat GETs (`seat_admin_mount.go:350`, `:380`, `:386`) **without**
  `seatMutation`: a read emits no frame.
- New port method on `SeatRepository` — no new repository, no new package:
  `ListOccupantChanges(ctx context.Context, userID, seatID string) ([]OccupantChange, error)`, and one
  domain type `OccupantChange{ID, UserID, SeatID, Actor, At, FromRuntime, FromModel, ToRuntime, ToModel}`
  in `domain/repositories/repositories.go`. The handler calls it through `seatAdminSource`, exactly as
  it calls `ListSeatLinks`, so no service method is added.
- No MCP action. `manage_seat` stays as it is; a `tests`-free MCP reader can be added later as one
  action with no schema change (`ai_docs/agent-system/seat-model-and-mcp-surface.md:52`).

## 8. Retention

- Append-only: no `UPDATE`, no `DELETE` in Go, no pruning job, no cap. The repository has no delete
  method — the trail cannot be shortened by a caller.
- A row lives exactly as long as its seat: `ON DELETE CASCADE` (§5, the INT-03 "keep" class) removes
  the history with the seat, so `RemoveSeat` (`room_deletion_service`) needs no new call and no future
  deletion path can leave orphans. Deletion is itself unrecorded today; the alternative — keeping
  history past the seat, as `task_audit_records` deliberately does for a pruned task — needs the row to
  stop referencing the seat and carry room + seat_key instead. That is the one-line FK decision to
  revisit **if** the owner ever asks what a deleted seat was, and it is not in this task.
- No backfill. Changes already made cannot be reconstructed, and a guessed row would be a lie.

## 9. Risks

- **The read route could be mistaken for live state.** A row says the stored occupant changed; a
  running seat keeps the snapshot it launched with (`syncing-seats-with-the-cloud.md:87`). The handler's
  doc comment and the response field names say "changes", not "runtime now".
- **A second writer of `seats.runtime/model` would silently bypass the trail.** Today there is one
  UPDATE (`seat_repository.go:88`) and `Create`'s INSERT. A future writer must go through
  `UpdateOccupant`; the INSERT's presence in the same closure is the reason it cannot be forgotten here.
- **The actor equals the tenant id for as long as only the owner may write** (writes resolve the room
  through `GetRoomBySlug`). If team viewers are ever given writes, the two ids diverge and the column is
  already right; do not "simplify" it back into `user_id`.
- **The table is the sixth FILE a seat table must be declared in** (§11). Missing one turns a schema
  guard red, which is the intended behaviour — but it is the step most likely to be half-done.

## 10. The test contract

**The test that asserts the RECORD exists** — one name, in the package that writes it, running with no
database so it is part of `go -C agenthub_go test ./... -count=1`:

```
TestUpdateOccupantRecordsTheChange
  agenthub_go/fastmcp/seat_management/infrastructure/repositories/orm/occupant_change_repository_test.go
```

It uses the scripted `fakeDriver` (`orm_repositories_test.go:21-108`) whose `respond` answers the
`SELECT … FOR UPDATE` with `("claude-code","sonnet")`, calls
`UpdateOccupant(ctx, testUser, testSeatID, "codex", "gpt-5.1", testUser)`, and asserts, in order:
the locked SELECT ran; the `UPDATE "seats"` ran; an `INSERT INTO "seat_occupant_changes"` ran carrying
`user_id`, `seat_id`, `actor`, a non-zero `at`, `from_runtime`/`from_model` from the SELECT, and
`to_runtime`/`to_model` from the call. The fake driver records SQL text only today (`fakeStmt.Exec`
drops its args, `orm_repositories_test.go:80-87`); it gains an `execArgs` capture of a few lines so the
arguments are assertable. Extend the driver, not the production code, and do not change what the
existing recordings return.

Companions, each pinning one plausible failure rather than restating the above:

| Test | File | Pins |
| --- | --- | --- |
| `TestUpdateOccupantSkipsTheRecordForANoOp` | same file | a PUT of the stored values writes neither UPDATE nor row |
| `TestListOccupantChangesIsTenantScoped` | same file | the read selects by `"user_id" = $1` and `"seat_id" = $2`, `ORDER BY "at" DESC` |
| `TestSeatAdminSetOccupantRefusesAnActorField` | `server/httpapp/seat_occupant_record_test.go` | body `{"runtime":"codex","actor":"someone-else"}` is a 400 (unknown field) |
| `TestSeatAdminSetOccupantPassesTheAuthenticatedActor` | same file | the store receives `userID(u)`, never a request value |
| `TestSeatAdminOccupantHistoryReturnsOneSeatsChanges` | same file | `GET …/occupant-history` → `{success, changes[7 fields]}`; a team viewer reads through `seatAdminScope`; the route emits no frame |
| `TestOccupantChangeIsRecordedIntegration` | `orm/integration_test.go` (skips without `SEAT_TEST_DATABASE_URL`) | real durability: two switches → two rows newest first, a repeated one adds none, deleting the seat removes them |

A `TEST-CHANGELOG.md` entry is mandatory for this change (`AGENTS.md:59`).

## 11. Handoff

**@go-dev**, task `35431928`, in this order:

1. Schema — the table must appear in **all six** places, because four guards read them:
   `seat_management/infrastructure/schema/seat_management_postgresql.sql` (the file a human applies;
   `seat_ddl_parity_test.go` compares it with the registry — columns, referenced tables, CHECKs);
   `seat_management/infrastructure/database/seat_tables.go` (`TableDef` appended to `seatDatabaseTables`
   **after** `seats`, because the creation order is a dependency — the list is registered at `:466-471`;
   its DDL string is the `seat_links` form: `CREATE TABLE seat_occupant_changes (` with no
   `IF NOT EXISTS`, `PRIMARY KEY (id)` among the constraints, the FK inline on
   `seat_id UUID NOT NULL REFERENCES seats (id) ON DELETE CASCADE`, and the index as its own string,
   while the `.sql` file keeps `IF NOT EXISTS`; the seat parity test compares referenced-table multisets
   through `seatReferencesClause`, so `ON DELETE` needs no registry field and the seat `TableDef` has
   none);
   `seat_management/infrastructure/database/seat_occupant_change_orm.go` (`SeatOccupantChangeORM`, the
   per-table sibling shape of `seat_feedback_orm.go`);
   `seat_occupant_change_orm_test.go` (its sibling, registering
   `seatTableTypes["seat_occupant_changes"]` in an `init()` — the `seat_settings_orm_test.go:5-10`
   pattern; `TestSeatORMMatchesDDL` fails on an unregistered table);
   `task_management/infrastructure/database/migrations/0001_baseline.sql`
   (`TestBaselineMatchesEveryRegisteredTableDef` requires every registered `TableDef` there);
   and `migrations/0007_seat_occupant_changes.sql`, idempotent, so a database that already applied
   `0001` gets the table — the same reason `0005` exists (`migrations/README.md`; `0006` is the highest
   number today).
2. Write path — `UpdateOccupant` and `UpdateSeatOccupant` take `actor`; migrate `SeatAdminStore`
   (`seat_admin_service.go:25`), the adapter `seatAdminRepos.UpdateSeatOccupant`
   (`seat_admin_mount.go:228`), the domain port (`domain/repositories/repositories.go`, `SeatRepository`),
   and every fake that implements them: `fakeSeatAdmin` (`seat_admin_mount_test.go:243`),
   `fakeSeatAdminStore` (`seat_admin_service_test.go:92`), `fakeStore` (`manage_seat_controller_test.go:86`).
3. Read path — the domain type, the port method, the adapter, the route (`seat_admin_mount.go:350`
   beside it), the handler, and `fakeSeatAdmin.ListSeatOccupantChanges`.
4. Tests per §10, then `go -C agenthub_go test ./... -count=1`.
5. Doc of record corrections in the same task: `ai_docs/api-integration/surface-inventory.md:274-275`
   calls `seatMutation` "a broadcast + audit wrapper" — it audits nothing; correct it and add the route
   to the route list at `:252-257`. One line in
   `ai_docs/agent-system/seat-model-and-mcp-surface.md` §"The seat model" (`:13-28`) naming the record.
6. One `CHANGELOG/2026-10-20--<title>.md` for the build task, plus the `TEST-CHANGELOG.md` entry.

Out of scope, stated so nobody adds it here: a history UI (`agenthub-frontend`, its own follow-up —
`SeatDetailPage.tsx:689` shows the current pair only), an MCP action, recording create/permission-policy/
pin changes, and any backfill. The client needs no change: it reads only `success` from the PUT
(`agenthub_client/internal/clientsync/switchverb.go:236`) and refetches the seats list for display.
