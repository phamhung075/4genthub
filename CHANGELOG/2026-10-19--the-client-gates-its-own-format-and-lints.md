# The client gates its own format and lints

Client `252c42b` on client main (pin bumped in the same commit). Closes open gate G3 in
`ai_docs/core-architecture/nfr-register.md` (MAINT-04's residual).

## Changed

- `agenthub_client/.github/workflows/ci.yml`: the go job gains a `gofmt -l` check before `go vet`;
  the rust job gains `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings` before
  `cargo test --locked`. The header says why: a format drift or a new clippy finding is the author's
  finding, not something a later reader inherits.
- The drift the gates exposed, fixed rather than allowed: `internal/clientguard/guard_test.go` was
  unformatted; the runtime crate was not rustfmt-clean (`src/frame.rs:69` was the first diff); and
  `cargo clippy --all-targets -- -D warnings` failed with 15 findings, the shape of them
  `matches!` for a two-arm boolean match, `next_back` for `last` on a `DoubleEndedIterator`, and
  `assert!` messages on multi-condition assertions in the tests. No `#[allow]` was added (0 in the
  diff), no dependency changed, no production seam was added.

## Tested

- At `252c42b`: `gofmt -l .` empty, `cargo fmt --check` exits 0, and
  `cargo clippy --all-targets -- -D warnings` exits 0 - run by go-dev, by the reviewer's gate, and
  re-run by the lead in the go-dev worktree before landing.
- `go vet ./...` and `go test ./...` green; `cargo test --locked` green (209 tests).
- Reviewer gate PASS (`qitem-20261019202159`).

## Effect on the register

G3's stated change - the client gains Go and Rust format and lint gates - has landed. The register
row MAINT-04 can drop its "residual" clause on the next reseed, and G3 can be struck once the
register is amended.
