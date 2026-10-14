# Client pin: rig-shim removed, decision skill uses decide

### Changed
- `agenthub_client` gitlink moved to `4eed4bb`: removes the `rig-shim` verb (`8193820`, `compact` names `room compact`) and rewrites `skills/share/room-decision-request` for `4genteam decide` (`4eed4bb`).

### Testing
Client `go test ./...` green. Parent `cd agenthub_go && go build ./... && go test ./...`.
