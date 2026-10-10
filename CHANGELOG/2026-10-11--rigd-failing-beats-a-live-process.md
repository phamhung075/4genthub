## rigd: a `failing` row is not running, even while its process is alive

### Changed
- `ai_docs/core-architecture/rigd-boundaries.md` §7.2: the architect's ruling on minor m1 of `GATE-39e51529`, requested in the lead's `qitem-20261010234255-72dac9f9fb10cae8`. A row that rigd records as `failing` (3 deaths in the window) is `failing` whether or not its process is momentarily alive, so `doctor` and `up` exit 3 on it.
  - The precedence is stopped, then failing, then silent, then running.
  - The code change belongs to go-dev, under `e59f4162`: `verifyRow` checks the recorded `failing` before the liveness switch.

### Verified
- The architect read `agenthub_client/internal/clientservices/services.go:328-365`. Its `verifyRow` honours the recorded `failing` only when no process is live. The architect also read `internal/clientlifecycle/rigd.go:410-448`, which shows that rigd persists `failing` and clears it in `prune`.
- No code changed in this commit, so no tests apply.
