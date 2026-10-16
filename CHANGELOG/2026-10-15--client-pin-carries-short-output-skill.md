# Client pin carries the short-output skill

### Changed
- `agenthub_client` pin moves to `7b48e20`: the `short-output` seat skill (pointer thinking, result-first replies of at most 5 lines, docs change once at task done) and `7a9b2fd` (the reseat verb announces its wait; a claim whose publisher is gone is a death).

### Testing
- Client `go test ./internal/clientskills` passes; the skill is present in all five seats of `4genthub-min` after `sync room` and reseat. No test files changed in this repo.
