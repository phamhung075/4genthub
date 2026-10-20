# Pin: the client carries a respawn that outlives its caller (client f0c898b)

The hub gitlink moves `f743a64 -> f0c898b`, which carries the prod-break fix for `up --respawn`:

- `f0c898b` - `4genteam up RIG --respawn` re-execs itself in a new session BEFORE it signals anything
  (`internal/clientlifecycle/lifecycle.go:342`), with both streams on `<state root>/up-respawn.log`
  (`respawn.go:111`) and `SysProcAttr{Setsid: true}` (`respawn.go:159` in `detachRespawnImpl`,
  `respawn.go:140`). The calling process prints that log's path and returns 0; the child is marked by
  `FOURGENTEAM_UP_RESPAWN_DETACHED` (`respawn.go:107`), not by a flag a person could write. The child
  then runs the old order unchanged: agent, then the daemon by pattern (`respawnDaemon`,
  `respawn.go:50`), then the reads, the peak gate, the worktrees and the room start.

Why the pin moves: `up --respawn` stops agent, which is the parent of every seat, so run from a seat the
agent stop is the CALLER's own death and the run died between the two halves - the daemon replaced, the
seats and agent never started. Measured three times: 2026-10-18 21:38Z, 2026-10-19 05:06Z, and
2026-10-20 17:29:38Z (daemon SIGTERM at 17:30:02Z; the lead's own `build.sh --respawn` left four omp
seats and agent down until the owner restored them).

Order, per `RULING-pin-names-a-pushed-client.md`: client `origin/main` carries `f0c898b` before this pin
commit, so a fresh clone and a submodule sync resolve the gitlink. `f0c898b`'s parent is the previous
pin, `f743a64`.

Measured at this pin before landing (lead, 2026-10-20, detached worktree at `f0c898b`): `go test ./... -count=1`
35 packages ok, 0 FAIL; `go test ./internal/clientlifecycle -run Respawn -count=1` names
`TestUpRespawnReExecsItselfBeforeItStopsAnything`, `TestTheDetachedRespawnIsItsOwnSession`,
`TestUpRespawnStopsTheSupervisionThenTheDaemonBeforeTheRoomStarts`,
`TestUpRespawnRefusesToStartASecondDaemon`, `TestRespawnRefusesWhenTheProbeCannotRun`,
`TestRespawnDaemonReplacesARealProcessForTheRoot`, all PASS; `go vet` and `gofmt -l` clean on the
package. Reviewer PASSed `f0c898b` independently (session isolation verified).

Until the installed client is rebuilt, the running binary is the old one and the operator's rule still
holds: never run `--respawn` inline from a seat; use `build.sh --no-test` then `setsid nohup 4genteam up
RIG --respawn`. After the rebuild the detached form is the verb's own behaviour and the wrapper is
unnecessary.
