## The migration's subject is the writing seats, and the reviewer is out of it on purpose

### Ruled

- `ai_docs/core-architecture/seat-worktrees.md` - the migration (`clearStaleClientWorktrees`) removes the
  pre-derivation `<seat>-client` path for derived **writing** seats only. A writing seat's legacy holds a
  branch its link needs and a branch is checked out in one worktree per repository, so the legacy is what
  makes the link impossible. A reviewer's link is detached, so a stale `reviewer-client` beside it
  obstructs nothing: `Start` neither reads nor removes it, `Check` passes on the derived path, and the
  leftover is foreign in `worktree list`; removing it is the operator's, under `worktree prune`'s rule that
  a detached `HEAD` on no branch and not in `main` is refused rather than deleted.

### Measured 2026-10-18, live room after the migration

- `wt/architect-client` and `wt/fe-dev-client` cleared; the links placed on `4genthub-min/architect-client`
  (`2eeae5d`) and `4genthub-min/fe-dev-edit-yield` (`51f614b`).
- `wt/reviewer-client` left detached at `287f7bc`; the reviewer's derived link is detached at the pin
  `7034a80`.
- `heal --check` clean, and a second `up` prints kept for all six paths.

### Rejected

- Extending the subject list to the reviewer: one more deletion path, with the reachability guard, for a
  checkout that blocks nothing. The migration removes what obstructs; it is not the room's cleaner.
