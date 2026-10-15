## NEXT-GEN2 C2 records which parity items already exist

### Changed
- `NEXT-GEN2.md` (C2): auto-resume, the idle-seat nudge and the `send` envelope are marked implemented with their code locations; large RPC responses are recorded as handled by resume, with the chunking question left to the owner; `send` submission confirmation is recorded at client commit `041c18b`, not yet measured on a live pane.

### Tested
Documentation only. Each claim was read from `rust/agenthub-runtime` and the client at `041c18b`; `cargo test --offline` (74) and `go test ./...` pass there.
