## The notify ingress refuses a notification addressed to another user

### Fixed

- `agenthub_go/fastmcp/server/httpapp/routes_mount.go`: a `POST /api/v2/broadcast/notify` whose
  `entity_type` is `notification` is refused with **403** when `metadata.user_id` or `metadata.user_ids`
  names a user other than the caller, and the refusal names the offending user. `BroadcastDataChange`
  (`fastmcp/server/routes/websocket_routes.go`) resolves the recipients it stores for while they are
  offline from those two keys as well as from the token's user, so before this a caller could put a
  notification into another user's dashboard with the message and the sender (`data.from`, which the
  dashboard renders as `from: message`) of its choosing, and that user's next connect replayed it as a
  toast. No client presents a scope or a service identity that authorizes addressing another user, so
  such a frame is refused rather than silently re-addressed. The route's own comment — "the target user
  is the caller's, never the body's" — is now true as written. A notification naming only the caller, or
  naming nobody, still goes through unchanged.
- The common fan-out is deliberately NOT narrowed: `websocket_routes.go`'s metadata targeting is how an
  entity type that is legitimately addressed to several users reaches them, so the guard sits at the
  route (the only client ingress, verified by grep for `TriggerBroadcast` and `/broadcast/notify`) and
  other entity types keep their recipients.

### Testing

- `fastmcp/server/httpapp/notify_target_scope_test.go` (new, no database): the refusal for
  `metadata.user_id`, for `metadata.user_ids`, and for a list that names the caller *and* another user;
  the two allowed shapes (the caller's own id, no targets at all) still reach the broadcast addressed to
  the caller, and a refused frame never reaches it; a non-notification entity type with
  `metadata.user_ids` is neither refused nor stripped.
- `fastmcp/server/httpapp/notify_target_scope_store_test.go` (new, needs `AGENTHUB_TEST_PG_URL`): the
  finding's reproduction end to end through the production wiring — the plant is refused, 0 rows for the
  victim and 0 for the caller, and the victim's next connect replays nothing — while in the same run the
  caller's own notification is stored and replayed exactly once; and an entity type addressed to two
  users still stores one row for each of them.
- RED FIRST: with the guard's condition forced false, the plant answers **200** and both new files fail.
  With it restored: `go test -count=1 ./fastmcp/server/httpapp/` → **ok, 212 passed, 0 failed, 0 skipped**
  with the database up; `go test -count=1 ./fastmcp/server/routes/` → **ok, 25 passed, 0 failed, 0
  skipped**; `go vet` clean on both packages.
