# Seat skills: one source, delivered by the client, checked at launch

Architect ruling, 2026-10-11, on the owner's rule that seats use skills from `agenthub_client/skills` only.
- **Request:** `qitem-20261010232050-55adaf600cf70857` and its 23:21Z owner addition; board `9a5c1bb4`.
- **Client work:** `622e9faf` and `fad0bb21`.
- **Ruling row:** `718778c1`.
- **Composes with:** `seat-worktrees.md`, the worktree ruling.

**The problem, measured.** A seat can take skills from six places today:
- the seat's cloud snapshot;
- the client tree;
- the project `.claude/skills`, a symlink tracked in the `.claude` hooks repository that points at the git-ignored `.agents/skills`;
- `~/.agents/skills` and `~/.claude/skills`;
- user-installed Claude Code plugins.

None of these agree, and none of them is what the runtime reads. The lead's finding `072996ad`: `sync rig` delivered `seat-worktree` into 10 of 10 materialized agent directories, but no running seat's harness directory has a skills directory at all.

## 1. Levels: each skill lives in exactly one place

The rule: a skill used by more than one room goes in `share/`, a skill used by more than one seat of one room goes in `rooms/<room>/`, and a skill used by exactly one seat goes in `rooms/<room>/<seat>/`. A copy at two levels is not allowed, which leaves the loader's "more specific replaces shared" override with nothing to do.

| Skill | Level | Source of the bytes |
|---|---|---|
| agent-browser, changelog-updater, development-team, dogfood, safe-file-removal, seat-worktree, systematic-debugging, test-driven-development, token-economy, unused-code-cleanup, verification-before-completion | `share/` | already there |
| comm-guard-skill | `share/` | cloud snapshot: in all 10 materialized seats, every copy hashed identical (5 hashed) |
| queue-handoff | `share/` | cloud snapshot: in all 10, identical (5 hashed) |
| context-engineering | `rooms/4genthub-min/` | cloud snapshot: developer seats only, identical (2 hashed) |
| specification-system | `rooms/4genthub-min/` | cloud snapshot: developer seats and the reviewer, identical (4 hashed) |
| offpeak-gate, rig-runtime-switch, spawn-team, watch-team | `client/` | already there; these are for the LLM running the client and are never delivered to a seat |
| none | `rooms/<room>/<seat>/` | no skill is single-seat today |

The two room-level skills also reach the lead and the architect. That is cheaper than keeping two copies, which the single-source rule forbids.

**The move rule (compare each pair, keep the newer content), applied.** The architect measured on 2026-10-11, comparing the latest client commit time with the newest `.agents` file mtime:

| `.agents/skills` | Client copy | Content | Newer |
|---|---|---|---|
| changelog-updater, safe-file-removal, test-driven-development, verification-before-completion | `share/` | identical | - |
| agent-browser, development-team, dogfood, systematic-debugging, token-economy, unused-code-cleanup | `share/` | differs | client (10-10) |
| rig-runtime-switch, spawn-team | `client/` | differs | client (10-10 18:01) |
| watch-team-grid | `client/watch-team` | differs | client: the renamed successor |

**So nothing moves out of `.agents/skills`.** Its copies retire (see section 4). The lead's count of three skills with no counterpart missed `client/`, which holds all three.

The four cloud-snapshot skills have no client copy. They are copied once from the snapshot into the level above, by the client item, as one client commit.

## 2. One source, one delivery

Every skill a seat uses lives under `agenthub_client/skills`, and the client's existing resolution (`clientskills`: share, then the room, then the seat; never `client/`) delivers it. `4genteam sync rig` is the only delivery.

The cloud snapshot's skills stop being a source. `sync rig` removes from each `agents/<seat>/skills/` and from `agent.yaml` every skill the client tree did not resolve, and names each one on stderr. The server-side seat-skill attachment is then unused for seats. Removing it is a separate clean-break item for the lead to file, with no compatibility kept.

## 3. `agent.yaml` `resources.skills`

`sync rig` writes `resources.skills` (`- id: <name>, path: skills/<name>`) and the profile's `skills:` list as **exactly** the resolved set, in resolution order. Every other entry is dropped. No one writes either list by hand.

## 4. `.agents/skills` and the project `.claude/skills` stop being sources

