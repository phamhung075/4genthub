### Changed

**`NEXT_GEN.md` status corrections** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: fixed defects marked with commit hashes; superseded items use `[~]` with a legend; F1 and F4 are unticked (check pending). Documentation only, no tests run.

**Permission policy is a property of each seat, rendered per member** (2026-10-03)

- Breaking, clean cut: the rig-level `permission_policy` line and the `?permission_policy=` query on `GET /api/v2/openrig/rooms/{room}/rigspec` are removed, and so is the `--permission-policy` flag of `scripts/openrig_seat_sync.py rig` (the script now takes the policy from the rendered spec). `rigspec.RenderRoom(roomSlug, roomName, seats, edges)` no longer takes a policy; `rigspec.Seat.PermissionPolicy` renders as `permission_policy: builtin:<name>` (or `none`) on that member.
- `seats.permission_policy TEXT NOT NULL` (ORM `SeatORM`, `seat_tables.go`, `seat_management_postgresql.sql`). The accepted values are `resolver.PermissionPolicies` (`locked`, `standard`, `open`, `yolo`, `none`), the one list shared by the seat service, the admin routes and the renderer. A seat created without a policy gets `resolver.DefaultPermissionPolicy` (`standard`, never `yolo`); an unknown one is a 400 naming the accepted values.
- New `PUT /api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy` (`{"permission_policy": "..."}`, tenant scoped, 404 for an unknown room or seat); `SeatBody` and `POST .../seats` carry `permission_policy`. A seat already launched keeps the posture it launched with; the next rigspec render carries the change.
- Production schema: `seats.permission_policy` is a new NOT NULL column (owner decision through the lead; no migration helper is shipped).
- Files: `seat_management/domain/{resolver,rigspec,repositories}`, `application/services/seat_admin_service.go`, `infrastructure/{database,repositories/orm,schema}`, `server/httpapp/{seat_admin_mount,seat_rigspec_mount}.go`, `scripts/openrig_seat_sync.py`.
- Verified: go vet, `go test ./seat_management/... ./server/...`, pytest `test_openrig_seat_sync.py` (66 passed), and the real `rig spec validate` + `rig spec preflight` on a rendered room for every policy (yolo preflights as `full_bypass`, none as `floor`). Not run: Postgres integration tests.
