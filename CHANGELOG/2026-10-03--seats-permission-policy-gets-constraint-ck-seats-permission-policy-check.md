### Fixed

**An empty permission policy can no longer be stored or rendered** (2026-10-03)

- `seats.permission_policy` gets `CONSTRAINT ck_seats_permission_policy CHECK (permission_policy IN ('locked', 'standard', 'open', 'yolo', 'none'))`, like `ck_seat_links_kind` (`seat_tables.go`, `seat_management_postgresql.sql`); a test ties the list to `resolver.PermissionPolicies`. `rigspec.RenderRoom` rejects a seat without a valid policy instead of rendering no line (an absent line meant the OpenRig floor, not `standard`).
- `PUT .../seats/{seat}/permission-policy` logs the user id, room, seat and the new policy.
- Production: a column added with `DEFAULT 'standard'` satisfies the CHECK for existing rows; a manual fill with `''` does not. Owner decision, no migration shipped.
