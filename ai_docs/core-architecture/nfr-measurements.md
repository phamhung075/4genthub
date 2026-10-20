# NFR measurements — PERF-04, PERF-05 and PERF-06

The measurement spec for the rows open gates T5 and T7 name (`ai_docs/core-architecture/nfr-register.md`).
It states, per row, the exact command, the metric and its unit, the threshold and that threshold's
source, and the load the measurement applies. It changes **no row status**: the register reseed after
the numbers exist is a separate ruling ("a status change is a ruling, not an edit").

Provenance: written 2026-10-19 by the architect seat, from the row text at `nfr-register.md:44`,
`:45` and `:46` and the claim catalogue the register is derived from,
`ai_docs/reports-status/NFR-analysis-2026-10-19.md` (`:43`, `:44`, `:45`).

## PERF-04 — realtime fan-out

Exercised path: `/ws/realtime` is mounted at `agenthub_go/fastmcp/server/httpapp/ws_mount.go:70` and
served by `handleRealtime` (`:140`); a task event reaches the sockets through
`routes.BroadcastDataChange` (`agenthub_go/fastmcp/server/routes/websocket_routes.go:421`), which
snapshots the registry, runs `IsUserAuthorizedForMessage` per socket (`:322`), and calls `wrSendJSON`
(`:194`) — one frame marshal **per socket** and one `SendText` hand-off. The frame build alone is
already measured by `BenchmarkTaskEventFrame`
(`agenthub_go/fastmcp/task_management/application/services/unified_context_bench_test.go:81`, PERF-05:
1.4-1.8 us/op at commit `81074bd6`); that benchmark uses a discard broker and does not exercise
fan-out.

Command, from `agenthub_go/`:

```
go test ./fastmcp/server/routes -run '^$' -bench '^BenchmarkRealtimeFanout$' -benchmem -count=1
```

The benchmark (test-only file `fastmcp/server/routes/websocket_fanout_bench_test.go`):

1. registers N sockets through the production `routes.RegisterConnection`, all owned by one user;
2. broadcasts once per iteration with `BroadcastDataChange(ctx, "updated", "task", "task-bench",
   <user>, payload, nil)`, `payload` a ~2 KB TaskData (the size PERF-05's claim describes);
3. runs N = 1, 10, 100 as sub-benchmarks.

- **Metric and unit**: `ns/op` per broadcast (one event to all N sockets) and `allocs/op`; also
  report the per-socket cost (`ns/op ÷ N`).
- **Load applied**: N registered sockets, N = 1, 10, 100.
- **Latency measured**: one broadcast from the calling goroutine to the last `SendText` hand-off, in
  process. The wire and the browser are **not** measured: the register citation must read
  "server-side fan-out".
- **Threshold**: fan-out of one event to 100 sockets **< 500 ms**. Source: the PERF-04 claim,
  `ai_docs/reports-status/NFR-analysis-2026-10-19.md:43` ("End-to-end WebSocket fanout < 500 ms"),
  against the measured frame-build floor above (`81074bd6`). A superlinear jump from N=10 to N=100
  is the scaling regression the ceiling alone misses.
- **Tautology guards**: every socket must receive exactly one frame (count its `SendText` calls) — a
  loop that dead-ends measures nothing; registration happens outside the timed loop; the per-user
  queue is reset between iterations (bookkeeping, exactly as `BenchmarkTaskEventFrame` clears its
  duplicate-cache key); the discard broker and `SyncBroadcastTask` are not used (that is PERF-05).

## PERF-06 — watch wall

Exercised path: each grid pane runs that seat's own feed (`agenthub_client/docs/WATCH.md:28`), which
is `runFeed` (`agenthub_client/internal/clientwatch/feed.go:16`): it tails the seat's session log,
renders each line with `eventsWith` (`render.go:435`), and writes it straight to `out` with
`fmt.Fprintln`/`Fprintf` — no buffered writer. The tail re-scans every `feedPollInterval =
time.Second` (`feed.go:12`, the wait at `:166`).

Command, from `agenthub_client/`:

```
go test ./internal/clientwatch -run '^TestFeedWritesEachLineWithinOnePoll$' -count=1 -v
```

The test (test-only file `internal/clientwatch/feed_timing_test.go`):

1. starts `runFeed` with the package's existing seams (`newFakeExec`, `withSeatStore`,
   `withStateRoot`, a session log where `seatlog.SeatLog` reads it) and an `io.Writer` that records
   (arrival time, bytes) per `Write`;
2. lets the startup replay finish, then appends ONE distinguishable event line to the seat's log;
3. asserts the rendered marker reaches the writer within **2 × feedPollInterval** and in a `Write` of
   its own — not coalesced with a later line and not held until the test's context ends.

