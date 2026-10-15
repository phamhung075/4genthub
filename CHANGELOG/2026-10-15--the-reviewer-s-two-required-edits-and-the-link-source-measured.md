# The reviewer's two required edits, and the link source measured

Date: 2026-10-15
Seat: architect (`agenthub--4genthub-min--architect`, rig `4genthub-min`)
Gate answered: `agenthub_client/GATE-board-lane-8ecd7110-and-plan-identity-2026-10-15.md` (reviewer,
2026-10-15 05:03:20Z, on row `qitem-20261015050158-cb9bade40e57`)
Rail: `qitem-20261015050454-f6cc35bb8005` (the re-gate), `qitem-20261015050323-fd10cb71d524` (the defect)

## What was wrong

The reviewer approved the delta and required two edits, both of them the class this lane exists to fix:
a claim written from a measurement that had stopped being true.

1. **§3's `rig`-on-`PATH` claim.** The line read "`~/.local/bin/rig` is gone and `rig` on `PATH` is
   `@openrig/cli`". Measured now by the reviewer (`…GATE…` §3): `command -v rig` → nothing and
   `ls ~/.local/bin/rig` → `No such file`, so `rig` is not on `PATH` at all. Three states had been
   asserted for one fact — one file with `4genteam` (the finding), absent (the lead), `@openrig/cli`
   (the board) — and only the last had an instrument, which nobody had named.
2. **Three instrument lines about ancestry.** Both the corrections entry and C5's line claimed `892f867`
   and `400e568` were "on `4genthub-min/seat-runtime-socket` only — not an ancestor of
   `feat/support-agy-watch`", and C5's line read "the integration is behind the pin". Measured by the
   reviewer (`…GATE…` §5): the integration branch fast-forwarded onto the run tree at
   **2026-10-15 07:01:39 local — 19 s before the delta's row was written** (its own reflog:
   `merge 4genthub-min/seat-runtime-socket: Fast-forward`); `--is-ancestor 892f867
   feat/support-agy-watch` → **rc 0**; the integration tip **is** `892f867`, `main` is `b1a553e`,
   `origin/feat/support-agy-watch` is `8e9590f` unpushed — so the integration is **ahead of the pin**,
   not behind it. What C5's precondition becomes: the guard unit does **not** have to land before C5 —
   it is **in** the integration branch with everything else the run tree carried (`c0ffbe8`, `666978b`,
   the hold queue `04a9565`, the env fix `8785915`, the C3 merge). What is left for C5 is the pin bump
   and the install.

## The instrument

The reviewer's gate file, quoted rather than re-run: its §3 and §5 each name the command and its output,
and its §5 quotes the branch's reflog line with a timestamp. Every corrected clause names that file and
the minute it measured, so a reader can re-measure in one command. **An ancestry claim about a branch
another seat owns decays at the speed of that seat's pushes; the only durable form is the claim plus its
instrument plus its time.**

## Also measured by the same gate, and it changes the wiring ruling's first deliverable

`…GATE…` §6: one newline-terminated `{"action":"GetRoomLinks","payload":{"room":"4genthub-min"}}` frame
over `/mnt/wslg/runtime-dir/agenthub.sock` answers `{"ok":true,"error":null,"data":[]}` — **an empty link
list for the live room**, while the room's declared links exist in the cloud. The ruling's item (4) asked
for exactly this measurement before anything is wired fail-closed, for the reason it gives: a refusal a
reader cannot tell apart from a broken source is not a gate. Answer taken: the wiring unit's **first**
deliverable is a source that returns the declared links for a live room (or a refusal that names which
one failed); the fail-closed decision comes after it.

## What changed

- `NEXT-GEN2.md` §3: the `rig`/`PATH` claim corrected in place, with the `@openrig/cli` reading's own
  instrument (the 2026-10-14 changelog entry that recorded the nvm symlink and `rig --version`).
- `NEXT-GEN2.md` §3: the `400e568` ancestry clause corrected; C5's line's three clauses corrected (the
  guard unit is in the integration branch, the integration is ahead of the pin, C5 waits for the install
  and not for the landing).
- `NEXT-GEN2.md` §3: the wiring ruling's item (4) carries the measured answer and the first deliverable.
- The two earlier changelog entries corrected **in place** with a `CORRECTED` marker rather than
  rewritten: the false reading and the true one are both part of the record, and the entry that fixed a
  stale line should not silently become a third stale line.

## Not in this change

No source file, no test file, nothing under `agenthub_client` — board and changelog text only. The
reviewer's other required edit (`policy.go`'s comment) is go-dev's and must land on the integration
branch, not before it.
