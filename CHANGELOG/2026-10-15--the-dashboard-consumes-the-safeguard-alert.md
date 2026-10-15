## 2026-10-15 - the dashboard consumes the safeguard alert

### Fixed
- `agenthub-frontend/src/hooks/useRealtimeSync.ts`: the entity switch handled task, subtask, project, branch, seat, `agent_session`, room and `notification`, so 7.3's alert - entity `rig_safeguard`, action/event_type `safeguard_alert` - fell to its default branch and the dashboard logged it at debug level and showed nowhere. A stopped or failing safeguard, and the dead-man alert for a machine whose connector stayed silent, reached the owner as nothing at all, live and replayed alike (`wsReplayMissedNotifications` re-sends the stored frame unchanged, so the replay carried the same unrouted entity).

### Added
- `agenthub-frontend/src/hooks/useRealtimeSync.ts`: a `rig_safeguard` case and its handler put the alert in the existing dashboard inbox (`useNotificationStore`) with a warning toast. The frame carries the ROW, not a message, so `describeSafeguardAlert` composes the line from the row's own fields: `Safeguard compact (rig demo, connector conn-1) is failing (3 restarts, last beat 41s ago)`. A frame with no `state` is 7.3's dead-man alert, which is the connector's silence rather than a reported state, so it reads `... is unreachable: the connector stayed offline past its heartbeat close` instead of inventing one.
- `agenthub-frontend/src/types/websocket-protocol.ts`: `RigSafeguardAlertPayload`, the frame's own fields with `state` optional.

### Notes
- **The dedupe key is the FRAME id, not `metadata.entity_id`.** `entity_id` for this entity is the row key (`<connector>/<rig>/<safeguard>`), which repeats across the row's life: keying on it would swallow a genuine second alert - stopped again after a recovery. A replayed frame keeps its id, so a reconnect still yields one inbox row.
- **No safeguard page and no new store**: the ruled owner channel is the dashboard notification store (rigd-boundaries.md 7.3(c)), and 2.3a now records the browser's handling of this entity beside the `agent_session` one.
- **UI line not observed against a live producer**: nothing on the deployed server emits entity `rig_safeguard` yet (item 4's server half is unlanded), so the surface is proven at the seam - frame in, inbox row and badge out, `NotificationBell` rendered - and not against a real alert.

### Testing
- `agenthub-frontend/src/tests/hooks/test_useRealtimeSync_rigSafeguard.test.tsx`: six cases - the row with its counters lands in the inbox and toasts once; the dead-man frame reads as unreachable; a replayed frame stays one row and one toast; a second alert about the same row is a second row (the `entity_id` trap); a frame naming no safeguard is dropped with a warning; and the rendered `NotificationBell` shows the line and the unread badge.
- `npx vitest run src/tests/hooks` -> 17 files, 135 tests passed; `npx tsc --noEmit` clean.
- RED before, measured with a throwaway probe on the pre-change tree: the same frame left the store empty with only `debug('[useRealtimeSync] Unknown entity type:', 'rig_safeguard')`, while the control frame (entity `notification`) landed in the store - so the empty inbox was the missing case, not the harness.
