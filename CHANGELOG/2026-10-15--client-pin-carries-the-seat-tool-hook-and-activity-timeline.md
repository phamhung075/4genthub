# The client pin carries the seat tool hook and the activity timeline

### Changed
- `agenthub_client` gitlink: `729153d` -> `6e55e0d`. The pin now carries `8c8233b` (the redactor's `unsure` rule keeps paths and ids), `6e55e0d` (the seat tool hook `seat-guard.ts`, written into every seat at start, and the `4genteam activity` verb), plus the room's own `926ca1e` and `e41d827` (a room created with its links; the required-links guard's changelog).

### Testing
- `go test ./internal/clientactivity ./cmd/...` and `cargo test --offline the_seat_` pass in the client; the build was installed and the room restarted on it (5 seats running, `heal --check` clean).
