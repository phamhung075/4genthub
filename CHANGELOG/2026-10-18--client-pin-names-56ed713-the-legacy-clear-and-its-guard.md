# The client pin names `56ed713`: the detached legacy is cleared, and an unreachable HEAD is refused

`agenthub_client` moves `287f7bc` -> `56ed713`, the architect's reversed reading (`70aaa0fe`, doc row
"the migration covers every derived seat") carried to code and tested:

- `c9dfee7` - `clearStaleClientWorktrees` visits every derived seat, the skip on an empty `Branch`
  gone, so the reviewer's clean detached `<seat>-client` at the pin is removed and named instead of
  being left as a second client location.
- `56ed713` - the guard from `prune`: a detached `<seat>-client` whose HEAD the client repository's
  `main` does not contain is **refused and named**, the seat is blocked and nothing is placed for it
  (created path included), because removing it would delete the only reference to that commit.

Test ledger: the hub's `ade5e701` (`TestEnsureClearsADetachedLegacyClientWorktree`) and `1743785e`
(`TestEnsureRefusesToClearADetachedLegacyOnNoBranch`); both are red on the tip before them and green
on the pin. Gate: `qitem-20261018122638-a3e2af7f2112` PASS on `56ed713`.

The pin is local: `main` here is not pushed (owner's approval governs the push).

## The build stamp: build.sh reads the checkout it stands in

`scripts/build.sh` builds **in place** - `cd $root; go vet ./...; go test ./...; go build -o
$bin_dir/.4genteam.new ./cmd/4genteam` - so Go's VCS stamping reads `$root/.git` and
`git status` of that working tree. Untracked files there (`ai_docs/reports-status/` in the hub's
`agenthub_client` checkout, left as someone's evidence) stamp `vcs.modified=true` and a `+dirty`
module version into the binary, even though the pin is exact. The script has no clean-export step.

Measured on the pin: built in place, `vcs.revision=56ed713b80c4` **`vcs.modified=true`**
(`...+dirty`); built from `git clone --no-hardlinks agenthub_client tmp/` at `56ed713` (clean tree,
`dirty=0`), `vcs.revision=56ed713b80c4` **`vcs.modified=false`**, which is what is installed. The
rust half is untouched by this pin (`git diff 287f7bc..56ed713 -- rust` is empty), so only the Go
binary needed the clean-clone build.
