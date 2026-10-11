## The OF4 local-stack recipe instructed two scripts the tree no longer has

### Fixed
- `ai_docs/verification/of4-local-stack.md`: §6 named the seeding entry point as `scripts/openrig_team_setup.py apply [--team DIR]` with citations into that file (`:77-82`, parser at `:925-928`) — **a path absent from the working tree and the index, so the citations pointed into a file no reader can open** — and §7's launch recipe ran `python3 scripts/openrig_seat_sync.py rig of4room --out …`, which no longer runs at all. Both now name the live verbs: `4genteam team apply [--team TEAM] [--dry-run]` and `4genteam sync rig ROOM [--out OUT] [--update]`, each with a dated correction naming the module's real home (`agenthub_client/src/agenthub_client/team_setup.py`, `seat_sync.py`). The dead citations are struck with the path rather than left dangling.

### Verified
- `4genteam team apply --help` -> `[--dry-run] [--team TEAM]`; `4genteam sync rig --help` -> `room` with `--out` (default `~/.openrig/agenthub-seats`) and `--update`. `grep -n "scripts/" ai_docs/verification/of4-local-stack.md` -> the two corrected lines were the only `scripts/` claims the file carried.
