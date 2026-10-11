### Added

**Bridge v1: OpenRig and herdr status to 4genthub** (2026-10-03)

- `scripts/openrig_bridge.py`, `scripts/openrig_scrub.py`: background bridge (allow-list payload, secret scrubber, heartbeat, printed systemd unit).
- `agenthub_go/fastmcp/seat_management/domain/secretscan/`, `server/httpapp/seat_status_mount.go`, `infrastructure/repositories/orm/machine_status_repository.go`, tables `machines` and `seat_status` in `seat_management_postgresql.sql`: `POST /api/v2/openrig/seat-status`, `GET /api/v2/openrig/machines`; bodies containing secrets are rejected with 422.
- `.gitignore`: exception for the `secretscan` directory (the `*secret*` rule hid it).
- Frontend: machines panel, see `agenthub-frontend/CHANGELOG.md`.
