## Client pin carries the clearer watch display

### Changed
- `agenthub_client` pin: `658588a` to `b1a553e`. `4genteam watch`, `feed` and `grid` show a call's stated purpose with its argument below it, MCP calls as `mcp <server_tool>`, results headed by their tool, and runtime-injected notices as `HOOK`, `RULE` and `EXIT` blocks.

### Tested
Client `go vet ./...` and `go test ./...` pass; the output was checked on the live `4genthub-min` lead log.
