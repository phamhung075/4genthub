## C3 holds at the installed tip, and the `send` path reports a real submission

### C3 — the count is 0 and the check is measured, at the tip the seats run
Measured 2026-10-14 on `feat/support-agy-watch` tip `4567c37` (the build the live seats run), with the pinned
instrument — *a call site that ISSUES an exec of the program named `rig`*, non-test Go only:

- `git grep -n 'rig\.Run' 4567c37 -- internal cmd` → **no hits**.
- `git grep -n 'exec\.LookPath\|exec\.Command(' 4567c37 -- internal cmd` → every hit names another program
  (`agenthub-runtime`, `tmux`, `pgrep`, `pkill`, `tail`, `herdr`, `git`, the client's own binary).
- The only literal `"rig"` in non-test Go is flag names, JSON field names, a room name in bridge testdata,
  and two comments. `internal/clientseat/sync.go:24` spawns `self sync rig …` — its own binary, not `rig`.
- `rig-shim` is gone (`8193820`): the only remaining mention is `clientruntime/command_test.go:5-10`, which
  pins its absence.
- The 39 remaining `openrig` strings are cloud route names (`/api/v2/openrig/…`) — the server's own path
  segment, not a client dependency.

**The check, with `rig` unreachable** (`PATH=/home/daihu/.local/bin:/usr/bin:/bin`; `command -v rig` prints
nothing):

| invocation | exit | first line |
|---|---|---|
| `4genteam whoami --json` | 0 | identity JSON |
| `4genteam ps 4genthub-min --nodes --json` | 0 | the seat array |
| `4genteam room queue list 4genthub-min` | 0 | `room 4genthub-min: the rail is empty` |
| `4genteam send` | 2 | `4genteam send: SESSION and MESSAGE, or RIG SEAT and MESSAGE, are required` |

Two notes for whoever reads the plan's row next: the plan's check names `queue`, which as a top-level verb no
longer exists — the native spelling is `4genteam room queue list ROOM`; and the earlier "`queue list` exits 1"
report was a **stale daemon refusing `QueueList`** (go-dev measured it at 05:2xZ), which the 21:09 daemon
restart cleared — measured above as exit 0.

### C2 — `send` reported a real submission, and the agent acted on it
`4genteam send 4genthub-min reviewer '<the R2 gate request>'` printed `Sent to
agenthub--4genthub-min--reviewer` — the runtime's `submitted` branch, not `Pasted to …, submission
unconfirmed` (`041c18b`). The stronger evidence is the pane: within seconds the reviewer's transcript showed
it running the gate commands it was asked for (`git rev-parse HEAD`, `git worktree list`, `git log 666978b`),
so the text was not left staged in the input box. The same shape held for the go-dev and fe-dev briefs.

### Still open
- The forced-provider-stream-error half of C2: allotted to fe-dev, on a scratch room.
- C4's U3 run: the harness's bytes are recovered at `/tmp/acc.bak7` (1564 lines, the run-11 vintage; the
  canonical copy under `~/.openrig/agenthub-seats/4genthub-min/` is gone with the seat home).
