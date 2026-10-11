### Fixed

**Creating a seat validates the occupant** (2026-10-03, found driving the UI)

- `POST /api/v2/openrig/rooms/{room}/seats` checked only the runtime, so a Claude model on `codex` and a model id such as `a b; rm -rf` were stored (and later rendered into the rigspec and passed to `rig seat set-model`), while `PUT .../occupant` rejected both. `handleCreateSeat` (`server/httpapp/seat_admin_mount.go`) now uses `repositories.ValidateOccupant(runtime, model)`, the same rule as the occupant switch: 400 and nothing stored; an empty model stays allowed.
