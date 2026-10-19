# Task events carry a flat delta under a 2048-byte cap (T7, PERF-05)

PERF-05 was a GAP: every task event broadcast `payload.data.primary` as the whole 17-key seed
object, `details` included, so one 41k-char note made every frame that size, and the duplicate key
(`eventType:entityType:entityID:userID`) dropped a second write by the same user inside 5 s while
letting the SAME write ship twice from the two emitter families (`"system"` hook stamp vs the
facade's request user). Captured earlier under `T7 go` (branch `4genthub-min/t7-event-delta`). The
architect's ruling `RULING-perf05-task-event-delta-2026-10-19.md` sets the shape; this lands the
server side, and the frontend merge is fe-dev's row.

## What changed

- `WebSocketPayloadBuilder.BuildTaskPayload` always excludes `details`; the dead
  `includeProgressHistory` flag and `BuildLightweightPayload` are deleted, not kept.
- `WebSocketPayloadBuilder.BuildTaskDelta(full, changed)` builds the flat delta: `id`,
  `updated_at`, and each changed field at the top level of `primary` (never a `changed` wrapper);
  `details` becomes `details_changed: true`, and a name the payload does not carry is omitted.
- `SyncTaskEventParams` gains `Changed []string`; the three use-case hook sites
  (`create` nil, `update` from the request's non-nil fields via `use_cases.ChangedTaskFields`,
  `complete` `["status"]`) and the five facade sites (`created` nil, `updated` from the request,
  dependency `["has_dependencies"]`, `completed` its completion fields) populate it.
- The facade's completion payload carries the row's `updated_at`, so its frame and the use-case
  hook's frame for the same completion share the dedup identity and collapse to one.
- `SyncBroadcastTask` picks the shape by event type (`created`/`deleted` unchanged, `updated`/
  `completed` deltas) and enforces `WebSocketTaskPayloadCap = 2048` at emit time with
  `EstimatePayloadSize`; an over-cap delta becomes `{"id", "refetch": true}`.
- The duplicate key is `eventType:entityType:entityID:updated_at` when the payload carries
  `updated_at`, else the user-scoped key: one write emitted by both families collapses, two writes
  inside the TTL both ship, `deleted` keeps the old key.
- `WebSocketNotificationService.BroadcastTaskEvent` (no production call site) is deleted.
- `BenchmarkTaskEventDelta` replaces `BenchmarkTaskEventFrame`: four sub-benchmarks (`status`,
  `completion`, `details`, `wide`) each report the emitted primary's bytes and ns/op. Before them it
  asserts the reachability of every writable payload field through some `Changed` path, the
  `created` seed (no `details`) and the `deleted` shape (id, title, git_branch_id), `≤ 512 B` for
  status-only, completion and details, the cap or the refetch shape for the wide case, and the
  duplicate gate both ways: one write from both emitter families collapses, two distinct writes
  inside 5 s ship two frames with two different primaries.
- `ai_docs/core-architecture/agenthub-system-architecture.md` §3.6 now states the envelope the code
  emits and the post-T7 size statement.

## Verification

- `cd agenthub_go && go build ./...` clean; `go vet ./...` clean; `gofmt -l .` empty.
- `cd agenthub_go && go test ./... -count=1` green, whole module.
- `go test -run='^$' -bench BenchmarkTaskEventDelta -benchmem -count=3
  ./fastmcp/task_management/application/services/`, three runs each:
  - status: primary **90 B**, 3894-4525 ns/op, 53-54 allocs/op
  - completion: primary **208 B**, 7764-8696 ns/op, 85 allocs/op
  - details (41,000-rune note): primary **91 B**, 3857-4635 ns/op, 52 allocs/op
  - wide: delta 4069 B over the cap -> refetch primary **42 B**, 37-54 us/op
  (was a whole 17-key object, unbounded in `details`).
- Service tests: a delta carries `id`, `updated_at`, the changed fields and `details_changed` and
  never the note; an over-cap delta is the refetch shape; two emitter families stamping one write
  deliver one frame and a second write inside 5 s delivers a second.
