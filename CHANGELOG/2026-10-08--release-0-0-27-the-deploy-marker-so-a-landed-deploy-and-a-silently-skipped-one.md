## Release `0.0.27` — the deploy marker, so a landed deploy and a silently-skipped one stop looking identical



### Changed
- `agenthub_go/fastmcp/config/version.go:21`: `ReleaseVersion` `0.0.26` -> **`0.0.27`**. It is the only *code* literal that moves (`git grep -n '0\.0\.26'` returns this line plus two historical CHANGELOG prose lines about the previous release, which are a log and stay), and no surface keeps a copy: `httpapp/http.go:160` declares `const healthVersion = config.ReleaseVersion`, so `/health`, the MCP `initialize` `serverInfo`, the MCP status tool, `register_mcp_client` and the connection-management health route all move with it.
- Why it is on the critical path: the owner's push auto-deploys, and the Docker build context has no `.git` — so no commit id can be embedded and the version string on `/health` is the *only* thing that can confirm a deploy actually landed. Without a bump, a successful deploy and a skipped one are indistinguishable, which is the failure this day was about.

### Verified
- From `agenthub_go` with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`: `gofmt -l fastmcp/config/version.go` prints nothing; `go build ./...` exit **0**; `go vet ./...` exit **0**; `go test ./...` exit **0** — **143 packages ok, 0 failing** — including `TestEveryVersionSurfaceReportsTheOneRelease` (**PASS**), which asserts all four version surfaces report `config.ReleaseVersion` and that the two fossils (`0.0.2c`, `2.1.0`) are gone from every one of them.

### Not in this release
- `GO-2026-5932` (`golang.org/x/crypto/openpgp`) is unchanged and stays severity **UNKNOWN**, invisible to the deploy gate (`severity: CRITICAL,HIGH`): its DB record carries `introduced: 0` with no `fixed` event, and `x/crypto v0.57.0` is already `@latest`. Named here so a later all-severity scan does not read it as a new alarm.