| Source | How it stops | By whom |
|---|---|---|
| `.claude/skills`, a symlink tracked in the `.claude` hooks repository | a commit in that repository removes it, then the parent's gitlink moves | the hooks owner, through the lead. Never `rm`. `.claude` stays out of seat commits. |
| `.agents/skills`, git-ignored and untracked | emptied file by file through `safe-file-removal`, once its 13 entries have been compared above | the lead, after the client check (section 6) passes |
| `~/.agents/skills`, `~/.claude/skills` | **not deleted**: they are the owner's own, for the owner's sessions. They are disabled for seats by the launch configuration (section 5). | the client |
| user-installed Claude Code plugins | disabled for seats by `--setting-sources` (section 5) | the client |

A seat in its own worktree (`seat-worktrees.md`) has no `.agents/` at all, because the directory is ignored. Its `.claude/skills` symlink points at nothing until it is removed. The launch configuration below is what actually closes each source. Retirement only removes the confusion.

## 5. The client configures, at launch, the skill path the runtime reads

`up`, `sync rig` and every seat launch or relaunch write the following. No seat is launched with `rig up` directly (7.8).

**omp seats.** omp discovers skills through `skills.*` settings. These ids were read from the omp binary on 2026-10-11:

| Setting | Default | Default source of skills |
|---|---|---|
| `skills.enableAgentsUser` | true | `~/.agents/skills` |
| `skills.enableAgentsProject` | not read | the project walk-up of `.agent(s)/skills` |
| `skills.enableClaudeProject` | not read | `.claude/skills` |
| `skills.enablePiUser`, `skills.enablePiProject` | true | |

`skills.enableClaudeUser` and `skills.enableCodexUser` default to false.

The client merges this into the `config.yml` that the **running runtime** reads, the same key-level merge `rigOMPConfigInstallName` already does:

```yaml
skills:
  enabled: true
  customDirectories: [<agent dir>/skills]   # absolute: the delivered set
  enableAgentsUser: false
  enableAgentsProject: false
  enableClaudeUser: false
  enableClaudeProject: false
  enableCodexUser: false
  enablePiUser: false
  enablePiProject: false
```

"The `config.yml` the running runtime reads" is the harness agent directory OpenRig launches omp with (`~/.openrig/state/omp/<session>/agent/` per `072996ad`), not only `rig/agents/<seat>/`. **Which of the two omp actually reads is the first thing the client item measures**, and the check in section 6 proves it. The test is `omp skill list --json`, which reports each loaded skill's `filePath` and `source`.

The architect measured it in an empty directory: it listed `openrig-skills`, `refocusing` and `rigs` from `~/.agents/skills` (`source: agents:user`). A seat started today gets those three skills.

**claude-code seats** (the architect):
- `--setting-sources project,local`
- `--plugin-dir <agent dir>/skills-plugin`

The client builds `skills-plugin`: `.claude-plugin/plugin.json` with `{"name":"seat"}`, plus `skills/`, which holds the delivered set.

Measured by the architect on 2026-10-11 with claude 2.1.296, in an empty directory with no tools:

| | user skills, e.g. `openrig-skills`, `refocusing`, `rigs` | user-installed plugins (`design`, `typesafe`, ...) | the scratch plugin's skill, as `seatskills:probe-skill` | the runtime's bundled skills (`verify`, `debug`, ...) and `builtin` plugins |
|---|---|---|---|---|
| `--setting-sources user,project,local` | loaded | loaded | loaded | loaded |
| `--setting-sources project,local` | absent | absent | loaded | loaded |

`project` stays on, because the worktree's `.claude/settings.json` carries the hooks.

**Correction, measured 2026-10-11 23:5xZ on the owner's question.** A sender I could not authenticate claimed to be the owner session. The architect probed in the main checkout with its own argv and stopped each probe at the init event:

| Launch | Project `.claude/skills` (→ `.agents/skills`) | `~/.claude/skills` | User plugins | Agent directory |
|---|---|---|---|---|
| today's argv: `--dangerously-skip-permissions --model opus`, no `--setting-sources`, no `--plugin-dir` | 13 loaded | 3 loaded | 7 loaded | **none loaded**, `seat-worktree` included |
| `--setting-sources project,local --plugin-dir <plugin>` | **13 loaded** | 0 | 0 | 18 as `seat:<name>` |
| `--setting-sources local --plugin-dir <plugin>` | 0 | 0 | 0 | 18 as `seat:<name>` |

