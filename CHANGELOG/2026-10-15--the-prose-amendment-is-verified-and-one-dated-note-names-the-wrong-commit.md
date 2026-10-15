# The prose amendment is verified, and one dated note names the wrong commit

**What this adds.** An erratum on T13's measured line: the amendment it described as unlanded has
landed, and every number in it was checked against the code.

**The amendment, verified.** `4genthub-min/census-repoint` is now two commits, tip `b114d0ae`
(own patch-id `09dfce8d…`, 3 files, +76/−14, ff-ready from main `80e51824`). It repairs the four live
prose doc-lines — `surface-inventory.md:84` → `:179`/`:184`/`:185`/`:189`, `:86` → `:148`/`:149`,
`:441` → `:99` (with the `+28` named, not assumed from the table's `+9`), `:563` → `:88-92` — and
`ai_docs/setup-guides/complete-setup-guide.md:559` → `:179`/`:184`/`:185-186`/`:189`. The five dated
quotations (`:63`, `:409`, `:720`, `:735`) are untouched: eight changed lines in the inventory, four
pairs, exactly the four live clauses.

**At that tip, run not quoted.** `CITATION-AUDIT.py` → `rows 148  stale 0  unresolved 0`, exit 0;
`--self-test` → `perturbed the citation on line 76 by +7 → 1 stale reported against a baseline of 0,
the perturbed row named (PASS)`; `pytest --noconftest -p no:cacheprovider scripts/tests -q` →
`91 passed` (main reads `2 failed, 89 passed`). The self-test is the coupling the board's line
claimed, confirmed from the other side: it can demonstrate failure only when the baseline is clean.

**The one defect it did not fix.** The dated note on `:84` reads *"RE-RESOLVED 2026-10-13 (docs duty
pass 10) at `6adbbc3f` — these four read `:146`/`:151`/`:152`/`:156`, the same block 24 lines higher"*.
Measured: at `6adbbc3f` the block is `const base` `:169`, registration `:170`, `_ = r.ParseForm()`
`:175`, `missingForm(r, "name")` `:176`, `r.PostForm.Get("name")` `:180` — which is what the same
note's own parenthetical then says. `:146`/`:151`/`:152`/`:156` are `36716e6e`'s lines (`const base`
`:145`, registration `:146`, `:151`, `:152`, `:156`), the pre-movement reading. So the note names one
commit for two readings that differ by 24 lines; reported to the lead.

**Not in this change.** No code, no test, no instrument, no repoint: `NEXT-GEN2.md` plus this entry.
The guard question — nothing measures the prose class — stays with the lead as
`seats/architect/DESIGN-NOTE-census-instrument-coverage-and-the-prose-class.md`.
