## The safeguard comment names the client's seven, budget included

`agenthub-frontend/src/types/websocket-protocol.ts` told a reader that the client sends six
safeguard names. It sends seven: the client pin on `main` (`agenthub_client` = `6c25e316`) declares
`Compact, Watchdog, Messages, RoomGuard, Budget, Bridge, Agent` in
`internal/clientservices/services.go:115`, and its `RoomScoped` walk adds `Budget` to the four row
scopes. A comment that names the client's set is a claim about the client, and it was one name short
(board task `b7a2c44c-90f4-464f-8596-de450ffe2a6b`, the architect's finding in queue row
`qitem-20261020223827-f15a0fe8d709`).

### Changed

- `agenthub-frontend/src/types/websocket-protocol.ts:272`: "one of the six the client has always
  sent" becomes "one of the seven the client sends". The word `always` carried the second error:
  `budget` is the newest name, not one the client has always had.
- `:276`: the name list on `safeguard` gains `budget` in the position the client uses - the four
  room-scoped names and `budget` first, then the two machine-scoped `bridge` and `agent`. The field
  stays `string` and the state and room sentences are untouched: the frontend narrows nothing, so
  there is no union to widen.

### The hub half is in flight, and it is not frontend work

At the pin, the client sends `budget`; the hub's `ck_room_safeguards_safeguard` on `main` admits
only the six (`agenthub_go/fastmcp/room_safeguard/infrastructure/database/room_safeguard_tables.go:41`
and `infrastructure/schema/room_safeguard_postgresql.sql:45`). The seventh is on
`4genthub-min/int03-cascades` (`7ab4a3e9 feat(safeguards): accept budget as the seventh name,
widened by migration 0009`, then `13e103a1` for the socket test), two commits ahead of `main`. So the
comment now matches the client and the widened schema, and a `budget` alert cannot be stored by
today's deployed hub until that branch lands - a merge-ordering fact for the lead, not a code change
here.

### Checks

`npx tsc --noEmit -p .` in `agenthub-frontend` afterwards: no output, exit 0. No test run: the edit
is two comments in a docblock and a field's own, and no test reads comment text. Grep over
`agenthub-frontend/src`, `e2e`, and `ai_docs/public-docs` for a competing six-name or seven-name
list: none (the `safeguard` field is typed `string` everywhere, and the public docs do not enumerate
the names).
