## The readiness report still listed an environment variable Go stopped reading

### Changed
- `agenthub_go/PROD_READINESS_REPORT.md`: `MCP_AUTH_TYPE` is removed from the list of names Go reads and production does not provide. Its only Go read lived in `mcp_auth_config.go`'s `GetDefaultAuthProvider`, deleted with the unreachable `fastmcp/server/auth` chain (row `ecea11ab`), so the line asserted a read that cannot happen and made a production gap out of nothing. This is the third site of row `7117bab2`; the other two are `MIGRATION.md`'s `entities.AgentNameResolver` claims, which land in the writer's pass on that file under the lead's one-owner ruling.

### Verified
- **Read, not inferred:** `grep -rn "MCP_AUTH_TYPE" --include=*.go agenthub_go` returns nothing outside the build caches, and every other hit in the tree is a record of the deletion rather than a read - `CHANGELOG.md`, `TEST-CHANGELOG.md`, `NEXT_GEN.md`'s account of it, and `MIGRATION.md`'s `removed-unreachable` row.

### Found by
- Row `7117bab2`.
