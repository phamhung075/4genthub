# Seat worktrees: one worktree per seat, and how main changes

Architect ruling, 2026-10-11. Requested by the owner through the lead (`qitem-20261010231611-1d0b3910e7407c7f`, board item `ca8f57ad`); ruling row `72b889e6`. Blocked on this: `622e9faf` (the client implementation, go-dev) and `e66a3e63` (the migration, the lead). The seat-side rules are in the client skill `skills/share/seat-worktree/SKILL.md`. This document is the ruling that skill points to.

**Why.** Every seat edits one shared checkout and commits through one shared index. `2c4582de` absorbed fe-dev's uncommitted TEST-CHANGELOG entry, and `9ebb454f` had to take it out again. The gates run in unowned, detached `/tmp/gate-*` worktrees. `git worktree list` (architect, 2026-10-11) shows 26 worktrees under `/tmp` that no seat owns, three of them prunable.

## 0. The single home

| | A: the room's seat file, `scripts/team/<room>/team.json`, plus one derivation rule in the client | B: the materialized rig, `~/.openrig/agenthub-seats/<room>/rig/{rig.yaml, agents/}` |
|---|---|---|
| Tracked and reviewable | yes | no: `sync rig` generates it, and no seat may edit it by hand |
| Already true today | it defines the five live seats, including the architect | it lists ten members and no architect: stale, finding `072996ad` |
| Sits with the obligatory-service list | the rule sits beside `clientservices.Obligatory` (7.8) | no |

**Ruling: A.** No hand-written worktree list exists anywhere; the list is derived.
- **The data** is the `seats` array of `team.json`, through `seat_type`, which it already carries.
- **The rule** is one function beside `Obligatory` in `internal/clientservices/services.go`. That keeps it in one place with the obligatory list, compiled for 7.8's reason: an operator cannot remove a seat's isolation.

  `SeatWorktree(roomDir, rig, seat, seatType) (path, branch string)`

  | `seat_type` | Path | Branch |
  |---|---|---|
  | `lead`, `developer`, `architect` (a writing seat) | `<roomDir>/wt/<seat>` | `<rig>/<seat>` |
  | `reviewer` | `<roomDir>/wt/<seat>` | none: detached, it never commits |

  In the same function, a room that has a `lead` also gets `<roomDir>/wt/integration` on `<rig>/integration`.

**What moves.** Each member's `cwd` in `rig.yaml` becomes output of this rule. `rigLaunchSpec` (`clientsync/rigverb.go:589`) stops setting it to the room directory. The hand-made variants `rig/rig-claude.yaml` and `rig/rig-omp.yaml`, whose members carry `cwd: .`, are not sources and are retired by re-materializing, never by hand.

**Why `<roomDir>/wt/`.** It is the client's own directory: `rigLaunchSpec` already treats `roomDir` as the one directory no build replaces. The rejected location is a sibling of the repository, which no client code owns.

**Prior art.** Room `4genthub-ab` already runs seats this way: `4genthub-ab/wt/arm-*` on `ab/arm-*` branches.

## (a) Branch naming

| | A: one long-lived branch per seat, `<rig>/<seat>` | B: one branch per work item, `<rig>/<seat>/<item>` |
|---|---|---|
| `up` can create or reuse it without asking anyone | yes, the name is derived | no, the item is not known at launch |
| Shows which item a commit belongs to | the commit message and the board row do | the branch name does |

**Ruling: A.** For example `4genthub-min/go-dev`. The architect's branch is `4genthub-min/architect`. No current branch collides with these names (`git branch --list '4genthub*'` is empty).

**After a land:** a seat whose tip is contained in `main` runs `git merge --ff-only main` in its own worktree before its next edit. The client never moves a seat's branch.

**The submodules.** `agenthub_client` and `.claude` inside a seat's worktree are **linked worktrees of the main checkout's own submodule repositories**, never `git submodule update`.

The reason is measured. The architect ran it on scratch repositories on 2026-10-11: in a new linked worktree, `submodule update --init` clones from the submodule URL and fails on a pin that was never pushed, with `fatal: git upload-pack: not our ref`. This room never pushes, so every pin is unpushed. A `git -C <main>/agenthub_client worktree add <wt>/agenthub_client <gitlink-sha>` placed at the submodule path is accepted by the parent as the submodule. A seat's commit there lands in the shared client repository, where the lead can see it with no fetch.

| Submodule | In a writing seat's worktree |
|---|---|
| `agenthub_client` | on branch `<rig>/<seat>` of the client repository, created at the parent's gitlink |
| `.claude` | detached at the gitlink. It stays out of every commit, as before. |

## (b) The merge routine

| | A: each seat tip fast-forwards `main` directly | B: one integration branch, gated as a whole, then fast-forwarded |
|---|---|---|
| The gated tree is the landed tree | yes | yes |
| Gates needed for N seats ready at once | up to N(N+1)/2: every land moves `main` and stales every other verdict | one per batch |
| Where a conflict is found | the author, at each re-base | the lead, on merge into integration, before the gate |

**Ruling: B.** The routine, run by the lead:

1. **Collect.** The lead merges each ready seat's tip into `<rig>/integration`, in `<roomDir>/wt/integration`, using `git merge --no-ff <sha>` with the SHA the seat named. On a conflict the lead runs `git merge --abort` and returns the item to the author. The author runs `git merge <rig>/integration` on its own branch, resolves the conflict there (requirement 3), and names its new tip. The lead never resolves another seat's conflict.
2. **Gate.** The reviewer checks out the integration tip `C`, detached, in its own worktree and tests a clean export of it (rule 82). **The verdict must NAME:**
   - `C`;
   - the `main` tip `M`, with `git merge-base --is-ancestor M C` true;
   - every seat tip it contains, as `branch=sha`, which equals `git log --first-parent --format=%s M..C`;
   - the commands run and each result;
   - PASS or FAIL.
