# U3 run 2 was invalid: its own hygiene had deleted the lab room's fixtures

## What happened
Acceptance run 2 (`--all`, started 2026-10-14T20:14:26Z, `CUTOVER_STATE_DIR=$HOME/.config/4genthub`,
binaries from `wt/4genthub-min/u3bin`) executed against a room directory that did not exist. It scored
**68 pass / 22 fail** against run 1's 123 / 2, and **not one of the 22 failures was about the code**:
every live-room leg failed on the same line, `no env with AGENTHUB_SEAT=<seat> in the room tree — is the
room up?`, and A1 failed at its first assertion, `spec.json has no seats — run A0/up first`.

**The run was killed (exit 143) at ~20:36Z rather than allowed to finish**, because an invalid run's
verdict is worse than no verdict: `a failing run blocks C5`, and a failure that measures a missing room
would park the cutover for the wrong reason.

## Evidence
- `ls /home/daihu/.config/4genthub/rooms/cutover-lab` → **No such file or directory**; `rooms/` mtime
  22:14, i.e. the deletion is contemporaneous with run 2's start (22:14:26).
- The job log that started the run prints, as its first line, `room dir removed: ls: cannot access
  '…/rooms/cutover-lab': No such file or directory`.
- The check that failed reads the **seat processes'** `/proc/<pid>/environ` (harness `build_env`), so it
  cannot succeed while no seat is running: 22 FAILs, one cause.
- A1 asserts `room dir has seats/ logs/ run/ and spec.json` **after** `up`, while `room_seats()` reads
  `spec.json` **before** it — so the fixture must pre-exist and the deleted directory was exactly the
  precondition the run needed.

## Cause
The wrapper that launched run 2 removed the lab room directory wholesale. The harness's own hygiene is
narrower than that and says so: `RUN_STATE_SUBDIRS="run seats logs"` plus `queue.sqlite`, with `team/`
and `spec.json` named as **FIXTURES** that stay. The over-deletion came from outside the script, and the
script cannot defend against it: it only calls `bad` (leg failure) and `--all` carries on into the next
leg, which is what turned one missing precondition into 22 findings-shaped failures.

## Fix
The fixture is rebuilt and durable, in the state the run needs:
- `rooms/cutover-lab/team/team.json` — three seats (`lead`/`developer`/`reviewer`), runtime `omp`,
  model `deepseek/deepseek-flash`, empty links; the seat shape copied from the live room's own
  `spec.json`, not invented.
- `4genteam up cutover-lab --team … --state-dir $HOME/.config/4genthub --room-only` → **exit 0**, all
  three seats running; `spec.json` 850 B with exactly `lead dev reviewer`.
- then `4genteam room stop cutover-lab` → `stopped, and no longer meant to run`, and it left the
  directory in place (`spec.json`, `seats/`, `logs/`, `run/`, `team/`) — the state to start a run from.
- off-peak was confirmed first (`4genteam offpeak` → `OFF-PEAK 20:37 UTC`), so no `--allow-peak`.

## Rules this run produced
1. **No run may delete the room directory or its fixtures.** The hygiene scope is `run/`, `seats/`,
   `logs/`, `queue.sqlite`; `spec.json` and `team/` are inputs a run reads and never writes.
2. **A run that finds no `spec.json` must refuse, not proceed.** Today it returned 1 from A1 and
   continued into A2/B2, so a missing precondition was reported in the shape of product failures.

## Limits
- Run 2's 68/22 is **not a result about the branch** and must not be cited as one; run 1 (123/2) remains
  the last valid measurement, and its own two failures stand as filed.
- Run 3 (`evidence-run3-20261014T2040Z`, same tip binaries, `--all`) was started from the rebuilt
  fixture; **its verdict is not in this entry** and is owed as its own.
