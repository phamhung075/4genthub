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

## 4. Architect analysis

Written 2026-10-11 by the architect seat for the owner. This section replaces the architect's earlier
note on the same question (`DECISION-team-features-2026-10-11.md`, kept outside the repository); that note
now only points here, so there is one version.

Words used below:
- **Seat**: one AI agent working in the room, such as the lead, the reviewer or go-dev.
- **Runtime**: the agent program a seat runs. There are four: omp, claude-code (Claude Code), Codex and agy.
- **Worktree**: a seat's own copy of the repository, on its own branch. The **shared checkout** is the one
  copy at `/home/daihu/__projects__/4genthub`, which is on `main`.
- **rigd**: the client's background helper for a room. It already runs the watchdog, the compaction
  supervisor and the bridge.
- **Daemon**: OpenRig's own background service, which delivers messages between seats.
- **Hook**: a small check that runs automatically before an action. A **blocking** hook can refuse the
  action; a **warning** only reports.
- **Board**: the 4genthub task board (`manage_task`).

### 4.1 Build, defer or drop each item in section 1

**Why this order of thinking.** Every failure the team had on 2026-10-11 was a seat in the wrong place, under
the wrong name, or in the wrong state:
1. The architect seat's shell ran in the shared checkout, so two commits (`c53c4900`, `58d117be`) landed on
   `main`. The owner found it by measuring; no tool caught it.
2. Commit `ea3efb20` carries the author name `scan test`, because a test exported `GIT_DIR` (a git setting
   that points git at another repository) and changed the shared git identity.
3. A generated file, `ai_docs/index.json`, sat changed in the shared checkout with no seat owning it, and at
   08:33 local eleven landing-branch files appeared there with no seat claiming them.
4. No branch on the remote server contains the client commit the certified batch pins (`d0d75996`). The lead
   found it by hand.

A per-seat check finds each of these in seconds. None of them was two seats editing the same file.

| Section 1 item | Decision | Reason |
|---|---|---|
| **1.1 Code and branches** | | |
| Worktree per seat | **Build, inside the seat doctor and the git guard** | The design exists but nothing enforces it. The doctor reports a seat outside its worktree; the guard refuses a commit from the shared checkout. No separate feature. |
| File-overlap detector | **Build (4th)** | Useful, but it costs a rebase when missed, while the wrong-place failures above cost commits on `main`. It also needs seats in their own worktrees first. |
| Branch and merge status board | **Defer** | It falls out of the overlap detector's data (ahead and behind counts per seat). Show it after the detector exists. |
| Pre-merge gate | **Defer** | The reviewer seat does this today. Automate it only after the done report (item 6) shows what is checked every time. |
| Stale-branch alert | **Build, inside the overlap detector** | The same scan sees each branch's last commit time. No separate feature. |
| Guard on `git add -A`, `commit -a`, push and force | **Build (2nd), the git guard** | Push and force are the only actions here that cannot be undone. See 4.4 for which parts block. |
| **1.2 Work tracking** | | |
| Board view per seat | **Defer, check first** | The board already stores the assignee and state of each task. Check whether the board page can filter by seat before building anything; if not, it is a small fe-dev change. |
| Stuck-item alert | **Build (5th), with the idle alert** | One timer covers both. |
| Dependency check | **Drop as a client feature** | The board already computes it: each task answer carries `can_start` and `is_blocked`. The rule is that a seat reads them; nothing new to build. |
| Definition-of-done check | **Build (6th), as a report, not a gate** | It attaches evidence at close; the reviewer still decides. |
| **1.3 Communication** | | |
| `4genteam send` sender identity | **Build (3rd), the owner node** | Section 4.6. |
| Daily standup digest | **Defer** | The send audit (`seatcheck`) and the queue already record every message, so a digest is only a way of showing them. Do it after the stuck alerts. |
| Handoff note at reseat or compaction | **Defer, then fold into the seat doctor** | The compaction supervisor already sends `/compact` and a resume message. The doctor's launch check is the place to add the note. |
| Escalation route (seat, then lead, then owner) | **Build, inside the stuck alerts** | It is the same timer with a second, longer threshold. |
| **1.4 Environment** | | |
| `up`, `seat sync`, `seat reseat`, skills delivery | Exists | Nothing to do. |
| Seat doctor (cwd, branch, skills, tool access) | **Build (1st)** | It finds all four of the day's failures. |
| Fresh-seat orientation pack | **Defer** | Skills deliver it today. The doctor checks the skill version, which covers "is the pack current". |
| **1.5 Quality and safety** | | |
| Off-peak gate | Exists | Nothing to do. |
| Watchdog and restarts | Exists in rigd's design | Restart-after-reboot is rigd's own work, not a team feature. |
| Per-seat audit log of every command | **Defer** | Messages are already recorded. A command log is only possible for omp and claude-code (the only runtimes whose session logs the client can read), so it would be incomplete. |
| Forbidden-actions list and auto-fix circuit breaker | **Already ruled elsewhere** | The circuit breaker was ruled on board task `411f5351-10e2-4990-856e-0e3b1adf0ab0`. The git guard (item 2) enforces the forbidden-actions list for push and force. |
| Secret scan on diffs before commit | **Build, inside the git guard, as a warning** | The scanner exists (`secretscan`). A secret in a local commit can still be removed before anything is pushed, so it warns rather than blocks; push is blocked anyway. |
| **1.6 Cost and capacity** | | |
| Token and cost per seat | **Defer** | The server already records cost rows. Showing them is a later fe-dev view. |
| Idle nudge | **Build, inside the stuck alerts** | Same timer. |
| Load balancing | **Defer** | It needs the stuck and idle data first. |
| Review queue limit | **Defer** | Same reason. |
| **1.7 Knowledge** | | |
| Seat memory and shared notes | Exists | Nothing to do. |
| Doc-drift check | **Build, inside the done report** | "Code changed but no doc or changelog entry" is one more line in that report. |
| Decision log | **Drop as a new tool** | The board is the decision log: rulings go to the board first. Make board search cover it instead of keeping a second log. |

