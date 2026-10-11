### Fixed

**Overlay ops must name modules the catalog holds** (2026-10-03, found driving the UI)

- `agenthub_go/fastmcp/server/httpapp/seat_admin_mount.go`: `PUT` of a company, room or seat overlay stored an `add` or `pin` op for a module (or module version) that does not exist; every later resolution of the seats it reached then failed with `module X@latest not found in catalog` (the preview route answered 404 for a seat that exists). The three overlay routes now answer 422 `module <slug>@<version> not found in catalog` and store nothing; the room and seat lookups (404) still run first, and `remove`/`override` ops are not checked because they may name modules only the seat type supplies.
- Tests: `TestSeatAdminOverlayRejectsUnknownModules`; `TestSeatAdminOverlays` and `TestSeatAdminGetOverlays` now seed the modules their ops name.