3. **Land.** The lead re-measures `git rev-parse <rig>/integration` = `C` and `git rev-parse main` = `M`. If either differs, the verdict is stale and the lead goes back to step 2. Then, in the main checkout, the lead runs `git merge --ff-only C`, giving the SHA and not the branch name, so a moved branch cannot slip in.
4. **Re-measure.** `git rev-parse main` = `C`, and `git status --porcelain --untracked-files=no` prints nothing.
5. **Record.** The lead writes `landed C (verdict <qitem>)` into each contained item's board row, then tells each contained seat to fast-forward.
6. **A failed gate.** The lead resets `<rig>/integration` to `main` (`git reset --hard M` in the integration worktree, which is the lead's own unpublished branch) and re-collects without the failing tip.

**Where the merged candidate set lives:** in git, as `git log --first-parent M..C` on `<rig>/integration`. One merge commit per seat tip, so nothing is listed by hand. Once landed, the same log on `main` is the history.

**The main checkout** (`~/__projects__/4genthub`) receives only step 3. No seat edits it, and the lead does not edit it either. Its tracked tree must be clean before the first land. That cleanup belongs to `e66a3e63`: each uncommitted path goes to its author's branch, and nothing is discarded unread.

**Client changes** land the same way one level down. A seat's client commits are on `<rig>/<seat>` in the shared client repository. The parent commit that moves the `agenthub_client` gitlink is an ordinary commit on the same seat branch, gated with it.

## (c) Staging instead of pathspec commits

The pathspec commit existed to keep one seat's commit from taking another seat's changes out of the shared index. With a private index per worktree, that reason is gone.

| Rule | Now |
|---|---|
| Stage by explicit path: `git add -- <paths>`, and `git add -N` for a new file | **stays** |
| Before every commit: `git diff --cached --stat` lists only your own paths | **new** |
| `git add -A`, `git add .`, `commit -a` | **forbidden, unchanged** |
| `CLAUDE.md`, `.claude`, `agenthub_go/seatcheck` and any gitlink you were not asked to move stay out of commits | **stays** |
| `git commit -- <paths>` as the isolation tool | **no longer required.** A plain `git commit` after the staging check is allowed. |
| "Do not name a shared file that carries another seat's uncommitted change" | **dropped**: no other seat has changes in your tree |
| No push, no `--amend`, no rebase of a branch that is not yours | **unchanged** |

## Composition with 7.8 and the CLI

- **A new `Obligatory` row, `worktrees`.** Scope `rig`; RestartBy `none`; start order `daemon`, `gate`, **`worktrees`**, `seats`, and so on, because a seat's `cwd` must exist before it launches.
  - **`Start`**, for each seat from `team.json`:
    - create the path from `SeatWorktree` if it is missing (`git worktree add -b <branch> <path> main`, or `--detach` for the reviewer);
    - add the two submodule worktrees;
    - link `.env` into it, through the existing `rigLinkProviderKey`. `.env` is ignored by `.gitignore:169`.

    An existing worktree on the right branch is reused. A path that exists on another branch, or is not a worktree, is **refused and named**. Nothing is overwritten.
  - **`Check`**: every derived path is registered in `git worktree list`, on its branch, with both submodules present.
- **`sync rig`**: sets each member's `cwd` to `SeatWorktree(...)`. The path is deterministic, so sync can write it before the worktree exists.
- **New verbs:**
  - `4genteam worktree list RIG` prints the derived worktrees and every other entry of `git worktree list`, labelled `foreign`.
  - `4genteam worktree prune RIG` removes only `/tmp/wt-*`, `/tmp/gate-*` and entries git marks `prunable`, then runs `git worktree prune`. Removal is `git worktree remove` without `--force`, so a dirty worktree is named and left in place. A worktree whose detached `HEAD` is on no branch and not in `main` is **refused and named**: removing it deletes its reflog, which is the only reference to that commit. The case is real: `06410692` is on no branch today.
  - Anything else foreign, for example `~/__projects__/4genthub-urgent-subtask-details`, is listed and never removed.
- **`doctor`**: the `worktrees` row. A foreign count above zero is a detail on that row, not a failure.
- **7.10**: no repair verb touches a worktree.

## Facts the lead should know (none are ruled here)

- `.claude` is recorded at `b376accb` and checked out at `6e8bf881` in the main checkout. A new seat worktree gets the recorded hooks (`b376accb`), not the checked-out ones, until someone lands that change.
- The architect seat is `claude-code` and is missing from the materialized rig (`072996ad`). Its worktree follows the same rule, and how it is launched belongs to that item.
- An ignored file is not in a new worktree. The frontend seat installs `node_modules` in its own worktree, and the client does not.

## Tests the implementation must pass (`622e9faf`)

| Case | Expected |
|---|---|
| `team.json` with lead, developer, reviewer and architect | four seat paths and `integration`; the reviewer has no branch |
| `Start` run twice | the second run changes nothing |
| a derived path that exists on another branch | refused, named, untouched |
| prune over `/tmp/wt-x` (clean), `/tmp/gate-y` (dirty) and `/tmp/wt-z` (`HEAD` on no branch) | x removed; y and z named and kept |
| a fixture parent repository whose submodule pin was never pushed | `Start` succeeds, and `git -C <wt> submodule status` shows the pin |
| `sync rig` | every member's `cwd` is its derived path |