**Compared with the owner session's first four** (overlap detector, seat doctor, stuck alerts, done check):
the same four are built, the seat doctor moves first, and two items are added before the overlap detector:
the git guard and the owner node. The one fact that would move the overlap detector back to first place is
evidence that two seats editing the same file has actually cost the team a merge. The architect has not
counted any.

### 4.2 Build order and what each item depends on

| # | Item | Depends on | Why it is here |
|---|---|---|---|
| 1 | Seat doctor | Nothing; it is a new set of checks inside the existing `4genteam doctor` | Finds the day's four failures. Every later item assumes seats are in their own worktrees, which only the doctor checks. |
| 2 | Git guard | Item 1 (the doctor reports whether the guard is installed and switched on) | Makes push impossible from any seat, whatever its runtime. Item 3 relies on that. |
| 3 | Owner node | Item 2 | With push already blocked for every seat, a message signed by the owner never has to be trusted for an action that cannot be undone. See 4.6. |
| 4 | Overlap detector, with stale-branch alert | Item 1, and a rigd loop | Only correct for seats the doctor shows working in their own worktree. |
| 5 | Stuck and idle alerts, with escalation | rigd's loop (same as 4); the owner node (3) so escalation to the owner reaches a real place | |
| 6 | Done report, with doc-drift line | Nothing technical; placed last because it is the least urgent | |

### 4.3 Which runtimes each item works for

The client can read the session logs of omp and claude-code only (`internal/seatlog`); it has no reader for
Codex or agy. Anything based on git, files, the queue or the board works for all four.

| Item | omp | claude-code | Codex | agy | Notes |
|---|---|---|---|---|---|
| 1 Seat doctor | yes | yes | yes | yes | Git and file checks only. |
| 2 Git guard | yes | yes | yes | yes | Git runs the hook whatever program called git. **The only guard that covers Codex and agy.** `add -A` and `commit -a` cannot be seen from a git hook, so they stay in the per-seat deny lists, which exist for omp and claude-code only. |
| 3 Owner node | n/a | n/a | n/a | n/a | It is a plain shell, not an agent. Every seat receives its messages the same way. |
| 4 Overlap detector | yes | yes | yes | yes | The git method (4.5) covers all four. The earlier warning from session logs is omp and claude-code only. |
| 5 Stuck and idle alerts | yes | yes | yes | yes | Queue and board timers cover all four. "No log activity for K minutes" is omp and claude-code only; Codex and agy rely on the queue and board timers. |
| 6 Done report | yes | yes | yes | yes | Git and queue only. |

