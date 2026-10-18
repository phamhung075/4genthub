# The pin carries the seat-key destination resolution, and its record awaits a carrier

The hub's gitlink moves `927d52d -> b57e72d` (hub pin, gitlink only; `927d52d` was the nudge-pass merge
on top of `0d0f114`).

## Changed (client)

`internal/clientroom/queue.go`: a `create`'s `--to` is written to the rail as the session name the nudge
pass actually compares, so the address a caller types and the key the pass matches are one:

- a session name passes through; `<seat>@<room>` and the bare seat key resolve to that seat's session
  name, and a `<seat>@<other-room>` value is refused because a destination resolves only against the room
  the row is on;
- `principal@<room>` resolves to `agenthub--<room>--principal`, the documented principal address
  (`skills/share/room-decision-request` and `skills/share/jev-decisions` both name it, and the owner
  answers on the dashboard under Decision Requests);
- a value naming no seat and no session is refused with exit 2, the room's seats and their session names
  printed, and nothing written - the class this closes is silent storage: measured 2026-10-16, a row to
  `reviewer@4genthub-min` produced no nudge for ten minutes while the session-name twin woke the seat in
  one second, and 128 of 1080 stored rows carried non-session destinations (68 of them `principal@`,
  16 `owner-session`).

The help text now states the accepted forms, and the refusal names what would have worked.

## Evidence

- Reviewer gate PASS at `b57e72d` (row `qitem-20261017063151-f0ab9b1b4e64`): `go test ./...` 32 packages
  green, `cargo test --offline` 157 unit + 17 integration green, the lane's evidence file verified.
- The lane's live check: before the change the value was stored as typed and no nudge appeared in 5.1 s;
  at the tip attempt 1 lands at +3.0 s with the queued-work alert.
- Lead at the merged tip: fast-forward `927d52d -> b57e72d`, 3 files `+193/-3`; `go test ./...` rc 0; the
  hub commit is a bare gitlink bump (`numstat` 1 file `+1 -1`).

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a pin+docs
commit arrives docs-only and the docs-only guard refuses it; no hook was bypassed). The push is not
authorized and waits for the owner's word (`qitem-20261017030506`).
