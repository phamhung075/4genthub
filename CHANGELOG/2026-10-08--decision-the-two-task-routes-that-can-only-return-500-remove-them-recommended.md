## Decision: the two task routes that can only return 500 — remove them (recommended), keep them for Python parity, or build a statistic now

### Added
- `ai_docs/architecture-design/decision-task-stats-endpoint.md` (board row 6d520676): `GET /api/v2/tasks/stats/summary` and `GET /api/tasks/{task_id}` both end in a deliberate `panic` in `httpapp/task_adapter.go:70-76`, ported from Python's AttributeError. The board row named only the first route. Neither route has a frontend caller (`apiReference.ts` only lists them). The note compares keeping parity, building a statistic now, and removing both routes, and recommends removal: the statistic arrives once, under O8, from the ledger. The owner rules. The acceptance command was run at HEAD: build, vet and test pass, and the symbol grep prints 21 lines (red), which is the instrument for the removal.
- `ai_docs/index.json`: regenerated with the note's entry.

### Changed
- `agenthub_go/NEXT_GEN.md` O1a: records that the ledger's entity, table and read route (`bc6349ac`, `task_routes.go:107`) are in the tree. The box stays open until the PostgreSQL tests are reported as run.

### Fixed
- The no-prestage decision's entry below gave the wrong reason why the ten policy modules change together (the fold). It now gives the consistency reason, matching the note's correction in `20fcf17a`.
