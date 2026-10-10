### Added

**`GET /api/v2/openrig/machines` reports hash drift per seat** (2026-10-03)

- Each seat now carries `expected_hash` (hash of the seat's latest stored resolved snapshot, empty when the room or seat is not in the cloud; no re-resolve on read) and `sync` (`in_sync` | `drift` | `unknown`), after `hash` (the running hash). `seat_management/domain/seatsync` holds the single rule: `unknown` if either hash is empty, `in_sync` if equal, else `drift`.
- `machine_status_repository.go` `List`: `seat_status` joins `rooms` (slug), `seats` (seat_key) and the newest `resolved_seats` row (created_at, id), every join on the same `user_id`. `SeatStatus.ExpectedHash` is read-only; `ReplaceSnapshot` ignores it. No schema change.

**Communication guard on every seat type (comm-guard)** (2026-10-03)

- `seat_management/domain/seedlibrary/shared-modules/`: two shared modules appended to every seed (single definition, embedded): tool `comm-guard` (`permissions.deny`: `rig send`, `rig queue`, `rig broadcast`, `tmux send-keys`, `tmux paste-buffer`; `permissions.allow`: `seatcheck send`) and skill `comm-guard-skill` (the only way to message a seat is `seatcheck send --to <seat> --intent <intent> -- <text>`; exit 3 = denied, do not try another way). `seedlibrary.Parse` now takes the shared modules; `seedmap.Spec.Shared` appends them and skips tool modules for a codex seat type (tool modules are Claude settings fragments), so a codex seat type is NOT deny-guarded at L2, it only gets the skill.
- `seat_management/domain/seatrenderer/renderer.go` `mergeToolModules`: `permissions.deny/allow/ask` are now the deduplicated union across tool modules (before: a later module with a `permissions` key replaced the whole object and dropped comm-guard's deny); other keys stay later-wins; a non-array or non-string list is an error naming the module.
- `seedVersion` 1.0.0 -> 1.1.0 (`seedmap.go`): a stored seat type version is immutable, so re-seeding a tenant with the new module set needs a new version. Existing tenants gain `1.1.0` on the next `POST /seat-types/seed`; no old-version path. `healthVersion` 0.0.10 -> 0.0.11. Not deployed.
