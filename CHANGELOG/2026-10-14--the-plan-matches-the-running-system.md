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
  `PATH` is the 4genteam npm CLI. The native `whoami` half is re-measured working.
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
  the **21** non-test `exec.Command`/`exec.CommandContext` code sites — `25` is the string count, = 21 code + 3 comment lines + 1 seam assignment (`internal/clientrestore/paths.go:66`), re-measured at `4567c37` under `internal/`+`cmd/`, and none of them can spell `rig` — 4 pass `argv[0]`, a 5th through the `execCommand` seam, 2 resolve `os.Executable()`, 1 is self-derived `args[0]`, 2 are the toolchain `command[0]`, the rest literals or runtime/`pgrep` paths — no `Rig` primitive), and the check re-run gives `whoami`/`ps`/
  `room queue list` rc 0 and `send` a client-usage dispatch.
- **C4:** run 2 is recorded as **killed as INVALID at ~20:36Z**, not as a verdict — the room its live legs
  needed had been deleted before it started, so its 22 failures measured a missing room, not the branch
  (`CHANGELOG/2026-10-14--u3-run-2-was-invalid-its-hygiene-ate-the-lab-room.md`); the in-flight reading
  this pass took at 20:2xZ is kept as provenance and marked superseded, and **run 3** (`--all`, pid 1704,
  started 20:37:56Z, evidence `u3-run/evidence-run3-20261014T2040Z`) is the run whose verdict is owed.
- **C7:** at the tip the client names `config/4genthub` **0** times and `AGENTHUB_STATE_ROOT` **0** times, and
  `~/config/4genthub` is already gone from disk — the 7-site list was measured on an earlier tree.
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
  `cargo test --offline` in its own dated addenda, twice — 20:55:09–11Z, and again 21:47Z headed *the gate is
  CLOSED*, in the lead's named clone (raw logs `/tmp/offline-666978b.log`, `/tmp/r2-offline-reviewer.log`) —
  **88 passed / 0 failed, `EXIT=0`** each time, with a falsification that reproduces the recorded
  defect's own words, verdict `APPROVE` (`agenthub_client/GATE-666978b-compact-refusal-noop-2026-10-14.md`).
  What the fix still waits on is the install window.
- **Item 11 and the C4 provenance bullet carry run 2 as INVALID with run 3 executing**, and §5's item 5
  reads run 3's verdict as what opens C5 — **both superseded by the section below** (run 3 ran against
  the live daemon and cannot open C5; run 4, isolated, is the acceptance run). The lead's C4 row keeps the run-2 verdict, the rebuilt fixture
  and the rule it produced ("clean run-state, never fixtures"); this pass only corrected its own stale
  readings and did not restate them.

## The reviewer's three plan corrections, applied pre-merge (2026-10-14 22:0xZ)

The reviewer's row (`qitem-20261014214322-8ba7b263ebe8`) named three text corrections and the lead's landing
order (`qitem-20261014215945-a6d88f4fad3e`) made them a pre-merge condition. All three are in the two bullets
above and in item 10 of the plan.

- **The R2 line stops attributing `--offline` to the gate's plain run.** That run is `cargo +stable test` with
  no flag; the offline form is in the same file's own addenda (20:55:09–11Z, and 21:47Z, the second headed
  *the gate is CLOSED*), and item 10 cites those. `GATE-c3`'s "the R2 `cargo test --offline` … stays held"
  (20:41Z) is superseded by them, not by this branch.
- **The `exec.Command` count carries its scope and its instrument:** 21 non-test code sites at client
  `4567c37` (`exec.Command(` 15 + `exec.CommandContext(` 6, `internal/`+`cmd/`); the `25` a string grep
  returns is 21 code + 3 comment lines + 1 seam assignment (`internal/clientrestore/paths.go:66`).
- **The argv[0] class replaces the symlink premise:** `~/.local/bin/rig` does not exist on this box, so the
  gate's "symlink to `4genteam`" sentence is deleted rather than annotated, and no site can spell `rig` —
  4 of the 21 pass `argv[0]`, a 5th through the `execCommand` seam, 2 resolve `os.Executable()`, 1 is
  self-derived `args[0]`, 2 are the toolchain `command[0]`, the rest literals or a runtime/`pgrep` path.

