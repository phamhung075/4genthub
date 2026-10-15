## 2026-10-14 — pin: `send` is one message, the `forcecompact` helper is gone

### Changed
- `agenthub_client` pinned to `9a9a4d3`: `4genteam send` reaches a runner seat as one `text` frame instead of one
  prompt per pasted line (`11438a5`), and `compact-run` compacts through the runtime daemon with the
  `forcecompact` helper removed (`9a9a4d3`).

### Tested
- Client: Rust 86 pass on a clean archive; `go build ./... && go vet ./... && go test ./...`.
- Live on `4genthub-min`: a non-raw multi-line `send` to the architect (claude-code) and the lead (omp) arrived whole;
  `room compact` relayed to all five seats; `up` printed no `setcap` hint.
