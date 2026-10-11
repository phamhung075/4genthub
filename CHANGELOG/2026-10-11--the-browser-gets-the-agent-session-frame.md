## The browser gets the session frame: `agent_session` created and updated, one per session `MarkOffline` marks

### What this is
The push half of `rigd-boundaries.md` section 2.3a. The read half landed with the rigd slice (`seat_state`
stored and returned by `GET /api/v2/sessions`); this is the frame that tells a browser the row changed.

### The frame
- Entity **`agent_session`** — not `session`, which reads as an auth session — on the same
  `routes.BroadcastDataChange` path the seat frames use, so per-user scoping is unchanged. The seam
  `agentSessionBroadcastFn` mirrors `seatBroadcastFn`, so tests observe frames without a live socket.
- `created` on the first `session` frame for a new `(user_id, connector_id, session_key)`; `updated` on a
  `seat_state` change or a `status` change; nothing at all when neither moved.
- `MarkOffline` now returns the rows it marked, and each row gets its **own** `updated` frame naming its id,
  its last reported `seat_state` and the new `offline` status — exactly the rule 2.3a states for the close
  path. Its previous behaviour is unchanged: `last_seen` still bumps for every row, and a row already
  offline is not "marked" again.
- The payload is deliberately the minimum (`id`, `seat_state`, `status`): the browser invalidates its
  sessions list on this frame instead of parsing a row out of it.

### The store
`SessionUpsert` reports whether the write INSERTED, whether `seat_state` moved, and whether `status` moved,
so the caller emits exactly one frame per real change — the branch that decides is the same one that
already decided the SQL.

### Tests, and the red
`fastmcp/server/httpapp/ws_session_push_test.go` (new) holds the five acceptance cases through the seam:
created exactly once; silent when nothing changed; updated on a `seat_state` change; two sessions marked
offline yield exactly two frames; the frame carries the frame's user. `repository_test.go` gains the
store-side pair (created/state-change reporting, and one report per marked session) and follows the two
changed `MarkOffline` call sites.

**RED FIRST, quoted:** the new symbols did not exist —
`undefined: agentSessionBroadcastFn` and `assignment mismatch: 2 variables but MarkOffline returns 1 value` —
and the cases were written before the implementation, not after it.

### Verified by the seat that committed it
`gofmt -l` on the four touched files printed nothing; `go build ./...` rc 0; `go vet
./fastmcp/server/httpapp/ ./fastmcp/session_stream/` rc 0. The five cases plus the store pair, run by this
seat: `go test -count=1 -run 'TestAgentSessionPush|TestUpsertSessionReports|TestMarkOfflineReturns|TestMarkOfflineWithoutSessions'
./fastmcp/server/httpapp/ ./fastmcp/session_stream/` → **ok 43.7s, ok 21.8s**. Both packages were also run in
full: `session_stream` **ok 19.9s**, `httpapp` **ok 189.3s**.

### What this does NOT do
`ws_mount.go` is one of the three files this project treats as shared; it was checked before editing (no
other seat's changes present) and this commit carries only the two call sites and the seam. No row is
deleted, no route is added, and the frames are inert until a browser handles `agent_session`.
