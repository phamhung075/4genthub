### Fixed

**Overlay slug and version are scanned too** (2026-10-03)

- `seatAdminOverlayOps` (`server/httpapp/seat_admin_mount.go`) ran `secretscan.Contains` on op content only; slug and version are free strings echoed back by the overlay body, so they are scanned as well (422 `secret detected in content`, nothing stored).
