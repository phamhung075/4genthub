## 2026-10-15

### Changed
- The `agenthub_client` pin moves from `bc725e6` to `e2c5668`: the `agent` daemon and `sync connector` upload with `AGENTHUB_CONNECTOR_TOKEN` (scope `sessions:write` only), and `AGENTHUB_TOKEN` stays the MCP key. `up` names a missing connector token before starting the daemon.
- Docs touched with the pin: the client `README.md` and `docs/AGENT-SETUP.md` now describe two credentials.
- Tested: client `go test ./...` and `cargo test --offline` (102) clean.
