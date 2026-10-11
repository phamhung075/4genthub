### Added

- `agenthub_go/fastmcp/seat_management/domain/rigspec/`, `server/httpapp/seat_rigspec_mount.go`: `GET /api/v2/openrig/rooms/{room}/rigspec` renders a room as RigSpec 0.2 (validated with real `rig spec validate` and `rig spec preflight`).
- `scripts/openrig_seat_sync.py`: `rig ROOM` subcommand builds a launchable `rig.yaml` plus pinned `agents/<seat>` links.
