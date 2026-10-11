## `4genteam up` starts every service the client needs, and the supervisor force-compacts omp seats at the hard limit

### Added
- `agenthub_client/src/agenthub_client/cli.py`: `up` now runs `ensure_daemon`, `ensure_rig` (`rig up RIG --existing` when any seat is not running), `ensure_forcecompact` (builds the binary when absent; prints the one-time `sudo setcap cap_sys_ptrace+ep` command when the capability is missing), `start_bridge`, then the supervisor, the herdr watch view and the UI. `stop` also stops the bridge.
- `start_bridge` runs the status bridge detached (log `logs/bridge.log`), loading `AGENTHUB_URL` and the machine token from `~/.config/agenthub-bridge.env`. Before this the bridge ran only under a systemd unit that WSL has no bus for: the server's last report was 2026-10-07 and the machine read offline. A report brought it online with 36 seats.
- `agenthub_client/rust/forcecompact/` (std-only Rust): finds a seat's `omp --mode rpc` socket through `/proc` and `ss`, duplicates the runner's end with `pidfd_getfd`, and writes an RPC `compact`. `paths.FORCECOMPACT` points at the built binary; it needs CAP_SYS_PTRACE, which a rebuild clears.

### Changed
- `agenthub_client/src/agenthub_client/compact.py`: at `HARD_LIMIT` an omp seat gets that RPC compact whatever it is doing (a typed `/compact` is read as text by a working seat); a send with no witness resets the cooldown so it retries; notices no longer block the loop.

### Verified
- `agenthub_client/tests/test_cli.py`: new `test_up_initialises_every_service_in_order`; 6 passed. Live: `lead` 499k to 33k by the tool, `reviewer` and `context-dev` witnessed by the supervisor; nine `4genthub-min` seats `in_sync` after `4genteam sync pull`. The supervisor's own hard-limit call has not yet fired (no seat past 300k).
- Not done: edges for the Topology page. The server refuses allowing links on omp seats, so the graph for `4genthub-min` needs the bridge to report OpenRig's edges; queued to the lead, server half first because the status route rejects unknown fields.
