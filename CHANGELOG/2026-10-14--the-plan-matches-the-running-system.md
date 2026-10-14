# The plan now matches the running system

The owner's instruction to the architect seat was "review the ACTUAL system as it runs today and update
`NEXT-GEN2.md` to match it — measure, do not trust the plan", with four named questions: which process
hosts each of the five seats (and whether C1 is met), cloud versus `~/.config/4genthub/rooms` and the
edges, which R/C/O/P items are really done, and the state of today's compact defect. Every correction
below cites the measurement that forced it.

## Changed

- **New §3 sub-block, "The measured state, 2026-10-14 20:2xZ"** — the thirteen measurements with their
  instruments (process table, `agenthub-runtime status`, tmux pane table, the cloud API, `git grep` at
  the pinned sha, `find`, the live `.env`, the run-2 evidence directory). Each item carries the command
  and the result, so a later reader can re-run rather than re-derive.
- **New §5, "Next five, in order"** — the ordered next work with the measurement that puts each one there.
- **§2 topology table:** `architect` was `claude-code / opus`; it is **`omp / deepseek/deepseek-flash`**
  now (the owner replaced the seat's session at 20:21Z, and `status 4genthub-min` reports five `omp Running`).
- **§2 edges paragraph:** "these edges exist in this plan only" is **disproved** — the cloud returns
  exactly one room (`4genthub-min`) and its 12 links, kind-for-kind equal to the table; only the local
  `spec.json` still has `"links": []`, which is why `whoami` reports empty `edges`.
- **C1:** the check's own `architect = claude-code Running` is corrected to `omp Running`, with today's
  ps/tmux/status evidence added beside it. C1 itself still holds.
- **§1.5 and R7:** the `rig` shim is **gone** — `~/.local/bin/rig` does not exist, `4genteam rig-shim` is
  an unknown command (removal pinned by `TestNoCompatibilityShimVerbIsRegistered`), and the `rig` on
  `PATH` is the OpenRig npm CLI. The native `whoami` half is re-measured working.
- **R1:** re-measured at the room's tip `4567c37` — `pty/mod.rs` is 36 tmux hits with 0 `portable_pty`,
  and `socketpair` is 3 in `runner/mod.rs`, so the socketpair half holds at the tip and only the
  "headless PTY" wording stays unsupported.
- **R2:** the live `.env` carries `150000 / 200000 / 250000`, not the `150k / 250k / 300k` this item
  stated; and "the architect seat stays blocked" is stale — the state files read `idle` today while the
  defect itself is still unmerged and uninstalled (branch `fix/compact-reply-not-a-turn` is **two**
  commits, pushed, not an ancestor of `feat/support-agy-watch`).
- **R6:** the socket is `$XDG_RUNTIME_DIR/agenthub.sock` (**`/mnt/wslg/runtime-dir/agenthub.sock`** here,
  and it answers), not `/run/user/$UID/agenthub.sock`; each room also has `run/<seat>.sock`. The room
  layout is now fully observable, and two rooms are live at once.
- **C3:** the "`~/.local/bin/rig` is a symlink to `4genteam`" explanation has no subject today, the
  `rig`-exec remainder is **0** at the tip (0 `rig.Run(`, 0 `RequireRig`, 0 `LookPath("rig")`, none of
  the 25 non-test `exec.Command` sites, no `Rig` primitive), and the check re-run gives `whoami`/`ps`/
  `room queue list` rc 0 and `send` a client-usage dispatch.
- **C4:** run 2 is recorded as **killed as INVALID at ~20:36Z**, not as a verdict — the room its live legs
  needed had been deleted before it started, so its 22 failures measured a missing room, not the branch
  (`CHANGELOG/2026-10-14--u3-run-2-was-invalid-its-hygiene-ate-the-lab-room.md`); the in-flight reading
  this pass took at 20:2xZ is kept as provenance and marked superseded, and **run 3** (`--all`, pid 1704,
  started 20:37:56Z, evidence `u3-run/evidence-run3-20261014T2040Z`) is the run whose verdict is owed.
- **C7:** at the tip the client names `.openrig` **0** times and `OPENRIG_STATE_ROOT` **0** times, and
  `~/.openrig` is already gone from disk — the 7-site list was measured on an earlier tree.
- **P1:** the "18 exec call sites remain" reading is superseded by **0** at the room's tip, and the
  "`send` is a dead verb" sentence is corrected (the shim's refusal is gone; dispatch is measured).
- **The delivery path itself was measured, because this pass had to deliver its own summary.** `4genteam send`
  to the lead printed `Sent to …` (rc 0) and landed in neither the transcript nor the pane; the rail
  (`room queue create`) answered and its two rows are `pending`; and `4genteam send owner-session …` is
  **refused by name** (no seat named `owner-session` in any room the daemon hosts), so no local `send`
  reaches the owner-session. Recorded in C2's row and in next-item 1: until the install, a handoff goes
  on the rail.
- **O1c / T13 / O-P-D artifacts:** O1c's counts re-run unchanged (51 / 26 / 5), T13's `scripts/tests`
  premise still holds, the cited commits all resolve, and the files those items name exist at those paths.

## Corrected with the first pass in hand (2026-10-14 20:4xZ)

- **The branch was rebased onto main's tip** so the plan delta no longer carries main's newer text as
  reversions: this file's entry and the §3/§5 corrections are now the branch's only delta over main,
  and the code main gained after this branch's base (the env-loader fix and its test) is untouched.
- **Item 10's owed measurement is done, not owed.** The reviewer's gate on `666978b` ran the tip's
  `cargo test --offline`: **88 passed / 0 failed**, with a falsification that reproduces the recorded
  defect's own words, verdict `APPROVE` (`agenthub_client/GATE-666978b-compact-refusal-noop-2026-10-14.md`).
  What the fix still waits on is the install window.
- **Item 11 and the C4 provenance bullet carry run 2 as INVALID with run 3 executing**, and §5's item 5
  reads run 3's verdict as what opens C5 — **both superseded by the section below** (run 3 ran against
  the live daemon and cannot open C5; run 4, isolated, is the acceptance run). The lead's C4 row keeps the run-2 verdict, the rebuilt fixture
  and the rule it produced ("clean run-state, never fixtures"); this pass only corrected its own stale
  readings and did not restate them.

## The `logs/` ruling, and the runs it corrects (2026-10-14 21:1xZ)

- **`rooms/<room>/logs/` is OUT of the room layout, and the concept was RETIRED rather than merely
  unimplemented.** The runtime holds exactly one definition of a seat's transcript and it is not
  `logs/`: `supervisor::transcript_path` resolves the newest `*.jsonl` under
  `<room>/seats/<seat>/sessions/` (`rust/agenthub-runtime/src/supervisor/mod.rs:1233-1243`, its own
  test writing that path at `:1687-1697`), and the change that made it so says the removal in the
  client's own changelog — **"The dead `logs/<seat>.jsonl` creation is removed"**
  (`agenthub_client/CHANGELOG/2026-10-14--runtime-reads-the-agent-session-transcript.md`). So "make
  `up` create it" is refused: it would restore a concept deleted the day before and add product code
  to pass an assertion. The change list is harness-side and four items long — A1 drops `logs` from its
  loop and label (`ACCEPTANCE-cutover-lab-U3.sh:618-619`), `RUN_STATE_SUBDIRS` drops it (`:245`,
  tidy-up: removing a directory that never exists is a no-op), the three stale labels that still say
  `logs/$VICTIM.jsonl` (`:519`, `:696`, `:792`) are re-pointed at the transcript they already read,
  and the client's shipped `room stop` prose — a false claim in user-facing text — drops the word
  (`internal/clientroom/room.go:107-108`, `:324`, `:342`, and the stale comment in
  `room_test.go:382`; that file is go-dev's).
- **One correction to the finding this plan carries: B2 is NOT vacuous.** Its cap-string leg reads
  `$(victim_transcript)`, a helper defined at `ACCEPTANCE-cutover-lab-U3.sh:360-361` as "the file omp
  really writes: the newest session jsonl of the victim seat", so it measures a real file; only the
  *label* names `logs/$VICTIM.jsonl`. The finding inferred vacuity from the label, and that inference
  is withdrawn in the R6 row.
- **The run rows are corrected, not merely re-dated.** Run 3 ran against the **live** daemon
  (`CUTOVER_STATE_DIR=$HOME/.config/4genthub`), so 7 of its 10 failures are that daemon's stale rail
  and it cannot open C5; **run 4** — isolated on its own state dir and socket (`/tmp/u3run4/{state,rt}`,
  a fresh daemon with 0 queue fds) — is the acceptance run at `69 pass / 1 fail / 9 skip`, whose single
  failure is A1's `logs/` assertion that this ruling resolves. Its rule 2 then skipped A2, B1, A3, B2,
  B3, C2, C3 and C4, so nine legs were starved by one assertion, and **the verdict is owed from a run
  on the corrected A1**.

## Evidence

`ps -eo pid,ppid,cmd`; `agenthub-runtime --state-dir ~/.config/4genthub status 4genthub-min`;
`TMUX_TMPDIR=~/.config/4genthub/tmux tmux list-panes -a`; `GET /api/v2/openrig/rooms`, `…/seats`,
`…/seats/<seat>/links` (read-only, token from `~/.config/4genthub/.env`); `git grep` on `4567c37` and
`git cat-file -t` for every cited sha; `ls`/`find` over `~/.config/4genthub/rooms` and `seats/`;
`sha256sum` of both installed binaries; `PATH=/usr/bin:/bin 4genteam whoami|ps|room queue|send`; the
live `.env`; `u3-run/evidence-run2-20261014T201426Z.stdout`. Nothing on the running room, the cloud or
the lab was changed by this pass.

For the `logs/` ruling: `rust/agenthub-runtime/src/supervisor/mod.rs:1233-1243` and its own test at
`:1687-1697`; `agenthub_client/CHANGELOG/2026-10-14--runtime-reads-the-agent-session-transcript.md`;
`internal/clientroom/room.go:107-108,324,342`; and the acceptance harness read — not run — at
`wt/4genthub-min/u3-run/ACCEPTANCE-cutover-lab-U3.sh:245,360-361,519,618-619,696,792`. Nothing in the
lab was edited, and no run was started, stopped or read past its evidence directory.
