# U3 run 1's rollback killed the live room's daemon

## What happened
The acceptance harness finished its run with a rollback whose stated intent was to "stop the room, leave
nothing behind, touch nothing global" and whose closing footer read "Nothing global was touched: the live
room, `~/config/4genthub` and the 4genteam daemon were never addressed." It performed this:

```
for d in /proc/[0-9]*; do if tr '\0' ' ' < $d/cmdline 2>/dev/null | grep -Eq '[/]agenthub-runtime .*daemon'; then kill -TERM ${d#/proc/} && echo SIGTERM ${d#/proc/}; fi; done
SIGTERM 24859
SIGTERM 31665
```

**pid 24859 was the daemon serving `4genthub-min`**, up since `10:11:07Z`, and its own log records the
kill as its last line:

```
/home/daihu/.config/4genthub/daemon.log
2026-10-14T19:55:57.501765Z  INFO agenthub_runtime::ipc: SIGTERM: stopping the daemon
```

There is **one** daemon socket, `<XDG_RUNTIME_DIR>/agenthub.sock` (`/mnt/wslg/runtime-dir/agenthub.sock`),
and the live room resolves that same path — the harness's own header says as much ("the ONE daemon socket
the client resolves … the runtime has no per-room socket"). So a sweep by argv pattern could not
distinguish the lab's daemon from the live room's, and did not.

## Blast radius, measured
- **The five seats survived.** Their runners and their `omp` children are separate processes: `ps` showed
  runner pids 24886/24978/25094/25225/27123 (uptime 48m) with panes `dead=0`, and the agents as their
  children. Nothing about the seats was lost.
- **The control plane did not.** For ~3 minutes every client verb that resolves that socket failed, e.g.
  `4genteam send …` → `cannot connect to agenthub-runtime at /mnt/wslg/runtime-dir/agenthub.sock: dial unix
  …: connect: no such file or directory; nothing was sent`. The refused send was the brief to fe-dev; the
  two sends immediately before it (the reviewer's three gate units, go-dev's C3 ruling) had already
  reported `Sent to …` and were delivered.
- The room's own state files stopped advancing at the kill (last writes 19:49–19:53Z).

## Repair
Restarted a daemon at `19:58:51Z` with the *installed* binary, same state dir, same socket path:
`agenthub-runtime --state-dir /home/daihu/.config/4genthub --socket /mnt/wslg/runtime-dir/agenthub.sock daemon`
(pid 6512). Safe by inspection, not by hope: `main.rs` `Commands::Daemon` runs only
`IpcServer::new(socket_path, supervisor).run()` — a fresh daemon starts **no** rooms, so it cannot relaunch
or disturb the live seats; rooms are started by explicit `StartRoom` requests from the client. Verified
after: `4genteam ps 4genthub-min` → `5 seat(s) … running`, `--nodes` shows activity per seat,
`whoami --json` exit 0, and the re-sent brief reported `Sent to …`.

## Correction to the run's own record
`CHANGELOG/2026-10-14--u3-acceptance-run-1-123-pass-2-fail.md` lists under "What passed" a line reading
"C4-rollback 2/2 (the room socket is gone; nothing global was addressed)". The second clause is false and
this entry supersedes it: the rollback's *room* assertions passed (`no cutover-lab tmux session remains`,
the socket is gone), and its machine-wide step reached the live room's daemon. The harness's own footer
carries the same false claim.

## The instrument defect, assigned
The rollback must stop only what the run started: capture the daemon pid when the run calls `up` and kill
that pid, or refuse to touch a daemon whose socket predates the run's own mark; never select by argv
pattern. The footer's claim must be derived from what the run did. Reported to the harness's author (the
reviewer) with the evidence above, together with the standing rule that a second run cannot be started
until this is scoped — the alternative is taking the live room's control plane down again.
