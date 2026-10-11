# Seat compaction supervisor

Keeps every seat of a rig under a per-session context limit without cutting a job short, and forces
compaction when a seat does not compact on its own. The harness itself only compacts near 850k, far past
what a seat can work with.

Code: `agenthub_client/src/agenthub_client/compact.py` (the loop), `watch.py` (the limits), and
`agenthub_client/rust/forcecompact/` (the RPC tool). **CORRECTED 2026-10-10 (writer seat, at the pinned client commit `eaa6ba7`): the first two names are the retired Python's, and the third half of this sentence still stands.** The loop is `agenthub_client/internal/clientlifecycle/supervisor.go`, whose own header reads *"the compaction supervisor: the loop, one pass of it, and the start/stop/status of a supervisor process, ported from `compact.py` and `cli.py`"*; the limits are read by `agenthub_client/internal/seatlog/seatlog.go:35` (`ApplyLimits` reads `COMPACT_LIMIT_TOKENS`, `COMPACT_WARN_TOKENS` and `COMPACT_HARD_TOKENS`) and the token bars read them at `agenthub_client/internal/clientwatch/grid.go:31`; and `agenthub_client/rust/forcecompact/` **is still in the client at the pin** (four files, including `src/main.rs`), so that citation was never stale. Run it with `4genteam compact [RIG]` (detached, log
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
| `omp` | RPC compact through `forcecompact`; omp applies it at its next turn boundary | `/abort`, then the RPC compact |
| any other | `/compact` as soon as the seat is idle | Escape in the tmux pane while working, then `/compact` once idle |

Why two paths: the omp runner (`pi-runner.js`) turns pane text into an RPC `prompt` (idle) or `steer`
(streaming) and handles only `/abort` and `/followup` as commands. A `/compact` typed into a working omp
seat is therefore read as text. `forcecompact` duplicates the runner's socket end with `pidfd_getfd(2)` and
writes `{"type":"compact"}` straight to omp, which reads it whatever the seat is doing.

## Witness, retry, resume

- A send counts only when a new `"type":"compaction"` record appears in the log, or the context falls
  below 60% of its value at the send. The log shows `WITNESSED (226k -> 32k)`.
- No witness within 180 s logs `NOT witnessed` and the seat is retried. After a witnessed compaction the
  same seat is not considered again for 900 s (`COOLDOWN`).
- After a witnessed compaction the seat is sent a resume message (re-read the role file and board item,
  check the working tree, carry on), so the owner does not type "continue".
- Interrupts of the same seat are at least 60 s apart.

## Requirements and traps

- `forcecompact` needs `CAP_SYS_PTRACE` on Linux with Yama `ptrace_scope=1`:
  `sudo setcap cap_sys_ptrace+ep agenthub_client/rust/forcecompact/target/release/forcecompact`.
  **A rebuild clears the capability.** `4genteam up` builds the binary when absent and prints the setcap
  command when the capability is missing.
- An RPC compact sent mid-turn is applied at the turn boundary, so a very long turn can stay over the limit
  for a while (`go-dev` went from 534k to 100k only when its turn ended). The 300k abort exists for that case.
- The 300k abort path has not fired in production yet; the 250k RPC path has (`reviewer`, 279k).
- The supervisor is a Python process: restart it (`4genteam compact <rig>`) after editing `compact.py` or
  the limits. The uv install of `agenthub_client` is editable, so no reinstall is needed.
- Seats are discovered from OpenRig at run time; a seat whose session log cannot be found is skipped.
