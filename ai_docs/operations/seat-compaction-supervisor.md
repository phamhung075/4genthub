# Seat compaction supervisor

Keeps every seat of a rig under a per-session context limit without cutting a job short, and forces
compaction when a seat does not compact on its own. The harness itself only compacts near 850k, far past
what a seat can work with.

Code: `agenthub_client/internal/clientlifecycle/supervisor.go` (the loop, one pass, and its start/stop/status), the limits at `agenthub_client/internal/seatlog/seatlog.go:35` (`ApplyLimits`), and the delivery path through the runtime daemon's `ForceCompact` IPC (below). The retired Python names (`compact.py`, `watch.py`) and the retired `agenthub_client/rust/forcecompact/` binary are gone - `agenthub_client/rust/` holds only `agenthub-runtime` (measured 2026-10-19 at client `872ae41`). Run it with `4genteam compact [RIG]` (detached, log
`logs/compact-supervisor-<rig>.log`); `4genteam up` starts it as part of the full lifecycle, and
`4genteam compact-run` is the foreground loop. Run it from the host, never inside a seat pane: a loop in a
seat dies with the seats it watches.

## The three tiers

Each limit is read from the environment (`COMPACT_LIMIT_TOKENS`, `COMPACT_WARN_TOKENS`,
`COMPACT_HARD_TOKENS`). The loop runs every 10 s and reads each seat's session log for its newest context size.

| Context | Seat is told | Supervisor does |
|---|---|---|
| 150k (`COMPACT_LIMIT`) | Once: find your own safe point, note what is done and next, stop and send nothing. Do not type `/compact`. | Waits until the seat's log is silent for `--quiet` seconds (default 15), then compacts it. |
| 250k (`WARN_LIMIT`) | Once: "VERY IMPORTANT", stop now; a compaction is requested and the turn is aborted at 300k. | Compacts now, without waiting for quiet. |
| 300k (`HARD_LIMIT`), still not compacted | (already warned) | Cuts the running turn, then compacts. |

How a compaction is delivered depends on the runtime:

| Runtime | 250k | 300k |
|---|---|---|
| `omp` | RPC `ForceCompact` through the runtime daemon; omp applies it at its next turn boundary | `/abort`, then the RPC compact |
| any other | `/compact` as soon as the seat is idle | Escape in the tmux pane while working, then `/compact` once idle |

Why two paths: the omp runner (`pi-runner.js`) turns pane text into an RPC `prompt` (idle) or `steer`
(streaming) and handles only `/abort` and `/followup` as commands. A `/compact` typed into a working omp
seat is therefore read as text. The runtime daemon relays `{"type":"compact"}` into the seat's mailbox
socket (`rust/agenthub-runtime/src/runner/mod.rs:1161-1178`), which omp reads whatever it is doing. The
retired `forcecompact` binary stole the runner's socket end with `pidfd_getfd(2)`; the relay replaced it.

## Witness, retry, resume

- A send counts only when a new `"type":"compaction"` record appears in the log, or the context falls
  below 60% of its value at the send. The log shows `WITNESSED (226k -> 32k)`.
- No witness within 180 s logs `NOT witnessed` and the seat is retried. After a witnessed compaction the
  same seat is not considered again for 900 s (`COOLDOWN`).
- After a witnessed compaction the seat is sent a resume message (re-read the role file and board item,
  check the working tree, carry on), so the owner does not type "continue".
- Interrupts of the same seat are at least 60 s apart.

## Requirements and traps

- No capability is needed: the retired `forcecompact` binary required `CAP_SYS_PTRACE` with Yama
  `ptrace_scope=1`; the runtime daemon's relay does not (`src/runner/mod.rs:20-21`).
- An RPC compact sent mid-turn is applied at the turn boundary, so a very long turn can stay over the limit
  for a while (`go-dev` went from 534k to 100k only when its turn ended). The 300k abort exists for that case.
- The 300k abort path has not fired in production yet; the 250k RPC path has (`reviewer`, 279k).
- The supervisor is a Go command (`4genteam compact <rig>`): restart it after a change to the loop or a
  limit, and no reinstall is needed because the client install is editable.
- Seats are discovered from 4genteam at run time; a seat whose session log cannot be found is skipped.
