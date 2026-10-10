## 2026-10-11 — operations doc: `seat reseat` and `send`

### Added
- `ai_docs/operations/syncing-seats-with-the-cloud.md`: the `4genteam seat reseat` and `4genteam send` commands,
  why `seat sync --relaunch quiet` cannot restart a seat whose pin is already current, and the launch-timeout rule.
- Client change behind it: `agenthub_client` commits `seat reseat`, `send` and the relaunch check (see its CHANGELOG).

### Testing
- `go test ./internal/clientseat/` passes; `fe-dev` was restarted with `seat reseat` and runs in the live rig directory.
