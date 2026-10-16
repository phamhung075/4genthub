## A session opens on its newest events and shows each step as a card

### Changed
- `agenthub_go/fastmcp/session_stream/repository.go`: `ListEventsBefore` (the newest N events before a seq, oldest first) and `TailAfterSeq` (the after_seq that leaves the newest N after it); `ListEvents` and the new reads share `queryEvents`.
- `agenthub_go/fastmcp/server/httpapp/ws_session_viewer.go`: `/ws/sessions/{id}?tail=N` on a first connection (`after_seq` 0) replays only the newest N stored events, then follows live. Without `tail` the whole history replays as before.
- `agenthub_go/fastmcp/server/httpapp/session_stream_routes.go`, `server/routes/session_stream_routes.go`: `GET /api/v2/sessions/{id}/events?before_seq=N&limit=M` pages history backwards.
- `agenthub-frontend/src/hooks/useSessions.ts`, `services/sessionApi.ts`: a session opens with `tail=200` (was the whole history on every click); `loadOlder` fetches 200 earlier events per call.
- `agenthub-frontend/src/utils/sessionSteps.ts`, `components/sessions/SessionLiveView.tsx`, `pages/SessionsPage.tsx`: a stored transcript line is shown as steps - user, assistant, collapsed thinking, tool call with collapsed arguments, tool result with its error flag, a muted line for session bookkeeping, and a withheld gap - with a "Load older events" button and follow-the-newest scrolling.

### Impact
- Opening a session no longer downloads its whole history. The viewer sends at most 200 events up front.

### Testing
- `go test ./fastmcp/server/httpapp/ -run SessionViewer`, `go test ./fastmcp/server/routes/ ./fastmcp/session_stream/` pass. The Postgres repository case needs `AGENTHUB_TEST_PG_URL` and was skipped here.
- `npx tsc --noEmit` passes. The frontend specs were not run (no local frontend test run).
