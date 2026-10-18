# The client copy takes the same sk- boundary

The server copy's scanner had no left boundary, so `clientdecide` refused a brief that named
`ai_docs/agent-system/task-workflow-and-reporting.md` — `decide.go:109` runs
`secretscan.Contains(summary|detail)` and answered `usageError` at `:110`, because
`sk-workflow-and-reporting` is 22 body characters.

## What changed

- `agenthub_client/internal/secretscan/secretscan.go` and `redact.go`: the sk pattern becomes
  `\bsk-[A-Za-z0-9_-]{20,}` in both the detector and the redactor — the same line the server copy
  carries. The boundary is the fix; the body alphabet is unchanged, because an alnum-only tail was
  measured not to match `sk-ant-api03-AbCd_EfGhIjKlMn_OpQrStUvWxYz_0123456789AbCd`.
- `agenthub_client/internal/secretscan/testdata/scan_cases.json`: the same five cases the server
  fixture carries — `openai-project-key`, `anthropic-key` and `anthropic-key-with-underscores` as
  secrets; `sk-hyphenated-filename` not a secret; `sk-hyphenated-filename-line-start` a secret (the
  accepted over-redaction).
- `agenthub_client/internal/clientdecide/decide_test.go`: one regression test runs the real refusal
  path with a summary and a detail that name the doc and asserts the ask is decided (exit 0, one Jev
  call), not refused as a credential.

## Copy parity, measured

The three shared files are compared against the server copy's blobs in the commit below this one
(`084b3faa`): `secretscan.go` and `testdata/scan_cases.json` byte-identical; `redact.go` identical on
the pattern line and still different elsewhere by the client's pre-existing `RedactKnownValues`
refactor (unchanged here).

## Runs at this change

- `cd agenthub_client && go test -count=1 ./...` = exit 0.
- `go vet ./internal/secretscan/ ./internal/clientdecide/` clean.
- `TestContainsMatchesSharedFixture`, `TestRedactMatchesTheReferenceImplementation`,
  `TestRedactCoversWhatTheSharedFixtureDoesNot`, `TestRedactFailsClosed`: pass.
- `TestABriefThatNamesAHyphenatedDocIsNotACredential`: pass (one Jev call on the stub).

Client branch `4genthub-min/client-secretscan-boundary`: `ccc1acc`.
