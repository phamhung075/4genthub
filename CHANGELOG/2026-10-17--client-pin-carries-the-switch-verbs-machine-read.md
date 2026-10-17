## Changed

- `agenthub_client` pin moves `e2b81cb` -> `dde9561` (5 commits).

### Fixed

- `sync switch` decides "is this a runtime change?" from the RUNTIME's own room status when `--runtime` is given and the cloud already records that runtime, instead of reading the cloud's occupant record alone (`dde9561`). The 2026-10-16 22:47Z incident: the cloud said `agy` while the seat ran `omp`, so `--runtime agy --model gemini-3.8-flash-low --apply restart` read as a model-only change, set the agy model on an omp seat and restarted it - omp cannot start on `gemini-3.8-flash-low`, so the seat died and the verb answered "died before it reported readiness".
- The daily report explains itself in `--help`, and its usage body carries no trailing newline (`7a17186`, `2c35205`).

Validated: `go test -count=1 ./...` green at `dde9561` (32 packages) and gated by the reviewer, whose incident pin fails on the base `29fa7bb` (measured on the pre-fix code: `set-model` then `restart-fresh`, `applied=restart`).
