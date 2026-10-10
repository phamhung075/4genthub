## Release `0.0.28` — the deploy marker, because production already reports `0.0.27`

### Changed
- `agenthub_go/fastmcp/config/version.go:21`: `ReleaseVersion` `0.0.27` -> **`0.0.28`**. It is the only *code* literal that moves: `git grep -n '0\.0\.27'` returns this line and five dated prose records (`CHANGELOG.md` twice, `README.md` twice, `agenthub-frontend/CHANGELOG.md` once), which are a log and stay. **Confirmed by reading the files rather than assuming:** `httpapp/http.go:160` declares `const healthVersion = config.ReleaseVersion` and `httpapp/misc_mount.go:190` sets the MCP `serverInfo.version` from the same constant, so `/health`, the MCP `initialize` `serverInfo`, the status tool, `register_mcp_client` and the connection-management health route all move with that one string — the `http.go` constant was NOT edited.
- `README.md:540` and `:663` still read "the tree's release literal reads `0.0.27`" as a **dated 2026-10-08 measurement**, so they are now one release behind the tree. They are left alone deliberately — this commit moves the marker, and a new number belongs to the next README measurement pass — and this line is the pointer for whoever runs it.

### Why it is on the critical path
- **Production already reports `0.0.27`** — measured live by the lead at 2026-10-09 19:32Z and re-read first-hand while this commit was written (`GET https://api.4genthub.com/health` -> `"version":"0.0.27"`, `"status":"healthy"`, `uptime_seconds` 1596) — because the deploy caught up to the previously pushed tree while this batch was being written. Pushing the batch as it stood would have left `/health` reading `0.0.27` and given the owner no way to confirm the deploy from the version — the one thing the Docker build context can still provide, having no `.git` to embed a commit id from.

### Verified
- From `agenthub_go`, with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`: `gofmt -l` over the **1266 tracked `.go` files** printed nothing; `go build ./...` exit **0**; `go vet ./...` exit **0**; `go test -count=1 ./...` exit **0** — **144 packages ok, 0 failures**.
- It is the **last commit in the set**: nothing lands on top of it before the owner pushes, so the string cannot cover a tree that lacks the content it marks (`version.go:19-20`).