- **Metric and unit**: delay in seconds from the append to the first `Write` carrying the rendered
  line.
- **Threshold**: ≤ 2 × `feedPollInterval` = 2 s. Source: `feed.go:12` — one interval is the soonest
  the loop can see a new line, the second is slack for a loaded CI (the scan itself costs
  microseconds) — against the PERF-06 claim,
  `ai_docs/reports-status/NFR-analysis-2026-10-19.md:45` ("zero line-buffering delay on
  stdout/stderr feeds").
- **How buffering shows up**: a line buffer in front of `out` holds the line until the buffer fills
  (4 KB ≈ tens of rendered lines) or the process ends, so the write lands past the bound — or the
  test's context ends with no write at all.
- **Not measured**: the terminal provider's own rendering (herdr/tmux); the check covers the feed's
  stdout path, which is the client's.

## PERF-05 — task-event delta and cap

Exercised path: a task write reaches `SyncBroadcastTask`
(`agenthub_go/fastmcp/task_management/application/services/websocket_notification_service.go:311`),
which builds one `payload.data.primary`, hands it to `routes.BroadcastDataChange`
(`fastmcp/server/routes/websocket_routes.go:421`), and marshals that frame once per authorized
socket. Before T7 the primary is the whole task payload built by
`WebSocketPayloadBuilder.BuildTaskPayload` (`websocket_payload_builder.go:22`), with `details`
copied verbatim (`:38-46`); `BenchmarkTaskEventFrame`
(`unified_context_bench_test.go:81-107`) times that path with a 3-key payload into a discard broker
and measures no frame and no size.

Command, from `agenthub_go/`:

```
go test ./fastmcp/task_management/application/services -run '^$' -bench '^BenchmarkTaskEventDelta$' -benchmem -count=1
```

The benchmark (test-only, replacing `BenchmarkTaskEventFrame`'s 3-key payload) builds one task with
`details` of 41,000 runes, a 200-rune description, 20 labels and 20 assignees, and runs four
sub-benchmarks against a broker that counts frames and keeps the marshal length:

1. **status** - an update changing `status` only;
2. **completion** - the `completed` event;
3. **details** - an update appending to `details`;
4. **wide** - an update changing description, labels and assignees together.

- **Metric and unit**: bytes of the compact JSON of `payload.data.primary` (`len` of the marshalled
  primary, the same bytes `wrSendJSON` writes), plus `ns/op` and `allocs/op` for the emit path.
- **Threshold**: **≤ 2048 B** for every case; the **status** and **completion** cases additionally
  **≤ 512 B**. Sources: Q6 (`nfr-register.md` Rulings) for the cap, and the PERF-05 claim,
  `ai_docs/reports-status/NFR-analysis-2026-10-19.md:44` ("state transition payloads < 500 bytes",
  "full 2KB+ entity snapshots") for the transition bound; the fan-out ceiling PERF-04 already
  measures is taken at ~2 KB, so it covers this cap.
- **Shape assertions**: no case's primary carries a `details` byte string; the **details** case
  carries `details_changed: true`; the **wide** case is either <= 2048 B or exactly the refetch
  shape `{"id": <id>, "refetch": true}`; `id` and `updated_at` are present in every delta; the
  `created` shape is the task payload without `details`; `deleted` stays `{id, title}`.
- **Tautology guards**: the pre-delta full payload must marshal to > 41,000 B, so the cap is not
  proven against a payload too small to fail it; the broker counts one frame per broadcast; the
  duplicate cache is cleared per iteration exactly as the old benchmark did, and a separate case
  fires two updates inside 5 s and asserts **two** frames with distinct primaries (the dedup key
  carries `updated_at`); a case with a user-stamped and a `"system"`-stamped emission of the same
  write asserts **one** frame.
- **Not measured**: the browser's merge cost and the HTTP refetch the `refetch` shape triggers.

## Where the numbers land

After `go-dev` runs the two commands and a reviewer gate confirms them:

- **PERF-04**'s Verification cell cites the benchmark command with the date, commit, host and the
  `ns/op` range (register rule 2: a baseline names its host and is a range, not a promise).
- **PERF-06**'s cell cites the test, and its status moves TARGET -> GATE (a test fails when buffering
  appears — the register's GATE vocabulary).
- **T5** (`nfr-register.md:132`) then reads one benchmark (PERF-04, baseline cited) and one test
  (PERF-06, GATE).
- **PERF-05**'s cell cites the `BenchmarkTaskEventDelta` command with the date, commit, host and the
  per-case byte figures, and its status moves GAP -> GATE once the benchmark asserts the delta, the
  cap and the dedup key at the landed sha (gate T7).

Those edits are the architect's, after the numbers exist; they are not part of this document.
