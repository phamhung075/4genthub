## A notification is answered to its target socket, and the others are skipped

### Fixed
- `agenthub_go/fastmcp/server/routes/websocket_routes.go`: the fan-out in `BroadcastDataChange` now skips a socket that is not the notification's target - and a socket with no resolved user - BEFORE the authorization check, for `entityType == "notification"` only. That check answered every non-target socket with TWO error frames: `authorization_denied` (from `IsUserAuthorizedForMessage`) and `notification_blocked` (from the fan-out's own else branch), and both carry `entity_id`. So one notification addressed to one user put two error frames naming that row on every other connected screen - noise on every other user's UI, and a cross-tenant leak of the notification row id.
- A notification addressed to nobody (`userID == ""`) now reaches no socket at all. Before, a socket with no resolved user matched the empty trigger id and was sent the frame.
- Every other entity keeps today's deny-and-notify path, denial frames included: the seat sibling test asserts the second user IS told for a seat frame and still passes.

### Testing
- `agenthub_go/fastmcp/server/routes/websocket_routes_test.go` (new) `TestNotificationFanOutSkipsEveryNonTargetSocket`: the target, another user and a socket with no user are registered, one `"notification"` broadcast is sent for `msg-target-only`, and the target must receive exactly one frame carrying the entity id while the other two receive zero frames. Before the change this case fails, measured: `a socket with no user received 2 frame(s), want 0: {... "action":"authorization_denied" ... "entity_id":"msg-target-only" ...}`.
- `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`: `gofmt -l` on both files printed nothing; `go vet ./fastmcp/server/routes/... ./fastmcp/server/httpapp/...` rc=0; `go test -count=1 ./fastmcp/server/routes/ ./fastmcp/server/httpapp/` -> both `ok`.

### Not part of this change
- The credential half of row `ac2d6106` is open, and its premise is stale at HEAD: `POST /api/v2/broadcast/notify` is already behind `authed` with `UserID: userID(u)` (`routes_mount.go:173`), and `machineAuthed` no longer exists - `e5ecff63` deleted it with the per-machine token. Reported to the lead, who owns the re-decision. `version.go` untouched.
