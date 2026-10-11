## The census instrument stops asserting an attribution it cannot support, and stops calling an empty read clean

### Fixed
- `scripts/S3-REDERIVE.py`: with a base that is not in the checkout, a not-fresh anchor was labelled `STALE->EARLIER` while the BASE column read `None` — an attribution to a base that was never read. It now prints `STALE (unattributed)`, and the summary line uses the same words. Reported as the reviewer's MINOR on row `9e3249e2` and reproduced here with a perturbed copy plus a dead base.
- The same file could be VACUOUS: a section 3 with no parseable rows, or a document with no `## 3.`/`## 4.` headings, printed `every anchor in section 3 is fresh` and exited 0 — a clean line from a read that found nothing. The missing headings also raised `StopIteration` rather than answering. Both now print `REFUSED-VACUOUS: no anchors were collected from section 3 ... This is NOT a pass.` and exit 2.

### Documented rather than left to be discovered later
- The docstring's uncovered list gains the two limits the same gate named: `find` takes the FIRST match per candidate path, so a file carrying several `Tables = append(` lines would only ever have its first considered — the §3.2 attach-line species; no row cites a later one today (all 66 anchors fresh), and `def`/`sql` are table-named so the first match is the right one for them. And the two sibling instruments read the WORKTREE document while this reads the commit at `rev`, so an uncommitted edit to the inventory can make their verdicts disagree, which the suite reports as a red run rather than a silent pass.

### Testing
- `scripts/tests/test_census_audits.py` gains two cases (11 total): a perturbed copy audited against an absent base must exit 1, print `STALE (unattributed)`, and must NOT print `STALE->EARLIER`; a document with no section 3 must exit 2 with `REFUSED-VACUOUS` and must NOT print a clean line.
- `python3 scripts/S3-REDERIVE.py` at HEAD -> `rev=HEAD base=a7990665 rows=46 anchors=66`, `FRESH 66`, rc 0.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` -> 101 passed.
