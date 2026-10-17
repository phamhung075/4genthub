## Client pin carries the evidence verb's failing names

### Changed
- `agenthub_client` pin `5bf9570` -> `5aeb223` (1 commit, `fix(evidence): a Playwright failure is named, and a log line never is`): a failed run's stored failing-test name now comes from Playwright's own list line, location and title path, and only when the command failed; a line merely starting with `FAILED` can no longer become a name (the pytest shape requires its `::`); a failing run that names nothing stores `(no failing test name in the output)` instead of an empty list. Also carries the three TEST-CHANGELOG sections that had no hub commit to ride: the budget safeguard's clauses, the ceiling a seat may not raise, and this lane's.

### Testing
- Client, at the pinned commit `5aeb223`: `go build ./...` clean, `go test ./...` 32 packages ok / 0 failures, `gofmt -l internal/clientevidence/` empty (lead's own run); reviewer gate PASS on the lane (rail row `qitem-20261016180502`) with the red-first measured against the old parser: `FAILED READ {"status":503}` named `[READ]`, the Playwright lines named nothing, a nameless failing run stored `[]`.
- Known limit, accepted: evidence seq 26 keeps its wrong `['READ']` - `PATCH`/`PUT`/`DELETE` on the event answer 405 and a re-post 409 - so the correction applies to runs recorded after this pin.
