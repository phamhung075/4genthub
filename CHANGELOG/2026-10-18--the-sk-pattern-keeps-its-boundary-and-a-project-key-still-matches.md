## The `sk-` pattern keeps its boundary, and every real key shape still matches

`sk-[A-Za-z0-9_-]{20,}` had no left boundary, so `task-workflow-and-reporting` (which carries
`sk-workflow-and-reporting`, 22 body characters) read as a credential and `secretscan.Contains`
refused it — two refusals reported on 2026-10-18. The pattern is now
`\bsk-[A-Za-z0-9_-]{20,}`.

The `\b` is the whole fix: inside `task-workflow-and-reporting.md` the `sk` is preceded by `a`, so
there is no word boundary and nothing matches. The body alphabet is NOT narrowed. A first attempt
required the tail to be alphanumeric and was measured wrong on this machine before it shipped: the
delivered `\bsk-(?:[A-Za-z0-9]+-)*[A-Za-z0-9]{20,}` does not match
`sk-ant-api03-AbCd_EfGhIjKlMn_OpQrStUvWxYz_0123456789AbCd`, which `\bsk-[A-Za-z0-9_-]{20,}` does.
Underscores are part of the body of real Anthropic keys.

The cost is stated rather than hidden: a doc name that begins a line (`sk-workflow-and-reporting.md is
the doc`) still matches and is over-redacted. A boundary cannot tell that word from a key, and losing
real keys is the worse failure.

### Changed
- `agenthub_go/fastmcp/seat_management/domain/secretscan/secretscan.go`: the `sk-` detection pattern
  gains the left boundary; the body alphabet stays as it was.
- `agenthub_go/fastmcp/seat_management/domain/secretscan/redact.go`: the labelled `sk` pattern is the
  same line, because the package's contract is that detection and redaction never disagree about what
  a secret looks like.
- `agenthub_go/fastmcp/seat_management/domain/secretscan/testdata/scan_cases.json`: `openai-project-key`,
  `anthropic-key` and `anthropic-key-with-underscores` stay `has_secret=true`; the doc name inside a
  longer word is `false`; the doc name at a line start is `true` (the accepted over-redaction).

### Testing
- RUN: `cd agenthub_go && go test ./fastmcp/seat_management/domain/secretscan/...` = ok.
- RUN: `cd agenthub_go && go test -count=1 ./...` = all packages ok.
- Pattern measured with a throwaway `go run` over five shapes: boundary-less `old=true` for all six
  strings; `\bsk-[A-Za-z0-9_-]{20,}` gives true for the three key shapes, false for the doc name in a
  longer word, true for the line-start doc; the alnum-only tail gave false for the underscored key.
- `redact_cases.json` is a parity fixture generated from the original Python scrub script, so it is
  not hand-edited; its `sk` expectations still pass, because the pattern matches the same span of
  `sk-abcdefghijklmnopqrstuvwxyz0123456789ABCD`.

### Not carried here
- `agenthub_client/internal/secretscan` takes the same line, fixtures and redaction in the commit that
  follows this one, so the copies do not disagree.
- The Python bridge scrubber that shares `scan_cases.json` is not in this tree; its own pattern needs
  the same boundary, and the fixture's `sk-hyphenated-filename` case is what will tell.
