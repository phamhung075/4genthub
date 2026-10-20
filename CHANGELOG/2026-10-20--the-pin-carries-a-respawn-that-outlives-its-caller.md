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

The inline-respawn ban is lifted. The installed client was rebuilt from `f0c898b`:
`go version -m ~/.local/bin/4genteam` names `vcs.revision=f0c898b`, `vcs.modified=false`, and the binary
carries `FOURGENTEAM_UP_RESPAWN_DETACHED` and `up-respawn.log`; the hub gitlink names the same commit and
`agenthub_client` `origin/main` is `f0c898b`.

Two runs were measured after the rebuild, and only the second proves the inline case:

- 18:27Z, `setsid -f bash -c '4genteam up 4genthub-min --respawn'`: the detached child went through the
  agent stop and the daemon replacement (pids 26326 26523 26715 26978 30399) and started all five seats
  (new daemon and agent 25119, 26045). This proves the child completes; it does NOT prove an inline call is
  safe, because `setsid` already put the caller outside the tree that was stopped.
- 18:30:48Z, bare `4genteam up 4genthub-min --respawn` from the lead seat, with no `setsid`, no `nohup`
  and no wrapper: `/tmp/inline-respawn-bare.txt` records the caller's ancestor chain (its `omp` process,
  then `agenthub-runtime runner 4genthub-min/lead`, then the tmux server), the printed detach line, and
  `EXIT=0 AT=2026-10-20T18:30:48Z`. `up-respawn.log` kept writing to 18:31:15Z - 27 s after the caller
  returned - recording `agent: stopped with its children`, the daemon replacement (`daemon: stopping
  [965 1211 1369 1676 1928]`, the caller's own runner 1211 among them), the five worktrees kept, all five
  seats running, and `agent: pid 6311` (daemon 5316). The caller pid is gone afterwards, and the lead's
  next session starts at 18:30:51Z, after the caller's exit.

So `up --respawn` may be run inline from a seat: the detach is the verb's own behaviour, the caller returns
the log path and exits 0 before the stop, and the wrapper the previous rule required is unnecessary. The ban
held only while the installed binary predated this pin.
