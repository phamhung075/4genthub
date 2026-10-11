## Anyone could forge a notification for any user through POST /api/v2/broadcast/notify

### Changed
- `agenthub_go/fastmcp/server/httpapp/routes_mount.go`: `POST /api/v2/broadcast/notify` is now **machine-authenticated**, and the target user comes **from the machine token, never from the request body**. The route was a bare `mux.HandleFunc` with **no auth wrapper at all** that read `user_id` straight out of the JSON body, so an unauthenticated caller could write a notification into any user's session - a live unauthenticated write path, not a theoretical one. The wrapper is **`machineAuthed`**, already in the tree (`machine_token_mount.go:111`) and already used for `POST /api/v2/openrig/seat-status` (`seat_status_mount.go:113`); it is mounted **at the broadcast mount itself**, in `mountBroadcastRoutes`, and the handler no longer reads the body's `user_id`, which is no longer a required field.
- **Why the machine wrapper and not the user one:** the only caller is the bridge, which holds `AGENTHUB_MACHINE_TOKEN` (`agenthub_go/internal/clientbridge/commands.go:252`; `agenthub_client/.../bridge.py`). The ordinary user wrapper would have left the bridge unable to post at all and blocked the producer row `628a445d` that depends on this route. Nothing about the producer's ingress assumption changes.
- **Residual, stated rather than implied:** `metadata.user_id` / `metadata.user_ids` still add broadcast targets inside `BroadcastDataChange` (`fastmcp/server/routes/websocket_routes.go:578-589`). That is the ported fan-out feature and it is now reachable only with a machine token, but it does mean a body can still name an additional recipient; the top-level `user_id` - the field the defect was about - cannot.

### Verified
- `fastmcp/server/httpapp/broadcast_notify_auth_test.go` (new) drives the route through the same `mountBroadcastRoutes` the server mounts: **no `Authorization` header -> 403**, **unknown machine token -> 401**, **valid machine token -> 200**, and the broadcast callback receives the **token's user** while the body names another user. On the old code the first case could not hold - the unauthenticated request reached the broadcast - which is the defect the case pins.

### Not verified, stated rather than omitted
- `TestMissedNotificationStoredOfflineAndReplayedOnce` now authenticates with a machine token belonging to the target and forges the body's `user_id` to the other user. It **SKIPS without `AGENTHUB_TEST_PG_URL`**, so that edit is compile-verified only and has not been run against a database.

### Found by
- Row `ac2d6106`; the ingress shape is the dependency assumption recorded on row `628a445d`.
