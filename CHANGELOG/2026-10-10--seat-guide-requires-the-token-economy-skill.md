## The shared seat guide requires the token-economy skill for everything a seat writes

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: the "Writing style" section now tells every seat to apply the `token-economy` skill to task text, changelogs and every message to another seat, and states its message order (verdict or ask, evidence as path or command, what is needed from the reader).
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/guides.lock.json`: `sha256` and `source_sha256` of `guide-common` re-recorded.

### Why
- `guide-common` is carried by every seat type, so one sentence reaches all seats. The skill itself (seat-message rules) was added in the client at `80cc766`.

### Testing
- `cd agenthub_go && go test ./fastmcp/seat_management/...` passes, including the lock and block-drift tests.
- Seats read the guide at their next reseat; running seats keep the old text until then.
