### Added

**Per-member permission policy in the rendered RigSpec (domain)** (2026-10-03)

- `seat_management/domain/resolver/permission.go`: `PermissionPolicies` (`locked`, `standard`, `open`, `yolo`, `none`, the bare names of `rig policy list`), `DefaultPermissionPolicy` (`standard`, never yolo) and `CheckPermissionPolicy`, the one list; `rigspec.ValidatePermissionPolicy` reads it. `rigspec.Seat.PermissionPolicy` renders `permission_policy: builtin:<name>` (or the literal `none`) on the member, no line when empty; member overrides the rig-level line (OpenRig precedence member > rig > floor). The seat model, API and client script follow in a later commit.
- `rigspec` cycle test: self-loop cases (`a delegates_to a`, `a spawned_by a`).
