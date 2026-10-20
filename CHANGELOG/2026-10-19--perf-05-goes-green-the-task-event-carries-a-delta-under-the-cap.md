# PERF-05 goes green: the task event carries a delta under the cap

Gate T7 landed. `agenthub_go` at `0f2c67fd` builds a flat delta for `updated` and `completed`
events, `{id, updated_at}` plus only the changed fields, with `created` carrying the payload
without `details`, `deleted` keeping `{id, title}`, and a changed `details` signalled by
`details_changed: true`. Every primary over 2048 bytes is replaced by `{"id": …, "refetch": true}`;
the dedup key carries the row's `updated_at`, so two distinct writes inside the 5 s window both
ship and one write emitted by both emitter families collapses. `BroadcastTaskEvent`,
`BuildLightweightPayload` and the `includeProgressHistory` flag are gone.

`BenchmarkTaskEventDelta` replaces `BenchmarkTaskEventFrame` and reports four cases on the i7-12700F
host at `0f2c67fd`: status 90 B, completion 208 B, details 91 B, wide over-cap 4069 B delta
replaced by the 42-byte refetch shape. `agenthub-frontend` at `b6ab0203` merges the delta into the
cached task and invalidates `['task', id]` on the refetch shape or a stale `details`.

With that, the register row moves GAP -> GATE, T7 leaves the open-gates table, and the register
has no open gate row.
