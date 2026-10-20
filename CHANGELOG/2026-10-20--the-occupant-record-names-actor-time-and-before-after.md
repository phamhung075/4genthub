## The occupant record names who switched a seat, when, and from what to what

### Added

- `seat_occupant_changes` — one append-only row per stored change of a seat's occupant, carrying
  `actor`, `at`, `seat_id`, `from_runtime`, `from_model`, `to_runtime`, `to_model` (plus `id` and
  the tenant `user_id`), with the change declared in the six places a seat table must appear:
  `seat_management/infrastructure/schema/seat_management_postgresql.sql`,
  `seat_management/infrastructure/database/seat_tables.go`,
  `seat_management/infrastructure/database/seat_occupant_change_orm.go`,
  `seat_management/infrastructure/database/seat_occupant_change_orm_test.go`,
  `task_management/infrastructure/database/migrations/0001_baseline.sql`, and the idempotent step
  `fastmcp/task_management/infrastructure/database/migrations/0007_seat_occupant_changes.sql`.
- `GET /api/v2/rooms/{room}/seats/{seat}/occupant-history` — one seat's changes, newest first, as
  `{success, changes[]}`; registered without `seatMutation`, so it emits no frame. A team viewer
  reads through `seatAdminScope`, the same scope the seat list uses.
- `ai_docs/core-architecture/seat-occupant-record.md` — the design of record (task `84e06ad1`,
  architect), committed here because the branch it was written in had not landed it.

### Changed

- `ORMSeatRepository.UpdateOccupant` takes `actor` and does three statements in one transaction: a
  `SELECT … FOR UPDATE` of the stored pair, the `seats` overwrite, and the `seat_occupant_changes`
  insert. `from_*` is read under the row lock, so the trail cannot disagree with the row, and the
  insert and the overwrite commit or roll back together. An identical pair writes neither statement.
- `SeatAdminStore.UpdateSeatOccupant` / `SeatRepository.UpdateOccupant` /
  `seatAdminSource.UpdateSeatOccupant` carry `actor`; `SeatAdminService.SetOccupant` passes the
  authenticated caller and logs one `[SEAT] user … switched …` line beside the pin and
  permission-policy handlers. Every caller and fake is migrated; no shim.
- `ai_docs/api-integration/surface-inventory.md` lists the new route, its registration lines were
  refreshed from the source, and the `seatMutation` note now says it broadcasts and audits nothing.
- `ai_docs/agent-system/seat-model-and-mcp-surface.md` names the durable record.
- `agenthub-frontend/src/docs/apiReference.ts` regenerated (`go -C agenthub_go run ./cmd/apirefgen`):
  the new GET entry, 157 routes. Without it `TestTheCommittedArtefactMatchesTheProducer` fails in
  direction 1, because the page would understate the API.

### Testing

- `go -C agenthub_go test ./... -count=1` — exit 0; the suite that carries the new tests.
- Against a real PostgreSQL 16 (`tools/testpg/start.sh`, fresh cluster on port 55460):
  `SEAT_TEST_DATABASE_URL=… go test ./fastmcp/seat_management/infrastructure/repositories/orm/ ./fastmcp/seat_management/application/services/ -count=1`
  — exit 0, including `TestOccupantChangeIsRecordedIntegration` (two switches make two rows newest
  first, a repeat adds none, and deleting the seat takes them through the FK cascade).
- `TestUpdateOccupantRecordsTheChange` asserts the RECORD: the locked read, the `seats` update and
  the `seat_occupant_changes` insert with its arguments. Companions:
  `TestUpdateOccupantSkipsTheRecordForANoOp`, `TestListOccupantChangesIsTenantScoped`,
  `TestSeatAdminSetOccupantRefusesAnActorField`,
  `TestSeatAdminSetOccupantPassesTheAuthenticatedActor`,
  `TestSeatAdminOccupantHistoryReturnsOneSeatsChanges`, and
  `TestOccupantChangeIsRecordedIntegration` (skips without `SEAT_TEST_DATABASE_URL`).
- `TEST-CHANGELOG.md` records the suite changes.
