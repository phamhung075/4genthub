## The catalogue refusal records itself as a DELIBERATE departure, so no parity sweep restores the swallow

### Changed
- `agenthub_go/fastmcp/task_management/infrastructure/database/db_initializer.go` — the package header now states, where the next reader of that file will meet it, that the port **deliberately departs from the reference**: the Python `_get_existing_tables` (`agenthub_main/db_initializer.py:133-146` at `a50929c6^`) catches every exception, logs "Failed to get existing tables" and returns an **empty set**, so `initialize()` reads a failed read as an empty database — line 69 falls into the "Database is empty - initializing with SQL files..." branch at 84-85 — and runs the init file, `DROP TABLE IF EXISTS ... CASCADE` included. This port returns the error and refuses the DDL instead (row 8ee196db). **Why that sentence is load-bearing rather than tidy:** a parity sweep that reads a header promising a faithful port, finds a behaviour differing from the Python and repairs it toward the reference would restore the swallow and take the DROP back with it.
- `db_initializer.go:79-80` — the safety comment said the failed read "returns false above", where the code that returns false is **below** it. It points at the error branch that exists.

### Verified
- The reference behaviour was re-read in history rather than quoted: `git show a50929c6^:agenthub_main/src/fastmcp/task_management/infrastructure/database/db_initializer.py` shows `_get_existing_tables` at 133-146 returning `set()` on `Exception`, and `initialize()` calling it at 69 with the empty branch at 84-85.
- Comment-only: `gofmt -l` on the file prints nothing, and `go test -count=1 ./fastmcp/task_management/infrastructure/database/` → **ok**.
- **NOT RUN:** no Postgres and no broken `search_path` — unchanged from `24efafbd`: the refusal is proven against the scripted driver and must not read as server-proven.
