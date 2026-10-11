## Section 4's gone list re-measured — and the near-miss it caught about the working tree

### Changed

- `ai_docs/api-integration/surface-inventory.md` §4, in four places:
  - **the table's row 1 Result cell** now carries the re-measured pickaxe answer: `git log --oneline -1
    -S'agent-library' -- agenthub_main` returns **`a50929c6 chore: remove agenthub_main, the retired Python
    backend`** today, because that later commit deleted the rest of the tree the path sits in, while
    **`60bcdb68` remains the library's own removal** (its diff carries 261 lines of `agent-library/README.md`).
  - **the two `NO MATCH (both)` cells** now read `NO MATCH (Go)` with the `agenthub_main` half marked
    **UNRUNNABLE as written**: that tree no longer exists, so the command errors `No such file or directory`
    instead of returning a result. One tree, not two, is the honest phrasing from here on.
  - **the distinction block** — the part that must not be collapsed — keeps its two live anchors and re-points
    the dead one: `ddd_compliant_mcp_tools.go:249` (the `manage_agent` definition) and
    `tool_input_schemas.go:126` (the `call_agent` schema entry) are **unchanged at HEAD**;
    `agent_mcp_controller/unified_agent_description.go:101` was **deleted by `8fa51fd7`**, so it is replaced by
    the description's current home `manage_agent_description.go:26`/`:45`, and the handler that consumes the
    field (`mcp_routes.go:481`-`:486`) and the served schema's pin (`testdata/tools_golden.json:668` through
    `mcp_routes_test.go:119`) are added.
  - **a dated RE-MEASURED 2026-10-10 note (docs duty pass 7)** carrying all of the above, including the
    near-miss below.

### The near-miss, recorded because it is the reusable part

- **The first measurement of the three anchors was taken in the dirty working tree and concluded "all three are
  dead".** Re-measured at HEAD in a clean worktree, two of them are alive and carry exactly what the 2026-10-06
  note claims — the dirty tree showed `}` and a comment line because **go-dev's item-3 edits are uncommitted**
  (files of 296 and 177 lines instead of 311 and 186). **The note therefore leads with the hazard rather than
  the fix: measure at HEAD, in a worktree, or the working tree will be mistaken for the repository.**
- **The same in-flight work moves the instruments, and the note says so:** `scripts/COUNTS-AUDIT.py` in the
  dirty tree reports published MCP tools **9** against the document's 10, core tables 19 against 20 and
  registered tables 39 against 40, while the same audit on a clean HEAD copy ends "all numbers re-derived and
  matching" with rc 0. A red COUNTS standing beside an item-3 edit is the tree, not the document.
- **A watcher for the next pass:** the distinction's present tense ("still live") is true at HEAD and expires
  with item 3 (`manage_agent` retires; its step-1 test is already in the working tree), after which it is a
  dated record.

### Verified

- A 19-claim throwaway check over the edited §4 and the code side at HEAD — all pass, including both re-pointed
  anchors, the successor file's two `call_agent` lines, and the deleted file's absence.
- The dead anchor's original claim was confirmed before re-pointing by reading it out of the commit that
  removed the file: `8fa51fd7^:…/unified_agent_description.go:101` is
  `props.Set("call_agent", unifiedAgentStringProperty(unifiedParamDesc("call_agent")))` — exactly what the
  document said the line was.
- `scripts/S3-REDERIVE.py` rc 0 (`every anchor in section 3 is fresh at rev=HEAD`, 0 of 46 rows with a
  not-fresh anchor); `scripts/CITATION-AUDIT.py` `rows 145 stale 0 unresolved 0` rc 0; `scripts/COUNTS-AUDIT.py`
  green on a clean HEAD copy and red only in the dirty tree, as recorded above.

### Not touched

- No Go source, test, route, table, migration or frontend file. One document is edited; explicit paths only,
  because the tree carries other seats' in-flight work.
