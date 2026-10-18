# The pin carries the daemon-side destination resolution, and its record awaits a carrier

The hub's gitlink moves `97f648d -> f71becd` (hub pin, gitlink only). Client main took `1e0d6f0` as a
merge (`f71becd`, parents `97f648d` + `1e0d6f0`).

## What the earlier pin's half became

`b57e72d` resolved a queue row's `--to` in the CLIENT (`clientroom.createDestination`). `1e0d6f0`
supersedes it: the resolution now lives in the DAEMON, the rail's only writer, so every caller gets it
rather than one verb, and the client half is deleted.

## Changed (client)

- `rust/agenthub-runtime/src/supervisor/mod.rs`: `resolve_queue_destination` maps a destination written
  as a session name, the rig orchestrator form `<room>-<seat>@<room>`, `<seat>@<room>`, or the bare
  seat key to the session name the alert and nudge passes compare; a value naming no seat of the room
  is refused by name with the seats that would have worked, and nothing is written. `principal@<room>`
  is refused with it - the room declares five seats and no principal, so resolving it would be the same
  silence under a familiar name.
- `addressed_names` gained `seat@room`, so the 32 rows already stored in that spelling (the owner asks
  among them) are counted by the alert and reachable by the nudge pass instead of reading as nothing
  waiting; the join reads four spellings, none of them a second canonical form.
- `skills/share/room-decision-request` and `skills/share/jev-decisions`: an owner ask is filed to the
  room's lead (`agenthub--<room>--lead`), which is the seat that carries it to the owner - the principal
  address named a session the room does not run.
- `internal/clientroom/queue.go` loses `createDestination` and its four cases; the verb sends what the
  caller typed and renders the daemon's refusal.

## Evidence

- Reviewer gate PASS at `1e0d6f0` (row `qitem-20261017063626-d16e8d80cd23`): `cargo test --offline`
  158 unit + 1 + 15 + 1 green, `go test ./...` 32 packages green, the lane's evidence verified.
- The lane's live check: an old-client row typing `rev@nudge-lab` is nudged at +3.1 s after the daemon
  resolution; `revv@` and `principal@` exit 2 with the seats listed.
- Lead at the merged tip: `go test -count=1 ./...` rc 0, `cargo test --offline` green, merge clean
  against `97f648d`; the hub commit is a bare gitlink bump (`numstat` 1 file `+1 -1`).

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives docs-only and the docs-only guard refuses it; no hook was bypassed). The push is
not authorized and waits for the owner's word (`qitem-20261017030506`).
