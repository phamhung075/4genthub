### Fixed

**seatcheck accepts the full session name a seat replies to** (2026-10-03)

- `agenthub_go/cmd/seatcheck/main.go`: a message header names its sender by session (`From: finalroom-alpha@finalroom`) but the policy speaks in seat keys, so `seatcheck send --to finalroom-alpha@finalroom` was denied "no link" while `--to alpha` was allowed. `--to` may now be a seat key or a full session name of the roster: the session is mapped to its member before the policy check, the audit line records the member, and delivery goes to exactly that session (so a session of a member name repeated across pods is not ambiguous). A name that is neither is still denied "no link" (exit 3, audited, no delivery) and now also prints `unknown recipient "X"; use a seat key: a, b, c`. Exit codes are unchanged.
- Verified: gofmt, go vet, `go test ./cmd/seatcheck`; a mutation check (no session mapping) fails 4 tests.
