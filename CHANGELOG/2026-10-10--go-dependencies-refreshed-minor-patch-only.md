# Go dependencies refreshed to their latest minor/patch, and the one finding no bump can clear

## What moved (go.mod / go.sum, explicit paths)

`go get -u ./...` then `go mod tidy`, in `agenthub_go`:

| module | from | to | why |
|---|---|---|---|
| `github.com/dlclark/regexp2` | v1.11.5 | **v1.12.0** | latest minor; nothing we build required a higher pin |
| `github.com/jackc/puddle/v2` | v2.2.2 | **v2.2.3** | latest patch of pgx's own connection pool |
| `golang.org/x/crypto` | v0.57.0 | **v0.58.0** | latest minor; see the finding below — this does NOT clear GO-2026-5932 |
| `golang.org/x/sync` | v0.23.0 | **v0.24.0** | latest minor |
| `golang.org/x/text` | v0.42.0 | **v0.43.0** | latest minor |

No major-version bump anywhere: every move stays inside its current major, and `go 1.26.0` / `toolchain go1.26.8` are unchanged.

## What did NOT move, and why (measured, not assumed)

`go list -m -u all` reports fifteen modules newer than the ones in the build list. Ten stayed:

`github.com/creack/pty` v1.1.9→v1.1.24, `github.com/kr/pretty` v0.3.0→v0.3.1, `github.com/rogpeppe/go-internal` v1.13.1→v1.16.0, `github.com/stretchr/objx` v0.1.0→v0.5.3, `github.com/stretchr/testify` v1.11.1→v1.12.1, `golang.org/x/mod` v0.41.0→v0.42.0, `golang.org/x/net` v0.58.0→v0.61.0, `golang.org/x/sys` v0.48.0→v0.49.0, `golang.org/x/tools` v0.49.0→v0.51.0, `golang.org/x/term` v0.46.0→v0.47.0.

`go get -u ./...` upgrades the modules the packages we build and test actually require; these ten are in the module graph without anything we compile needing the newer version, so the toolchain left them at the version the requirer pins. Moving them would mean `go get <module>@latest` on modules no build target compiles — a version change with no reason, which the row's own rule forbids. **No advisory attaches to any of them**: the scan below reports exactly one finding in the whole graph.

## The finding no dependency bump can clear: GO-2026-5932

`go run golang.org/x/vuln/cmd/govulncheck@latest -show verbose ./...` at this tree:

```
Vulnerability #1: GO-2026-5932
    The golang.org/x/crypto/openpgp package is unmaintained, unsafe by design,
    and has known security issues
  Module: golang.org/x/crypto
    Found in: golang.org/x/crypto@v0.57.0
    Fixed in: N/A
Your code is affected by 0 vulnerabilities.
```

Three measurements say no bump, and no version pin, can clear it:

1. **There is no fixed version to move to.** The advisory's own `Fixed in:` is `N/A` — `openpgp` is deprecated and unmaintained, so every release carries it.
2. **The latest release still ships the package.** I downloaded v0.58.0 and listed the extracted module: it contains both `bcrypt` and `openpgp`, exactly as v0.57.0 does. So the upgrade in this commit narrows the gap but cannot remove the package from the graph.
3. **The module cannot leave the graph.** `go mod why -m golang.org/x/crypto` answers `agenthub/fastmcp/auth/domain/services` → `golang.org/x/crypto/bcrypt`. Dropping x/crypto would mean replacing bcrypt, which is a design change, not a dependency bump.

And the finding is **not reachable by any code path**: govulncheck reports 0 vulnerabilities in the code and 0 in the packages we import; the single entry sits under "modules you require, but your code doesn't appear to call these vulnerabilities".

So the decision this row cannot make is the gate's: accept GO-2026-5932 with a written justification (no fixed version exists; the package is never imported), or change the password-hashing dependency. Neither is a bump, and I have made neither.

## Verification

From `agenthub_go` with `GOCACHE`/`TMPDIR` in-tree:

- `gofmt -l cmd fastmcp internal` printed nothing; `go build ./...` → BUILD_OK; `go vet ./...` → VET_OK.
- `go test ./...` → **zero failures** (`grep -cE '^(FAIL|--- FAIL)'` = 0; no `panic:`), run twice.
- The DB-backed suites were then run for real, because this bump moves `pgx`'s pool (`puddle`): `bash tools/testpg/start.sh` provided `AGENTHUB_TEST_PG_URL`, and `go test -count=1 ./fastmcp/server/httpapp/ ./fastmcp/task_management/infrastructure/database/ ./fastmcp/session_stream/` → **ok / ok / ok**. One DB case re-run verbosely to prove it RAN rather than skipped: `TestMCPStatusCallIsAttributedToTheSeatThatMadeIt` → `--- PASS (1.80s)`.
- `go list -m -u all` and `govulncheck` outputs above are the measurement the row asked for.

Nothing pushed.
