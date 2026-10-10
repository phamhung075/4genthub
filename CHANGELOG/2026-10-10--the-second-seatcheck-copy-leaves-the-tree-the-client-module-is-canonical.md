## The second seatcheck copy leaves this repository; the client module is the guard's canonical source

### Removed

- `agenthub_go/cmd/seatcheck/` (`main.go`, `main_test.go`, `exec_test.go`, 1371 lines): the guard was
  tracked twice and the two entry points had drifted. **The rule it lands on: the canonical copy is the one
  the installer builds, on the module the installer names.** `agenthub_client/README.md:73` gives the
  operator `4genteam sync install-checker --go-dir .`, `install-checker` requires `--go-dir` (the Python-era
  default is gone with the Python) and builds `<GO_DIR>/cmd/seatcheck` — so the module an operator names IS
  the source of the guard they install, and the client is the module that ships to operators and the tree
  the seat is pulled from (G3: the enforcement point "ships with the seat as the only communication tool").
- The two entry points, diffed rather than sized — every behaviour they do not share, 32 lines and no
  others: the import block (`agenthub_go/cmd/seatcheck/main.go:18-25` imports
  `agenthub/fastmcp/seat_management/domain/commpolicy` and `os/user`;
  `agenthub_client/cmd/seatcheck/main.go:25-26` imports this module's `internal/commpolicy` and
  `internal/clientenv`), and the pin-store resolution (`main.go:51-55` + `:83-105` against `:78-91`). The
  deleted copy joined `defaultPinsDir = ".openrig/agenthub-seats"` to `realHome()`, the passwd entry — "the
  same resolution as `real_home()` in `scripts/openrig_seat_sync.py`, one language over" — a script this
  repository no longer has; the kept copy calls `clientenv.ResolveSeatStore("")`, **this tree's one
  implementation of that store**, whose own comment records that de-duplication. That is the drift the
  finding predicted, measured: the copy that stayed is the copy that was maintained.
- Nothing in this repository built or ran the deleted copy, and the removal is the check: with it gone,
  `go build ./...` in `agenthub_go` is rc=0. A package `main` cannot be imported, no Go file outside it
  named the package, and the script test that used to build it (`scripts/tests/test_seatcheck_guard.py`,
  `--go-dir agenthub_go`) was deleted in the Python cutover. `agenthub_go/NEXT_GEN.md:317`'s "ONE source …
  absorbing `cmd/seatcheck` as a subcommand" predates the client repository and names a target
  (`agenthub_go/cmd/agenthubclient`) that is not the binary that ships (`4genteam`), so it does not make
  this copy canonical.
- The client-side half is recorded rather than edited from here: board row `655ccf70` (client lane) — the
  client's `cmd/seatcheck` is now the tree's only copy, so keeping it buildable with `--go-dir .`, not
  re-introducing a second copy anywhere, and the one-binary decision now apply there alone.

### Changed

- `agenthub_go/cmd/agenthubclient/main.go:48-60`: the refused `seatcheck` verb's owner sentence no longer
  names `cmd/seatcheck`, the file this change removes; it still names the live installer
  (`4genteam sync install-checker`) and now says the guard comes from the client module. No test pinned that
  wording — `TestUnportedCommandRefusesRatherThanStubbing` asserts the exit code, `not ported` and an empty
  stdout — so the sentence stayed a sentence.

### Verified

- From `agenthub_go`: `go build ./...` → rc=0; `go test -count=1 ./cmd/agenthubclient/` → `ok 0.003s`;
  `gofmt -l cmd/agenthubclient` → empty; `go vet ./cmd/agenthubclient/` → clean.
- From `agenthub_client` (read-only here, the canonical copy): `go build ./cmd/seatcheck` → rc=0;
  `go test -count=1 ./cmd/seatcheck/` → `ok 0.101s`; `gofmt -l cmd/seatcheck` → empty;
  `go vet ./cmd/seatcheck/` → clean.
