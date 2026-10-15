## Run 5's preconditions are recorded on the board, landed so the plan branch can fast-forward

### Changed

- `NEXT-GEN2.md` gains the lead's 21:2xZ row **"RUN 5'S PRECONDITIONS, ALL MEASURED"** — the two commits the room legs cannot produce a verdict without (`69006b5` "a replaced rail is the rail the daemon uses" on `4genthub-min/rail-per-request`, and `c0ffbe8` "hold a refused send and publish the turn it was refused in" on `4genthub-min/refused-send`), with the lead's measured reading of the rail test at its tip.

### Why this landed as its own commit

- The line was sitting **uncommitted** in main's worktree (one added line, no removals - measured with `git diff -U0 -- NEXT-GEN2.md`), and it is the lead's own content: the plan branch `4genthub-min/architect-nextgen2-measured` (`1da88594`) does **not** carry it (`git show 1da88594:NEXT-GEN2.md | grep -c "RUN 5'S PRECONDITIONS"` -> 0), so a fast-forward would neither carry nor preserve it.
- Landing it by pathspec clears the first of the two refusals the architect's `git merge --ff-only 1da88594` hit in main's worktree ("local changes would be overwritten" on `NEXT-GEN2.md`). The second - the untracked **stale** `CHANGELOG/2026-10-14--the-plan-matches-the-running-system.md` (62 lines, the old generation of the entry the branch carries at 161 lines) - was retired by rename to `.obsolete`, which is reversible and deletes nothing.
- Nothing else in main's worktree was touched: the uncommitted `D agenthub_go/NEXT_GEN.md`, the `agenthub_client` submodule state and `scripts/mem-sampler.sh` are other seats' work.

### Verified

- Before committing: `git diff -U0 -- NEXT-GEN2.md` = 1 added line, 0 removed; `git status --short` showed no other modification to the file.
- After committing: `git show --numstat --format=` names exactly the two paths this entry claims, and `git status --short` still shows the other seats' paths untouched.
- The plan branch was still **not** a fast-forward of main when this landed (main had moved to `44211d6b`, the branch base was `6085fd35`): the architect re-rebases before landing, as the lead's answer to `qitem-20261014214149-4390c24b675e` says.
