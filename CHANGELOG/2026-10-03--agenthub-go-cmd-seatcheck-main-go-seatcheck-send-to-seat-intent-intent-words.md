### Changed

**`seatcheck send` takes its identity from `rig whoami`** (2026-10-03)

- `agenthub_go/cmd/seatcheck/main.go`: `seatcheck send --to <seat> --intent <intent> -- <words>`. Rig and member come from `rig whoami --json` (single source); the seat directory is `<pins>/<rig>/<member>` with `policy.json` and an append-only `audit.jsonl` (0600, written before delivery). `--pins` (default `~/.openrig/agenthub-seats`, constant `defaultPinsDir`) is the only path flag. Delivery is `rig send <seat>@<rig> "<words>"`; its exit code passes through. Removed: `--policy`, `--audit`, `--deliver-cmd`. A missing or corrupt policy, a failed identity lookup and usage errors exit 2 with nothing delivered or audited; denied exits 3; audit write failure exits 1.
- Breaking for anything calling the old flags (none in the repository).
