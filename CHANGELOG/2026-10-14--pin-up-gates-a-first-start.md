## 2026-10-14 — pin: `up` gates a first start on the definition

### Changed
- `agenthub_client` pinned to `a532514`: a first `4genteam up` decides the DeepSeek peak gate on the seats its team
  definition declares, instead of proceeding with "the gate did NOT run".

### Tested
- Client `go build ./... && go vet ./... && go test ./...`; a live `up` of `4genthub-min` off-peak passes the gate.
