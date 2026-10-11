## Rule 84 in the counts audit — an anchor that matches nothing now fails and names itself

Found the same evening it was written into a rule: bolding one figure in `surface-inventory.md` made
`scripts/COUNTS-AUDIT.py` **quieter instead of redder**. The row's document figure could not be read, so the
audit printed `-` for it, compared nothing, and still ended "all numbers re-derived and matching". Rule 84
makes that a failure.

### Changed

- `scripts/COUNTS-AUDIT.py`:
  - **`read_document()` now returns `(figures, failures)`.** A DECLARED anchor that finds nothing — or that
    matches but whose group is not an integer, or whose document cannot be opened — produces a failure naming
    the key and the pattern. Only a key that declares no anchor (`DOC_ANCHORS[key] is None`) may state no
    figure, which is the honest half kept from before.
  - **Failures are counted before the quiet return**, so `--self-test` cannot report a pass over an instrument
    that has gone quiet, and they are printed as `ANCHOR    <key>: <why>` with the pattern beneath.
  - **The row's document cell shows `??`** instead of `-` when its declared anchor could not be read, so the
    table itself says "unreadable" rather than "absent"; the COVERAGE block and the verdict explain the rule
    and count those rows separately from a tree-vs-document disagreement.
  - **`--self-test` gains a third leg**: one anchor is replaced by a phrase that is in no document and the
    run must fail. It now prints `tree exit 1, document exit 1, unmatchable anchor exit 1 (PASS)`.
  - The header states the rule, and two stale examples in `DOC_ANCHORS`' comments (S1's line, §3.5's totals)
    were refreshed to the document's current shapes.

- `ai_docs/api-integration/surface-inventory.md` §3.5's instrument note now states the contract: **by rule 84 a
  DECLARED anchor that matches nothing FAILS `COUNTS-AUDIT.py` and names itself, rather than printing `-` and
  comparing nothing.**

### Red first, measured

The version at HEAD and the changed version were run against the same deliberately reworded copy of the
document, in the same checkout, one after the other (the reword is `runtime: 19 (core)` → `runtime: **19**
(core)`, a style this document uses everywhere else):

| | row's document cell | ANCHOR line | exit | verdict |
|---|---|---|---|---|
| **before** | `-` | *(none)* | **0** | `all numbers re-derived and matching` |
| **after** | `??` | `ANCHOR core tables: no match in the document` | **1** | counted, with its pattern printed |

### Verified

- `python3 scripts/COUNTS-AUDIT.py --self-test` → three legs, all exit 1, `PASS`.
- `python3 scripts/tests/test_census_audits.py -q` → **12 passed** in a clean worktree at HEAD, which includes
  the new case (`test_counts_audit_refuses_an_anchor_that_matches_nothing`); `scripts/COUNTS-AUDIT.py` against
  the clean worktree prints every row matching, exit 0.
- The new case passes in the dirty primary as well, because it asserts the ANCHOR marker rather than an exit
  code — a run also reads the working tree, and a busy checkout can fail the tree half for reasons that have
  nothing to do with the anchor.

### Not touched, and observed

- No Go source, route, table or frontend file.
- **The census test file is dirty-tree-sensitive** (reported here rather than fixed): its "clean at HEAD" cases
  run the instruments against the WORKING TREE for the tree half, so the file went `3 failed, 9 passed` in this
  checkout while another seat had an uncommitted route — `httpapp` read 126 against the document's 125. A gate
  must run these in a clean worktree; the file does not enforce it.
