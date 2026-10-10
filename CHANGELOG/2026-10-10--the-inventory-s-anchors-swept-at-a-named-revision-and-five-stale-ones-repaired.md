## The surface inventory's anchors swept at a named revision — five stale ones repaired, and the instrument that was reading the wrong tree

### Changed

- `scripts/COUNTS-AUDIT.py`: the tracked census audit now prints `MEASURED AT <rev> in <root> - <n>
  uncommitted path(s)` above its table, and warns when that count is non-zero, so a red row can be attributed
  to the revision and the working state it was read at. Exit codes and row parsing are unchanged, and its own
  `--self-test` still reports PASS.
- `ai_docs/api-integration/surface-inventory.md`, in six places: a new **ANCHOR SWEEP** pass paragraph (docs
  duty pass 8, measured at `c08a742e` and re-read at `fa19f84a`), and the five stale claims it repaired,
  each keeping the line it used to name:
  - §1.1 **`app.go:120 → :121`** — `:120` is the doc comment `// Handler returns the HTTP mux.`; the
    declaration is one line below it.
  - §1.7 **`server/routes/websocket_routes.go:25 → :31`** — the sentence claims the `wslib` import "for the
    `WebSocket` type"; `:25` is the import block's `"time"` and `:31` is that `wslib` line. Its sibling
    anchor, `ws_mount.go:37`, was already exact.
  - §2.5's three **`IsWorkflowGuidanceEnabled()`** cites `:176 → :177`, `:336 → :339`, `:249 → :250` — the
    invocations, which is what the sentence claims ("the only method any caller invokes on it"); the old
    three were the enclosing declarations, and `subtask_mcp_controller.go:336` was a **blank line** above
    its `:338` declaration.
  - §3.4 **`models_prod.go:96 → :104`** and **`:8-12 → :13-16`** — `:104` is `var ProductionTables = …`;
    `:96` is a row-struct field. The `:8-12` range is the applied_migrations CORRECTION comment, while the
    "intentionally not appended" rule the sentence asserts is the header paragraph at `:13-16`, and that
    CORRECTION comment is what pushed the declaration from `:100` to `:104`.
  - §1.21 **`seat_feedback_mount.go:64-70 → :51-57`** — the range named the mount function and its list
    handler; the `seatFeedbackSubmission` struct the sentence promises is `:51-57`.
- **Coverage, stated in the pass paragraph rather than implied**, because the citations outside §1's route
  table are in no instrument: §1 by instrument (145 rows, 0 stale, 0 unresolved), §3 by instrument (66
  anchors fresh), §2/§3's table rows swept one by one (56 rows), every other `path:line` in prose read out
  of a clean worktree at HEAD. Not covered, and said so in the document: the 28 bare-path citations (their
  claim is only that the file exists), the citations inside dated records, and the client-package path —
  `agenthub_client` is a submodule, so nothing inside it resolves from this tree.

### The instrument that was reading the wrong tree

- **`~/.openrig/agenthub-seats/4genthub-min/COUNTS-AUDIT.py` was a pre-migration fork** whose `ROOT` was
  hardcoded to the primary checkout. Running it answered with whatever another seat had in flight: it
  reported published tools **9**, core tables **19** and registered tables **39** — go-dev's then-uncommitted
  item-3 retirement — while a clean copy of the same audit at HEAD reports **10 / 20 / 40** and exits 0 with
  every row matching, the document included. **That fork is removed.** The instrument is tracked as
  `scripts/COUNTS-AUDIT.py`, which derives its root from its own location and therefore measures the worktree
  it is copied into; **this pass added the line that says so out loud — `MEASURED AT <rev> in <root> - <n>
  uncommitted path(s)`, with a warning when that count is non-zero** — because a count is a claim about a
  revision (rule 82c). The fork's own stale `EXPECTED` memory, four rows behind the tree and the document, was
  the second half of the same failure, and the tracked file had already retuned those four.

### Verified

- At `c08a742e`: `scripts/CITATION-AUDIT.py` → `rows 145  stale 0  unresolved 0`, exit 0;
  `scripts/S3-REDERIVE.py` → `rows 46  anchors 66  FRESH 66  STALE->BATCH 0  STALE->EARLIER 0  UNRESOLVED 0`,
  exit 0; `scripts/COUNTS-AUDIT.py` → all eleven rows matching, exit 0, and its `--self-test` → PASS
  (perturbing one expectation fails both the tree half and the document half); and
  **`scripts/tests/test_census_audits.py` → 11 passed** in a clean worktree at that revision, which is what the
  instrument change had to keep true.
- The same audit run in the primary checkout prints the revision and its uncommitted-path count and shows the
  rows the dirty state moves — the reading is labelled now instead of being mistaken for the repository.
- The six repaired anchors were read again **from HEAD** at `fa19f84a`; five still hold where this lands. The
  sixth belonged to `agent_mcp_controller.go`, which **`76b800b9` retired** with the `manage_agent` tool and the
  `agents` table, and §2.5 says so in place of the citation it used to carry.

### The follow-on this pass does not claim to have swept

- **Item 3 landed between the measurement and this commit** (`76b800b9 refactor(agents): retire the manage_agent
  tool, the agents table and the role registry`), and at `678c0ae6` it moves three headline counts —
  `COUNTS-AUDIT.py` reads **9** published tools, **19** core tables and **39** registered tables against this
  document's 10 / 20 / 40 — and shifts **every §3.1 anchor in `models.go`**, which `S3-REDERIVE.py` reports as
  `20 anchor(s) are NOT fresh at rev=HEAD`. The consequence in a clean tree at that revision is that both
  instruments are red and the census test file fails: **that is the moved-counts pass, and it is its own task.**
  This pass's numbers are correct at the revision it measured, and the document's pass paragraph says which
  revision that is and what has moved since.

### Not touched

- No Go source, test, route, table or frontend file in this repository: one document and one script are edited
  (the census audit's revision line), plus the removal of the seat-local instrument fork, which is outside the
  repository. Explicit paths only — the tree carries other seats' in-flight work, and this pass had to measure
  around the item-3 retirement that landed in the middle of it.
