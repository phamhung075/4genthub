### Added

**Seat checker: install-checker and a PATH check in pull and rig** (2026-10-03)

- `scripts/openrig_seat_sync.py install-checker [--out DIR]`: builds `agenthub_go/cmd/seatcheck` to `<seat store>/bin/seatcheck` (GOCACHE/TMPDIR inside `agenthub_go/.gocache`/`.gotmp`) and links `~/.local/bin/seatcheck` to it with the atomic `place_agent` helper. It then checks that the bare name `seatcheck` resolves to that binary on PATH and fails (exit 2) with the exact fix (`add ~/.local/bin to PATH`) if not.
- `pull` and `rig` fail loudly (exit 2, before any network call) when `seatcheck` does not resolve to `<seat store>/bin/seatcheck`. Seats run the bare `seatcheck send ...`, matching the allow rule `Bash(seatcheck send:*)`; no rendered file changes, so seat hashes and pins are unaffected (architect decision F3: no absolute path, no settings env PATH).
- `.gitignore`: `agenthub_go/seatcheck` (the untracked binary was moved out of the tree). The `seatcheck` CLI itself is unchanged (owned by go-dev).
- Verified for real in a temp HOME and temp store: `go build` ran, link created, exit 2 with the PATH fix when `~/.local/bin` is not on PATH, exit 0 when it is, `pull` exit 2 without it.
