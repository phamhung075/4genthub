# A failed start names its stage in the seat's log, and retries once

Measured 2026-10-18 (feedback `3ac8b369`, three reproductions): a reseat killed the seat's pane, the
start failed, and the seat was stranded with **no reason anywhere** — the pane had scrolled, the seat's
own log (`logs/<seat>.jsonl`) had no line, and no state file had been written. The runner writes those
surfaces, and a start that dies before the runner exists writes nothing at all, so "the pane died" and
"nobody asked" read the same. Reseat is the only route a landed skill takes to a running seat, so the
silence is what stranded it.

## What changed

- `agenthub_client/rust/agenthub-runtime/src/runner/mod.rs`: `append_seat_log(state_dir, room, seat, text)`
  — one line appended to the seat's own log from OUTSIDE the runner. A log that cannot be written is said
  on stderr rather than returned, the same contract `append_mirrored` keeps for the runner's own lines:
  the failure being reported is the one that must not be swallowed.
- `.../supervisor/mod.rs`: `start_seat` is now the retry wrapper and `start_seat_once` is one attempt.
  The failure type is what decides the retry, so it is an enum and not a string a reader has to
  pattern-match:

  ```rust
  enum StartFailure {
      Preparation(String),                        // nothing launched; final on the first attempt
      Launch { stage: &'static str, reason: String }, // a pane was launched and died, at this stage
  }
  ```

  - **`Launch` is retried exactly once** (`START_ATTEMPTS = 2`), and the retry stops the half-started
    session first, so the second launch is not a collision with the first. Each failed launch writes
    `start attempt N/2 failed at <stage>: <reason>`; the last one writes `start final: 2 attempts failed,
    the last at <stage>: <reason>` and the returned refusal says `(final)` and `retried once`. There is
    no third attempt, and a test asserts the log holds exactly two attempt lines.
  - **`Preparation` is not retried**: a parked seat, a spec that cannot be read, a directory that cannot
    be written. A second attempt would repeat the same refusal verbatim and dress it up as a transient
    fault. `From<String>` keeps those sites returning strings.
  - The stage is one of `tmux launch`, `pane exit before readiness`, `runner death record`,
    `readiness window` — the same fact the returned refusal names, so the log and the error agree.

## Runs at this change

- `cd agenthub_client/rust/agenthub-runtime && cargo test --offline` = **182 passed**, 0 failed
  (three consecutive runs; also `tests/held_send.rs` 1, `tests/seat_guard.rs` 18,
  `tests/umask_at_the_entry.rs` 1).
- New case `a_dying_start_names_the_stage_in_the_seat_log_and_retries_exactly_once`: a seat whose command
  does not exist. Asserts the refusal says `(final)` / `did not start after 2 attempts`, the log holds
  exactly two `start attempt` lines and one `start final` line, and both name
  `pane exit before readiness`. **Falsified**: with `START_ATTEMPTS` set to 1 the case fails on the
  attempt count.
- Flake found while running the suite in parallel and fixed at its cause: `pty::pane_pid_tests::a_live_session_answers_a_pid_and_the_record_describes_it`
  opened a live pane without taking the process's tmux root, while every guarded pane test swaps
  `TMUX_TMPDIR` and runs `kill-server` when its guard drops — which ended that case's session
  (failed twice, passed alone). It now takes `test_servers::own("pane-pid-live")` like its neighbours.

Client branch `4genthub-min/test-argv-refusal` (submodule `agenthub_client`).
