# Client features that help the dev team work like a human team

Written 2026-10-11 for the owner to review. Status of each item: "Exists" means it is in the client or its docs. "Missing" means no code was found. Not every module was read in detail.

## 1. Options

### 1.1 Code and branches (git, code review)
- Worktree per seat. Exists in the design (`ai_docs/core-architecture/seat-worktrees.md`), not enforced.
- File-overlap detector. Missing. Detail in section 2.
- Branch and merge status board: which seat is ahead or behind main, which tips wait for review. Missing.
- Pre-merge gate: tests, build and secret scan on the tip before the lead merges. Partly there (secretscan, reviewer).
- Stale-branch alert: a seat branch untouched for N hours with unmerged commits. Missing.
- Guard on `git add -A`, `commit -a`, push and force. Partly there (seat policies deny push).

### 1.2 Work tracking (Jira, Kanban board)
- Board view of items per seat: owner, state, age. Missing.
- Stuck-item alert: an item "in progress" with no activity for N minutes. Missing.
- Dependency check: do not start an item whose blocker is open. Missing.
- Definition-of-done check before an item closes (tests run, changelog entry written, diff inspected). Missing.

### 1.3 Communication (Slack, standup)
- `4genteam send`. Exists, but the sender is not trusted, see section 3.
- Daily standup digest from the seat logs: what each seat did, what blocks it. Missing.
- Handoff note when a seat is reseated or compacted, so the next session knows its state. Partly there (compaction supervisor).
- Escalation route: a seat blocked for N minutes tells the lead, then the owner. Missing.

### 1.4 Environment and onboarding
- `up` for the whole room, `seat sync`, `seat reseat`, skills delivery. Exists.
- Seat doctor: cwd, branch, skills, guide version, tool access. `doctor` exists, the worktree and skill checks are not built.
- Fresh-seat orientation pack: repo map, rules, current board. Partly in skills.

### 1.5 Quality and safety
- Off-peak gate and usage window. Exists.
- Watchdog and restarts. Exists, but needs a manual restart after a reboot until rigd exists.
- Audit log of every command a seat ran, per seat, append-only. Partly (`clientevidence`).
- Forbidden-actions list and auto-fix circuit breaker. Requested, not built.
- Secret scan on diffs before commit. Exists (`secretscan`).

### 1.6 Cost and capacity (team budget)
- Token and cost per seat, per item. Partly (cost rows exist in the server).
- Idle nudge and load balancing: give a task to an idle seat. Idle nudge requested, not built.
- Review queue limit, so the reviewer is not buried. Missing.

### 1.7 Knowledge (wiki, docs)
- Seat memory and shared notes. Exists as files.
- Doc-drift check: changed code with no matching doc or changelog entry. Missing.
- Decision log: the architect's rulings in one searchable place. Partly (`ai_docs`).

### First four, proposed by the owner session
1. File-overlap detector in the watchdog.
2. Seat doctor that checks cwd, branch and skills.
3. Stuck-item and idle alerts to the lead.
4. Definition-of-done check at item close.

## 2. How the client could detect two seats editing the same file

1. Compare branches in git. With one worktree per seat, run `git diff --name-only <base>...<rig>/<seat>` plus `git status --short` per worktree and intersect the file lists. Reliable, needs no seat cooperation, runs from the watchdog. It sees only saved files, and only after the fact.
2. Read the seat session logs (`seatlog`). Edit and write calls show the file path as they happen, so the warning comes earlier. Works for omp and claude-code seats only. Codex and agy have no log reader.
3. A check in each seat's pre-edit hook. Earliest warning, but a hook is needed in every runtime and a false positive blocks work.

On a hit the client sends a message to both seats and the lead naming the file and the two branches. The author resolves the conflict on its own branch, as the architect ruled.

This works only when each seat edits inside its own worktree. Today the seats run in the shared `rig` directory, so the client cannot tell which seat changed which file.

## 3. Sender identity for `4genteam send` (open problem)

`rig send` takes the sender from the session the daemon stamps (`X-OpenRig-Session`) and ignores any name passed by the caller. The owner session is not a managed seat, so its messages arrive unsigned and the architect refuses to treat them as the owner.

Proposal: `4genteam up` adds one `owner` node to the room (a plain shell seat, no model). `4genteam send` runs `rig send` inside that node's session, so the daemon stamps `owner@<rig>` and seats can verify it. The client must not set `OPENRIG_SESSION_NAME` to another name, because that is forging.

Not yet verified: that rig accepts a node with no agent runtime, that the stamp survives `tmux send-keys` into that pane, and how seat policies rank owner against lead. Anything running as the owner's Linux user could send as `owner`, which is already true today with `rig send` and `tmux`.

## 4. Architect analysis (to be written by the architect)

The lead gives this file to the architect. The architect rewrites this section with its full analysis, in plain wording, so the owner can review it in one place. It covers:

1. For each item in section 1: build, defer or drop, with the reason.
2. Order of the items that are built, and what each depends on.
3. Per item: which runtimes it works for (omp, claude-code, Codex, agy) and which need a different method.
4. Which items may block a seat and which only warn, with the risks of blocking hooks.
5. The detector design in section 2: which method first, which base branch, how a message to both seats is worded, how often it runs.
6. The owner-node proposal in section 3: trust rule, node design, policy ranking, test plan.
7. Cost: size of each item, who builds it (go-dev or fe-dev), and the board ids.

Earlier ruling for reference: the architect wrote `~/.openrig/agenthub-seats/4genthub-min/architect/DECISION-team-features-2026-10-11.md` on 2026-10-11 (order: seat doctor, git pre-push/pre-commit guard, overlap detector, stuck and idle alerts, done report). Fold it into the analysis above; do not leave two versions.

### Analysis

(pending)
