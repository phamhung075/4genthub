### Fixed

**Overlay content is scanned for secrets** (2026-10-03)

- `PUT /api/v2/openrig/overlay`, `/rooms/{room}/overlay` and `/rooms/{room}/seats/{seat}/overlay` stored override content unscanned, while module versions were scanned. `seatAdminOverlayOps` (`server/httpapp/seat_admin_mount.go`), shared by the three routes, now runs `secretscan.Contains` on every op's content and answers 422 `secret detected in content` without echoing the secret; nothing is stored.
