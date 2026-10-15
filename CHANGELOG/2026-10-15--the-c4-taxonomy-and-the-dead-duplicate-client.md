# The C4 taxonomy and the dead duplicate client, on the board

Two facts the lead asked the board to carry rather than remember: what the C4 reading's three failures
actually are, and a second client living inside the backend. Both are re-measured here, and two numbers
in the row that routed the second one do not reproduce.

## Changed

- **The C4 taxonomy is on the board: one runtime tree defect, one reading gap, one harness fault.** Each
  with its file:line, re-read at the source rather than copied:
  - FAIL 1 `pty/mod.rs:154` — `.and_then(|l| l.parse().ok()).unwrap_or(0)`: a failed tmux read becomes
    **pid `0`**, logged as fact at `:155`, and `supervisor/mod.rs:557-563` declares the seat dead with
    that pid in its own sentence. C4's criterion 1 is measured through that launcher, so it can fail a
    room for no product reason.
  - FAIL 2 — the cap is the product's own: `frame.rs:28` **`MAX_FRAME_BYTES = 131_072`**, so no size the
    sweep reaches can spill, which is why "no cap" and "a cap above the sweep" look the same.
  - FAIL 3 — the nudge cadence **is** wired: `ipc/mod.rs:284` `NUDGE_POLL_INTERVAL_SECS = 2`,
    `runner/mod.rs:1168` `MAX_NUDGE_ATTEMPTS = 3`, ladder 1/2/4 s at `:1170` (asserted `:1959-1964`).
    The lead's own "knob not wired" claim is corrected on the record.
- **A dead duplicate client in the backend is now a board line, ruled a deletion candidate ordered after
  the C4 sequence:** `agenthub_go/cmd/agenthubclient` + `agenthub_go/internal/{clientbridge,clientcmd,clientsync}`,
  imported by nothing but that command, absent from every deploy config, CI, Makefile and shell script,
  with no `commpolicy` at all.
- **Two corrections to the row that routed it, because the surface was re-measured instead of copied:**
  only **two** of the four internal packages it names exist (`clientlifecycle` and `clientwatch` are the
  live client's packages in the submodule); and the copy is **36 files (29 .go)**, with **63** files
  differing from the submodule's same-named packages — not 88. The finding survives; its size is now the
  measured one.

## Instruments

- `sed -n '150,158p' agenthub_client/rust/agenthub-runtime/src/pty/mod.rs` → the `unwrap_or(0)` at line 154.
- `sed -n '555,562p' …/supervisor/mod.rs` → the death message naming `pid {pid}`.
- `grep -rn 'MAX_FRAME_BYTES' …/src/` → `frame.rs:28` is the definition; `runner/mod.rs` are the users.
- `grep -rn 'NUDGE_POLL_INTERVAL_SECS\|MAX_NUDGE_ATTEMPTS' …/src/` → `ipc/mod.rs:284`, `runner/mod.rs:1168`.
- `grep -rn 'agenthubclient'` over Dockerfiles, captain-definitions, yml, Makefiles and shell scripts → nothing.
- `diff -rq` per package pair → clientbridge 19, clientsync 42, clientcmd 2.
- Both landings recorded in the same commit: `main = 0ac44533`, `git diff 1d659db5..main | git patch-id --stable`
  = `ae899a1a…`, `team.json` at main reads `links` 0 with five `omp` seats.

## Not in this change

No code, no test, no pin; `e3074353` untouched. `NEXT-GEN2.md` plus this entry, one commit above the
landed main.
