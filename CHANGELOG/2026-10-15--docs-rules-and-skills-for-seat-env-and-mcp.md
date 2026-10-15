## 2026-10-15 - Docs, rules and skills for the seat env and MCP config

### Changed
- `AGENTS.md` section 5: how a seat gets the `agenthub_http` server (the state root `.env` and the seat `mcp.json`), and that a running seat needs a reseat.
- `CLAUDE.local.md`: quick commands now say a push to `main` deploys and no local Docker rebuild; client test and build commands are the Go and Rust ones.
- Client: `docs/WATCH.md` (clock and meter on the rule in a one-seat pane, wrapped rows stay indented) and `skills/client/spawn-team/SKILL.md` (seat env and MCP config).
- `TEST-CHANGELOG.md`: the new tests of this day.
