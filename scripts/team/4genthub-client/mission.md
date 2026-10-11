# Mission: the 4genthub client becomes Go (plus Rust for modules), Python is removed

Owner decision: the client has ONE language, Go. Rust is allowed only for a self-contained
module (the existing `forcecompact` helper stays Rust). No Python remains in the client at the
end. Rewrite, do not translate line by line: port each behavior, keep its tests.

## Where things are
- Client repo (public, standalone, no dependency on the server repo): the `agenthub_client`
  checkout, remote `phamhung075/4genthub-client`, branch `main`. It holds the Python client
  (`src/agenthub_client/*.py`, about 5.3k lines, tests in `tests/`) and `rust/forcecompact`.
- Already-Go code, in the server repo's `agenthub_go` module: `internal/clientcmd` (verb contract),
  `internal/clientsync` (sync, status, messages, connector), `internal/clientbridge` (bridge),
  `cmd/agenthubclient` (dispatcher), `cmd/seatcheck`. It imports two small server packages,
  `fastmcp/seat_management/domain/commpolicy` and `.../secretscan`.
- Python verbs still to port (the Python tests are the spec until the verb is ported):
  `cli.py` (up, compact, stop, status, log, ui), `compact.py` (supervisor), `seat_client.py`,
  `seat_policy.py`, `team_setup.py` (apply, import-project, publish-skills, drift-check),
  `watch.py`, `scrub.py`, the rest of `seat_sync.py`, `feedback`.

## Phases (each ends with tests green, a commit in the client repo, a report to the lead)
1. Move the Go client into the client repo as its own module (`go.mod` at the repo root, module
   path `github.com/phamhung075/4genthub-client`). Copy `commpolicy` and `secretscan` in so there is
   no import of the server module. The binary is `4genteam`. Build and test pass from a clean clone.
2. Lifecycle and supervisor: `up`, `compact`, `compact-run`, `stop`, `status`, `log`, `ui`, plus
   `seat` and `policy`. Config limits (`COMPACT_*`) keep the rule: a blank value means default.
3. `team apply`, `import-project`, `publish-skills`, `drift-check`.
4. `watch` (herdr grid, lead window, feed, inputs).
5. `feedback` and every remaining `sync` verb. `4genteam --help` lists the same verbs the Python
   client listed.
6. Delete the Python sources, tests, `pyproject.toml` and `build/`. Rewrite `README.md` for an LLM
   agent installing the Go binary into any project, and `.env.sample`. Final check: a clean clone
   builds and passes its tests with no Python installed.

## Rules
- ONE credential: `AGENTHUB_TOKEN` with `AGENTHUB_URL`. ONE env file: `~/.config/4genthub/.env`; a
  variable already in the environment wins. Never print or write a token.
- Clean code only: no compatibility layer, no fallback, no Python shim, no legacy flag.
- The client names no private path, person, host or rig. Defaults that point at the owner's own team
  (a default rig name, hard-coded seat roles) are removed or become arguments.
- Every verb answers `--help`. A verb that needs something this machine lacks exits non-zero with one
  message naming it. No shell strings: `exec.Command` with an argument list.
- Behavior change needs a test. Tests need no network, rig or seat.
- Commit with an explicit pathspec, noreply identity `phamhung075 <40054920+phamhung075@users.noreply.github.com>`.
  NO SEAT PUSHES - the PRINCIPAL pushes the hashes to the client repo `main` once the lead has seen
  the phase green. The server repo is not
  touched by this room; the lead tells the owner what to delete there once phase 6 lands.
- Do not touch the `4genthub-min` room or its seats.
- Respect `rm` being blocked by the hook: use the editor or a Python one-liner for deletions.
