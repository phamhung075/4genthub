# The inventory's counts and §3 anchors follow the occupant table

`python3 -m pytest scripts/tests -q` is four tests red at `2b89edfc`, which is MAIN. The cause is
`f7744ae5` (task 35431928, the occupant record): it added one route
(`GET /api/v2/rooms/{room}/seats/{seat}/occupant-history`), one registered table
(`seat_occupant_changes`) and one DDL statement, and while §1 gained the route's row, nothing
downstream moved with it.

## Measured at `2b89edfc` (main), on a clean worktree

- `scripts/COUNTS-AUDIT.py` exit 1 on four rows: httpapp registrations **137** vs 136, seat tables
  **17** vs 16, registered tables total **41** vs 40, SQL `CREATE TABLE` statements **19** vs 18.
- `scripts/S3-REDERIVE.py`: **26 `STALE->BATCH` + 2 `STALE (unattributed)`** anchors; 18 of its 46
  §3.3 rows held at least one not-fresh anchor. The shifts are +28 in `seat_tables.go` (the new
  depth-1 entry) and +1 / +18 in `seat_management_postgresql.sql` (the new DDL).
- `scripts/tests/test_census_audits.py`: four failures, two of them the clean-export cases.

## The repair

- `ai_docs/api-integration/surface-inventory.md`: the 28 stale anchors set to the numbers the
  instrument reads at `57300c49`; the missing `seat_occupant_changes` row added (`:161`, DDL `:246`)
  after `seats`; §3.3's entry count, composition anchors (`:466 -> :494`, `:471 -> :499`) and DDL
  statement pair (18/19 -> 19/20) moved; §3.5's totals 16/40 -> 17/41 with the new reading stated;
  §1's Reproduce line 156/136 -> 157/137, naming the one registration.
- `scripts/COUNTS-AUDIT.py`: `EXPECTED` retuned on those four keys, each with the commit and the
  re-derivation beside it.
- `scripts/S3-REDERIVE.py`: the docstring's own measured counts 46 rows / 66 anchors -> 47 / 69.

## Verified after the change

- `python3 scripts/S3-REDERIVE.py --doc-file ai_docs/api-integration/surface-inventory.md` ->
  `FRESH 69  STALE->BATCH 0  STALE->EARLIER 0  UNRESOLVED 0`, 47 of 47 rows fresh, exit 0.
- `python3 scripts/COUNTS-AUDIT.py` -> all eleven rows matching, exit 0.
- `python3 scripts/DOC-CITATIONS.py` -> `docs 50  citations 732  test names 23  violations 0`.
- `python3 scripts/CITATION-AUDIT.py` -> `rows 149  stale 0  unresolved 0`.
- `python3 -m pytest scripts/tests -q` -> green (the clean-export cases read this commit).

The rule this records: a table or a route that lands without moving the instrument and the
document is a red main, and the seat that landed it owns the retune.
