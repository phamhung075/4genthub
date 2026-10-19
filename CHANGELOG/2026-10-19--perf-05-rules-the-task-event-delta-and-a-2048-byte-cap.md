# PERF-05 rules the task-event delta and a 2048-byte cap

The register's PERF-05 ("A task event sends a delta under a size cap", GAP) had no ruling and no
delta: `SyncBroadcastTask` hands the caller's payload to `BroadcastDataChange`
(`websocket_notification_service.go:359`), the live emitter builds the whole task payload
(`task_hooks.go:101`, 17 keys) with `details` copied verbatim (`websocket_payload_builder.go:38-46`;
a hub task has held 41k characters), and the benchmark that cites the row times that path with a
3-key payload into a discard broker (`unified_context_bench_test.go:81-107`) - no frame, no size, no
cap. The frontend replaces the whole cached task on `updated` (`useRealtimeSync.ts:224-243`), while
`completed` already merges (`:331-393`).

Q6 rules the shape: a task event's `payload.data.primary` is a **flat field map** - `id` and
`updated_at` plus only the fields the write changed; `created` carries the task payload without
`details`; `deleted` keeps `{id, title}`; a changed `details` is signalled by `details_changed:
true` and never carried. Every primary serialises to **<= 2048 bytes**; a shape that would exceed it
is replaced by `{id, refetch: true}` and the consumer refetches. The emitter takes the changed field
names, `SyncBroadcastTask`'s dedup key carries the row's `updated_at` (two distinct writes inside
the 5 s window both ship; one write emitted by both emitter families collapses - today it ships
twice because the hook stamps `"system"` and the facade stamps the request user), and the frontend
merges `primary` into `['task', id, false|true]`.

## What changed

- `nfr-register.md`: PERF-05's requirement names the 2048-byte cap; the open-gates table gains
  **T7**; the Rulings section gains **Q6** with the contract above. The row stays **GAP** - a ruling
  is not a status.
- `nfr-measurements.md`: a PERF-05 section states the command, the payload the benchmark builds
  (41,000-rune `details`, 20 labels, 20 assignees), the per-case assertions (status/completion
  <= 512 B, every case <= 2048 B or the refetch shape, no `details` bytes, two updates inside 5 s
  -> two frames, one write emitted twice -> one frame) and the tautology guards.
- No code changed. The row's existing measurement (1,755 ns/op, 1,328 B/op, 25 allocs/op at
  `d45aa05d`) stays as the frame-build baseline it is; the new benchmark replaces its 3-key payload
  at T7.

## Verification

- Every fact above was opened at `d45aa05d`/`c46812c`: the emitter call sites
  (`task_hooks.go:101`, `create_task.go:211`, `update_task.go:209`, `complete_task.go:585`, and the
  facade sites `:568-580`, `:739-747`, `:1332-1340`, `:1459-1470`, `:1886-1898`), the dedup key
  (`websocket_notification_service.go:12-44`), the envelope (`websocket_routes.go:421-470`), the
  consumer branches (`useRealtimeSync.ts:167-203`, `:224-243`, `:260-328`, `:331-393`) and the
  benchmark (`unified_context_bench_test.go:81-107`, re-run at `d45aa05d`).
- Doc of record corrected at T7: `agenthub-system-architecture.md:329` states an envelope the code
  does not emit (`{event, data, metadata{source, timestamp, operation}}`) and a completion size claim
  ("under 500 bytes") that is false today; Q6's shape makes the size statement true for completion
  deltas.
- `python3 scripts/G3-DROP-CLASSIFY.py` does not read these files; `scripts/tests` does not read the
  register (unchanged by this entry).
