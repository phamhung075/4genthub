# The surface inventory reconciled with HEAD, so the census suite goes green

T13 unit 1, per `ARCH-RULING-T13-2026-10-13.md` (the architect's ruling) and the lead's row
`qitem-20261013193420-aebd8e6db82176f4`. Everything below was measured at `6adbbc3f`, read-only before
the edit and re-run after it; the commit is on `4genthub-min/t13-surface-inventory`
(worktree `wt/t13-surface-inventory`), one commit, two files plus this record.

## What actually moved

Every diff the three instruments reported was decided row by row — *which side moved: the tree, the
document, or the instrument* — and in every case the tree moved and the document was a stale reading of
it. The evidence is a measurement on both sides, not a rewrite to make a check pass:

- **Routes (eight registrations, four commits).** The document's Reproduce line dated its figure at
  `3e81e1e9`, where `grep -rn "mux.HandleFunc(" … fastmcp/server/httpapp fastmcp/auth | wc -l` returns
  **148 (httpapp 128, auth 20)** — the document's own number, true when written. At HEAD the same
  command returns **156 (httpapp 136, auth 20)**; counted at each commit in between: 150 at `2634db82`,
  154 at `d50462e5`, 155 at `a2011dc2`, 156 at `c622ad4f`.
- **Tables (one table, one commit).** `2634db82` registered `room_decisions`: the depth-1 entry count of
  `seatDatabaseTables` is 15 at `2634db82^` and 16 at `2634db82` and HEAD, and the DDL file's
  `^CREATE TABLE IF NOT EXISTS` count is 17 before that commit and 18 at it. That single table is the
  whole of seat tables 15 -> 16, registered total 39 -> 40 and SQL statements 17 -> 18; core 19, auth 3
  and team 2 were re-read at HEAD rather than carried.

## Fixed

`ai_docs/api-integration/surface-inventory.md`

- **11 stale route rows.** §1.1 `app.go` 137/162/175/183/191/212/220 -> 142/170/183/191/199/220/228
  (`GET /health` through `POST /api/v2/projects/{id}/health-check`); §1.3 `task_routes.go`
  121/150/173/177 -> 135/164/187/191. Each new number was opened at that line and is the registration
  the row names.
- **Four counts.** `httpapp` route registrations 128 -> 136 (the Reproduce line now heads with **156**,
  and keeps **148** at `3e81e1e9` in its own chain); seat tables 15 -> 16; registered tables total
  39 -> 40; SQL `CREATE TABLE` statements 17 -> 18 (the unanchored pair is therefore 19/18).
- **Five §3.3 anchors.** `machines` `:324` -> `:369`; `seat_messages` `seat_tables.go:357` -> `:426`
  and DDL `:306` -> `:351`; `seat_status` `:335` -> `:380`; `machine_edges` `:355` -> `:400`.
- **The row §3.3 was missing:** `room_decisions` (`RoomDecisionORM`, `seat_tables.go:362`, DDL `:311`),
  the registry's 16th seat table. This is the same class of absence the section already records for
  `seat_feedback` (2026-10-06): the section listed 15 of the registry's 16 tables while its own count
  statement said 15 — two numbers that agreed with each other and with nothing in the tree.
- **Prose citations, in the two paragraphs this pass had to rewrite anyway**, each verified one at a
  time: §1.1's project-creation clause (`app.go` 146/151/152/156 -> 170/175/176/180), `App.Handler`
  (`:121` -> `:139`), §3.3's composition and `init()` (`:397`/`:402` -> `:466`/`:471`), and the
  `seat_feedback` boot note (`app.go:61-63` -> `:79-83`). Dated notes record each, per the file's own
  rule that a citation asserts what the code says now while a quotation keeps what a document said then.

## Changed

`scripts/COUNTS-AUDIT.py` — `EXPECTED` re-derived for exactly those four rows (128 -> 136, 15 -> 16,
39 -> 40, 17 -> 18), with the movement named in each comment and the per-commit measurements recorded
there. This is required rather than incidental: the file defines `EXPECTED` as *the numbers the document
states*, and the audit's verdict is `doc == EXPECTED == tree`, so a document reconciled to the tree
cannot go green while the instrument's mirror of it is stale. No anchor pattern, coverage line, rule or
exit path changed — the instrument still fails on any of the three drifting again.

## Tests

Run in the worktree at the commit, with `PYTHONDONTWRITEBYTECODE=1`:

- `python3 scripts/CITATION-AUDIT.py` -> `rows 148  stale 0  unresolved 0`, exit 0.
- `python3 scripts/COUNTS-AUDIT.py` -> all eleven rows `matches`, "all numbers re-derived and matching",
  exit 0.
- `python3 scripts/S3-REDERIVE.py` -> `rev=HEAD base=a7990665  rows=46  anchors=67`, `FRESH 67
  STALE->BATCH 0  STALE->EARLIER 0  UNRESOLVED 0`, exit 0.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_census_audits.py -q` ->
  **13 passed** (its six reds included `…instrument_is_clean_at_head…` x3, the clean-revision no-op case
  and `test_the_census_instrument_can_fail[script0]`, which the ruling predicted would clear with the
  rest — it did, so the `--self-test` still goes red when perturbed).
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` -> **92 passed** (86 + the six).
- `cd agenthub_go && go test ./...` -> exit 0 (every package ok).
- `cd agenthub_client && go test ./...` -> exit 0, with the submodule initialized at the pin `f193f34`.

## Not in this change

- `NEXT-GEN2.md` and any other plan/root document: T13's own check line (`go test ./...` at the repo
  root) is wrong there — there is no root `go.mod`/`go.work` — and correcting it is the owner's call.
- **Prose citations outside those two paragraphs.** `S3-REDERIVE.py`'s own coverage block counts 161
  anchors on non-table lines that no instrument resolves, and this pass did not chase them: it fixed the
  ones inside the paragraphs it was already rewriting. A full prose re-resolution is its own unit, and
  it is named here rather than left to look covered.
