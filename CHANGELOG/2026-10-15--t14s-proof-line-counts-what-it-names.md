# T14's proof line counts what it names

**What this changes.** T14's proof line in `NEXT-GEN2.md` named "the five dated quotations" in
`ai_docs/api-integration/surface-inventory.md` as the case a checker must not touch. That count did
not resolve: the file has no set of five that a reader can point at. The line now names the **6
lines that state the reading they replaced**, lists them, and carries the command that reproduces
the count.

**Why it mattered.** It is an open item's evidence line. A number a reader cannot check is the same
defect the item exists to fix — a claim about a document resting on nothing that reads it — one
level up.

**The counts, re-runnable at `acf916c8`** (`ai_docs/api-integration/surface-inventory.md`):

| Reading | Command | Count |
|---|---|---|
| lines that name the reading they replaced | ``grep -nE 'this read `:[0-9]+`|this clause printed|this cited `'`` | **6** (`:86`, `:148`, `:441`, `:496`, `:572`, `:658`) |
| lines containing `re-resolved 2026-` | `grep -c 're-resolved 2026-'` | 10 |
| lines containing `2026-10-13` | `grep -c '2026-10-13'` | 8 |
| lines containing the word `quoted` | `grep -c quoted` | 5 |

The last three are the readings a reader can reach by guessing, and the entry names them because
none of them is the set the item needs: the first is the file's own annotation shape — a note that
prints the old `file:line` beside the new one — which is exactly a `file:line` that resolved at the
revision the note names and not at HEAD.

**Found by.** The reviewer's gate on `10a26acc` (verdict
`ai_docs/reports-status/GATE-board-item4-and-calibration-10a26acc-2026-10-15.md`), "One imprecision,
named not blocking", owner the architect.

**Not in this change.** No change to T14's check, its premise or the instrument.
