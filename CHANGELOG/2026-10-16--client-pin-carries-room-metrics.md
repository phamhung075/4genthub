# Client pin carries `room metrics`

### Added

- `agenthub_client` pin moves to `194343c`: `4genteam room metrics ROOM` appends a flat JSON-lines log per seat
  (`turn`, `tool`, `commit`, `queue_row` events, no commands or bodies) for `jq` analysis, and the seat guard hook
  adds `session`, `target_class`, `blocked_rule` and `bytes_out` to `tool-calls.jsonl`.
- Also carries the room-pin commit `09dc2dc0` (seed 1.4.12) already on this branch.

### Testing

- Client: `go vet`, `go test ./...`, `cargo test --offline` pass. Real-room check: lead's summed cost matches a manual jq sum.
