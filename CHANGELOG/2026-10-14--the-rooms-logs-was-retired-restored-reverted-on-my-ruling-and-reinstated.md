# The room's `logs/`: retired, restored, reverted on MY wrong ruling, reinstated — and both fixes verified at their tips

Three commits in `agenthub_client` decide the layout question, and the third was made because of a
mistake of mine. The rail defect's fix was delivered in the same window and is verified here too.

## 1. What each commit did

- **`cc0c62f` — "read the agent session transcript; per-session tmux env" — retired the room's `logs/`
  deliberately.** Its own changelog: "*The dead `logs/<seat>.jsonl` creation is removed*". The reader it
  retired was re-pointed at `supervisor::transcript_path` (the newest `*.jsonl` under
  `<room>/seats/<seat>/sessions`). After it, `grep '"logs"' rust/agenthub-runtime/src` found nothing.
- **`2800dfb` — "the room is prepared with its layout, and the seat writes its own log" — restored it.**
  `start_room` creates `seats/`, `logs/`, `run/`, and the runner mirrors the pane into
  `<state dir>/rooms/<room>/logs/<seat>.jsonl` (`seat_log_path`, `SEAT_LOG`), so B2's cap-string check has
  the file the design names. Its tests: `starting_a_room_creates_its_seats_logs_and_run_directories` and
  `the_seat_log_is_the_rooms_logs_dir_and_holds_what_the_pane_showed`.
- **`0277556` — "revert(runtime): the room's logs/ is not product state" (go-dev, 21:09:08Z) — reverted
  `2800dfb`, on my ruling, and the message carries my ruling's words.**
- **`f4528a1` — "revert(runtime): 2800dfb stands - the room's logs/ is the runner's log" — the branch tip
  now, which puts it back.**

## 2. The mistake, and what it cost

Measuring run 4 I found that *no product code creates `rooms/<room>/logs/`* — true at that tip — and
concluded the **acceptance** was wrong to assert it. I closed go-dev's row as superseded, filed "the fix
is harness-side, not product-side", and corrected the plan. **The measurement was right; the attribution
was wrong.** `cc0c62f` had retired a directory the design still requires, and the correct answer was the
one go-dev had already implemented.

What it cost, all measured:
- a **product revert** (`0277556`), which removed the layout creation, the pane mirror and its two tests;
- a **binary rebuild at 21:09:11Z — while run 4b was executing** (the lab binary `u3bin`, sha256
  `c1272c6c`, is stamped then);
- a **harness edit at 21:10:34Z — also mid-run**: a six-line comment now claims `logs/` "is NOT run-state"
  and cites "lead's ruling, row aa2a2ed0b966", `RUN_STATE_SUBDIRS` was cut to `"run seats"`, and A1's
  layout check was rewritten to stop requiring `logs/`.

## 3. Verified at the tips (my own runs, this session)

- **`4genthub-min/c3-printed-rig` @ `f4528a1`: `cargo test --offline` → 88 passed, 0 failed**; both layout
  tests pass by name (1 passed, 87 filtered out each); and the source carries the layout again
  (`supervisor/mod.rs:287` and its test at `:1788`: `for dir in ["seats", "logs", "run"]`;
  `runner/mod.rs:1342` joins `logs` for the seat's log).
- **`4genthub-min/rail-per-request` @ `69006b5` — "a replaced rail is the rail the daemon uses":
  `cargo test --offline` → 89 passed, 0 failed**, including **`supervisor::tests::a_replaced_rail_is_the_one_the_next_verb_uses`** — the exact assertion the R6 row demanded (replace the rail under a live store,
  then the next verb must use the NEW file). Diff: `queue/mod.rs` +7, `supervisor/mod.rs` +138/-38.
  **This fix is NOT in the c3 tip** (`cargo test --offline a_replaced_rail` matches 0 tests there), so it
  still has to land on the branch that lands.
- **R2** (unrelated to this entry, same session): `fix/compact-reply-not-a-turn` @ `666978b` → **88 passed,
  0 failed**, with `a_compact_reply_is_told_from_a_turn_by_its_id` and
  `a_compact_refusal_with_nothing_to_compact_is_a_no_op` passing by name.

## 4. What the harness owes — the exact undo

1. `:245-250` — delete the comment that calls `logs/` a predecessor remnant and cites the lead's ruling.
2. `:250` — `RUN_STATE_SUBDIRS="run seats"` → `"run seats logs"`. Clearing it between legs is still right:
   the product recreates the directory at `up`.
3. `:709-710` — restore `logs` to A1's layout check (`for d in seats run` → `for d in seats logs run`, and
   the refute's label with it). The layout is asserted policy, and it is now true.
4. `:885` — the label "cap string absent from the seat log" should name what `:882` actually reads: the
   seat's **transcript** (`victim_transcript()`; `:368`). Only the label lies.
5. **Keep** `assert_run_private_socket` (`:708`) — that guard is right and was asked for; the same guard is
   still owed around **`send`** (row on the rail), which is where the send leak measured.

## 5. Two artifacts, and run 4b's contamination

- The seat's **log** is the runner's pane mirror at `rooms/<room>/logs/<seat>.jsonl`; the seat's
  **transcript** is omp's own `rooms/<room>/seats/<seat>/sessions/*.jsonl`. A leg that prints
  `…/sessions/none.jsonl` is reporting that the seat took no turn — the fallback fires only when no
  transcript exists.
- **Run 4b is a contaminated instrument**: its legs ran 20:52-21:14Z, the binary was rebuilt at 21:09:11Z
  and the harness was edited at 21:10:34Z. Its verdicts stand only where the evidence lines are
  self-describing (A2's `attempt to write a readonly database` and the daemon's
  `fd 12 -> …/cutover-lab/queue.sqlite (deleted)`; B1/B2/C2's `send` refused by
  `/mnt/wslg/runtime-dir/agenthub.sock`; C4's clean rollback). **Run 5 must be one instrument, unedited,
  with a fresh daemon.**
