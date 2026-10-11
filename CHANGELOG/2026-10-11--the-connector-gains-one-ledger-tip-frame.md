## The connector gains one ledger-tip frame, gated by the capability its hello named

### Added

- `agenthub_go/fastmcp/server/httpapp/ws_connector_ledger.go` (new): P4's ONE server frame,
  `ledger_tip {user_seq}` (NEXT_GEN.md, P4), and the per-user registry of the sockets entitled to it.
  The registry is written from the ECHOED capability list - the value `ready` carried - so the frame
  rule (rigd-boundaries.md 2.3.1: a kind is sent only to a socket whose `hello` advertised the
  capability it belongs to and whose `ready` echoed it) has exactly one gate. A re-sent `hello`
  re-decides it, and a closing socket leaves it.
- `connectorCapabilityLedger = "ledger"` (`ws_connector_safeguard.go`), and `wsEnabledCapabilities`
  echoes it in `ready.capabilities` beside `ingest` and `safeguards`. `commands` stays unserved, so
  the server still never echoes a capability it cannot serve (2.3.1).

### Changed

- `agenthub_go/fastmcp/server/httpapp/ws_mount.go`: an accepted `hello` registers the socket with the
  echoed list, and the handler's close path unregisters it. `writeFrame` is split into
  `writeFrame`/`writeFrameLocked`, and the new `wsConn.SendTextWithin` writes one frame under a write
  deadline - cleared under the SAME hold of the socket mutex, so the read loop's next pong never
  inherits a deadline it did not ask for. `wsSendWithin` is the bounded twin of `wsSend`.
- `agenthub_go/fastmcp/server/httpapp/ledger_mount.go`: `ledgerIntentsWriterAdapter.SubmitIntents`
  nudges after the service call returns, i.e. after the transaction committed, with the highest
  `user_seq` the batch took (`ledgerAcceptedTip`). A batch that wrote nothing nudges nobody. The
  subject handed to the fan-out is the RAW authenticated one, which is what the connector keys its
  sockets by; the ledger's own normalization stays where it was, on its rows.

### Not changed, deliberately

- The pull is untouched and remains the only correctness path: `GET /api/v2/ledger` from the client's
  own cursor (P4; rigd-boundaries.md 2.8). The frame carries a tip and no entries; no request path
  reads it, and no code path acts on it.
- The client half (P5), the rigd boundary rule, and production are out of scope. The only other place
  the name appears in the tree is a comment that already predicted it
  (`task_management/infrastructure/repositories/task_event_repository.go:350`).

### Testing

- `gofmt -l fastmcp/server/httpapp/` prints nothing; `go build ./...` rc 0; `go vet` on the touched
  packages rc 0.
- RED MEASURED FIRST, one mutation per clause, on the Postgres named by `AGENTHUB_TEST_PG_URL`:
  - the emission removed from the adapter -> `TestLedgerTipArrivesAfterADecisionCommitsAndTheNextPullAdvancesTheCursor`
    fails at `ledger_pg_test.go:865: read frame header: read tcp ...: i/o timeout`;
  - `ledger` dropped from the served capability list -> `ready.capabilities = [ingest safeguards],
    want [ingest safeguards ledger]` and both frame cases fail on the same read timeout
    (`ws_rigd_test.go:689`, `:723`).
- Green with both restored. The frame cases (no database):
  `go test -count=1 -run 'LedgerTip|ConnectorReadyReportsProtocolHeartbeat|ConnectorPingIsAnswered' -v ./fastmcp/server/httpapp/`
  -> `TestConnectorReadyReportsProtocolHeartbeatAndEchoedCapabilities` PASS, `TestConnectorLedgerTipGoesOnlyToASocketThatAdvertisedAndWasEchoed`
  PASS (1.41s), `TestConnectorLedgerTipFollowsTheLastHandshake` PASS (0.70s),
  `TestLedgerTipIsAServerFrameAndNotAnInput` PASS, `ok 2.161s`.
- Green on real rows: `TestLedgerTipArrivesAfterADecisionCommitsAndTheNextPullAdvancesTheCursor` PASS
  (2.60s, `OBSERVED cursor 0 -> ledger_tip user_seq=1 -> pull count=1 tip=1`) and
  `TestAClientWithNoSocketStillConvergesByPulling` PASS (1.49s, `OBSERVED pull-only: cursor 0 ->
  committed user_seq 1 -> pull count=1 tip=1`).
- Touched packages, and then the whole suite, with `AGENTHUB_TEST_PG_URL` on the 55995 cluster:
  `go test -count=1 ./fastmcp/server/httpapp/ ./fastmcp/ledger/... ./fastmcp/server/routes/...` ->
  `ok agenthub/fastmcp/server/httpapp 133.422s`, `ok agenthub/fastmcp/ledger/domain/entities 0.002s`,
  `ok agenthub/fastmcp/server/routes 0.007s`; `go test -count=1 ./...` -> **exit 0, 141 packages ok, no
  `FAIL` line (315.59s)**. Base: `e0e75084` on `4genthub-min/go-dev` (the branch that carries the ledger
  at `bccf893d`; `4genthub-min/carry` has no `fastmcp/ledger` at all).
