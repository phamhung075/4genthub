### Fixed

**A guarded seat prompted for its own startup `rig whoami`** (2026-10-03)

- `seat_management/domain/seedlibrary/shared-modules/comm-guard.json`: `Bash(rig whoami:*)` joins the allow list next to `Bash(seatcheck send:*)` (read-only; under the default non-yolo policy the seat prompted for `rig whoami --json` and nobody could approve it because `rig send` is denied). Nothing else is allowed. `comm-guard-skill.md` explains exit code 5 (allowed but not delivered). `seedVersion` 1.1.0 -> 1.1.1: a stored module version is immutable, so a changed module needs a new version.
