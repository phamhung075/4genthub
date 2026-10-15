# `4genteam ps`: native room view without the 4genteam daemon

### Added
- `agenthub_client/internal/clientps/ps.go`: `4genteam ps [RIG]` (rollup banner + rig table), `--nodes`, `--compact`, `--grid` (card view with context meter and quota/error line), `--json`. Seats come from `tmux list-sessions` (`<rig>-<member>@<rig>`); a seat whose transcript tail (`~/.config/4genthub/transcripts/<rig>/`) shows a quota or credit message is `quota` and counts as needing attention.
- `agenthub_client/internal/clientwatch/snapshot.go`: `SeatSnapshot` exports the existing log/runtime/model/context-token reads so `ps` and `watch` agree.
- `agenthub_client/internal/clientps/ps_test.go`: session-name parsing, quota detection, rollup.

### Changed
- `agenthub_client/cmd/4genteam/main.go`: registers `ps`; the `rig ps` shim maps to `ps`; `status --nodes|--compact|--grid` routes to `ps`.
- The node table keeps only columns a local read can fill (no registry-only columns such as POD, ORIENTED, RESTORE).

### Testing
- `go test ./...` in `agenthub_client` passes; `ps 4genthub-min` in all four views reported 4 of 5 seats on `quota`.
