# Client pin carries the umask call-site guards

### Testing

- `agenthub_client` pin moves to `0cdea17`: the two `umask` **CALL SITES** now have cases that go red without the
  call, which is what the two function-level cases could not do - they call `restrict_umask`/`RestrictUmask`
  themselves, so a refactor that dropped the call at the top of `main` stayed green.
  `cmd/4genteam/umask_test.go` re-executes the test binary as the client (`TestMain` is the one place that can
  run `main`, because `main` is an ordinary function in the package) and reads the child's own umask out of
  `/proc/<pid>/status` while the child waits on stdin; `rust/agenthub-runtime/tests/umask_at_the_entry.rs` runs
  the BUILT runtime (the path `CARGO_BIN_EXE_agenthub-runtime` names) as a daemon on a scratch state root and
  reads the same field plus the mode of the state root that run creates. Each child is started under `umask 022`,
  so what is read can only be the call and not a seat's own `0077`.
- Red first: with `clientenv.RestrictUmask()` commented out the Go case fails on `the client's entry point never
  took the umask: the process still reads "0022" while it is waiting in its verb`; with `restrict_umask()` dropped
  at the top of `rust/agenthub-runtime/src/main.rs` the Rust case fails on `the daemon's own umask is "0022", want
  "0077"` - re-measured against the shipped blob (`sha256 b347ba63b3cd059d…`) in a throwaway clone of `0cdea17`
  that used its own target directory. Under that same mutation the crate's 120 unit tests stay green, including
  `pty::launch_env_tests::a_pane_runs_under_the_umask_the_runtime_took` - which is the hole, that case calls
  `restrict_umask` itself. Restored: `cargo test` 120 passed + `tests/umask_at_the_entry.rs` 1 passed;
  `go test -count=1 ./...` over the whole client module ok, run from a seat's `0077` shell.
- No product code moves with this pin. The three files are the two new cases plus seven lines in
  `internal/clientenv/set_test.go`, which asked for the `0640` it then asserted - a request the `0077` umask
  clamps, so in a seat it was handed `0600` and failed on a mode the file never had. `TEST-CHANGELOG.md` in this
  repo carries the same account (committed as `f8139cb1`).
