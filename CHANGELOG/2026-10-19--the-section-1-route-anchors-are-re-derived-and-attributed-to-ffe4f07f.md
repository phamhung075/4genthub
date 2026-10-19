# The surface inventory's section 1 route anchors are re-derived and attributed to `ffe4f07f`

## Fixed

`ai_docs/api-integration/surface-inventory.md` §1 — **every stale route anchor was moved by one commit,
and the section's counts are unchanged.** `scripts/CITATION-AUDIT.py` at `379dd005` reported
`rows 148  stale 51  unresolved 0`; after the edit it reports `stale 0`, exit 0.

**The cause is one commit, not fifty-one coincidences.** `ffe4f07f fix(context): the factory refuses
instead of installing a mock` is the only commit to touch
`agenthub_go/fastmcp/server/httpapp/app.go` or `routes_mount.go` since the inventory's last route sync
at `51f3dc01` (`git log --oneline 51f3dc01..379dd005 -- <both paths>` names it alone). Its
`git diff -U0` carries:

- `app.go` — three lines added at `:34` (the `ctxFactory` field and its comment) and four net at
  `:74` (the constructor's error return): **+7 above every cited registration**, which is the seven
  `app.go` rows.
- `routes_mount.go` — one net line at `:53` (the nil guard around the context mount): **+1 above
  every cited registration**, which is the forty-four rows from `:85` to `:475`.

No registration was added or removed: the audit still reads `rows 148`, and §1's Reproduce line keeps
`156 (httpapp 136, auth 20)`. The rewrite moved only the `file:line` cell of each stale row; a
line-by-line check confirmed each changed pair is identical apart from the number and the delta is
exactly +7 for `app.go` and +1 for `routes_mount.go` (51 pairs, 0 bad).

## Verified

- `python3 scripts/CITATION-AUDIT.py` at the worktree with the edit -> `rows 148  stale 0
  unresolved 0`, exit 0.
- `python3 scripts/S3-REDERIVE.py` -> `every anchor in section 3 is fresh`, exit 0 (the §3.1 fix is
  in the base, `c5cd8434`).
- `python3 scripts/COUNTS-AUDIT.py` -> exit 0.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_census_audits.py -q` at the
  **uncommitted** worktree -> `1 failed, 12 passed`; the one failure is
  `test_the_census_instrument_is_clean_at_head_and_says_how_much_it_read[script0-rows (\d+)]`, which
  reads a detached export at `HEAD` (`379dd005`, before this edit by construction). After the lead
  commits this path set, the same command is expected to be `13 passed`; that is the landing check.
- Docs only: no `.go`, `.sql` or test file changed.

## Not in this change

- §1's prose citations are outside `CITATION-AUDIT.py`'s row coverage (`S3-REDERIVE.py`'s coverage
  block counts 161 anchors on non-table lines that no instrument resolves). This pass re-derived the
  51 table rows the instrument reads; the prose class is its own unit.
