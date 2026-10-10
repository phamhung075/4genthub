## The notify ingress refuses any frame addressed to another user, not just a notification

### Changed

- `agenthub_go/fastmcp/server/httpapp/routes_mount.go` — the guard added by `c0fed377` fired only for `entity_type == "notification"`. It now fires for EVERY entity type: a `POST /api/v2/broadcast/notify` whose `metadata.user_ids` (list) or `metadata.user_id` (string) names a user other than the caller is refused **403**, the refusal naming that user, and it is refused BEFORE `routes.TriggerBroadcast` is called — so a refused frame stores nothing for anyone, the caller included. Same two keys, same status, same property the existing cases prove: a refused frame never reaches the broadcast.
- The `notificationEntityType` const is deleted with its comment. It existed only to scope the guard, and its comment carried the false premise corrected below.
- Nothing else changed. The fan-out keeps its metadata targeting (`routes.BroadcastDataChange` is unchanged), the seat and task/subtask producers are untouched, and no unrelated file was touched.

### Why the narrowing was wrong

`BroadcastDataChange` resolves the offline recipients it stores for from those two metadata keys for **every** entity type (`fastmcp/server/routes/websocket_routes.go:578-601`), and the dashboard toasts more than notifications. The **task** case is verified in this tree and is unconditional: `agenthub-frontend/src/hooks/useRealtimeSync.ts:161-162` shows the toast for a created task. The lead's correction adds subtask, project, branch, seat and room to that list — **I did not verify those five myself**, and they are named here as the premise they are. So a client could plant a `task` frame into another user's dashboard with a title, a body and a sender of its own choosing: the same cross-tenant write `338fe3a0` fixed for notifications, through the same route.

### Correction to a PUBLISHED entry

`c0fed377` is already on `main`, and its entry — `CHANGELOG/2026-10-10--the-notify-ingress-refuses-a-notification-addressed-to-another-user.md` — rests on the premise that only notification frames toast, so the other entity types "keep their recipients" as a feature. That premise is false. Published history is not amended; this entry records the correction. The same applies to that entry's `TEST-CHANGELOG.md` line for `TestNotifyRouteLeavesOtherEntityTypesAddressedToSeveralUsers`, which describes a rule this commit deletes — the case is **rewritten and kept**, not deleted.

### Testing

From `agenthub_go` with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`:

- **RED FIRST, measured**, before the production edit: `go test -count=1 -v ./fastmcp/server/httpapp/ -run 'TestNotifyRoute|TestTheFanOutStillStores'` (with `AGENTHUB_TEST_PG_URL` set) → `TestNotifyRouteRefusesAnyFrameThatNamesAnotherUser` failed at `a task frame naming another user in user_ids: status = 200, want 403 (body={"status":"broadcast_sent","entity_type":"task","event_type":"updated"})` and `TestNotifyRouteStoresNothingWhenAnotherUserIsNamedForAnyEntityType` failed at `status = 200, want 403` — the old rule's exact behaviour, on a real database. The two keep-cases passed in that same run, which is what makes the red specific.
- After the edit, same selection: all six pass.
- **With a real Postgres** (`tools/testpg/start.sh`, port 55432, `AGENTHUB_TEST_PG_URL`): `go test -count=1 -v ./fastmcp/server/httpapp/ ./fastmcp/server/routes/` → **240 passed, 0 failed, 0 skipped**, `ok agenthub/fastmcp/server/httpapp 15.006s`, `ok agenthub/fastmcp/server/routes 0.006s`. The three database-gated cases therefore RAN rather than skipping.
- **Without a database** (`env -u AGENTHUB_TEST_PG_URL`, same selection): four cases SKIP loudly (`TestMissedNotificationStoredOfflineAndReplayedOnce`, `TestNotifyRouteStoresNothingForAnotherUser`, `TestNotifyRouteStoresNothingWhenAnotherUserIsNamedForAnyEntityType`, `TestTheFanOutStillStoresForEveryUserMetadataNames`) while the two route-level cases — the widening's guard — PASS, which is the shape CI needs.
- `gofmt -l` on the three changed files printed nothing; `go vet ./fastmcp/server/httpapp/` was clean; `go build ./...` exit 0.
