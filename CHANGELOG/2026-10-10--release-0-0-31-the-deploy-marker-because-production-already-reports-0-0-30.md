## Release `0.0.31` — the deploy marker, because production already reports `0.0.30`

### Changed
- `agenthub_go/fastmcp/config/version.go:21`: `ReleaseVersion` `0.0.30` -> **`0.0.31`**, as the last commit of
  the gated batch. It is the only *code* literal that moves: `git grep -n '0\.0\.30' -- '*.go'` (build caches
  excluded) returns **nothing at all** after the bump, and the `0.0.30` text remaining in this tree is
  CHANGELOG prose, which is a log and stays. **Confirmed by reading the file rather than assuming:**
  `agenthub_go/fastmcp/server/httpapp/http.go:160` declares `const healthVersion = config.ReleaseVersion`
  (`:156`–`:157` say it is the same value every other version surface reports) and `:173` sets `/health`'s
  `version` from it, so `/health` — and the MCP surfaces built from the same constant — move with this one
  string. The `http.go` constant was NOT edited.
- `README.md:542` and `:665` carry dated release measurements — the tree's literal as `0.0.28`, `origin/main`
  (`07a66f8f`) as `0.0.27`, and a production read of `0.0.22` dated 2026-10-06 — which this bump makes stale
  by three. Left alone deliberately, the way the `0.0.30` entry left its predecessor's lines: a new number
  belongs to the next README measurement pass, and this file is one of the four paths the principal is
  editing in the same worktree, so it is not this seat's to move.

### Why it is on the critical path
- **Production already reports `0.0.30`, read first-hand rather than recalled:** `GET
  https://api.4genthub.com/health` (read-only; HTTP/2 200, `server: nginx`, `date: Sat, 10 Oct 2026
  09:00:54 GMT`) answers `{"status":"healthy",…,"version":"0.0.30",…}`, and its
  `connections.uptime_seconds` of `2974.67` puts that container up since about **08:11:19Z**. The Docker
  build context carries no `.git`, so this string is the only thing that confirms a deploy landed; pushing
  this batch without the bump would auto-deploy it under the number the deploy before already reports.
- **It is the LAST commit in the set.** 18 commits sat above `origin/main` (`e6a5a4aa`) when the bump was
  written, and per the lead's board every one of them carries a reviewer verdict; nothing lands on top of
  the bump before the owner pushes. That is the rule the constant's own comment states at `version.go:20` —
  "if a commit lands after the bump, the bump moves to it or the deploy waits".

### Verified
- **The tip was re-measured immediately before the commit rather than recalled:** `git rev-parse --short
  HEAD` -> `2a3ac86f`, `git rev-parse --short origin/main` -> `e6a5a4aa`, `git rev-list --count
  origin/main..HEAD` -> **18**; with the bump the batch is **19**. The worktree held exactly the four paths
  that are the principal's own work in progress (`.claude`, `.env.sample`, `README.md`,
  `agenthub_go/cmd/agenthubclient/main.go`), and nothing else was staged.
- From `agenthub_go`, with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`: `gofmt -l fastmcp/config/version.go
  fastmcp/server/httpapp/` printed nothing; `go vet ./fastmcp/config/... ./fastmcp/server/httpapp/...` exit
  **0**; `go test -count=1 ./fastmcp/config/... ./fastmcp/server/httpapp/...` exit **0** — `ok
  agenthub/fastmcp/config 0.052s`, `ok agenthub/fastmcp/server/httpapp 1.084s`.
- **The whole Go tree at the same tip, measured separately rather than inferred from two packages:** `go vet
  ./...` exit **0** and `go test -count=1 ./...` exit **0** across **141 packages, 0 FAIL**, taken at
  `2a3ac86f` — the commit this bump sits on.

### Found by
- The lead's order on the seal, after the reviewer's verdict on `d5567275`; landed by go-dev.
