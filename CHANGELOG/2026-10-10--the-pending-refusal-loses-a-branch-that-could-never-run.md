## The pending refusal loses a branch that could never run, and the comment stops blaming a command that is registered

### Changed
- `agenthub_go/cmd/agenthubclient/main.go`: `pendingCommand.Run` dropped its `if c.name == "bridge"` owner branch, which was UNREACHABLE rather than stale. `Run` is only ever reached for a PENDING verb, and `commands()` registers exactly two of those — `feedback` and `seatcheck` — while `bridge` is a REGISTERED command (`bridgeCommand.Name()` at `internal/clientbridge/commands.go:30`, and `clientbridge.Commands()` is appended to the registry at `main.go:71`). So no `pendingCommand` named `bridge` existed to run that branch. Its premise was backwards too: it told the reader the Python bridge was "the authority for it ... lands next", and the Go bridge was already in the tree.
- The comment above `Run` claimed the branch "keyed on a `bridge` command that is no longer registered at all". **That is false** — `bridge` is registered, and the reason the branch was dead is narrower: this method runs only for pending verbs, and the pending table holds `feedback` and `seatcheck` alone. The comment now states that, with the file and line that make it checkable.

### Testing
- `GOCACHE=$PWD/.gocache TMPDIR=$PWD/.gotmp go test ./cmd/agenthubclient/ -count=1` -> `ok agenthub/cmd/agenthubclient 0.003s` (re-run here rather than taken from the writer's audit).
- Live smoke on the built binary: the bare invocation prints the usage line naming `sync, bridge, feedback, seatcheck` and `feedback` answers with the pending refusal — the path that remains after the deletion.
