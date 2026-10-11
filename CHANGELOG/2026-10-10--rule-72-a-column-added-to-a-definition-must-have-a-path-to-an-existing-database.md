## Rule 72: a column added to a definition must ship with a path to an existing database

Written while pricing a live production incident (the lead's 18:15Z broadcast: a task status change fails with `column user_seq does not exist` while task creation succeeds), and adopted by the lead as the documentation half of the structural item he opened — the missing ensurer plus a guard that fails when a definition gains a column with no path to an existing database.

### Added
- `agenthub_go/NEXT_GEN.md`, process lessons: **rule 72**, stated **before its check exists** on rule 61's precedent, with the first failing case measured rather than argued:
  - `user_seq` is real in the Go shape — `task_event_tables.go:21` (TableDef entry, `BIGINT NOT NULL`) and the `CREATE TABLE` string at `:40` — and the repository reads and writes it (`task_event_repository.go:109`, `:126`); it arrived in `fa74db0a`, the P1 commit this batch's gate approved.
  - **No ensurer was registered for it.** The only registered ensurers are `session_columns.go:47` and `seat_management/ensure_seat_columns.go`, and a search for `task_events`/`user_seq` across every file that appends to `ColumnEnsurers` returns nothing.
  - The mechanism in one sentence: `createAll` creates a table only when it is ABSENT, and the ensurer seam is the one path that reaches an **existing** database, so a new column must be *registered* there — P1's was not.
  - The two consequences the rule carries: the repair is **conditional** (an ensurer works on boot only where `AUTO_MIGRATE=true`), and the **class** is what bit production, not the column.

### Verified
- All four facts read at HEAD in this tree, read-only, by the writer seat: the TableDef entry, the `CREATE TABLE` string, the two repository statements, and the absence of any ensurer naming `task_events` or `user_seq`.
- The health/creation asymmetry is the lead's, from production: a status change fails while creation succeeds and `/health` answers — which is why the batch's acceptance passed.

### Also in this commit, and DISCLOSED because it is a second subject in one file
- **Rule 71 gained a dated addendum closing the open question it recorded at 13:18Z.** That question was whether a pin bump would break the parent's tests that read the retired client path (`21 .py` at the pin `c401888b`, with `1eca7de` not an ancestor). The bump has happened — `df257e01` pins `eaa6ba7`, zero `.py` — and the tests were settled **before** it: `91cf4295` removed `test_seatcheck_guard.py` and `_client_tree.py`, re-homed `test_team_definition.py` to its 8 room-data cases, cut `test_team_roster.py` to its 3, and the `httpapp` guard had already been dropped above the published tip. The predicted failure did not occur, and the reason is ordering — the same remedy rule 71's own remedy asks for.

### Not run
- No test: **the guard this rule names does not exist yet** and is the lead's separate item. Until it does, the manual form is the one that found this — diff a definition against the ensurers and the DDL sources and ask what reaches a database that already holds the table.