### 4.4 Which items may block a seat, and the risks of blocking

**Only the git guard blocks, and only for these actions:** push, force-push, a commit made from the shared
checkout, and a commit whose author is not the seat's own name. Everything else only warns or reports to
the seat and the lead. The secret scan inside the guard warns.

Risks of blocking hooks, and how this design handles each:
1. **False alarms stop real work.** This repository's own pre-tool hook refuses any command containing the
   text "confirm /health", mistaking it for a dangerous delete. The retired `call_agent` check blocked every
   team agent twice before letting it through. A check on free text misfires, so the guard checks git facts
   (the branch, the folder, the author), never message text.
2. **A blocked seat with nobody watching waits forever.** A refusal without a human present is a stall, not
   a stop. The stuck alert (item 5) is what notices it, which is one reason it is built.
3. **Uneven coverage looks like full coverage.** claude-code has pre-tool hooks, omp has deny lists, and
   Codex and agy have neither here. A guard built into one runtime protects some seats and silently not
   others. Git hooks avoid this, which is why the guard lives in git.
4. **The hook can itself break.** If a broken hook blocks, it stops the seat; if it lets everything through,
   the guard silently disappears. Rule: push and force fail closed (a broken check blocks); nothing else is
   a blocking hook.
5. **A seat can step around a hook** (`git push --no-verify`, or pointing git at another hooks folder). The
   seat doctor therefore reports the hooks folder git uses and whether the guard is present, so a
   switched-off guard shows as a red line. The remote server is the final protection: seats hold no push
   credentials the owner has not given them.

### 4.5 The overlap detector (section 2)

**Method first: compare branches in git (method 1).** It needs nothing from the seat and works for all four
runtimes. Reading session logs (method 2) comes second, for omp and claude-code only, to warn earlier.
A check in each seat's pre-edit hook (method 3) is **not built**: it needs a hook in every runtime, and a
false alarm blocks work (risks 1 and 3 above).

**Base branch: set per room, never fixed to `main`.** During a batch the lead merges into the batch branch,
not `main`, and which line is the main line is not decided yet. The room's settings name the branch the lead
merges into; the detector compares each seat branch against it.

**What it compares:** for each seat worktree, the files changed on its branch since the base, plus the files
changed but not yet committed. Two seats with a file in common is a hit. Seats the doctor does not show in
their own worktree are skipped and named in the report, because their changes cannot be told apart.

**How often:** every 10 minutes from rigd's loop, and on request. A hit is sent once; the same file and the
same two seats are not reported again for an hour unless a third seat joins.

**The message, sent to both seats and the lead:**

> Two seats are changing the same file. File: `<path>`. Seat `<A>` on branch `<branch A>` (`<n>` commits not
> yet merged, last at `<time>`). Seat `<B>` on branch `<branch B>` (same details). Nothing is blocked. Each
> author keeps the change on its own branch; the lead decides the merge order. Reply to the lead, not to
> each other.

The last two sentences follow the standing rule: the author resolves a conflict on its own branch, and the
lead orders the merges.

### 4.6 The owner node (section 3) - the answer to board task `e2948011-6ea7-42bf-8ee9-c4725124e60b`

**What was measured in OpenRig's code** (the files under `/home/daihu/__projects__/openrig/packages`):
- The `From:` name on a message comes from a setting in the sending program's environment
  (`OPENRIG_SESSION_NAME`). The `rig` command copies it into the request (`cli/src/sender-identity.ts:11`),
  and the daemon writes it down as the sender, labelled `transport:v1`, without checking which program sent
  it (`daemon/src/routes/require-sender-identity.ts`).
- When the daemon starts any node, it sets that environment setting on the node's terminal session
  (`daemon/src/domain/node-launcher.ts:141-151`). That is why a command typed in a seat's terminal is
  signed with that seat's name.
- OpenRig already supports a node with no agent: `runtime: terminal`, `agent_ref: builtin:terminal`,
  `profile: none`, and such a node may not carry a role or a permission policy
  (`daemon/src/domain/rigspec-schema.ts:505-550`).

