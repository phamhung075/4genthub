### Changed

**Seat model coherent with OpenRig** (2026-10-03)

- `agenthub_go/fastmcp/seat_management/domain/commpolicy/policy.go`, `infrastructure/schema/seat_management_postgresql.sql`, `infrastructure/database/seat_tables.go`: link kinds are now OpenRig's five (`delegates_to`, `spawned_by`, `can_observe`, `collaborates_with`, `escalates_to`); `reports_to`, `consults`, `notifies` removed; intent-to-kind mapping documented in `agenthub_go/NEXT_GEN.md`.
- `agenthub_go/fastmcp/seat_management/domain/repositories/names.go`, `server/httpapp/seat_admin_mount.go`: room slugs and seat keys validated with OpenRig's id rule (no dots or spaces).
- `scripts/openrig_seat_sync.py`: safe-name rule relaxed to the OpenRig rule (uppercase allowed).
