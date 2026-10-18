## The migration's subject is every derived seat, the reviewer included

### Ruled

- `ai_docs/core-architecture/seat-worktrees.md` - the migration (`clearStaleClientWorktrees`) removes the
  pre-derivation `<seat>-client` path for **every** derived seat. A writing seat's legacy holds a branch its
  link needs, so it makes the link impossible; a reviewer's holds no branch, but it is still a second
  checkout of the client repository, and two checkouts at different commits are the ambiguity the ruling
  exists to remove.
- The one removal the rule forbids: a detached legacy whose `HEAD` is on no branch and not in `main` is
  **refused and named** - the same rule `worktree prune` applies (`internal/clientworktree/verbs.go:283`).
  Removing it would delete the only reference to that commit.

### Rejected (my first reading, an hour earlier)

- Leaving the reviewer out because its legacy "obstructs nothing". It obstructs nothing *for the link*; it
  does produce two working copies of one repository at different commits for one seat. Measured on the live
  room: `wt/reviewer-client` detached at `287f7bc`, the derived link detached at the pin `7034a80`.

### Measured 2026-10-18

- The live migration, with client `287f7bc`: `wt/architect-client` and `wt/fe-dev-client` cleared, their
  links placed on `4genthub-min/architect-client` (`2eeae5d`) and `4genthub-min/fe-dev-edit-yield`
  (`51f614b`); `wt/reviewer-client` left in place because `clearStaleClientWorktrees` skips a seat with no
  branch (`worktree.go:377`); `heal --check` clean, second `up` prints kept for all six paths.
- Hub `ade5e701` (go-dev, Task `2d601326`) added the `TEST-CHANGELOG.md` entry for the detached case ahead
  of the client: at client `287f7bc` neither `TestEnsureClearsADetachedLegacyClientWorktree` nor the dropped
  skip exists. The skip and that test are the implementation's remainder.