## The `logs/` ruling, and the runs it corrects (2026-10-14 21:1xZ — the ruling half of this section is REVERSED at 21:2xZ; read the next section first)

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

## The reversal, measured: `rooms/<room>/logs/` IS the runtime's own (2026-10-14 21:2xZ)

- **The section above is wrong, and this one supersedes it.** `logs/` is not a retired concept and the
  fix is not instrument-side: the runtime created that directory, the commit the ruling cited deleted
  the **writer**, and go-dev's delivery restores it. Read at the source: `agenthub_client@cc0c62f`'s own
  diff, a writer survey of `rust/agenthub-runtime/src`, the acceptance harness's `mkdir` sites, and
  go-dev's `2800dfb`.
- **`cc0c62f`'s diff deletes the creation of `logs/` itself**, and that is what "the dead
  `logs/<seat>.jsonl` creation is removed" means: the removed lines are
  `let logs_dir = room_dir.join("logs"); let _ = fs::create_dir_all(&logs_dir); let transcript_path =
  logs_dir.join(format!("{}.jsonl", seat.seat_key));` — so the directory was the native runtime's
  room-start layout, and the file stopped being read as the transcript when `transcript_path` moved to
  `seats/<seat>/sessions`. The plan's "created by a harness path, not the product" is therefore
  falsified: the harness creates no room directory at all (its `mkdir` sites are the evidence dir, the
  shims, `q1root`/`q1pin` and the team roots), and the two empty `logs/` dirs on this box (`p2default`,
  `q1probe-ok`, 12:11-12:12 — before `cc0c62f` at 17:58Z) are that deleted line's fossils.
- **The layout stands as `spec.json`, `seats/`, `logs/`, `run/`, `queue.sqlite`, with two artifacts
  that must not merge:** `logs/<seat>.jsonl` is the **runner's** log (the pane mirror: the
  retry/backoff ladder, the cap error, the refusals) and `seats/<seat>/sessions/*.jsonl` is the
  **agent's** session, the one definition of the transcript (`supervisor/mod.rs:1230` reads it;
  `runner/mod.rs:101` only points the agent at that directory; the crate's only appenders are the audit
  hook, the run-state writer, the queue and `spec.json`).
- **All four items of the change list are withdrawn.** A1's assertion, `RUN_STATE_SUBDIRS`, the
  `logs/$VICTIM.jsonl` labels and the client's `room stop` prose are correct as written; go-dev's
  `2800dfb` (`4genthub-min/c3-printed-rig`) makes `start_room` create the layout and the runner's
  `mirror` append to `logs/<seat>.jsonl`, with two tests pinning it and `cargo test --offline` at 88
  passed / 0 failed. **One instrument line remains:** B2's cap-string reader must read the runner's log
  instead of `$(victim_transcript)`, because the runtime never appends a record to a transcript — on the
  transcript that check cannot fail, while its own label already names the runner's file; the
  retry/backoff count at `:695` has the same reader and becomes real the same way, and that call is the
  gate's, not this entry's.
- **And the verdict run needs `2800dfb` to land:** with it A1 passes on the layout and the nine legs its
  single assertion starved become measurable. What the reversal costs is one evening's belief, recorded
  here rather than quietly dropped.

## Evidence

`ps -eo pid,ppid,cmd`; `agenthub-runtime --state-dir ~/.config/4genthub status 4genthub-min`;
`TMUX_TMPDIR=~/.config/4genthub/tmux tmux list-panes -a`; `GET /api/v2/rooms`, `…/seats`,
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

