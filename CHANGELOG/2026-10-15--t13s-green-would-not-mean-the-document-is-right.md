# T13's green would not mean the document is right

**What this adds.** One clause to T13's measured line on the board: the seven `app.go` re-points
that the suite is waiting for will turn `pytest scripts/tests -q` green, and the document will
still contradict itself seven lines below the table they repair.

**The measurement it rests on.** At main `80e51824` in `ai_docs/api-integration/surface-inventory.md`
the paragraph at `:84` is a live clause asserting `app.go:170` registers `POST /api/v2/projects/`,
`:175` parses the body, `:176` refuses the body without `name`, `:180` reads the value. The truth in
`agenthub_go/fastmcp/server/httpapp/app.go` at the same commit is `:179`, `:184`, `:185`, `:189`
(resolved by grep, not quoted from the instrument). Three more live prose cites are stale the same
way: `:86` (`:139`/`:140` → `:148`/`:149`), `:441` (`:71` → `:99`), `:563` (`:79-83` → `:88-92`).

**Why the suite cannot catch it.** `scripts/CITATION-AUDIT.py` reads exactly one file's table rows
(`INV`, line 61) and `--write` repairs only what it measures: measured on `4genthub-min/census-repoint`
at `7360008e` it rewrote **0** citations on a tree where `:84` was stale. So the acceptance clause and
the document's accuracy are different questions, and the clause must not be read as the second.

**The rest of the class is a record, not rot.** The same file holds ten non-table `app.go` citations;
the other five sit in dated records (`:63` the 2026-10-10 anchor sweep, `:409` the 2026-10-09 §2 pass,
`:720` the 2026-10-08 counts note, `:735` the companion rule quoting the 2026-10-06 CHANGELOG) and the
document's own rule at `:735` requires them kept: a quotation asserts what a document said then.

**Not in this change.** No code, no test, no instrument, no repoint: `NEXT-GEN2.md` plus this entry.
The design question this raises is with the lead as
`seats/architect/DESIGN-NOTE-census-instrument-coverage-and-the-prose-class.md` (17:25Z).
