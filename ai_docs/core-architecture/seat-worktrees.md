# Seat worktrees: one worktree per seat, and how main changes

Architect ruling, 2026-10-11. Requested by the owner through the lead (`qitem-20261010231611-1d0b3910e7407c7f`, board item `ca8f57ad`); ruling row `72b889e6`. Blocked on this: `622e9faf` (the client implementation, go-dev) and `e66a3e63` (the migration, the lead). The seat-side rules are in the client skill `skills/share/seat-worktree/SKILL.md`. This document is the ruling that skill points to.

**Why.** Every seat edits one shared checkout and commits through one shared index. `2c4582de` absorbed fe-dev's uncommitted TEST-CHANGELOG entry, and `9ebb454f` had to take it out again. The gates run in unowned, detached `/tmp/gate-*` worktrees. `git worktree list` (architect, 2026-10-11) shows 26 worktrees under `/tmp` that no seat owns, three of them prunable.

## 0. The single home

| | A: the room's seat file, `scripts/team/<room>/team.json`, plus one derivation rule in the client | B: the materialized rig, `~/.config/4genthub/agenthub-seats/<room>/rig/{rig.yaml, agents/}` |
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

**What moves.** Each member's `cwd` in `rig.yaml` becomes output of this rule. `rigLaunchSpec` left with the deleted `sync room` verb (client `ba96fee`); `up` now derives and creates the worktrees before it starts the seats, so each seat's cwd is its worktree rather than the room (`clientlifecycle/lifecycle.go:372`). The hand-made variants `rig/rig-claude.yaml` and `rig/rig-omp.yaml`, whose members carry `cwd: .`, are not sources and are retired by re-materializing, never by hand.

**Why `<roomDir>/wt/`.** It is the client's own directory: `rigLaunchSpec` already treats `roomDir` as the one directory no build replaces. The rejected location is a sibling of the repository, which no client code owns.

**Prior art.** Room `4genthub-ab` already runs seats this way: `4genthub-ab/wt/arm-*` on `ab/arm-*` branches.

## (a) Branch naming

| | A: one long-lived branch per seat, `<rig>/<seat>` | B: one branch per work item, `<rig>/<seat>/<item>` |
|---|---|---|
| `up` can create or reuse it without asking anyone | yes, the name is derived | no, the item is not known at launch |
| Shows which item a commit belongs to | the commit message and the board row do | the branch name does |

**Ruling: A.** For example `4genthub-min/go-dev`. The architect's branch is `4genthub-min/architect`. No current branch collides with these names (`git branch --list '4genthub*'` is empty).

**After a land:** a seat whose tip is contained in `main` runs `git merge --ff-only main` in its own worktree before its next edit. The client never moves a seat's branch.

**The submodule.** `agenthub_client` inside a seat's worktree is a **linked worktree of the main checkout's own submodule repository**, never `git submodule update`. `.claude` is not a submodule of this hub and is never linked: measured 2026-10-18, `.gitmodules` records `claude-automation` and `agenthub_client`, `git rev-parse HEAD:.claude` answers `fatal: path '.claude' exists on disk, but not in 'HEAD'`, and the derivation links nothing there (`f8989ba`).

The reason is measured. The architect ran it on scratch repositories on 2026-10-11: in a new linked worktree, `submodule update --init` clones from the submodule URL and fails on a pin that was never pushed, with `fatal: git upload-pack: not our ref`. This room never pushes, so every pin is unpushed. A `git -C <main>/agenthub_client worktree add <wt>/agenthub_client <gitlink-sha>` placed at the submodule path is accepted by the parent as the submodule. A seat's commit there lands in the shared client repository, where the lead can see it with no fetch.

| Submodule | In a writing seat's worktree |
|---|---|
| `agenthub_client` | on branch `<rig>/<seat>` of the client repository: attached to when that branch already exists with no worktree holding it, else created at the parent's gitlink; detached at the pin in the reviewer's worktree |

## Where a seat's client code lives

Ruling, 2026-10-18 (`qitem-20261018121114-9209ad06b981`): **one location**, `<roomDir>/wt/<seat>/agenthub_client`. A seat commits client code there, on its client branch: `<rig>/<seat>` for a seat that has none, and the branch its legacy worktree held for a seat the migration moves. `<roomDir>/wt/<seat>-client` is the pre-derivation layout; the migration (`clearStaleClientWorktrees`) removes it, clean only, and the branch survives.

