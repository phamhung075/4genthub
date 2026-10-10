## The seat's identity travels with every MCP block, and names the writer of every status change

### Changed

- `agenthub_go/fastmcp/seat_management/domain/mcpblock/mcpblock.go` — `SeatHeader` (`X-Agenthub-Seat`) and `SeatValue(room, key)` (`<room>/<seat>`), so the renderer that writes the header and the route that reads it cannot drift into two shapes.
- `.../domain/resolver/resolver.go` — `ResolvedSeat` carries `RoomSlug` and `SeatKey`. They are deliberately NOT part of `Hash`, and the reason is written at the field: the snapshot row is keyed `(user_id, seat_id, hash)` and no seat's room or key can change in place (the repository exposes `UpdateOccupant` and `UpdatePermissionPolicy` and nothing else), so a hash blind to the identity cannot hand one seat another seat's header.
- `.../domain/seatrenderer/renderer.go` — `renderMCPFragment` takes the seat and stamps the header on every HTTP server it emits, OVER whatever the block's content carried: attribution must not be claimable by the thing being attributed, the same reason a seat-scoped overlay may not grant itself a block. A seat with no identity gets an error and no block, rather than a block that claims to be nobody. One document, two destinations, one stamp — the claude fragment and the omp `.mcp.json` are the same bytes.
- `.../application/services/seat_resolution_service.go` — the room and seat key the service already resolved travel with the seat into the render.
- `agenthub_go/fastmcp/server/httpapp/mcp_routes.go` — `dispatchMCPTool` reads `X-Agenthub-Seat` into the request context, where the authenticated user and the public origin already travel.
- `.../task_management/application/services/task_event_recorder.go` — the recorder owns the actor decision, once, instead of every caller inventing a name: a request that named a seat is `seat` with the seat identity, a request that named no seat is `human` with the user the recorder was built for, and a recorder built with NO user refuses rather than stamping an anonymous class. (At this commit the table still permitted only `user|system|agent`, so the write used `agent`/`user` and the table's widening landed in P1 — which also rewrote this paragraph, and its tests, to the permanent spelling.)
- `.../task_management/application/use_cases/status_ledger.go`, `update_task.go`, `complete_task.go` — `SaveStatus` and `LedgerRecorder.RecordStatusChange` no longer take an actor, and the `statusActorSystem` constant is gone with them.
- `agenthub_go/fastmcp/server/httpapp/task_wiring.go` — the composition root passes the ledger's user to the recorder, which is where the default attribution comes from.

### Why the header is attribution only

A header is a claim by the caller. It names who made an MCP call so an entry can say so; nothing reads it to decide access, and no route may. That is why the renderer stamps it over block content rather than trusting content, and why the tests assert what the ROW recorded rather than what the request said.

### Testing

From `agenthub_go` with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`, and a throwaway PostgreSQL (`bash tools/testpg/start.sh`, port 55432):

- `gofmt -l` on `task_management`, `server/httpapp` and `seat_management` printed nothing; `go vet` clean on the same; `go build ./...` ok.
- `go test -count=1 ./fastmcp/task_management/... ./fastmcp/seat_management/...` -> no failures; `AGENTHUB_TEST_PG_URL=... go test -count=1 ./fastmcp/server/...` -> `httpapp 20.667s`, `routes`, `metrics` ok.
- **The renderer half, red first**: `TestRenderSeatMCPBlocksCarryTheSeatIdentity` renders `alpha/beta` at both destinations, leaves the block's own `Authorization` alone, gives a stdio server no header channel, overrides a block that names its own seat, and refuses an identity-less seat; with the single stamping line disabled the case failed `claude-code X-Agenthub-Seat = "", want "alpha/beta"`.
- **The route half, red first and read from the ROW**: `TestMCPStatusCallIsAttributedToTheSeatThatMadeIt` drives `POST /mcp` `tools/call` `manage_task` `update` through `app.Handler()` on a real database — with the header the newest `status_changed` row reads `seat`/`alpha/beta`, without it `human`/`<the scoped id>` — and with the route's stamped kind flipped it failed `entry actor = system/"alpha/beta", want seat/"alpha/beta"` (measured at the interim spelling, whose `agent` became `seat` when P1 landed the CHECK).
- Two things the MCP case needed, found by running it: the token must carry `tasks:update` (otherwise 200 with a `PERMISSION_DENIED` payload and no rows), and a status move must carry `details` (otherwise 200 with `VALIDATION_ERROR`).
- `agenthub_client` (a separate module) was run for the packages that read these documents: `internal/clientteam/...`, `internal/clientsync/...`.

### Not covered

No case here proves anything about a seat-header value a client might forge — the header is attribution only, and nothing reads it for access. `agenthub_go/NEXT_GEN.md` is NOT in this commit: its working tree carries another seat's held edit, so touching it would mix their work into this one.
