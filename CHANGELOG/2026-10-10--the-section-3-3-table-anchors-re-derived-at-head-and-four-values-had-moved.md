## The §3.3 table's anchors re-derived at HEAD: four values had moved, one of them moved by this release set

### Changed
- `ai_docs/api-integration/surface-inventory.md`, one value per line, nothing else:

| line | row | column | was | is | the species the anchor must point at |
|---|---|---|---|---|---|
| `:522` | `seat_feedback` | Declaration (Go) | `seat_tables.go:317` | **`:321`** | the TableDef registry entry `{Name: "seat_feedback", Model: "SeatFeedbackORM", Columns: ...}` |
| `:523` | `machines` | SQL | `:296` | **`:324`** | `CREATE TABLE IF NOT EXISTS machines (` |
| `:525` | `seat_status` | Declaration (Go) | `seat_tables.go:287` | **`:267`** | the registry entry `{Name: "seat_status", Model: "SeatStatusORM", Columns: ...}` |
| `:525` | `seat_status` | SQL | `:323` | **`:335`** | `CREATE TABLE IF NOT EXISTS seat_status (` |

- **A FIFTH occurrence of the same stale anchor, found by grepping the VALUE rather than the table.** The prose sentence under the table — "It is registered (`seat_tables.go:317`)" — now reads `:321`. Same species, same drift, and leaving it would have pointed a reader at a line that never carried the entry. Recorded here because it was not in the row's list of four.

- **A SIXTH occurrence was caught by the same sweep and PUT BACK, because it is a dated record rather than a live pointer.** The prose replacement was run as a value-wide replace, and it also caught §3.6's pass-3 record at `:556` ("... `seat_feedback` was missing entirely — registered at `seat_tables.go:317` ..."). That section states what the 2026-10-06 pass measured and keeps its own values: its other cites in the same sentence (`seat_tables.go:357` and `:362` for the composition and the single append) no longer match the tree either — the live prose in §3.2 gives the composition as `seat_tables.go:397` — so the record was restored to `317` and the committed diff is exactly four lines, no more. A record edited to read as current is a history that cannot be checked; two deliberate values in one file, one live and one frozen, is the correct shape.

### Verified
- **THE WHOLE TABLE WAS RE-DERIVED, NOT JUST THE FOUR.** All 17 rows of §3.3 (`modules` -> `machine_edges`) were re-parsed at HEAD: each Go anchor was matched against `{Name: "<table>",` in its cited file and each SQL anchor against `CREATE TABLE IF NOT EXISTS <table>`. Before the edit **3 rows / 4 values** mismatched; after it the same run reports **rows checked: 17, mismatches: 0** — the other 13 rows were exact, which is the control that says the method finds real drift rather than inventing it.
- **EACH VALUE WAS WALKED THROUGH EVERY REVISION THAT TOUCHED ITS FILE, newest first (the reviewer's method), cross-checked against HEAD:**

| anchor | at HEAD | the doc's value was last right at | what moved it |
|---|---|---|---|
| `seat_feedback` Go | **321** | `97fb2979` (317) | `02bfd416` inserted above it (317 -> 341), then `e5ecff63` removed the `machine_tokens` entry above it (341 -> 321) |
| `machines` SQL | **324** | `02bfd416` (296) | `7c81981b` inserted the `seat_messages` DDL above it (296 -> 324) |
| `seat_status` Go | **267** | `7c81981b` (287) | `e5ecff63` removed the `machine_tokens` registry entry above it (287 -> 267) |
| `seat_status` SQL | **335** | `02bfd416` (323) | `7c81981b` (323 -> 351), then `e5ecff63` (351 -> 335) |

  So exactly ONE of the four was broken by `e5ecff63` — the `seat_status` Go anchor — while two were broken by `7c81981b` and one by `02bfd416`; `e5ecff63` is also the last mover of the `seat_feedback` Go anchor. The species matters and is why a naive grep for the number is not the check: every one of these points at a TableDef registry entry or at the SQL statement, never at a struct declaration.
- **THE CENSUS DOES NOT COVER THIS TABLE, AND SAYING SO IS PART OF THE EVIDENCE.** `python3 ~/.openrig/agenthub-seats/<seat>/CITATION-AUDIT.py` (checking mode; `--write` is forbidden in a gate by its own header) reads **`rows 144 stale 0 unresolved 0`** BOTH before and after this change, because it resolves the ROUTE tables (`| METHOD | path | handler | file:line |`) and §3.3 is a registry/DDL table with no route in it. So a green census was true before the fix and is not the evidence that the fix was needed — the line-by-line derivation above is. A green instrument that does not measure the thing is the failure this document exists to prevent.
- **No number moved as a result.** The §3.3 counts are unchanged by this edit: the table still lists 13 rows plus the four core rows above it, the seat block is 15 tables, and the SQL statement count is 17 (`grep -cE '^CREATE TABLE IF NOT EXISTS'`), because only line references were corrected, never a count.

### Found by
- Board row `bd60b1ed`, opened from the reviewer's census at the seal. The reviewer measured the mismatch; this seat re-derived each value from the code, walked each one's history to name the commit that moved it, and found the fifth occurrence.