The subject list is **every derived seat, the reviewer included**. A writing seat's legacy holds a branch its link needs, and git checks a branch out in one worktree per repository, so the legacy is exactly what makes the link impossible; a reviewer's legacy holds no branch, but it is still a second checkout of the client repository, and two checkouts at different commits are the ambiguity this ruling exists to remove - measured 2026-10-18, `wt/reviewer-client` sat detached at `287f7bc` while the derived link was detached at the pin `7034a80`. The one thing a removal must not take is the only reference to a commit: a detached legacy whose `HEAD` is on no branch and not in `main` is **refused and named**, the same rule `worktree prune` applies (`verbs.go:283`). Client `287f7bc` still skips a seat with no branch (`worktree.go:377`), so a reviewer's legacy is left today; hub `ade5e701` records the case in `TEST-CHANGELOG.md` ahead of the client, and the skip and that test are the implementation's remainder.

There is no per-seat location to name, because a second location means a second check: `Check` tests the derived path, and it exists so a seat that cannot build the client is named before the build fails. Naming `<seat>-client` as a location for some seats would make the check's answer depend on a table that must be kept true, and the seat launched in `<seat>` would still not find the client where the derivation puts it.

Measured 2026-10-18, the reason for this ruling: go-dev's link holds `4genthub-min/go-dev` (52 commits ahead of `main`) and works; the architect's and fe-dev's links were never placed, and their client work sat in `architect-client` (`4genthub-min/architect-client`, 3 ahead) and `fe-dev-client` (`4genthub-min/fe-dev-edit-yield`, one untracked `captures/` directory) - so `Check` called two working seats wrong. The migration's first form matched a legacy worktree only when it held exactly `<rig>/<seat>`, so no lane branch ever matched it: the legacy path is identified by PATH, and the branch it holds is what the link then carries.

A legacy worktree holding uncommitted or untracked work is not removed: `git worktree remove` without `--force` refuses it, the path is named, and the seat keeps working there until it commits - no link is placed beside it, because a second client location is the thing this ruling forbids. `Check` names the seat until the link exists; that is the truthful state, not a defect of the seat.

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

## (c) The commit form is pathspec, fleet-wide

The old reading here was that a private worktree makes the pathspec form unnecessary. The owner's ruling
(2026-10-17, `CHANGELOG/2026-10-17--the-commit-form-is-pathspec-fleet-wide.md`) restores it fleet-wide: the
index is shared with every other seat working in this tree, so a staged line can be taken by another seat's
commit. The commit therefore names its paths and nothing is staged first.

| Rule | Now |
|---|---|
| Commit by pathspec: `git commit -m "<type(scope): subject>" -- <paths>` | **required** |
| A new file: `git add -N -- <new>` (intent-to-add, nothing enters the index) before the same pathspec commit | **the one exception** |
| `git add -- <paths>` followed by a bare `git commit` | **dropped**: the retired staged form |
| `git add -A`, `git add .`, `git commit -a`, `--amend` | **forbidden, unchanged** |
| Before committing: read `git status --porcelain -- <paths>` and `git diff HEAD -- <paths>`, and name every line; a line that is not yours means the file is held, not committed | **required** |
| `CLAUDE.md`, `.claude`, `agenthub_go/seatcheck` and any gitlink you were not asked to move stay out of commits | **stays** |
| "Do not name a shared file that carries another seat's uncommitted change" | **stays**, as the per-line read above |
| No push, no `--amend`, no rebase of a branch that is not yours | **unchanged** |

## Composition with 7.8 and the CLI

