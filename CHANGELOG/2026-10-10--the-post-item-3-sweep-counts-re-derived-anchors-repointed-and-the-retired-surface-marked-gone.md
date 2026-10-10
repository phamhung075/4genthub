## The post-item-3 sweep — three counts re-derived where they moved, nineteen anchors re-pointed, the retired agent surface marked gone

### Changed

- `ai_docs/api-integration/surface-inventory.md`:
  - **§3.1's twenty rows → nineteen, every remaining one re-pointed.** `76b800b9` deleted the agent registry out
    of the middle of `models.go`, so all nineteen surviving anchors were stale by 19 or 37 lines; each is
    re-derived at HEAD (`582`, `599`, `616`, `645`, `669`, `688`, `699`, `714`, `726`, `747`, `759`, `781`,
    `799`, `820`, `856`, `890`, `903`, `928`, `938`). **The `agents` row is struck rather than re-pointed: the
    table is no longer in `database.Tables`, so there is no line to cite.** `agent_sessions` and
    `agent_session_events` survive and are noted as session bookkeeping rather than registry.
  - **§3's registry cite `models.go:600 → :581`**; **§3.5's totals `20/40 → 19/39`** with the movement named as
    the retirement, and the `(core)` figure left unbolded because the audit anchors on that exact phrase.
  - **§2.3 is a nine-name table**: the `manage_agent` row is gone and its five `ToolDefinitions` anchors moved
    `:223/:227/:233/:239/:244 → :218/:222/:228/:234/:239`; the section's "all ten are present" sentence now
    says ten *until* `76b800b9`, nine at HEAD, and a dated re-measurement records the NINE with the generator's
    own output beside it (`145 routes, 9 tools`).
  - **§2.5's `TOOL_*` list is eleven names** (the twelfth was `manage_agent`, removed from `tool_config.go` by
    the same commit); **§2.4's `default` cite `:518 → :506`**; **§5's live registrations `:275 → :277` and
    `:139 → :141`**, with the report's own `:275` kept as the quotation it is instead of renumbered.
  - **§5's "distinction that must not be collapsed" is CLOSED rather than moved.** `call_agent` the tool was
    gone while `call_agent` remained a field of `manage_agent`; with `manage_agent` retired there is no host for
    the field, so the paragraph now says the distinction cannot be drawn in either direction, and says so with
    measurements (`ManageAgentToolName` → 0 hits, `manage_agent` in `tools_golden.json` → 0, the
    `agent_mcp_controller` package → absent, and the four surviving `call_agent` occurrences are the guards).
  - **§4's gone list gains three entries** — the `manage_agent` **tool**, the `agents` **table**, and the
    32-role registry with its controller tree — each with the command and its result, and the note that
    `76b800b9` added `manage_agent_absent_test.go`, which builds the registry through the production
    constructor and fails if the tool is published (so the absence is asserted, not assumed).
  - **A pass-9 paragraph** at the head records all of the above, names the revision it measured at, and states
    what it did not do; pass 8's closing sentence, which had deferred exactly this work, now points at it.

- `scripts/COUNTS-AUDIT.py`:
  - **Three `EXPECTED` rows retuned and annotated with the commit that moved them**: published MCP tools
    `10 → 9`, core tables `20 → 19`, registered total `40 → 39`. The lead's instruction was to record the
    movement rather than repin it silently, so each carries `76b800b9` by name and the sentence "the movement
    is the commit and not a counting change".
  - **The `published MCP tools` anchor moved off a dated record onto a live figure.** It used to read S1's
    generator line (`At db9d2bc3 it emitted **143 routes, 10 tools**`) — a DATED RECORD, so it would have kept
    reading 10 forever while the tree moved; it now reads §2.3's pass-9 re-measurement. This is the same class
    the pass is about, found in the instrument rather than in the document.

### Verified — at the revision this entry lands on (`585d18b3`), in a clean worktree

- `scripts/COUNTS-AUDIT.py` → **all eleven rows matching**, exit 0, with `MEASURED AT 585d18b3 … 0 uncommitted
  path(s)` (document 125/20/9/–/19/3/15/2/39/6/17 against the same tree figures).
- `scripts/S3-REDERIVE.py` → **`rows with >=1 not-fresh anchor: 0 of 45`**, "every anchor in section 3 is
  fresh at rev=HEAD" (45 not 46: the `agents` row is struck).
- `scripts/CITATION-AUDIT.py` → `rows 145  stale 0  unresolved 0`.
- `scripts/tests/test_census_audits.py` → **11 passed**. The three instruments read COMMITS, which is why this
  verification could only be run after the document was committed — S3 and COUNTS were red on the same content
  one commit earlier, from the working tree's point of view.
- The nineteen re-pointed anchors were derived twice and independently: by hand at `cd5d1187`, and by
  `S3-REDERIVE.py`'s own re-derivation, and the two agree (`models.go` moved between those revisions for
  unrelated seat work, so agreement is not a tautology).

### Not touched

- No Go source, test, route, table, migration or frontend file: one document and one instrument. The *dated*
  pass notes in the document keep their own numbers, because a record is read at its own revision — including
  the pass-7 note whose "the field is live" sentence this pass supersedes, which stays as written and is now
  answered by the paragraph below it.
