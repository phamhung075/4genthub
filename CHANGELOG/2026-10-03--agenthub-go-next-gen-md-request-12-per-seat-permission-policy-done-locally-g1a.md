### Changed

**`NEXT_GEN.md` per-seat permission policy and recent commits** (2026-10-03)

- `agenthub_go/NEXT_GEN.md`: Request 12 per-seat `permission_policy` done locally; G1a gains the `seats.permission_policy` column; commits `9115b6ab`, `1afc7555`, `e9a0c106`, `67ac9042`, `ed5c241f` and the seatcheck PATH limit recorded. Documentation only, no tests run.

**The seat checker PATH limit is stated** (2026-10-03)

- Seats inherit the PATH the OpenRig daemon had when it started (visible only as the daemon's tmux `-e PATH=` environment); `rig` 0.6.3 exposes it nowhere (`rig daemon status` has no `--json`, `rig whoami --json` carries no environment), so `openrig_seat_sync.py` cannot check it cheaply. The `install-checker` and `pull`/`rig` messages, and the script docstring, now say that the check reads the PATH of the current shell and tell the operator to restart the daemon (`rig daemon stop`, `rig daemon start`) from a shell where `seatcheck` resolves.