- **Which repository it derives in.** The step reads the room's own repository from the definition's seat `cwds` (git's common directory behind them, `SeatProjectRoot`), not the working directory's toplevel, so `up` from a seat's client worktree derives the same paths as `up` from the project root; when the readable seat directories name more than one repository, the disagreement is printed and the working directory's answer stands. Measured 2026-10-18: the same `up --room-only` refused 6 of 6 paths from a client worktree and printed six kept lines from the project root (`4fd6c67`); `doctor`'s worktrees row reads the same root (`68c7ae9`). The root is read, never guessed from the seat path: `<roomDir>/wt/<seat>` is still where the paths sit.
- **A new `Obligatory` row, `worktrees`.** Scope `rig`; RestartBy `none`; start order `daemon`, `gate`, **`worktrees`**, `seats`, and so on, because a seat's `cwd` must exist before it launches.
  - **`Start`**, for each seat from `team.json`:
    - create the path from `SeatWorktree` if it is missing: `git worktree add <path> <branch>` when that branch already exists with no worktree holding it (it carries the seat's own commits; attaching re-points nothing), `git worktree add -b <branch> <path> main` when it does not, `--detach` for the reviewer;
    - link the `agenthub_client` worktree into it (on the branch above, or detached at the pin for the reviewer), and nothing else;
    - link `.env` into it, through the existing `rigLinkProviderKey`. `.env` is ignored by `.gitignore:169`.

    A path that is already a registered worktree is **kept** - read, not re-derived: it is not moved and not refused for the branch it holds (a seat's worktree moves onto the lane it is working, and a reviewer's is detached). One thing is still placed: the `agenthub_client` link, when `<seat>/agenthub_client/.git` is absent. It attaches to the branch the seat's legacy `<seat>-client` worktree held when the migration removed it, else to the branch the derivation names, and is created at the parent's gitlink when that branch does not exist. A legacy worktree holding uncommitted or untracked work is named and left (no `--force`), no link is placed beside it, and the run continues: the seat's link waits until the seat commits, and `Check` says so. Everything else in a kept path is the seat's own business; the one other write is its `.env` link. A path that exists and is not a registered worktree is **refused and named**. Nothing is overwritten.
  - **`Check`**: every derived path is registered in `git worktree list` **whatever branch it holds**, with the `agenthub_client` link present (a `.git` under it). Wrong is "present but not a worktree, or the client link missing", never "on another branch": measured 2026-10-18, fe-dev sat on `fe-dashboard-update-depth` and the architect on `g3-drop-classification` while the reviewer was detached, and a check that called all three wrong made a room that `up` keeps read as broken.
- **`sync rig`**: sets each member's `cwd` to `SeatWorktree(...)`. The path is deterministic, so sync can write it before the worktree exists.
- **New verbs:**
  - `4genteam worktree list RIG` prints the derived worktrees and every other entry of `git worktree list`, labelled `foreign`.
  - `4genteam worktree prune RIG` removes only `/tmp/wt-*`, `/tmp/gate-*` and entries git marks `prunable`, then runs `git worktree prune`. Removal is `git worktree remove` without `--force`, so a dirty worktree is named and left in place. A worktree whose detached `HEAD` is on no branch and not in `main` is **refused and named**: removing it deletes its reflog, which is the only reference to that commit. The case is real: `06410692` is on no branch today.
  - Anything else foreign, for example `~/__projects__/4genthub-urgent-subtask-details`, is listed and never removed.
- **`doctor`**: the `worktrees` row. A foreign count above zero is a detail on that row, not a failure.
- **7.10**: no repair verb touches a worktree.

## Facts the lead should know (none are ruled here)

- `.claude` is not a submodule of this hub and no derived worktree carries one (`f8989ba`). The earlier fact here - recorded at `b376accb`, checked out at `6e8bf881`, a new worktree getting the recorded hooks - described a link the derivation never places. go-dev's worktree holds an empty `.claude` directory with no `.git` under it (2026-10-18 13:52); it is a directory, not a link, and nothing links or removes it.
- The client skill `skills/share/seat-worktree/SKILL.md` still says `.claude` is detached inside the seat worktree and does not mention the client-location migration; both sentences go with the implementation of this ruling (client lane, go-dev).
- The architect seat is `claude-code` and is missing from the materialized rig (`072996ad`). Its worktree follows the same rule, and how it is launched belongs to that item.
- An ignored file is not in a new worktree. The frontend seat installs `node_modules` in its own worktree, and the client does not.

## Tests the implementation must pass (`622e9faf`)

| Case | Expected |
|---|---|
| `team.json` with lead, developer, reviewer and architect | four seat paths and `integration`; the reviewer has no branch |
| `Start` run twice | the second run changes nothing |
| a derived path that exists on another branch | kept and named `kept`, untouched |
| a kept seat path with no client link and a clean `<seat>-client` on a lane branch | the legacy is removed and its line says so; the link exists at `<seat>/agenthub_client` on that lane branch |
| the same, with an untracked file in `<seat>-client` | the legacy is named and kept, no link is placed, the run continues, `Check` calls the path Wrong |
| a clean `<seat>-client` for the reviewer, detached at the parent's gitlink | removed and its line says so; the reviewer's derived link is detached at the pin |
| the same, detached at a commit on no branch and not in `main` | refused and named, kept; nothing is placed |
| prune over `/tmp/wt-x` (clean), `/tmp/gate-y` (dirty) and `/tmp/wt-z` (`HEAD` on no branch) | x removed; y and z named and kept |
| a fixture parent repository whose submodule pin was never pushed | `Start` succeeds, and `git -C <wt> submodule status` shows the pin |
| `sync rig` | every member's `cwd` is its derived path |
