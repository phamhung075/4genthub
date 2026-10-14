# U3 run 3 measured the live daemon's stale rail, not the room

## What happened
Acceptance run 3 (`--all`, harness `wt/4genthub-min/u3-run/ACCEPTANCE-cutover-lab-U3.sh`, tip binaries
from `wt/4genthub-min/u3bin`, evidence `wt/4genthub-min/u3-run/evidence-run3-20261014T2040Z`) scored
**106 pass / 10 fail**. It was launched with `CUTOVER_STATE_DIR=/home/daihu/.config/4genthub` — the
**live** state root — and `XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir`, so the harness's `SOCK` resolved to
`/mnt/wslg/runtime-dir/agenthub.sock`: the socket of the **live daemon**, not one the run started.

The run's own rollback section names exactly that:
`no daemon stopped: the record names no pid (this run started no daemon of its own)` and
`a daemon this run did NOT start is still serving`. That daemon is **pid 6512**
(`/home/daihu/.local/bin/agenthub-runtime --state-dir /home/daihu/.config/4genthub --socket
/mnt/wslg/runtime-dir/agenthub.sock daemon`), started **19:58:51Z** — the one restarted after run 1's
rollback killed the live room's daemon.

**Seven of the ten failures are one stale file handle, not the code under test.** Every
`room queue create` in the run failed, from A2's first operation (`qitem-20261014203806-7dc13a0c3f89`)
through B3's (`qitem-20261014204502-ed2b919b4fb2`), with
`attempt to write a readonly database`.

## Evidence
- **The daemon holds a deleted file**: `/proc/6512/fd/12 -> /home/daihu/.config/4genthub/rooms/cutover-lab/queue.sqlite (deleted)`.
  The room's rail was replaced under a daemon that was already running.
- **The file on disk is writable**: `-rw-r--r-- daihu:daihu 36864`, mode 644, owner writable
  (`test -w` true), directory writable, no immutable attribute (`lsattr` clean), 850 G free on `/`;
  `rooms/4genthub-min/queue.sqlite` was being written at that same moment.
- **Code**: `Supervisor.queue_stores` is `Arc<Mutex<HashMap<String, QueueStore>>>`
  (`rust/agenthub-runtime/src/supervisor/mod.rs:128`), populated once and never revalidated
  (`:238-250`, `stores.insert(room, QueueStore::open(&room_dir)?)`); `QueueStore::open` is
  `create_dir_all` + `rusqlite::Connection::open` + schema (`queue/mod.rs:300-304`) and the failing
  create is `queue/mod.rs:363`. SQLite's message for a database file moved out from under an open
  connection is this generic one — which is why it says "readonly" about a file that is not.
- **Reproduced in an isolated rig with the same binaries** (`--state-dir /tmp/u3iso1/state --socket
  /tmp/u3iso1/rt/agenthub.sock`): `queue create` on a pristine room → `rc=0`, row
  `qitem-20261014205201-7a91282dc37b`; `mv queue.sqlite queue.sqlite.old` (a room rebuilt under a live
  daemon); `queue create` → **`rc=2 attempt to write a readonly database`**; `queue list` → **`rc=0` and
  the row from the OLD file** — the rail answers a stale set of rows as fact. The daemon's fd follows the
  renamed file throughout.
- **Unbounded handles**: pid 6512 held **17 fds**, one open `queue.sqlite` per room ever touched, none
  closed.

## Cause
The native daemon caches one `QueueStore` per room for its whole lifetime and never notices that the
room's `queue.sqlite` has been renamed, replaced or re-created — which a rebuilt room, a restore, or the
harness's own hygiene (`ACCEPTANCE-cutover-lab-U3.sh:263-265`, `rm -f queue.sqlite`) does routinely.
Until the daemon restarts, writes fail with a misleading cause and reads keep answering the old file.
The harness's hygiene deletes the rail of the room it is about to test, so **any daemon left over from an
earlier run is guaranteed to be serving a deleted one**.

## Fix
- **Run 4 is the isolated re-measure and is the acceptance run**: same harness, same tip binaries, with
  `CUTOVER_STATE_DIR=/tmp/u3run4/state`, `XDG_RUNTIME_DIR=/tmp/u3run4/rt`,
  `AGENTHUB_RUNTIME_SOCKET=/tmp/u3run4/rt/agenthub.sock`; fixtures seeded (`spec.json` and
  `team/team.json` — the two files the harness refuses to run without) and a **fresh daemon started on
  that socket with that state dir** (zero queue fds at start, so no leg can be served by 6512). Evidence:
  `wt/4genthub-min/u3-run/evidence-run4-isolated-20261014T2055Z`.
- **The daemon defect is filed against R6** (`NEXT-GEN2.md`): open the rail per request, or revalidate
  `(st_dev, st_ino)` before each use and reopen when it changed, with a test that replaces the rail under
  a live store and asserts the next write lands in the NEW file and reads no longer see the old rows.
  Not a client defect.

## Rules this run produced
1. **An unisolated socket is not a run.** The live rig hosts this conversation and shares the box's one
   control-plane socket: `CUTOVER_STATE_DIR` **and** `XDG_RUNTIME_DIR`/`AGENTHUB_RUNTIME_SOCKET` must both
   be run-private, and the run must start its own daemon — verified by a `daemon-started` record naming
   the socket inode and the pid, not by a socket merely existing.
2. **A daemon must not serve a rail it can no longer prove is the room's.** Until R6's defect is fixed,
   any reading taken through a daemon that predates a room rebuild is a reading about the stale file.

## Limits
- **Run 3 is not the acceptance run and its queue legs are not results about the code**: A2's three
  assertions and B3's four are the R6 defect reproduced live.
- Its other failures are adjudicated separately and stay open: **A1** failed one assertion of four
  (`logs/` is absent after `up` — the runtime logs at the state root, so this is a harness expectation
  against product reality and wants a ruling); **B2**'s sweep found no spill artifact up to 16 MiB while
  every size also noted *"the seat was never seen busy"*, so its sends may never have landed —
  **inconclusive, not a verdict**; **C2**'s probe reached the receiver with **no sender envelope** in the
  transcript/feed, which is the C2 row's own subject.
- Everything run 3 passed (seating, `P1`/`P2`/`Q1`, `B1`/`A3`/`B1s`/`B1p`, `A4`, the rollback) stands as
  evidence *subject to* the shared-socket caveat above.
