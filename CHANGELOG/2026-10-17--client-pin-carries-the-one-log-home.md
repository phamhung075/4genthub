# The pin carries the one-log-home fix, and its record awaits a carrier

The hub's gitlink moves `b57e72d -> 97f648d` (hub pin, gitlink only). Client main took
`4genthub-min/fe-dev-loghome` as a merge (`97f648d`, parents `b57e72d` + `9beff89`).

## Changed (client)

The client kept a SECOND state home: `clientservices.logDir` derived every safeguard log and heartbeat
from `$XDG_STATE_HOME/4genthub/logs`, else `<real home>/.local/state/4genthub/logs`, while the rest of
its state lived under the resolved root. Measured before: `agent.log` (97K), `alerts.log` (153K),
`bridge.log`, `budget-guard-4genthub-min.log`, `compact-supervisor-*.log` and 24 heartbeat JSON files
outside the root. The lane ends the split:

- `clientservices`: `LogDir` loses its global and takes the resolved root; `HeartbeatPath`,
  `WriteHeartbeat`, the alert path and `AgentStatePath` take it too. Every log is
  `<root>/logs/<name>{.log,.json}`.
- `clientlifecycle`, `clientbridge`, `clientheal`, `clientrestore`, `clientsync`: every caller threads
  the root it already resolved; the agent supervisor passes `--state-root` to all children, so a child
  cannot beat into a different home than the verb that started it.
- The root derivation sites are gone: zero non-test `XDG_STATE_HOME` / `.local/state` hits in
  `internal/` (grep, measured at the lane tip).

## Evidence

- Reviewer gate PASS at `e435d94` (row `qitem-20261017063309`): gofmt clean, `go vet ./...` clean,
  `go test ./...` 32 packages green.
- Delta gate PASS at `9beff89` (row `qitem-20261017063531`): the only change over the gated sha is the
  changelog's owner-facing move pair, corrected to merge into the existing target (see below).
- Lead at the merged tip: `go test -count=1 ./...` rc 0, `go vet ./...` rc 0, `gofmt -l` silent;
  merge parents `b57e72d` + `9beff89`, 29 files `+389/-342`; the hub commit is a bare gitlink bump
  (`numstat` 1 file `+1 -1`).

## The owner's move (runs with the push, BEFORE any reseat)

`<root>/logs` is not an empty target - it already holds `rig-continue.log`, `rig-watchdog.log` and
`heartbeat/bridge.json` - so the copy merges contents and must not nest:

```
cp -a ~/.local/state/4genthub/logs/. ~/.config/4genthub/logs/ \
  && mv ~/.local/state/4genthub/logs ~/.local/state/4genthub/logs.obsolete
```

The copy adds and cleans nothing; the old tree is kept whole under `logs.obsolete`, so the move is
reversible. Reseating before the move makes every safeguard report stopped/unknown: the new code reads
only the root, which holds no beats yet.

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink; the
docs-only guard then refuses). The push is not authorized and waits for the owner's word
(`qitem-20261017030506`).