**What the flags close.** They close the user sources only. `project` also loads `<cwd>/.claude/skills`. Dropping `project` would also drop the hooks in `.claude/settings.json`, so it is rejected.

**What closes the project source:**
- section 4's removal of the symlink in the hooks repository;
- `F1`: a seat's cwd is its worktree, and `.agents/` is ignored and absent there.

Either one alone is enough. No Claude Code setting that turns off project skills was found, and none is relied on.

**F2 already names this case:** a project skill is loaded un-prefixed. Run in the main checkout today, the check fails with `F1` and `F2` (13 skills).

The architect's agent directory also still holds four skills that the client tree does not resolve (`agent-starters`, `openrig-architect`, `plan-review`, `topology-mutation-and-seat-management`). These are cloud-snapshot leftovers, and section 2's `sync rig` drops them.

## 6. The one check, run by `up` after every seat launch, exit 3 on failure

The check runs after every seat launch. A failure exits 3 (7.5) with one line per failure: `seat <seat>: <code> <detail>`. `doctor` runs the same function over running seats.

| Code | Fails when |
|---|---|
| `F1 cwd` | the seat's cwd is not its derived worktree (`SeatWorktree`). This includes the main checkout. |
| `F2 foreign` | the runtime loaded a skill that the resolution did not deliver. For omp this is any `skill list` entry not in the set. For claude it is any plugin in `init.plugins` other than `seat` and those whose path is `builtin`, or any un-prefixed skill whose name is a directory in `~/.claude/skills`, `~/.agents/skills` or `<cwd>/.claude/skills`. |
| `F3 missing` | a skill in the resolved set is not loaded: for omp, absent from `skill list`; for claude, `seat:<name>` absent from `init.skills`. |
| `F4 path` | a loaded skill of the set resolves outside the delivered tree: an omp `filePath` not under `<agent dir>/skills/`, or a claude plugin `seat` whose path is not `<agent dir>/skills-plugin`. |
| `F5 stale` | a delivered copy's content hash differs from the client tree's copy at the client's current commit. |

**The evidence each runtime gives:**
- **omp:** `omp skill list --json`, run with the seat's launch environment and cwd.
- **claude:** a headless probe with the seat's exact argv and cwd plus `-p --output-format stream-json --verbose`. The client reads the `system/init` event and kills the probe on that line. That the probe sends no model request on that path is asserted by a test with a fake `claude`, not assumed.

**For a seat that is already running:**
- The check reads the same evidence. For claude it also compares `/proc/<pid>/cmdline` with the launch argv.
- A difference is `doctor`'s `skills_stale` on the seats row.
- `up` does not kill a working seat to fix its skills. The lead relaunches it at an idle point (7.7).
- A skill added to the tree therefore reaches a running seat at its next launch, and never silently.

**The six stale materialized seats** (`context-dev`, `feedback-dev`, `go-dev2`, `skills-dev`, `web-dev`, `writer`, from `072996ad`) come from a server rigspec that has fallen behind `team.json`.
- The room's spec is updated from `team.json` by the lead's apply, not by a seat.
- `sync rig` then names the six as carried over.
- The client retires them; no seat removes them by hand.

The architect's absence from the rig is the same staleness.

## Tests the client item must pass

| Case | Expected |
|---|---|
| a fixture tree with a skill in `share/` and in `rooms/r/` under the same name | `sync rig` refuses it as a duplicate (section 1) |
| a snapshot holding a skill the tree does not resolve | `sync rig` removes it from `skills/` and `agent.yaml`, and names it |
| a fake `omp` whose `skill list` adds `openrig-skills` from `~/.agents` | `F2` |
| a fake `omp` missing `seat-worktree` | `F3` |
| a fake `omp` listing `seat-worktree` from `.agents/skills` | `F4` |
| a delivered copy edited after delivery | `F5` |
| a seat whose cwd is the main checkout | `F1` |
| a fake `claude` whose init event lists plugin `design` with a path that is not `builtin` | `F2`, and the probe was killed on the init line |
