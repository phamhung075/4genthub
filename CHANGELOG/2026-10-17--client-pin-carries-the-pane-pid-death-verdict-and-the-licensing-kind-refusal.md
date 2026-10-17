## Changed

- `agenthub_client` pin moves `131796e` -> `f5f102d` (2 commits), landed by fast-forward so the reviewer's gated sha is the landed sha (`f2c0765c`). Nothing pushed; the push is the owner's.

### Fixed

- An unreadable pane pid is no longer read as a dead pane: the pane's own death verdict is consulted instead of trusting the pid alone, so a live pane whose pid file exists but cannot be read is not declared dead (`dce05c8`, `rust/agenthub-runtime/src/pty/mod.rs`, `supervisor/mod.rs`, `hooks/mod.rs`).
- The "no declared link" refusal names the kind that would license the send, instead of refusing without telling the sender what to declare (`f5f102d`).

Validated: gated PASS by the reviewer at `f5f102d` on the rebased lane `4genthub-min/lane-rebase` - 159/0 tests, `go vet` rc 0, `go test` 32 ok, each half falsified red independently, and `131796e` is an ancestor of `f5f102d` so the fast-forward carried exactly the gated bytes. 9 files, +547/-57.
