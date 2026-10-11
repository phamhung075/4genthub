## Rule 72 gains a dated addendum: the ensurer it names now exists

Run four minutes after rule 72 landed, on the rule-70 discipline — a correction re-checked at a later tip — because the incident's fix landed in the very files the rule cites.

### Fixed
- `agenthub_go/NEXT_GEN.md`, rule 72: a dated addendum recording that **the ensurer now exists**. `1e0a53e6` ("fix(database): task_events reaches its definition through the ensurer seam") added `task_event_ensurer.go` and registered it (`ColumnEnsurers = append(ColumnEnsurers, EnsureTaskEventColumns)` at `:137`), and the file's own header names the mechanism rule 72 measured — the P1 delta postdates the table, so it must ship on BOTH paths, and *"`column \"user_seq\" does not exist` while /health kept answering"*. It adds the column nullable, backfills `WHERE user_seq IS NULL`, then `SET NOT NULL` and re-creates the constraint. `e555c816` carries the case (the one written twice — rule 73's instance) and `f059e78c` closes the sibling failure.
  - **The distinction the addendum draws:** this **instance** is repaired; the **class** is not. The guard that fails when a `TableDef` gains a column with no path to an existing database remains the lead's item, and the addendum says so rather than letting the fix read as the guard.

### Verified
- Rule 72's four cited lines were re-read at `f059e78c` and **still hold**: `task_event_tables.go:21` (the `user_seq` TableDef entry), `:40` (the `CREATE TABLE` string), `task_event_repository.go:109` (the `MAX(user_seq)+1` select) and `:126` (the INSERT). Head is `f059e78c`; the task-management, session_stream and seat_management trees are clean of uncommitted work.
- The ensurer's absence-then-presence was measured by the same search both times: `grep -rn "ColumnEnsurers = append" agenthub_go --include=*.go` returned two registrations at 18:18Z and returns **three** now, the third being `task_event_ensurer.go:137`.

### Not run
- No test was run: the fix's own case (`e555c816`) is its author's, and this change is the record. Nothing here was edited outside `NEXT_GEN.md`.
