## Client pin carries the per-tool glyphs

### Changed
- `agenthub_client` pin: `b1a553e` to `7925e39`. `4genteam watch`, `feed` and `grid` give each kind of tool its own glyph and colour (read, search, write, shell, web, delegate, ask, MCP).

### Tested
Client `go vet ./...` and `go test ./...` pass; the output was checked on the live `4genthub-min` lead log.
