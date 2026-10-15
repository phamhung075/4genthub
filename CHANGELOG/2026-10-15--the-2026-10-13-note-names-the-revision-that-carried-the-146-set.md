# The 2026-10-13 note names the revision that carried the `:146` set

`ai_docs/api-integration/surface-inventory.md:84` closed its 2026-10-13 re-resolution with "these four
read `:146`/`:151`/`:152`/`:156`, the same block 24 lines higher" and named `6adbbc3f` for that reading in
the same sentence, while its own parenthetical then gave `6adbbc3f`'s numbers as
`:170`/`:175`/`:176`/`:180`. Both halves cannot be `6adbbc3f`.

Measured from the source, not from the note's own description:

- `git show 6adbbc3f:agenthub_go/fastmcp/server/httpapp/app.go` — `const base` `:169`,
  `mux.HandleFunc("POST "+base+"/", …)` `:170`, `_ = r.ParseForm()` `:175`,
  `missingForm(r, "name")` `:176`, `r.PostForm.Get("name")` `:180`.
- `git show 36716e6e:agenthub_go/fastmcp/server/httpapp/app.go` — `const base` `:145`, the registration
  `:146`, `_ = r.ParseForm()` `:151`, `missingForm(r, "name")` `:152`, the value read `:156`.

So `:146`/`:151`/`:152`/`:156` is the SAME BLOCK 24 LINES HIGHER that `36716e6e` carried, and the note
attributed it to the revision after the movement. Found by the architect's second-pair-of-eyes row on
`b114d0ae`, which listed it as the one defect that amendment does not fix.

The note is corrected in place rather than annotated with a further dated note, because its subject is a
revision and not a document's wording — the rule this file states at `:735` (a citation asserts what the
code says now, a quotation asserts what a document said then). It now names `6adbbc3f` for
`:170`/`:175`/`:176`/`:180` and `36716e6e` for the `:146` set, and keeps the cause of the movement.

Evidence, in the worktree that carried it, tree clean before and after: `CI= python3
scripts/CITATION-AUDIT.py` printed `rows 148  stale 0  unresolved 0` and exited `0`; `python3 -m pytest
scripts/tests -q` printed `91 passed`.

## Not in this change

No citation moved and no other byte of the document changed: this is one sentence's attribution inside a
dated note.
