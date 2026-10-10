## Release `0.0.33` — the deploy marker, because production and `origin/main` both report `0.0.32`

### Changed

- `agenthub_go/fastmcp/config/version.go:21`: `ReleaseVersion` `0.0.32` -> **`0.0.33`**. One *code* literal moves and nothing else: after the bump `git grep -n -E '0\.0\.32' -- '*.go'` returns **nothing**, and `git grep -n -E '0\.0\.33' -- '*.go'` returns that one line. **Confirmed by reading the tree rather than assuming:** `fastmcp/server/httpapp/http.go:160` declares `const healthVersion = config.ReleaseVersion` and `:173` sets `/health`'s `version` from it, `misc_mount.go:190` puts the same constant on the MCP initialize `serverInfo`, and `http_health_test.go:99` asserts `/health` against `healthVersion` myself — so this one string moves every surface that advertises the release. No other file was edited.
- `CHANGELOG/README.md` — an index row, alongside the one the `0.0.30` entry has. `README.md` itself is not touched: its marker cell was de-numbered deliberately so no reading rots there.

### Why it is a requirement rather than tidiness

- **The requester measured that production and `origin/main` both report `0.0.32`:** `GET https://api.4genthub.com/health` answers `0.0.32`, and `git show origin/main:agenthub_go/fastmcp/config/version.go` line 21 reads `const ReleaseVersion = "0.0.32"` at tip **`96d37946`**. Both readings are the lead's, from the row that ordered this.
- **Measured here rather than relayed:** `git rev-list --count origin/main..HEAD` -> **24** at `2887e5ab`, the commit under this one, and before the bump the only Go literal in the tree was the line above (`git grep -n -E '0\.0\.32' -- '*.go'` returned `version.go:21` and nothing else). So twenty-four commits would have shipped carrying the same string as the deployed release, and `/health` could not have told anyone whether the deploy had happened. The failure is silent, which is why this is required.
- **Deploy confirmation stays with the principal, who pushes.** The Docker build context carries no `.git`, so this string is the only thing that confirms which release a container runs; nothing here pushes, tags or deploys.

### The bump is deliberately NOT the last commit above `origin/main`

`version.go`'s own comment says the bump is "the LAST commit in the set before a deploy is requested, so the string can never cover a tree that lacks the content it marks". The lead ordered this bump mid-batch with that rule in view, and rule 71 in `NEXT_GEN.md` says the record states such a deviation rather than glossing it — so here it is. The number's job in this batch is to be **distinguishable from the deployed `0.0.32`**, and it is: `0.0.33` cannot be produced by a container built before this commit. What the ordering gives up is exact coverage: if commits land above this one and the principal pushes that larger tree, `/health`'s `0.0.33` will name a tree at or below the one running, not the exact tip. That is the deviation, stated rather than implied.