For the reversal: `agenthub_client@cc0c62f` read through `git show` (the deleted
`create_dir_all(room_dir.join("logs"))` and the re-pointed `transcript_path`); `git show 2800dfb --stat`
and its own changelog entry; a writer survey of the crate (`grep -n 'create_dir_all\|fs::write\|append('
rust/agenthub-runtime/src/`); the harness's own `mkdir` sites (`grep -n mkdir …` → evidence dir, shims,
`q1root`/`q1pin`, team roots, and no room directory); `ls -la ~/.config/4genthub/rooms/*/logs` for the
two empty fossils; and `git branch -a --contains 2800dfb` → `4genthub-min/c3-printed-rig`, i.e. **not
yet reachable from main's submodule pointer**, which is why the verdict run waits on it. Nothing was
built, merged or run in this pass.

## The run-5 state, the two units' gate state and the instrument revision, on the board (2026-10-14 22:0xZ)

Taken from the lead's routing row (`qitem-20261014220540-a86035876e3f`), which handed the reviewer's three board
lines over rather than applying them, because this file is the architect's. Appended where the plan records run
state — the C4 bullet list and §5's item 5 — and independent of the three corrections above, which are unchanged.

- **Run 5b is the acceptance record: `132 pass / 4 fail / 2 skip`.** The room legs ran and their product
  assertions passed; all four FAILs are adjudicated INSTRUMENT in that record (Q1's scrubbed `HOME` baseline
  cannot start a seat, which makes the two PASSes under it vacuous; B2's leg models an omp artifact that omp does
  not write; C2 pins the pre-`623d29a` receipt vocabulary and sends to a mid-turn seat). **Parity 2 stays
  UNPROVEN and is written as a named unproven item, not as a pass.** Run 5c's numbers are VOID (it reached the
  live daemon) and run 5d is NOT COMPARABLE to 5b (the harness revision changed).
- **The two units after `a58e684` are gated and neither is landed:** `0a968fc` (a seat is told its daemon's
  socket) → APPROVE; `ad03a16` (the retired-verb class pin) → NOT as is, one required edit — its `Allowed[4]`
  entry names the retired command's own form rather than a negation while coverage is a substring match, so the
  one entry covering the pin's target verb is a licence for that verb's exact shape. Scope: go-dev — and the
  lead's ruling on that scope is narrow-the-`Match` first (reword-and-drop only if an un-negated `rig up`
  mention survives), with the acceptance count split so the pin's own constants are not counted as delivered
  spans.
- **The instrument revision is APPLIED, not staged (the lead applied it at 22:10:25Z after verifying the target,
  `qitem-20261014221131-075dfa5fbf2f`):** `8d7be24c…`, 136414 B, `bash -n` clean, +76/−3 against `65d36d1d`
  (131295 B), written atomically with the pre-patch bytes kept and logged — so the live harness IS that revision:
  run-private socket resolved and asserted before `up`, room-live check, seat-idle check, the harness's own
  sha256 in every `EVID` dir, and the `:456`/`:537` inversion. **The inversion itself is a separate later write
  and stays routed to go-dev** (an instrument may not author the fact it measures), with the locators the patch
  moved (injection `:463`, rebuild ~`:600`) and the sequencing fixed: build `u3bin/agenthub-runtime` from the tip
  carrying `0a968fc` and stamp commit + sha256 in the EVID's PROVENANCE, then drop the injection.

Folded into item 10 as well, from the reviewer's own row (`qitem-20261014220539-8176fe41e33a`): the held R2
offline run is MEASURED — 88 passed / 0 failed under `CARGO_NET_OFFLINE=true cargo test --offline`, cargo 1.91.1 —
and the neighbouring c3 tip `0a968fc` measures 90 passed / 0 failed, so the plan cites the runs themselves rather
than the gate's plain `cargo +stable test`, and its premise row (`qitem-20261014220539-e485aa132162`, item 1)
is answered by that measurement rather than by a text change.

### Evidence

`agenthub_client/GATE-u3-run5b-acceptance-2026-10-14.md`; `agenthub_client/GATE-ad03a16-0a968fc-two-units-2026-10-14.md`;
`agenthub_client/GATE-666978b-compact-refusal-noop-2026-10-14.md` (its two `--offline` addenda, read); the
reviewer's rows named above; and the lead's routing row. Nothing was run, built, installed or signalled in this
pass.
