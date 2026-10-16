# The seat guide names the short-output skill

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: the output rule now says to apply the `short-output` skill every turn (short pointer lines, no full reasoning, the result plus at most 5 short lines). The client delivers the skill, but a seat only loads a skill its guide names.
- `seedmap.go` `seedVersion` 1.4.7 -> 1.4.8 (a stored seat type version is immutable); `guides.lock.json` and `seedcontent.lock.json` re-recorded.

### Testing
- `go test ./...` and `go vet ./fastmcp/seat_management/...` pass in `agenthub_go`. No test file changed.
