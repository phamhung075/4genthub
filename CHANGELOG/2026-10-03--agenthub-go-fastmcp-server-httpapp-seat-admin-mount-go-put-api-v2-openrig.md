### Added

**Module authoring and the 4genthub development team** (2026-10-03)

- `agenthub_go/fastmcp/server/httpapp/seat_admin_mount.go`: `PUT /api/v2/openrig/modules/{slug}/versions/{version}` creates a module version (immutable; identical content is a no-op, different content for the same version is 409, secrets are rejected with 422); sentinel errors `ErrModuleKindConflict` and `ErrModuleVersionConflict` in `repositories.go`; validators in `names.go`; `resolver.ValidKind`.
- `scripts/openrig_team_setup.py`, `scripts/team/4genthub/`: idempotent setup of the OpenRig room `4genthub-dev` (nine seats, links, project, area and mission modules, company and seat overlays) through the API. The brain stays in 4genthub; OpenRig runs the room.
- `/health` reports `0.0.9`.
