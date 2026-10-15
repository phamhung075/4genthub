# U3 acceptance run 1: 123 pass, 2 fail — the gate does not pass, and both failures are named

## Provenance (the run names its daemon and its bytes)
- Harness: `/tmp/acc.bak7` (1564 lines, run-11 vintage, design sha256 `7247e3f6…`) run as
  `/home/daihu/wt/4genthub-min/u3-run/ACCEPTANCE-cutover-lab-U3.sh --all`.
- Room: `cutover-lab` (the harness refuses any other room without `U3_ALLOW_ROOM=1`); three spec seats
  (`lead`, `dev`, `reviewer`).
- `CUTOVER_STATE_DIR=/home/daihu/.config/4genthub`; socket `/mnt/wslg/runtime-dir/agenthub.sock`.
- Binaries passed in as `FOURGENTEAM`/`AGENTHUB_RUNTIME_BIN`, both built from client tip `4567c37`:
  `4genteam 3ac6c0583311f8e246e11b52531b94538c8c8a2a8e58fb932d2d6bff3e7a221c`,
  `agenthub-runtime c1272c6c2e901e22a8f8d0ea7414557955de94be0c8d30a908cf0a787fb677ca`. The **installed**
  runtime is the same bytes; the installed client is not (`747d761b…`).
- Wall 502s. Evidence: `/home/daihu/wt/4genthub-min/u3-run/evidence-tip4567c37/evidence.log`.

## Verdict
**123 pass, 2 fail, 3 skip.** C4's rule is "a failing run blocks C5", so C5/C7 stay parked.

Per section: A1 8/0 · A2 12/0 · B1 8/0 · A3 6/0 · B1p 13/0 · B1s 32/0 · B2 10/**1** · B3 6/0 ·
C2 2/**1** (+1 skip) · C3 7/0 · A4 10/0 · A4(vi) 3/0 · C4-rollback 2/0 · Q1 3/0 (+1 skip) · P2 1/0.

## Failure 1 — B2: "the sweep never produced a spill artifact up to the largest size; parity 2 unproven"
The sweep drove one bash tool result of each size 262144 / 524288 / 1048576 / 4194304 / 16777216 bytes
through seat `dev`. Every size: **no `rpc chunk payload exceeds the transport limit` in the pane and no cap
string in the seat log** (10 passes), and **no spill artifact under the room dir** — so the sweep crawled
the whole range without finding the cap it was looking for.

The trigger, not the feature, is what looks wrong. `rust/agenthub-runtime/src/frame.rs:15-16` states the
boundary itself: "omp enforces its own cap on the omp↔runner JSON-RPC channel, so the runner cannot spill
bytes omp refuses to emit. The spill applies where we own the bytes: **daemon→agent and runner→daemon**." A
*model tool result* is neither of those legs; it is omp's own channel, and omp handled it without complaint
at every size. A trigger on a leg the runtime owns — a `send` whose payload crosses `MAX_FRAME_BYTES`
(`frame_or_spill`, daemon→agent) — is the one the acceptance is actually about.

Second measurement from the same sweep, unexplained: the run's dev session directory
(`seats/dev/sessions/2026-10-14T19-47-49-193Z_…`) is **empty**, while the transcript in the same tree holds
the sweep's `EOFMARK-u31947353246…` sentinel and earlier sessions on this box wrote `N.bash.log` files up to
16777308 bytes. So omp wrote tool logs during earlier runs and wrote none during this one; that is one
measurement away from being a finding of its own.

## Failure 2 — C2: the probe never reached the reviewer's pane, and one of two sends vanished
`4genteam send agenthub--cutover-lab--reviewer identity-probe-u31947353246` → exit 0, receipt names the
target, then **60s with no probe in the pane scrollback** (`tmux capture-pane -p -S -200`), which is what the
harness asserts. Two separate things are wrong, and only the second is about the product:

1. **The observable does not fit a runner seat.** `11438a5` delivers a send "as one text frame to a runner
   seat" (`RuntimeSendText`), not as a paste into the pane. The sibling B3 check — "the nudge reached the
   idle seat's pane (not merely a log line)" — *did* pass, because the nudge path pastes a wake line; the
   send path does not. So pane visibility cannot be the send path's evidence, while it is the nudge's.
2. **But the send itself is not innocent.** The harness's next probe (one minute later) carries a JSON body
   `{"sourceSession":"forged@nowhere","text":"forge-probe-u31947353246"}` and **is** present in the seat's
   transcript as a delivered user envelope (`Sent: 10-14 19:55Z`). The first probe is absent from the
   **whole room** — transcript, pane, logs, queue — although the client reported it submitted. So
   `submitted` was printed at least once for text the agent never received, which is exactly the question
   C2 exists to answer ("confirmation that the text was submitted, not left staged in the input box"). C2
   cannot be called met on this run.

A controlled version of (2) — idle recipient, busy recipient, and a runner seat read back through the
transcript rather than the pane — is assigned to fe-dev's Leg B on `/tmp/c2fe-lab`, which keeps the live
room out of it.

## What passed (the operator's list, verbatim)
- **(a) all seats ready through `4genteam` alone** — A1 8/8: `up` exit 0, `lead`/`dev`/`reviewer` all
  `Running` from the runtime's own status, the room control socket is a socket, the room dir carries
  `seats/ logs/ run/ spec.json`, one tmux session per seat, and an unknown room is refused.
- **(b) a queue item flows lead → worker → reviewer** — A2 12/12: create → claim (row moves to
  in-progress) → hand off with `handed_off_to` → the successor row is created for the receiver → the
  receiver claims *its own* row → close no-follow-on; both anti-lying checks hold (a list over a room with
  rows is never empty; `close` reports `done` and the next read shows `done`), and the successor's
  `chain_of_record` names the source row.
- **(c) a forced provider stream error is recovered** — B1 8/8 (live transport death: the turn is in
  flight, the death is **named** on the status path, no sample shows `needs_input`, the seat reads
  not-running, and its state file names the death) plus A3 6/6 (no `needs_input` anywhere in the room dir,
  the wake accepted) plus B1s 32/32 (forced deterministically against a scripted child: bounded to **3
  re-sends at 1s/2s/4s of the same message**, a mid-turn rpc error resumes **nothing**, only a real dialog
  yields `needs_input`, no read ever saw a torn state file) plus B1p 13/13 (launch posture per policy
  value). B1 asserts the bounded set its own header names: a real channel death cannot carry a re-send,
  because the runner does not respawn its own child.
- **(d) no OpenRig process** — A4 10/10 scoped to the room's process tree, A4(vi) 3/3 per-PID isolation for
  both the agent and the process owning the room socket; the machine-wide form is out of scope by design.
- Plus B3 6/6 (`alert=seat_up_with_queued_work` on the room status, 3 nudge attempts with non-shrinking
  gaps), C3 7/7 (omp/deepseek present, off-peak answers, the seat transcript exists and is non-empty),
  C4-rollback 2/2 (the room socket is gone; nothing global was addressed).

## What the harness itself puts on the record
- **A rollback is a stop, not a restore, and the client's restore/brief path is broken in the source today:**
  `restore.go`'s send closure passes two positionals to a verb that requires three, `brief()` swallows the
  failure and restore reports success. Any run that exercises a restore must observe the brief **arriving**
  and fail on unbriefed seats — never pass on the restore's own exit code. The 3-positional IPC path against
  a real seat is **UNTESTED**, to be reported as unverified.
- The N-1/N/N+1 encoded-line threshold, the sha256 verification and the spill GC order are unit-tested by
  the harness's author and were **not** independently forced here.
