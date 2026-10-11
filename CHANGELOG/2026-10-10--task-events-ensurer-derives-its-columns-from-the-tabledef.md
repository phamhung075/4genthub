# task_events' column ensurer now derives its columns from the TableDef

**Ruling**: architect `[ENS-RULE-1]` — option (a) for COLUMNS only, UNIQUE/CHECK hand-written, scope
`task_events` only (`RULING-ensurer-derivation-2026-10-10.md`, row `45fea4ce`).

**Why**: the landed ensurer added two columns it assumed production lacked, while the live table was missing
`subtask_id`, which the ensurer never adds and its own fixture already modelled as present. One failure shape
closed, the next opened.

## Change

| File | What |
|---|---|
| `column_ensurers.go` | `EnsureTableColumns`: the column delta derived from the TableDef; every `ADD COLUMN IF NOT EXISTS` first, then per NOT NULL column the named data move and `SET NOT NULL`; columns + the caller's constraint statements in ONE transaction; then a verify pass |
| `column_ensurers.go` | verify pass reads `pg_attribute` + `format_type` and compares presence, type and nullability, normalising only `VARCHAR(n)` ↔ `character varying(n)`, and **reports** (`table.column`, expected, found) — never repairs |
| `task_event_ensurer.go` | calls it for `task_events`; the `user_seq` backfill moved verbatim into a `ColumnDataMove`; the two uniques and two vocabularies stay hand-written, vocabularies in the second transaction |

A NOT NULL column with no data move is added nullable and then `SET NOT NULL`, which passes on an empty table
and fails loudly by column name on a populated one — the intended outcome, no guessed default.

## Evidence

| Check | Result |
|---|---|
| FALSIFICATION, new fixture vs the LANDED ensurer | `subtask_id is still missing after the ensurer ran`, and every non-PK column failed except `user_seq`/`client_event_id` — the two the hand-written list knew |
| `go test ./fastmcp/task_management/infrastructure/database/ -count=1` (PG via `AGENTHUB_TEST_PG_URL`) | `ok` 10.266s |
| `gofmt -l` on the changed files | empty |
| `go test ./... -count=1` with Postgres | **not rc 0**: 4 FAIL, all in files this change never touches (`services` build: `unknown field ProgressCount in task.TaskResponse`; `middleware`: `task.progress_count` validator cases). Proven not mine — with these five files stashed the identical failures appear |

The text guard `TestEnsureTaskEventColumnsMatchTheDefinition` lost its column half: derivation makes "the ensurer
adds a column the definition lacks" inexpressible, and the behaviour is measured by the new per-column case. Its
vocabulary half stays.

**Not in scope**: other TableDefs (follow-on row), constraint drift presence-by-name, and the live census, which
stays the owner's read. Never pushed.
