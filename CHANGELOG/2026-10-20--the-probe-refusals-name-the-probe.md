The client's readers refuse a probe they could not run, and §7.12 records the shape

The three client readers the failed-read sweep found (board row `6e1171ba`) answered "the probe could not
run" as "the probe ran and found nothing": `clientservices.livePIDs` returned no pids for a missing
`pgrep` (so every safeguard read `stopped`, and `up --respawn` started a second daemon),
`clientlifecycle.stopPattern` answered `false` for a missing `pkill` (so `stop` printed `was not running`
and exited 0 on a stop it never attempted), and `clientbridge.PinnedHash` answered `""` for a
`pinned.json` it could not read (so the server stored `no pin` over a real one).

All readers now answer `(value, error)`, where the zero value with a nil error is the absence the probe
itself observed and an error is refused by name at the verb boundary; `Verify` stops at the first error
and answers no rows. `up` gains a preflight (`clientservices.Probe`: `pgrep` + `pkill` on PATH) that runs
before the daemon, the agent or a seat. 7.2's four states and field set are unchanged.

Client commit: `bb30cb0` (`agenthub_client`, branch `4genthub-min/sec02-tmux-env`). Ruling:
`seats/architect/RULING-probe-unavailable-is-not-absence-2026-10-20.md`; addendum §7.12 in
`ai_docs/core-architecture/rigd-boundaries.md`.

Proven: `go test ./...`, `go vet ./...` and `gofmt -l` clean in `agenthub_client`, `cargo test --offline`
in `rust/agenthub-runtime` green, and on a `PATH` holding no pgrep/pkill the built binary gives `doctor`
exit 3 with the named line and no row, `up` exit 3 with nothing started, and `stop` exit 3 without
`was not running`; `bridge once --print` against a corrupt `pinned.json` exits 3 with empty stdout and
names the file.
