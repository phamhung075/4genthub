# The `sk-` detector: the left boundary decides, not the alphabet

A ruling, not a style change. Both copies of the secret detector carried `sk-[A-Za-z0-9_-]{20,}` with no
left boundary, which redacted a mid-word document name (`task-workflow-and-reporting.md`, because `task-`
supplies `sk-`). go-dev's first fix narrowed the tail to alphanumerics; that trades the observed false
positive for a silent false negative on any real key whose base64url tail carries `_` or `-`.

Ruled shape: `\bsk-[A-Za-z0-9_-]{20,}`. The boundary is the whole of the fix; the alphabet stays.

- Measured 2026-10-18, Go `regexp`: an Anthropic-shaped key
  (`sk-ant-api03-AbCd_EfGhIjKlMn_OpQrStUvWxYz_0123456789AbCd`) matches the ruled form and not the narrowed
  one; the `task-workflow-and-reporting.md` path is false under both boundaried forms; a document named at
  line start `sk-...` stays redacted, which is the accepted over-redaction.
- A fixture must exercise the real alphabet: alphanumeric-only test strings cannot fail on a `_`/`-` tail.

Doc of record: `ai_docs/core-architecture/rigd-boundaries.md` §4.3.1. Acceptance for both copies: the
ruled pattern plus a test asserting the base64url-shaped key redacts and the `task-workflow-...` path does
not.
