# U3 run 4 proved the isolation works, and one missing empty directory starved nine legs

## What happened
Acceptance run 4 (`--all`, harness `wt/4genthub-min/u3-run/ACCEPTANCE-cutover-lab-U3.sh`, tip binaries
from `wt/4genthub-min/u3bin`, evidence `wt/4genthub-min/u3-run/evidence-run4-isolated-20261014T2055Z`)
scored **69 pass, 1 fail, 9 skip** — and it was the first run whose socket belonged to the run:

```
CUTOVER_STATE_DIR=/tmp/u3run4/state
XDG_RUNTIME_DIR=/tmp/u3run4/rt
AGENTHUB_RUNTIME_SOCKET=/tmp/u3run4/rt/agenthub.sock
fixtures seeded: spec.json + team/team.json     fresh daemon: 0 queue fds at start
```

**The isolation is proven, not asserted.** A4's process tree for the room reads
`agenthub-runtime --state-dir /tmp/u3run4/state runner cutover-lab/lead` and its `omp` child with a
session dir under the same isolated root, and carries no OpenRig or `pi-runner.js` cmdline. P2 passes
with its own words — *"the client's daemon listens THERE — the knob works"*. The daemon record reads:
the socket **predates this run's own `up`**, so the rollback **refuses** to stop it — which is the
behaviour that has to be right, because that daemon was the lead's and a run must not kill it.

## The single failure, and why it starved the rest
A1 failed one assertion of four: after `up`, `rooms/cutover-lab/logs/` does not exist. The harness's
own rule 2 then **skipped A2, B1, A3, B2, B3, C2, C3 and C4** with the stated reason *"A1 could not
bring the lab room up (its failures are above), so this leg would measure a room that is not there"*.
That is rule 2 working exactly as written — a stated skip, never a silent pass — but it means one
missing empty directory decided nine legs, and **run 4 is not the acceptance verdict either**.

## Cause: the room's `logs/` is asserted by the acceptance and created by nothing
- The harness asserts `for d in seats logs run … must NOT match DIR-MISSING` (`:618-619`) **and**
  removes `logs/` as run-state in the same leg (`RUN_STATE_SUBDIRS="run seats logs"`, `:245`;
  `rm -rf` at `:263`). A room can therefore pass only if `up` recreates the directory.
- **No product code does.** The client has no `rooms/<room>/logs` path at all — its only `logs` is the
  **state-root** one, `clientservices/services.go:151` (`<base>/4genthub/logs`) — and the Rust runtime
  never mentions `logs`.
- On disk: `rooms/cutover-lab` (post-`up`), `rooms/4genthub-min` (**the live room**),
  `rooms/test-alpha`, `rooms/q1probe-badcwd`, `rooms/q1probe-badrt` have **no** `logs/`. Only
  `rooms/p2default/logs` and `rooms/q1probe-ok/logs` exist, both **empty**, dated 12:11-12:12 — created
  by a harness path, not by the product.
- **Second consequence, same cause:** B2 reads `logs/$VICTIM.jsonl` for the cap string, so its
  *"cap string absent from the seat log"* PASSes are **vacuous** while that file does not exist.
- **Where the product's logs actually are, read from the source:** the client's only `logs` is the
  **state root** — `clientservices/services.go:151` and `clientrestore/paths.go:47`
  (`logDir() = stateSubdir("logs")`), which holds `logs/rig-watchdog.log` — and the native client's own
  definition of **a seat's log is its session transcript**, `internal/seatlog/seatlog.go:80-82`
  (`NewestSession`: the most recently written `*.jsonl` under `<seat dir>/sessions`). The Rust runtime
  never mentions `logs` at all **at that tip, and that is the tell: `cc0c62f` had retired the room's
  `logs/` on purpose ("*The dead `logs/<seat>.jsonl` creation is removed*").** The room's `logs/` is a
  **third** thing — the runtime's own pane mirror per seat — and go-dev's `2800dfb` restored it. See Fix.

## Fix
- **RULING, RESTORED — THIS SECTION CARRIED TWO WRONG STATEMENTS OF MINE AND THIS IS THE THIRD AND
  CORRECT ONE (lead; evidence read in full: `cc0c62f`, `2800dfb` and the revert `0277556` in
  `agenthub_client`).** The room's `logs/` **belongs to the layout and the acceptance is right to assert
  it.** `cc0c62f` retired it on purpose ("*The dead `logs/<seat>.jsonl` creation is removed*");
  go-dev's `2800dfb` restored it — `start_room` creates `seats/`, `logs/`, `run/`, and the runner mirrors
  the pane into `logs/<seat>.jsonl` — and my "harness-side fix" ruling made go-dev **revert it**
  (`0277556 revert(runtime): the room's logs/ is not product state`, 21:09:08Z). That revert is being
  undone on `4genthub-min/c3-printed-rig`, because the layout and the pane mirror are product state.
- **Two artifacts, not one:** the seat's **log** is the runner's pane mirror at
  `rooms/<room>/logs/<seat>.jsonl`, and the seat's **transcript** is omp's own
  `rooms/<room>/seats/<seat>/sessions/*.jsonl`. The harness's `victim_transcript()` globs the transcript
  and falls back to a literal `none.jsonl` **only when no transcript exists** — so a leg that prints that
  path is telling you the seat took no turn, not that the reader is wrong.
- **What is withdrawn:** dropping `logs` from `RUN_STATE_SUBDIRS`, re-pointing the B2 reader, and the
  harness edits made on that ruling (a `logs/` comment now sits at `:249`). They are to be reverted.
- **The starved legs are measured now, individually, in the same isolated rig** (`--check A2 B1 A3 B2
  B3 C2 C3 C4`, each with its own evidence dir, against the room run 4 brought up). A1's hygiene runs
  only inside A1, so an individual leg does not delete the directory and the measurement is not
  starved; the room's `logs/` was created by hand first, and the one leg that would have asserted the
  layout is the one that is not being run.

## Rules this run produced
1. **An unisolated socket is not a run** — `CUTOVER_STATE_DIR` and
   `XDG_RUNTIME_DIR`/`AGENTHUB_RUNTIME_SOCKET` must both be run-private, and the run's daemon must be
   fresh (0 cached rails), verified by a `daemon-started` record naming the socket inode and pid.
2. **A leg-failing precondition must not be able to starve the rest silently** — rule 2 already
   states each skip; the remaining gap is that a *fixture/layout* precondition (not a code
   precondition) is enough to skip eight legs, so the runner must read the skips as loudly as the
   failure.

## Limits
- Run 4 is not the acceptance verdict: nine legs are SKIP, and a skip is never a pass.
- Its 69 passes are the legs that need no room; they stand, and they are the first set measured
  through the run's own daemon on the run's own state root.
