# U3 run 4b: the room legs name ONE product defect (R6) and TWO instrument defects

Run 4b measured the eight legs run 4 starved, against the same isolated lab (`CUTOVER_STATE_DIR` set
first, state `/tmp/u3run4/state`, socket `/tmp/u3run4/rt/agenthub.sock`), on `agenthub-runtime` sha256
`c1272c6c…` and `4genteam` sha256 `3ac6c058…`, each leg with its own evidence dir under
`/home/daihu/wt/4genthub-min/u3-run/evidence-run4b-<LEG>-20261014T2100Z`. Legs, in order: A2, B1, A3,
B2, B3, C2, C3, C4.

## Verdicts

| leg | result | cause |
|---|---|---|
| A2 queue flow lead->dev->reviewer | **0 pass, 3 fail** | R6: the daemon's cached rail is a deleted inode |
| B1 channel death on a provider stream error | 6 pass, **2 fail** | `send` reached another daemon |
| A3 death reason + reseat | 6 pass, 0 fail | - |
| B2 RPC chunk-cap sweep | 10 pass, **1 fail** | the ten passes are VACUOUS; the one fail is honest |
| B3 idle nudge + backoff | 2 pass, **4 fail** | R6: the wake row could not be written |
| C2 send identity + submission confirmation | **0 pass, 3 fail** | `send` reached another daemon |
| C3 presence (offpeak/compaction/transcript/ps/grid/feed) | 6 pass, **1 fail** | the harness reads a literal `none.jsonl` |
| C4 rollback | 2 pass, 0 fail | - (it selected its daemon by the run's own `daemon-started` record) |

**32 pass, 14 fail - and this is NOT the acceptance verdict**: ten of the passes are vacuous and five
of the fails are the instrument's, not the product's.

## 1. R6 - the product defect (A2's three fails and B3's four): the daemon serves a DELETED rail

- A2's **first** command: `4genteam room queue create cutover-lab --to … --state-dir
  /tmp/u3run4/state --socket /tmp/u3run4/rt/agenthub.sock` → `cannot create queue row
  'qitem-20261014205558-b183f13beeef': attempt to write a readonly database` (exit 2). The follow-up
  `list` then answered **"the rail is empty"** although the file on disk is 36864 bytes and holds a
  `queue_rows` table.
- Proof of the mechanism, on the live process: `ls -l /proc/24854/fd` gives
  `12 -> /tmp/u3run4/state/rooms/cutover-lab/queue.sqlite (deleted)`. The daemon caches one
  `QueueStore` per room for its whole life; the harness's hygiene then removed the rail
  (`ACCEPTANCE-cutover-lab-U3.sh:245` `RUN_STATE_SUBDIRS`, `:263-265` removes `queue.sqlite` with its
  `-wal`/`-shm`) and `up` recreated it - and the daemon kept the deleted inode. **Writes answer
  SQLITE_READONLY, reads answer the deleted file's rows, for the rest of the daemon's life.**
- B3's four fails are the same cause: its wake row could not be created (`readonly database`), so no
  nudge was attempted, no alert appeared within 360 s, and `run/reviewer.nudge.jsonl` was never
  written ("backoff not demonstrated").
- The trigger is not exotic: **run-state cleared or replaced under a live daemon** - which the
  acceptance's own hygiene does deliberately and legitimately (it names what it clears and keeps
  `spec.json` and `team/`), and which any operator reset, any restore that rebuilds a room dir, and any
  second daemon started on the same state dir also does. `NEXT-GEN2.md` R6 already requires the daemon
  to survive it: "must not fail every write or answer stale rows after its rail is replaced under it
  (open per request, or revalidate `st_dev`/`st_ino` and reopen)". The fix is routed to go-dev with
  that test to write.
- **Correction to my own earlier record:** I first wrote that `stop` then `up` is the production path
  that replaces a rail. It is not - `4genteam room stop` leaves the room's directory in place and no
  product path deletes `queue.sqlite`. The trigger is external run-state clearing, as above.

## 2. The `send` leak (B1's two fails, B2's ten vacuous passes, C2's three): the instrument's sends address ANOTHER daemon

- Every `4genteam send …` in B1, B2 and C2 came back: `the runtime at
  /mnt/wslg/runtime-dir/agenthub.sock refused it: no runner for cutover-lab/<seat>: cannot reach its
  mailbox /home/daihu/.config/4genthub/rooms/cutover-lab/run/<seat>.sock (Connection refused (os error
  111)); nothing was sent`. The run's socket is `/tmp/u3run4/rt/agenthub.sock`; `ss -xl` shows **two**
  daemons listening, and `send` picked the box's live one.
- `send` accepts **no `--socket`/`--state-dir`** - usage `send SESSION MESSAGE [options]`, options
  `--raw`, `--json`, `--from`, `--rig`, `--pod`, `--host`, `--context` - so its target is env-only, and
  the run's env is wrong: the run's daemon (pid 24854) **and the run's own seat** (pid 26727, runner
  `cutover-lab/lead`) both carry `XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir` and **no
  `AGENTHUB_RUNTIME_SOCKET`**, because the socket was passed as a flag and is not exported into the
  seats the daemon launches.
- **This voids B2's ten passes** (a cap string cannot be found absent from a pane that never received
  it); B2's one honest FAIL is "the sweep never produced a spill artifact up to the largest size; parity
  2 unproven". B1's two fails and C2's three were therefore measured on the wrong runtime, not on the
  product: B1's death/resume observation never started ("never saw the turn in flight").
- Fixes routed: **product** - `up` exports its own socket to the seats it launches, and `send` takes
  `--socket`/`--state-dir` like its siblings; **harness** - assert the resolved socket is run-private
  before any send, and let a refused send fail its dependent assertions. The plan's rule already covers
  the class: an unisolated socket is not a run.

## 3. The `none.jsonl` literal (C3's one fail; the same artifact in A3 and B1): the harness composes a transcript name

- C3 failed `the seat's transcript exists and is non-empty` because it tested
  `seats/dev/sessions/none.jsonl`. Seat transcripts are timestamped, and the client already names the
  right one: `internal/seatlog/seatlog.go:80-82` (`NewestSession` globs `<seat dir>/sessions/*.jsonl`).
  A3's and B1's `log bytes before the kill: 0` lines are the same artifact (a `none.jsonl` that never
  exists).
- So this fail is the instrument's, and it takes the same correction as the `logs/` finding: read the
  seat's log where the client says it is.

## What this changes

- **C4 is not passed**, and it cannot be until R6 is fixed (product) and both instrument defects are
  closed: the acceptance's room legs cannot produce a trustworthy verdict while `send` addresses a
  foreign daemon and the transcript reader looks for `none.jsonl`.
- The legs themselves behaved where the instrument held: A3 (6/0) and C4 (2/0) are clean, C3 proves the
  presence surfaces answer (6 passes), and C4's rollback selected its daemon by the record this run
  wrote at its own `up` - socket inode, pid and that pid's start time - and stopped nothing it did not
  start.
