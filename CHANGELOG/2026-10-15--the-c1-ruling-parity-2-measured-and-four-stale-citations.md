# The C1 ruling is written, parity 2 is measured, and four stale citations are corrected

Five board corrections and one ruling, all from measurements taken for this landing. Two of them
correct sentences this file wrote an hour earlier, and one corrects a citation the LEAD's row carried.

## Changed

- **§3 gains THE C1 RULING — the third primitive is the third reach, and the ruling is a ruling on a
  deletion.** The lead named the subject at 05:14Z (`qitem-20261015051416-842330a0f342`) and the
  definition was on this board the whole time, in P1's own sentence — which is the lesson recorded in
  the bullet: a definition can be a sentence inside the document it defines, and searching the rail, the
  transcripts and the task store instead of the board cost two hours of a blocked ruling. The ruling
  carries (1) the three reaches as they now stand, each verified by ancestry at `892f867`: read native
  (`55597e2`), delivery native (`9e392ae`), **third reach DELETED (`b24acfc`)** with the refusal and the
  three runtime-mediated builders (`rigSessionCandidates:196`, `rigSeatFor:274`, `rigTranscript:292`) in
  its place; (2) the refusal shapes, with the door's facts attached to them rather than to the deleted
  primitive; (3) the freeze list — no reach may shell out to the installed CLI, the third reach stays
  deleted, the decision attaches to the capability, the seat's own log stays the C2 observable, and
  **the ONE remaining text reach is named as a live exception so a successor does not re-open it**:
  `internal/clientwatch/watch.go:232-250`, `selfPath()` returning the literal `"4genteam"` when
  `os.Executable()` fails, emitted into a pane as text by `paneCommand`.
- **P1's clause "whose behaviour is unchanged" is corrected in place** — the reach is deleted, and the
  correction now says so explicitly instead of leaving the clause standing beside a correction that
  contradicted it.
- **THE PARITY-2 ADJUDICATION IS CORRECTED, in both places it appears (§3's run-5b bullet and §5 item
  5).** fe-dev sent the measured text; I re-measured the instrument, the leg and the artifact, and
  the change is deliberately partial: **run 5d PASSED B2 at 262144 B** (`evidence-run5d-all-20261014T2157Z`,
  327.6 KB / 1433 lines, TOTAL at line **1433** `124 pass / 3 fail / 2 skip`, the B2 leg's PASS lines at
  **671-686**), and the artifact is still on disk at 262173 B = `A`×262144 + newline +
  `EOFMARK-u32157516985-262144`. So
  "the leg's model of omp" was wrong and the item is **measured, not unproven** — but it is **not**
  promoted to a 5b pass and **not** deleted, and **the comparability clause stands**: 5d is not
  comparable to 5b (the harness revision changed at 21:41:16Z, during 5b), so `124/3/2` is not an
  improvement on `132/4/2`.
- **THE INTEGRATE PRECONDITION IS SATISFIED, and the hold clause with it.** Re-measured by ancestry:
  `c0ffbe8` **IN**, `666978b` **IN** `feat/support-agy-watch`; and `04a9565` *"the hold is a queue, so a
  second refusal cannot drop the first"* **IN** — so "the `c0ffbe8` required edit (single-slot hold)" is
  a phrase about an edit that landed (and it lives in the lead's amendment row, not on this board:
  `grep 'single-slot|single slot'` here returns nothing). What IS outstanding is the pair the lead
  named, both halves re-measured: **a BOUND on the queue** (`grep -cE 'MAX_HOLD|HOLD_DEPTH|MAX_HELD|the
  hold is full'` over `runner/mod.rs`, 2207 lines → **0**) and **the PUBLISHED COUNT** (`:484` mirrors
  the depth sentence while `:491` writes the count-free one into the state file). §5 item 1's
  parenthetical about `666978b` is corrected the same way — the diff is in the branch, the INSTALL is
  what is owed.
- **The lead's management ruling and the go-ahead land on the defect line.** The `manage_task` fault
  now carries the lead's INTERIM POLICY (`qitem-20261015051911-1c4575a9be36`): the rail and the gate
  files are the record, `delete`-and-recreate is forbidden as a repair, and create-then-update stays
  best-effort with the failure named on the rail — which replaces this file's own "the only repair a
  seat has is delete and recreate" from an hour ago. The fix is go-ahead to build, sequenced AFTER the
  two hold edits and the one rebuild, staged by go-dev and deployed only in the owner's window.
- **The link-set bullet gains the lead's SPLIT and the reviewer's deny fact.** Mechanism rides go-dev's
  unit today; the table of 12+11 is a data change the lead has put to the owner, and the gate is not
  armed on the live room until he ratifies it. And all twelve of the room's links are `allow:true` — the
  guard's explicit-deny branch has **no live instance** here, so the deny half is unexercised by this
  room's own data.

## Instruments

- `git merge-base --is-ancestor <sha> feat/support-agy-watch` in `agenthub_client` (tip `892f867`), one
  call per sha: `55597e2`, `9e392ae`, `b24acfc`, `04a9565`, `c0ffbe8`, `666978b` → **rc 0** each;
  **`b648c58` and `cf20608` → rc 1** (they are on `4genthub-min/go-dev`), which is why the C1 ruling
  names `b24acfc` alone.
- `grep -cE 'MAX_HOLD|HOLD_DEPTH|MAX_HELD|the hold is full' rust/agenthub-runtime/src/runner/mod.rs`
  → `0`; `:484` and `:491` read verbatim from the same file.
- `/home/daihu/wt/4genthub-min/u3-run/evidence-run5d-all-20261014T2157Z/evidence.log` → line 1433
  (TOTAL) and lines 671-686 (the B2 leg); `stat -c %s` on the artifact → **262173**; the artifact's
  tail is `EOFMARK-u32157516985-262144`. **fe-dev's path for the log does not exist** — the real root
  is `/home/daihu/wt/4genthub-min/u3-run/`, which the board already names as a third root.
- `internal/clientwatch/watch.go:232-250` read verbatim, and the reviewer's inventory
  `agenthub_client/GATE-reach-inventory-ea68236-2026-10-15.md` (§1 line 19, summary lines 22-23).
- **A tooling note that cost two of this landing's four verifications:** the read-only scouts this seat
  spawned had **no shell** (`read xd://bash` → "No such tool"), so their git claims came from reflog
  files and they said so; every ancestry and grep figure above was re-run by this seat with `bash`
  before it was written. Two of their four payloads carried a wrong path or a mis-scoped claim that a
  single command resolved — which is the argument for the rule, not against the delegation.

## Not in this change

No code, no test, no pin. `NEXT-GEN2.md` plus this entry; it sits one commit above the T13 landing
(which does touch `scripts/` and the test suite) and both fast-forward from `02c63789`.
