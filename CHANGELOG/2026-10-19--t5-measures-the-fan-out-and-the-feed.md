# T5's two measurements land: the fan-out benchmark and the feed timing test

Client `c21e702` on client main (pin bumped in the same commit), hub `86da875e`, against the spec
`ai_docs/core-architecture/nfr-measurements.md` (`8aaf7506`). Open gate T5.

## Changed

- `agenthub_go/fastmcp/server/routes/websocket_fanout_bench_test.go` (new): `BenchmarkRealtimeFanout`
  registers N sockets through the production `routes.RegisterConnection`, all owned by one user
  (Rule 1), and broadcasts one ~2 KB task event with `BroadcastDataChange`; N = 1, 10, 100 as
  sub-benchmarks. The fake records one `SendText` per socket, so the number is delivery to N, not a
  loop that dead-ends. It reports `ns/op`, `ns/socket` and `allocs/op`.
- `agenthub_client/internal/clientwatch/feed_timing_test.go` (new): `TestFeedWritesEachLineWithinOnePoll`
  runs `runFeed` against a recording writer, lets the replay finish, appends one marker line and
  asserts the marker arrives in a `Write` of its own within 2 × `feedPollInterval`. A line buffer in
  front of `out` defers the write past that bound, so the test fails on exactly the property PERF-06
  claims.
- No production file changed - test-only on both sides - and no `feedPollInterval` knob was added.

## Measured

- `go test ./fastmcp/server/routes -run '^$' -bench '^BenchmarkRealtimeFanout$' -benchmem -count=1`
  at `86da875e`, re-run by the lead: 15 380 ns/op (N=1), 134 879 (N=10), 1 309 776 (N=100); per socket
  13-15 us; 178 / 1 421 / 13 841 allocs/op. The PERF-04 ceiling is 500 ms for one event to 100
  sockets, so the server-side fan-out is three orders under it; the superlinear case the spec warned
  about does not appear (per-socket cost is flat).
- `go test ./internal/clientwatch -run '^TestFeedWritesEachLineWithinOnePoll$' -count=1` at
  `c21e702`: PASS in 1.00 s, the loop's own poll interval - no buffering delay observed.
- Both suites green: `go test ./...` (client and hub). Reviewer gate PASS
  (`qitem-20261019202745`, `qitem-20261019202820`).

## Effect on the register

PERF-04 keeps PARTIAL with its baseline now cited (server-side fan-out; the wire and the browser
remain unmeasured and the row says so). PERF-06 moves TARGET -> GATE once the register reseed cites
this test. T5's wording changes accordingly in the same reseed.
