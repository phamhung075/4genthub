### Added

**Bridge v1: 4genteam and herdr status to 4genthub** (2026-10-03)

- `scripts/bridge.py`, `scripts/scrub.py`: background bridge (allow-list payload, secret scrubber, heartbeat, printed systemd unit).
- `agenthub_go/fastmcp/seat_management/domain/secretscan/`, `server/httpapp/seat_status_mount.go`, `infrastructure/repositories/orm/machine_status_repository.go`, tables `machines` and `seat_status` in `seat_management_postgresql.sql`: `POST /api/v2/seat-status`, `GET /api/v2/machines`; bodies containing secrets are rejected with 422.
- `.gitignore`: exception for the `secretscan` directory (the `*secret*` rule hid it).
- Frontend: machines panel, see `agenthub-frontend/CHANGELOG.md`.
