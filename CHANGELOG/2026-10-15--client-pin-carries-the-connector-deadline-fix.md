## 2026-10-15 - client pin carries the connector deadline fix

### Changed
- `agenthub_client` pin: `e2c5668` -> `729153d`. The agent's connector socket no longer dies about a second after connecting (`net.Conn.SetDeadline` also set the write deadline; the drain poll's 1 ms deadline then failed the next write). Details in `agenthub_client/CHANGELOG/2026-10-15--connector-deadline-bounds-reads-only.md`.

### Testing
- `go test ./internal/clientsync` passes in the client; the installed binary ran 10+ minutes without a reconnect.
