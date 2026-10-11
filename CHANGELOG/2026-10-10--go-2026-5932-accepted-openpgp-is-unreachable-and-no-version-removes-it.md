# GO-2026-5932 accepted with a written justification: `openpgp` is unreachable, and no version can remove it

The lead's ruling of 2026-10-10: **accept the finding, do not change `bcrypt`.** This entry is the
justification, so the next scan's reviewer reads a decision rather than re-deriving one.

## The finding

`go run golang.org/x/vuln/cmd/govulncheck@latest -show verbose ./...` on this tree:

```
Vulnerability #1: GO-2026-5932
    The golang.org/x/crypto/openpgp package is unmaintained, unsafe by design,
    and has known security issues
  Module: golang.org/x/crypto
    Found in: golang.org/x/crypto@v0.57.0
    Fixed in: N/A
Your code is affected by 0 vulnerabilities.
This scan also found 0 vulnerabilities in packages you import and 1 vulnerability in
modules you require, but your code doesn't appear to call these vulnerabilities.
```

## Why it cannot be reached

**0 vulnerabilities in the code and 0 in the packages we import** — the entry is a *module-level* one,
and the scanner itself files it under "modules you require, but your code doesn't appear to call these".
No package in the tree imports the affected one: `grep -rn "golang.org/x/crypto" --include=*.go .`
(excluding the module cache) returns a single consumer, `fastmcp/auth/domain/services`, and it imports
`golang.org/x/crypto/bcrypt`. Nothing imports `openpgp`, and nothing can: it is a deprecated,
unmaintained package that the Go team keeps only for history.

## Why no dependency bump can clear it — three measurements

1. **There is no fixed version to move to.** The advisory's own `Fixed in:` is `N/A`.
2. **The latest release still ships the package.** v0.58.0 — the newest available — was downloaded and
   its extracted module listed: it contains `bcrypt` **and** `openpgp`, exactly as v0.57.0 does. So the
   refresh in `6bf538d1` (v0.57.0 → v0.58.0) moved it for currency, not for this finding.
3. **The module cannot leave the graph.** `go mod why -m golang.org/x/crypto` answers
   `agenthub/fastmcp/auth/domain/services` → `golang.org/x/crypto/bcrypt`. Dropping the module would
   mean replacing bcrypt — a rewrite of the password-hashing path to satisfy a module-level entry no
   code path can reach, which is why the lead ruled against it.

## What this entry is, and what it is not

- **It is the decision of record.** This repository already carries one documented acceptance, in
  `.trivyignore` (CVE-2024-23342: no fix available, mitigating context, risk assessment, the bare id).
  This entry follows that form.
- **It is not a `.trivyignore` line, deliberately.** The scan step that would read one is no longer in
  this repository: `.github/workflows` holds only `ci.yml`, and `production-deployment.yml` — the only
  Trivy step — was deleted by `1c7b6631`. If a scan returns, this entry is the justification to carry
  into it; adding an ignore line now would configure a reader that does not exist.
- **It changes no code.** No dependency moved for this finding (moving cannot help it), no pin was
  added, and `bcrypt` is untouched.
