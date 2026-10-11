## Seat worktrees are ruled: branch naming, the merge routine, staging and the single home

### Added
- `ai_docs/core-architecture/seat-worktrees.md`: the architect's ruling on the owner's one-worktree-per-seat decision (`qitem-20261010231611-1d0b3910e7407c7f`, board `ca8f57ad`, ruling row `72b889e6`).
  - **The single home** is `team.json`'s seats plus one derivation rule, `SeatWorktree`, beside `clientservices.Obligatory`. Worktree `<roomDir>/wt/<seat>` on `<rig>/<seat>`. The materialized rig directory is rejected as a home.
  - **The submodules** are linked worktrees of the main checkout's submodule repositories. `submodule update` fails on unpushed pins (measured).
  - **The merge routine:** seat tips are merged `--no-ff` into `<rig>/integration`. The reviewer gates the tip, and the verdict names `C`, `M`, each `branch=sha`, the commands run and each result. The lead fast-forwards `main` with `--ff-only C` and re-measures.
  - **Staging:** stage by explicit path and check `git diff --cached --stat`. A pathspec commit is no longer required, and the shared-file rule is dropped.
  - **7.8:** a new `Obligatory` row, `worktrees`, before `seats`. `sync rig` sets each member's `cwd` to its worktree. New verbs `4genteam worktree list|prune RIG`. Prune refuses dirty worktrees and worktrees whose `HEAD` is on no branch.
- The client skill `skills/share/seat-worktree/SKILL.md` carries the same branch naming and merge routine in client commit `55ffdeb`. The parent's `agenthub_client` gitlink moves to it with the pending, gated pin bump. It is not moved here.

### Verified
- On scratch repositories, the architect measured:
  - in a new linked worktree, `git submodule update --init` fails on an unpushed pin with "not our ref";
  - a linked worktree of the submodule repository at the submodule path is accepted, and a seat commit there is visible from the main checkout.
- `git worktree list` shows 26 `/tmp` worktrees, 3 of them prunable. `git branch --list '4genthub*'` is empty.
- No code changed in this commit, so no tests apply.