**1. The trust rule.** "Anything running as the owner's Linux user may send as the owner" is acceptable,
because it is already true: that user can type into any seat's terminal, and the terminal is the wire.
**In plain words: the owner node gives attribution and an audit trail, not authentication.** It records
who a message claims to come from, through the same path every seat uses. It is **not proof against anything
running on this machine**, and that includes the seats themselves: every seat runs as the same Linux user
and can run commands, so a seat could set the same environment setting, or type into the owner node's
terminal. No seat may ever treat the owner's name on a message as proof against a local adversary.

**What makes this safe enough:** the owner's name must never unlock an action that cannot be undone.
- Push, force-push and production changes stay blocked for every seat by the git guard (item 2) and the
  standing rules, whoever the message comes from. The owner does those actions personally.
- An owner-signed message may set priorities, scope and the next task, and it outranks the lead on those.
  If a forged one ever arrives, the worst result is wasted work that can be undone.
- To make forging visible, the per-seat deny lists (omp and claude-code) refuse a command that sets
  `OPENRIG_SESSION_NAME` or types into another seat's terminal. Codex and agy have no deny list; for them
  the send audit (`seatcheck`) records the sending seat.

**2. The node design.**
- **Name and registration.** `4genteam up` adds one member to the room: name `owner`, `runtime: terminal`,
  `agent_ref: builtin:terminal`, `profile: none`, no role. Its signed name follows the room's pattern:
  `4genthub-min-owner@4genthub-min`.
- **It is not a seat in the team list.** The team list is built from roles, and a terminal node may not
  have one. So `team apply --prune`, which deletes room members missing from the team list, must leave the
  owner node alone; otherwise the next prune deletes it.
- **Snapshot and restore.** The node is part of the room's saved layout. On restore it comes back as an
  empty shell; it has no conversation to recover.
- **Watchdog, compaction, parked and idle.** The node runs no model, so the compaction supervisor must skip
  it, and the stuck and idle alerts must not count it as idle. It must also never appear as a stopped seat
  owing work in `rig parked`.
- **Replies to the owner.** Seats keep replying through the lead, as today. Nothing reads the owner node's
  queue, so a message left there would wait unseen.
- **How `4genteam send` uses it.** Three ways were compared:
  - **A. Type the message into the node's terminal** (`tmux send-keys`, which types keys into a terminal
    as if from the keyboard). It works, but the message text passes through the shell's command line (quoting
    and length problems, and it lands in the shell history), and `4genteam send` cannot read the result,
    such as the message ID or an error.
  - **B. Run `rig send` directly with the owner name put in its environment.** Rejected. The daemon cannot
    tell it apart from the forging the owner forbade, and if the client does it, there is no clean rule left
    to deny the same command to the seats.
  - **C, recommended: write the message to a private file, then type one short command into the node's
    terminal that sends that file.** The node's own shell signs it, as in A. Only a file path passes
    through the command line, so there is no quoting problem, and the command writes the result (message ID
    or error) to a second file that `4genteam send` reads back and shows to the owner. The client never writes the
    owner name anywhere.
