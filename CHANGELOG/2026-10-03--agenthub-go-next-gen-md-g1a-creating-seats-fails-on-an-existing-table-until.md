### Changed

**`NEXT_GEN.md` G1a: dropping `seats.status` is mandatory** (2026-10-03)

- `agenthub_go/NEXT_GEN.md` G1a: creating seats fails on an existing table until `ALTER TABLE seats DROP COLUMN status` runs. Documentation only, no tests run.

**`NEXT_GEN.md` seat removal and production schema list** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: G1 and Request 11 say seat removal is a hard delete (`945648f5`); G1a lists all pending production schema changes. Documentation only, no tests run.

**`MaxRoomNameLength` lives with the Room entity** (2026-10-03)

- The 200-character room-name limit is defined once, as `repositories.MaxRoomNameLength` directly above `Room` in `seat_management/domain/repositories/repositories.go` (it was in `names.go`); `ValidateRoomName` in `names.go` and the `rooms.name` comment in `seat_management_postgresql.sql` refer to it. No behavior change.
