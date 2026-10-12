# Release marker 0.0.38: the seedVersion 1.4.3 push becomes version-confirmable

Date: 2026-10-12
Scope: `agenthub_go/fastmcp/config`

## Summary
`config/version.go:25` goes `0.0.37` -> `0.0.38`. One line, one place: `healthVersion = config.ReleaseVersion`
(`fastmcp/server/httpapp/http.go:160`), so this single edit moves every surface that advertises the server's own
version - `/health`, the MCP initialize `serverInfo`, the MCP status tool, the `register_mcp_client` response, the
access-level health checker and the connection-management server records (`misc_mount.go:190`, `mcp_routes.go:193`,
`get_server_capabilities.go:46`, `get_server_status.go:56`, `check_server_health.go:59`). No second file and no
environment variable: the comment above the constant records why the identity is a literal rather than an override.

## Why it was owed BEFORE the seed
The push that landed today (`origin/main 5b33a8a7` -> `b403e61b`) carries `533d64b6`, which changes seeder behaviour
(`seedVersion` `1.4.2` -> `1.4.3` plus the drift guard), and the marker did not move with it: production answered
`version 0.0.37`, a version already live before that push. Measured read-only at ~16:55Z: `git ls-remote origin
refs/heads/main` = `b403e61b`; `git merge-base --is-ancestor` confirms `533d64b6`, `eec5922b`, `5defdbd2` and
`39b4cfcb` are all in it; `GET https://api.4genthub.com/health` returned `version 0.0.37` with `uptime_seconds` 246 -
so the restart was observable while the release string was not. That is the case the marker exists for, and the seed
sequence (`deploy` -> `/health` shows the new version -> `POST /api/v2/openrig/seat-types/seed` -> re-pin) was
designed to be confirmed by it. Bumping before the seed keeps the rule's own instrument usable for the one operator
action that is not cheaply reversible: the store freezes what a version names.

## Where this marker sits in the batch
The constant's own comment makes the placement a regime question and leaves the regime to the owner. This bump is the
tip of the next batch, above `407c4837` (the C5 record line): under the manual batched push the marker goes LAST, so
`0.0.38` never names a tree that lacks the content it identifies - the seeder change is already on `origin/main`, and
this commit plus `407c4837` are what a push of this batch adds.

## Tests
- `gofmt -l fastmcp/config/version.go` -> no output, exit 0.
- `go build ./...` -> exit 0; `go vet ./...` -> exit 0.
- `go test -count=1 ./fastmcp/config/... ./fastmcp/server/httpapp/...` -> `ok agenthub/fastmcp/config 0.057s`,
  `ok agenthub/fastmcp/server/httpapp 3.829s`.
- `go test -count=1 ./...` -> exit 0, **141 packages ok, 0 FAIL**, 37 no-test-file packages.
- NO TEST FILE IS EDITED, and that is the point rather than an omission: every version-surface assertion compares
  against `config.ReleaseVersion` instead of a literal - `http_health_test.go:175,195,203,210` (the four surfaces
  together), `misc_mount_test.go:58`, `mcp_routes_test.go:291`, and the connection-management parity tests - so the
  value lives in exactly one place, and `grep -rn '0\.0\.37' agenthub_go --include='*.go'` returned that one line
  before this change.

## Not run / limits
The deployed string can only be confirmed after the owner's next deploy: this change is local, and production still
serves `0.0.37` until that push lands. Nothing DB-backed is reachable from this change.