- **Which parts need the owner or the lead to decide:** whether the owner's word outranks the lead on
  priorities only (this ruling) or also on merges (the architect recommends priorities only; merges stay
  the lead's). This does not block building the node.

**3. Which half each piece belongs to.**

| Piece | Half |
|---|---|
| Signing the sender from the terminal's environment | OpenRig's daemon and `rig` command. Exists; nothing to change. |
| A node with no agent (`runtime: terminal`) | OpenRig. Exists. |
| Making the signature real proof (checking which program sent a request, not just what it claims) | OpenRig's daemon, and **not built**. It is the only change that would turn attribution into authentication against the seats. Out of scope for this client work. |
| Adding the owner node in `4genteam up`, protecting it from `--prune`, skipping it in compaction and idle checks | Client (agenthub_client), go-dev. |
| `4genteam send` method C | Client, go-dev. |
| Deny-list lines for `OPENRIG_SESSION_NAME` and typing into another terminal | Client (`internal/clientpolicy`), go-dev. |

**4. The three open questions, settled or tested.**
- (a) Does rig accept a node with no agent? **Known now: yes** (the code above).
- (b) Does the signature survive a message sent by typing into that terminal? **Known from code, needs one
  test.** The signature comes from the environment of the program running `rig send`, and the daemon sets
  that environment on the node's terminal at start. Typing only starts a program in that terminal, which
  inherits it. One test confirms that the shell the node starts really keeps the setting.
- (c) How do seats rank the owner against the lead? **A decision, not a test:** see the trust rule above.

**Test plan, on a throwaway room only, never on 4genthub-min:**
1. Start a throwaway room with one owner node and one test seat.
2. From the owner node, send with method C. Check that the message shows `From: <room>-owner@<room>`,
   labelled `transport:v1`, and that `4genteam send` printed the message ID.
3. From a plain shell outside any node, send once. Check that it shows `<unknown sender>`; this is what a
   seat sees when the signature is missing.
4. Save the room's layout and restore it. Check that the owner node comes back as an empty shell.
5. Run `team apply --prune` as a dry run. Check that the owner node is not listed for deletion.
6. Leave the room alone for longer than the idle threshold. Check that no idle alert or compaction is sent
   to the owner node, and that `rig parked` does not list it.
7. Stop and remove the throwaway room.

The test does **not** try setting the owner name in another program's environment. That is the forging the
owner forbade, and the code already shows it would succeed.

**Ruling:** the client half is approved as written here. Board task `44d2fd0b-81c8-4d31-bf2b-731d8b35bbe1`
(go-dev) may start when the lead releases it.

### 4.7 Cost, builder and board tasks

Sizes: **small** is up to half a day, **medium** is one to two days.

| # | Item | Size | Builder | Board task |
|---|---|---|---|---|
| 1 | Seat doctor | small | go-dev | none yet |
| 2 | Git guard (with secret-scan warning) | small to medium | go-dev | none yet |
| 3 | Owner node and `4genteam send` method C | medium, including the throwaway-room test | go-dev | `44d2fd0b-81c8-4d31-bf2b-731d8b35bbe1` |
| 4 | Overlap detector, with stale-branch alert | medium (a rigd loop) | go-dev | none yet |
| 5 | Stuck and idle alerts, with escalation | medium (same rigd loop) | go-dev | none yet |
| 6 | Done report, with doc-drift line | small | go-dev | none yet |
| later | Board filter per seat, cost view, branch status view | small each | fe-dev | none yet, deferred |

The lead creates one board task per item when the owner approves this analysis. The architect did not create
them, because assigning work to go-dev and fe-dev is the lead's call.

## 5. Which product each item lands in

Section 4 decided what to build and in what order. This section says which codebase each piece is built in, and names the decisions still owed to the owner. It is a plan; no code is written from it until the owner approves.

Words used: the **board** is the 4genthub task board; the **queue** is OpenRig's coordination queue; **rigd** is the client's supervision loop (`agenthub_client/internal/clientlifecycle`).

### 5.1 The products

- **4genthub** - the server and its UI: Go under `agenthub_go` (the board, rooms and seats, `seat_links`, the ledger) and React under `agenthub-frontend`. Repository `/home/daihu/__projects__/4genthub`.
- **4genteam** - the client's operational surface: the `4genteam` command (`agenthub_client/cmd/4genteam`), the rigd loops (`agenthub_client/internal/clientlifecycle`), and the git hooks (`4genthub/scripts/git-hooks`). `4genteam` is the one binary the client repository builds.
- **4gent-client** - the same client repository (`agenthub_client`, `github.com/phamhung075/4genthub-client`) read as its library surface: the policy, session-log and secret-scan packages (`internal/clientpolicy`, `internal/seatlog`, `internal/secretscan`), the seat-side checker (`cmd/seatcheck`) and the seat state (`internal/clientservices`).

**One repository, two names.** Measured: `4genteam` and `4gent-client` are one repository. `agenthub_client` is the only client checkout (`.gitmodules` names `git@github.com:phamhung075/4genthub-client.git`), and it ships the `4genteam` binary, rigd and the library packages together; the retired Python `openrig_*.py` scripts are no longer in the tree. So the last two columns below are that repository's two surfaces - what it runs and what it links - not two products. If two repositories were intended, that is open decision (d).

### 5.2 The split

| Item (section 4) | 4genthub (server / frontend) | 4genteam (CLI / rigd) | 4gent-client (client library) |
|---|---|---|---|
| **1 Seat doctor** | n/a - it reads git and files on the seat's machine only | **lands**: new checks in the `4genteam doctor` verb (`internal/clientlifecycle/doctor.go`), run at launch, reseat and on demand | **reads**: the seat's deny rules (`internal/clientpolicy`) and its log (`internal/seatlog`) for the skills and guide-version rows; no new package |
| **2 Git guard** | **partly**: the hook scripts live in this repo's own tree (`scripts/git-hooks/`), and this repo is the first one guarded | **lands**: the verb that installs the hook into any repo, and the hook entry points | **lands**: the secret scan the hook calls (`internal/secretscan`) and the forbidden-action rules (`internal/clientpolicy`) |
| **3 Owner node + `4genteam send` method C** (board `44d2fd0b`) | **lands**: the terminal member (`runtime: terminal`, `agent_ref: builtin:terminal`, `profile: none`), the `team apply --prune` exemption, and the `seat_links` that attribute its messages | **lands**: `up` adds the owner node; the new `4genteam send` verb (write a private file, type one command into the node's terminal, read the result file) | n/a - the send is a CLI command, not a library |
| **4 Overlap detector + stale-branch alert** | n/a beyond the base-branch setting it reads (decision a) | **lands**: a new rigd loop in `internal/clientlifecycle` scanning every worktree | **partly**: the earlier session-log warning uses `internal/seatlog` (omp and claude-code only) - phase 2 |
| **5 Stuck and idle alerts + escalation** | **partly**: it watches board rows, which are server data; no change unless a read is missing | **lands**: the same rigd loop, plus the escalation row it writes to the queue | **partly**: "no log activity for K minutes" uses `internal/seatlog` (omp and claude-code only) |
| **6 Done report + doc-drift** | **partly**: it reads the board row it closes | **lands**: assembled by the client at item close (diff, changelog presence) | **partly**: the diff and changelog checks are client-side git reads |

The deferred set, by product:

| Deferred item | Product |
|---|---|
| Branch status board | 4genthub frontend; its data comes from the detector (4genteam) |
| Pre-merge gate | 4genteam (client) plus this repo's hook scripts |
| Board view per seat | 4genthub frontend - check whether the board page can already filter by seat first |
| Standup digest | 4gent-client (seat logs) plus 4genthub (board data) |
| Cost view | 4genthub frontend; the server's cost rows already exist |
| Load balancing | 4genthub server plus 4genteam |
| Review-queue limit | 4genthub server |
| Command audit log | dropped/deferred - only omp and claude-code logs are readable, so it would be incomplete |
| Handoff note | 4genteam (the compaction supervisor) plus 4gent-client (`internal/seatlog`) |

### 5.3 The open decisions

**(a) Base branch per room.** The detector compares each seat branch against a configured base, not `main` (4.5). Decision: what each room's base branch is, and who owns it - a room setting on the server (4genthub), a client config key in `~/.config/4genthub/.env` (4genteam), or the lead per batch. Recommendation: a room setting the client reads, falling back to `main`.

**(b) "Owner outranks lead on priorities only."** The exact rule: an owner-signed message may set priorities, scope and the next task; it does not order a merge or a push. Where enforced: the git guard keeps push blocked for every seat whatever the sender (so the rule is not the only protection), and the lead follows it; no code reads message priority. Decision: confirm "priorities only, merges stay the lead's" (recommended).

**(c) The rigd loop.** Items 4 and 5 ride one rigd loop in `internal/clientlifecycle`. Decision: the cadence (4.5 proposes every 10 minutes), and what happens when rigd is down - the detector and the alerts go silent, so the seat doctor (item 1) must report rigd's state; rigd phase 1 already carries that safeguard report.

**(d) `4genteam` and `4gent-client`.** Measured as one repository (5.1). Decision: confirm they are two surfaces of `agenthub_client`, or name a second repository if one is intended. Does not block step 2 - both surfaces are go-dev's.

### 5.4 Handoff to step 2

The lead creates one board task per item in section 4.2's order: go-dev for the client items 1-6, fe-dev for the deferred board and cost views, and a reviewer gate on each tip.
