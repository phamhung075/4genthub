## The connector carries its cursor, the session row carries its state, and a safeguard's transition is a row and a push

### What this is
The server half of the phase-1 rigd wire (`rigd-boundaries.md` sections 2.1–2.3), the two columns the
client half now writes — `agent_sessions.client_cursor` and `agent_sessions.seat_state` — and a new
`rig_safeguards` table, so a safeguard's state is a row rather than something a reader has to infer from a
heartbeat.

### The frames
`ws_mount.go` gains what section 2.1 names: `hello` carries `protocol`, `client_version` and
`capabilities`, and `ready` answers `protocol` (the client's, capped at 1), `heartbeat_s` (25) and the
echoed capability subset; `ping` answers `pong{t}`; `session` passes `state`; `session_ack` answers the
stored `cursor`; `events` passes `events.cursor` and `events_ack` answers the stored one. An `error` frame
carries a stable `code` derived from the message and `fatal` (always false in phase 1). A new `safeguard`
frame upserts without an ack and raises an alert on a transition. The read loop refreshes a
`3 x heartbeat_s` deadline (2.2's server-side close), and the deferred close arms the rigd dead-man on the
connector's last socket.

### The store
`MaxCursorBytes = 512`. `AppendEvents` now takes `events.cursor` and writes `client_cursor` in the **same
statement and transaction** as `last_seq` and the events, so a lost ack can be re-sent without duplicating
a row. `UpsertSession` takes `session.state` and returns the cursor, and keeps a previously reported state
when a frame reports none. The session row behind `GET /api/v2/sessions` carries `seat_state`.

### The new table
`fastmcp/rig_safeguard/`: the ORM row keyed `(user_id, connector_id, rig, safeguard)` with the four states
and four safeguard names as closed sets, the hand-written `TableDef` with its two CHECKs registered from
`init()`, the DDL for the path a human applies, and a repository whose `Upsert` reads the previous row
`FOR UPDATE` inside the same transaction as the write and uses `INSERT ... ON CONFLICT` for the
overlapping-reconnect race. `transitionAlerts` is section 7.3's rule in one place.

### Verified, by the seat that committed it
- `gofmt -l` over the nine touched `.go` files: empty.
- `go build ./...` rc 0; `go vet ./fastmcp/session_stream/... ./fastmcp/rig_safeguard/... ./fastmcp/server/httpapp/...` rc 0.
- `go test -count=1 ./fastmcp/rig_safeguard/... ./fastmcp/session_stream/...` with
  `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres`: the `rig_safeguard` packages
  **ok** (3.5s), and `fastmcp/session_stream` **RED on exactly the two UNDECLARED columns the next commit
  declares** — `col client_cursor | character varying | 512 | YES | None | 13` and
  `col seat_state | character varying | 20 | YES | None | 14`. That red is the guard doing its job: this
  commit changes the schema, and the declaration naming it cannot exist inside it.
- The new acceptance cases run against the same cluster:
  `go test -count=1 -run 'Connector|Rigd|Safeguard|Cursor' ./fastmcp/server/httpapp/` → **ok, 15.1s**,
  including `TestConnectorCursorSurvivesALostAckAndStoresTheBatchOnce`, whose red-first induction (dropping
  `client_cursor = $3` from the UPDATE) is the worker seat's record and is re-run at the gate.

### Why two commits
The schema guard requires every declared divergence to name a commit that EXISTS, so the declarations are
deliberately not here: they land in the commit after this one, naming it. That is the shape of `14210172`
then `788bdd2c` — the change first, the declaration that names it second.
