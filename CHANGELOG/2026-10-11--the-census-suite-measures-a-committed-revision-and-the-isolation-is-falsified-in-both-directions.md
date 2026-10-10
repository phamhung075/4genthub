## The census suite measures a committed revision — and the isolation is falsified in both directions

The census test file's "clean at HEAD" cases ran the instruments against the **shared checkout**, so the
tree half measured whatever any seat happened to have in flight. Measured before this change: `3 failed,
9 passed` in this room while another seat's uncommitted route made the `httpapp` count read **126** against
the document's 125. A red with no defect behind it — rule 82's hazard inside a test, and precisely the red a
batch certification would read as a defect in the batch. This is the row the observation asked for.

### Changed

- `scripts/tests/test_census_audits.py`:
  - **A module-scoped `clean_export` fixture**: a detached `git worktree` at HEAD, unregistered in a
    `finally`. The three "clean at HEAD" cases run the **export's own copies** of the instruments with
    `cwd=<export>` — which works because each instrument derives its root from its own location, so a copy
    inside the export reads the export. One worktree for the module, not three: each `git worktree add` is a
    full checkout.
  - `run()` gained a `cwd` parameter; `in_export()` resolves the export's copy of a script.
  - **A new case, `test_the_clean_revision_reading_is_not_a_no_op`, with falsification in BOTH directions:**
    (1) green on the export as committed; (2) **red for a genuine TREE mismatch** — one counted line appended
    to the export's `httpapp/app.go` must move the route count (the probe is a *comment* carrying
    `mux.HandleFunc(`, which is enough because the instrument counts the pattern with grep — its documented
    naivety); (3) **red for a genuine DOCUMENT mismatch** — the export's own document reworded one route
    lower must fail and say `DOCUMENT says`; (4) green after each restore, so the red is the probe's doing.
    An isolation that is a no-op — an empty export, or instruments still reading the shared checkout — passes
    (1) and fails (2) or (3), which is the whole reason the case exists.

### Verified

- **Direction 1, the one that was measurable in the room as it stood:** the whole file in the DIRTY primary
  checkout, with **6 uncommitted paths** under `agenthub_go` at the time, is now **13 passed** — where the
  same file was `3 failed, 9 passed` before the change.
- **Direction 2, demonstrated by hand as well as inside the case** (a worktree, not the shared tree): clean
  export → **exit 0**; one counted line appended → `httpapp route registrations 125 125 126  TREE has 126,
  this file expects 125`, **exit 1**; restored → **exit 0**.
- The case restores by writing the original bytes back rather than by `git checkout`, because this seat's
  tool policy refuses that command — which also means it cannot silently revert more than it changed.

### Not touched, and one consequence worth knowing

- No instrument, document, Go, route or frontend file: the test file and this entry.
- **The suite now costs one checkout.** `git worktree add` per module, cleaned up in a `finally`; the run
  measured 3.1s in the dirty primary. If a future change makes the fixture fail, the failure is loud rather
  than a skip: without a git checkout the test fails with a message naming the missing `.git`, since a test
  that goes quiet is the failure this whole evening was about.
