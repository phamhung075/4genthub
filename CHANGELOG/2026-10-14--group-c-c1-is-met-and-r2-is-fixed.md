## Group C: C1 is met and the R2 defect is fixed; the seats are alive but guideless

### C1 — met, measured (the owner asked the plan be corrected if it already holds)
The plan's C1 row is written as "work sits on `4genthub-min/u2-native-runner`, not merged, not installed".
That is stale in three ways, and the owner's own note ("the 4genthub-min seats now run on
`agenthub-runtime` runner") is what the machine says:

- The u2 branch IS merged: `a118585 merge: 4genthub-min/u2-native-runner into feat/support-agy-watch` in the
  client repo, and the live room's state root is the one that merge introduced (`~/.config/4genthub`, not
  `~/config/4genthub`).
- The build IS installed: `~/.local/bin/agenthub-runtime` 21:09, `~/.local/bin/4genteam` 21:23.
- The check holds: `ps -eo pid,ppid,args | grep -E 'agenthub-runtime|pi-runner|the reference client'` lists five
  `agenthub-runtime --state-dir /home/daihu/.config/4genthub runner 4genthub-min/<seat>` processes under the
  room's own tmux session, and no `the reference client` and no `pi-runner.js`. `4genteam up 4genthub-min --team <team dir>
  --room-only` exits 0 and prints all five seats `running`.

C1's row still reads `[ ]`; the flip belongs to whoever holds the document (see the warning below).

### R2 — fixed, with the test the first attempt lacked
- Client branch `fix/compact-reply-not-a-turn`, tip `666978b`: one commit on top of `a8e18eb`, itself one on
  top of `feat/support-agy-watch` (`4567c37` — the build the live seats run).
- `666978b` adds `Failure::Noop` and `NOOP_SIGNATURES` (`Nothing to compact`, `session too small`), consulted
  **before** the retryable table; maps `Noop` to `Resume::Nothing` (no state write, so a fresh seat keeps the
  `idle` it published at handshake and stays wakeable); and names the caller's guard `is_compact_reply(id)` so
  a fire-and-forget compact's reply is never a turn's outcome whatever it says.
- `a8e18eb`, the first attempt written by another session, recognised the compact reply by its
  `forcecompact-` id and shipped a tautological test —
  `assert!(format!("{COMPACT_ID_PREFIX}{}", pid).starts_with(COMPACT_ID_PREFIX))` asserts that a
  concatenation starts with its own prefix. It is replaced by two tests that bind.
- Verified: `cargo +stable test` in `rust/agenthub-runtime` — **88 passed, 0 failed**. Falsified, not read:
  with the no-op table not consulted the new test fails with
  `a compact refusal classified terminal (the agent refused the turn)`, and the file was then restored
  byte-identical (sha256 `7da7e2ed390fa43d35389bffc59f4e0992721748a7677d4411f56c40239b73c1`).
- Nothing is pushed, merged or installed; the running seats still run the pre-fix binary.

### The seats are ALIVE — "blocked with no session log" was a stale state file
The four `run/<seat>.state.json` files do say `blocked` / `the agent refused the turn` (`updated_at`
19:12:55Z), and that is the R2 defect's own durable record. But by 21:38-21:39 every seat was demonstrably
running: each seat's `seats/<seat>/sessions/*.jsonl` was being appended (mtimes 21:38:22-21:39:02), the panes
showed live `turn_start` / `tool_execution_*` frames, and a `4genteam send` to the reviewer was accepted
(`Sent to agenthub--4genthub-min--reviewer`) and acted on — the reviewer immediately ran the gate commands it
was asked for. So "no session log" was true at first start and is not true now.
What the seats do NOT have is their guide — recorded separately in
`2026-10-14--the-native-room-never-applies-the-seat-overlays.md`.

### Working-tree warning for the next reader
`NEXT-GEN2.md` is being rewritten in the working tree by another session (modified again at 21:44:30, 27 s
before this entry was written; the topology section is replaced with a five-seat/edges table). Nothing in this
entry was written into that file, and its C1 and R2 rows still carry the old text.
