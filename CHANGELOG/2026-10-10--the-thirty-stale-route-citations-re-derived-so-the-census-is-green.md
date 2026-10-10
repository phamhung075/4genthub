## The thirty stale route citations are re-derived, so the census is green at HEAD

### Fixed
- `ai_docs/api-integration/surface-inventory.md`: the **30** rows whose `routes_mount.go` citation had
  moved now name the line each symbol resolves at, re-derived by the audit's OWN writer
  (`CI= python3 scripts/CITATION-AUDIT.py --write`). Each row moved forward by 38 to 52 lines, no row
  that was already correct was touched, and the diff is 30 insertions / 30 deletions in this one file —
  verified line by line: every changed pair differs in nothing but the trailing line number.
- Why it was red: `c0fed377` (the notify authorization fix) inserted lines above these routes in
  `agenthub_go/fastmcp/server/routes/routes_mount.go`, and the inventory's `file:line` citations follow
  that file. The last failure left in the canonical script suite was
  `scripts/tests/test_census_audits.py::test_the_census_instrument_is_clean_at_head_and_says_how_much_it_read`,
  which requires the check mode to exit 0 at HEAD. That case is green now and the suite is
  **81 passed, 0 failed** (it was 1 failed / 80 passed).
- `--write` refuses while a gate marker is set (`CI`, `PRE_COMMIT_*`), and this fleet's agent shells all
  carry `CI=true`, so the deliberate form is the tool's own documented one:
  `CI= python3 scripts/CITATION-AUDIT.py --write`. The rewrite re-runs the check itself afterwards and
  exits 1 if anything is still stale, so it cannot report a clean tree it did not leave.
- No source was edited: `routes_mount.go` is untouched, and the only path `--write` changed is the
  inventory above (`git status --porcelain` diffed before and after).

### Testing
- `python3 scripts/CITATION-AUDIT.py` -> rc **1** before (`rows 144  stale 30  unresolved 0`), rc **0**
  after (`rows 144  stale 0  unresolved 0`).
- `python3 scripts/CITATION-AUDIT.py --write` -> rc 0, `rewrote 30 citations in .../surface-inventory.md`.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_census_audits.py -q` -> **11 passed**.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q`, from the repository root with
  `OPENRIG_SKILLS_ROOT` unset and no `PYTHONPATH` -> **81 passed, 3 warnings in 11.4s**, 0 failed.
