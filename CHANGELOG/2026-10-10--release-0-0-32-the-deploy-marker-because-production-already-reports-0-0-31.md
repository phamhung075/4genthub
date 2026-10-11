## Release `0.0.32` — the deploy marker, because production already reports `0.0.31`

### Changed
- `agenthub_go/fastmcp/config/version.go:21`: `ReleaseVersion` `0.0.31` -> **`0.0.32`**, as the last commit above
  `origin/main`. One *code* literal moves and nothing else. **Confirmed by reading the file rather than
  assuming:** `agenthub_go/fastmcp/server/httpapp/http.go:160` declares `const healthVersion =
  config.ReleaseVersion`, and `:173` sets `/health`'s `version` from it; the same constant is the version on the
  MCP initialize `serverInfo` (`fastmcp/server/httpapp/misc_mount.go:190`), on the MCP routes
  (`fastmcp/server/httpapp/mcp_routes.go:191`) and in the three connection-management use cases
  (`connection_management/application/use_cases/get_server_capabilities.go:46`, `get_server_status.go:56`,
  `check_server_health.go:59`), so this one string moves every surface that advertises the release. None of those
  files was edited.
- `README.md` is NOT touched. Its marker cell was de-numbered at `e38b59a3` precisely so no reading rots there
  again; readings belong in `DEPLOY-READY.md`.

### Why it is on the critical path
- **Production already reports `0.0.31`, read first-hand rather than recalled:** `GET
  https://api.4genthub.com/health` (read-only) answers `{"status":"healthy",…,"version":"0.0.31",…}` with
  `connections.uptime_seconds` `5510.243` at the moment of the read, which puts that container up since roughly
  **09:18Z** today. The Docker build context carries no `.git`, so this string is the only thing that confirms a
  deploy landed; pushing this batch without the bump would auto-deploy it under the number the deploy before it
  already reports, and a failed deploy would be indistinguishable from a stale one.
- **It is the LAST commit above `origin/main`.** Twenty-one commits sat above it when the bump was written
  (`origin/main` = `7c7edf48`, local ref), and every commit above `a7990665` carries a reviewer verdict —
  **seven APPROVE** (`a691276c`, `79e54a50`, `e38b59a3`, `3a413d86`, `a4aed201`, `b79761e9`, `53e92346`) and
  **one REQUEST CHANGES**, `b4ca5c68` (the policy module that resolved outside its room), whose defect
  `a4aed201` fixes and which is therefore recorded as closed by `a4aed201` rather than as an APPROVE of its
  own. That is the rule the constant's own comment states — "if a commit lands after the bump, the bump
  moves to it or the deploy waits".

### Verified
- **The tip was measured immediately before the commit rather than recalled:** `git rev-parse --short HEAD` ->
  `53e92346`, `git rev-list --count origin/main..HEAD` -> **21** (22 with the bump). Nothing else was staged:
  in a shared tree that still holds other hands' uncommitted paths (`.claude`, `.env.sample`,
  `agenthub-frontend/CHANGELOG.md`, `agenthub-frontend/vite.config.ts`, `agenthub_client`,
  `agenthub_go/cmd/agenthubclient/main.go`) and the untracked `scripts/team/4genthub-ab/` (owner row
  `f465d5df`), the commit carries exactly two paths.
- From `agenthub_go`, with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`: `gofmt -l` over the touched files
  printed nothing; `go vet ./fastmcp/config/... ./fastmcp/server/httpapp/...` exit **0**; `go test -count=1` on
  the same two packages exit **0**, including `http_health_test.go`, which asserts the `version` `/health`
  serves — that test is the smoke for this exact path, and it runs against the bumped constant.
- `git grep -n '0\.0\.31' -- '*.go'` returns **nothing** after the bump; the remaining `0.0.31` text in the tree
  is CHANGELOG prose and the client's own binary version note, which are logs, not the release cell.
- `git show <hash>:agenthub_go/fastmcp/config/version.go | sed -n '21p'` printed verbatim in the hand-off to
  the lead.

### Found by
- The lead's seal order; landed by go-dev (row `c02e0506`). NO PUSH, no tag, no deploy — the push is the
  principal's, after the lead's certificate and the reviewer's gate on the seal.
