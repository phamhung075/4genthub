## Release `0.0.29` — the deploy marker, because production already reports `0.0.28`

### Changed
- `agenthub_go/fastmcp/config/version.go:21`: `ReleaseVersion` `0.0.28` -> **`0.0.29`**. It is the only *code* literal that moves: `git grep -n -E '0\.0\.28'` returns that line and four dated prose records (`CHANGELOG.md:373` and the `0.0.28` marker entry at `:749`/`:752`, `README.md:542` and `:665`), which are a log and stay. **Confirmed by reading the file rather than assuming:** `agenthub_go/fastmcp/server/httpapp/http.go:160` declares `const healthVersion = config.ReleaseVersion`, so `/health` — and the MCP surfaces the `0.0.28` entry enumerates from the same constant — moves with this one string. The `http.go` constant was NOT edited.
- `README.md:542` and `:665` read "the tree's release literal reads `0.0.28`" as a **dated 2026-10-09 measurement**, so they are now one release behind the tree. Left alone deliberately, the same way the `0.0.28` entry left its predecessor's lines: this commit moves the marker, and a new number belongs to the next README measurement pass — this line is the pointer for whoever runs it.

### Why it is on the critical path
- **Eleven commits sat above `origin/main` (`5d63e913`) with `ReleaseVersion` still reading `0.0.28`** — the value production already reports (measured live by the lead, 2026-10-09) — so pushing the batch as it stood would have auto-deployed it under a number that could not distinguish it from the deploy before. The Docker build context carries no `.git`, so this string is the only thing that confirms a deploy landed.
- **It is the LAST commit in the set**, and every one of the eleven above it carries a reviewer APPROVE: nothing lands on top of it before the owner pushes. That is the rule the constant's own comment states at `version.go:20` — "if a commit lands after the bump, the bump moves to it or the deploy waits".

### Verified
- **The tip was re-measured before the bump, not recalled:** `git rev-parse --short HEAD` -> `499abf30`; `git rev-list --count origin/main..HEAD` -> `11`; `git rev-parse --short origin/main` -> `5d63e913`.
- From `agenthub_go`, with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`: `gofmt -l fastmcp/config/version.go fastmcp/server/httpapp/` printed nothing; `go vet ./fastmcp/config/... ./fastmcp/server/httpapp/...` exit **0**; `go test -count=1 ./fastmcp/config/... ./fastmcp/server/httpapp/...` exit **0** — `ok agenthub/fastmcp/config 0.054s`, `ok agenthub/fastmcp/server/httpapp 1.013s`.

### Found by
- The lead, while assembling the push ask (row `83216474`); landed by context-dev because the seat that owns Go work is down (go-dev is detached on a harness-resume failure).
