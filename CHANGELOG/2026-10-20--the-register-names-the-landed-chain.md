# The INT-03 register row names the landed chain and cites the opened lines

`ai_docs/core-architecture/nfr-register.md` went GATE on the INT-03 deletes in `85257484` and the
branch delete became aggregate-scoped in `040f6248`. The row that landed describes neither the final
commit nor the lines that exist at that rev, so the register read wrong in three ways:

- The row carried eight cells under the seven-column header. The table read then shifts Owner and
  Measured out of their columns; it is seven cells again, one enforcement cell (the commit chain) and
  one verification cell (the two tests and the file anchors). Every requirement row measures seven
  under the escape-aware split. The eighth cell in SEC-03 is a valid GFM `\|`, not a defect.
- It said "Q7 landed in four commits" and closed the chain on `33e369a6` "with the working-tree
  finish", a phrase that died when the branch landed. It names five now - `76b0d84d`, `a04131e3`,
  `ce3b1d87`, `33e369a6` (the author condition leaves the rest of the branch delete) and `040f6248`
  (aggregate scope, the project check the only tenancy control) - and Q7's paragraph carries the
  same five.
- SEC-01's tenancy boundary moves to `git_branch_repository.go:440`, the project/user condition;
  `:432` is the `HasUser` guard. Q5's `context_inheritance_cache` delete moves to `:456`; `:457` is
  `return err`. `CHANGELOG/2026-10-20--branch-delete-takes-the-non-cascade-children.md` names the
  same boundary in its sentence on the aggregate-scope rule and moves with it.

Checks on the corrected file: `S3-REDERIVE.py` FRESH 67, 0 stale, 0 unresolved; `CITATION-AUDIT.py`
rows 148, stale 0, unresolved 0; `pytest scripts/tests` 115 passed; no requirement row off seven cells.
