# Seat friction loop — design (step 1: dedupe against what exists)

**Status:** DESIGN ONLY. No skill text is written in this step. Nothing here takes effect until the lead
ratifies the mechanics and the owner approves the autonomy charter (see §8).
**Owner request:** relayed 2026-10-11 09:44Z; board `4b0c5c51` (step 1). Plan; the relay is not production authorisation.
**Goal:** an auto-improvement loop so the owner stays out of the loop and only watches and decides important
things; the lead holds the context and is answerable that the team works correctly and matches the ecosystem.

## 0. The one-line thesis (what dedupe changed)

The owner's set is mostly right in *intent* and wrong in *shape*: **the transport and the record already exist.**
A friction-reporting channel ships end-to-end today (`submit_feedback` MCP + `4genteam feedback` → `POST
/api/v2/feedback`, with a closed `layer` vocabulary the owner already reads grouped by layer —
`agenthub_client/internal/clientfeedback/feedback.go:40-62`, `ai_docs/api-integration/surface-inventory.md:339-350`).
Upward routing already exists (queue-handoff `escalation`; comm-guard-skill `--intent escalation|report`). The record
of a landed change already exists (changelog-updater). **What is genuinely missing is the middle:** what a friction
item *is*, how it is triaged/deduped/ranked, how a cluster becomes a design ruling, and who reviews that the change
worked. So the set shrinks: **1 merge, 1 extend-and-merge, 4 new, and 1 that is a governance change.**

## 1. The placement tree (one source, one level)

From the seat-skills ruling (`ai_docs/core-architecture/seat-skills.md` §1–§2): a skill used by more than one room
goes in `share/`; more than one seat of one room goes in `rooms/<room>/`; exactly one seat goes in
`rooms/<room>/<seat>/`. A copy at two levels is not allowed. `client/` skills are for the LLM running the client and
are **never delivered to a seat**. One source under `agenthub_client/skills`; the runtime installs the
resolved tree under the seat's own `skills/` at every seat start, so a change reaches a seat at its next
start; the loader resolves share → room → seat, never `client/`.

The format (`agenthub_client/rust/agenthub-runtime/src/skills/mod.rs`, `parse_skill_file` and `resolve_for_seat`): a
directory that holds `SKILL.md` **is** a skill; a directory without one is a seat folder. A skill's id is its
front-matter `name` (`name` and `description` required; `allowed-tools`, `license`, `metadata.agenthub` and
`seat-type-version` optional). Delivery is `install_seat_skills`
(`agenthub_client/rust/agenthub-runtime/src/supervisor/mod.rs:411`, called at seat start, `:733`): it clears
`<seat dir>/skills/` and copies the resolved tree share → room → seat, so the more specific skill replaces a shared
one of the same name and a skill removed from the tree does not linger. There is no `sync rig`: the `sync` verbs are
pull, messages, connector, bundle, switch, install-checker, offline-install and respawn
(`agenthub_client/internal/clientsync/sync.go`), and nothing writes `agent.yaml`.

Where each of the seven lands:

| Proposed skill | Level | Why |
|---|---|---|
| `share/friction-report` | `share/` | every seat, every room |
| `share/self-check-while-working` | `share/` | every seat, every room |
| `lead/friction-triage` | `rooms/<room>/lead/` | exactly one seat (the lead) |
| `lead/architect-ecosystem-review` | `rooms/<room>/` | two seats of one room (lead + architect) |
| `architect/system-improvement-analysis` | `rooms/<room>/architect/` | exactly one seat (the architect) |
| `lead/autonomy-charter` | `rooms/<room>/lead/` | exactly one seat (the lead) |
| `reviewer/improvement-review` | `rooms/<room>/reviewer/` | exactly one seat (the reviewer) |

Nothing here is single-seat *today* (`seat-skills.md` §1 records `rooms/<room>/<seat>/` as empty); this set would be
its first occupants. If the owner wants the loop to generalize to other rooms, the two `share/` skills already do;
the seat-level ones become a room-level copy per room, or are promoted to `share/` only if a second room needs them.

## 2. The dedupe — every proposed skill, ruled

Evidence: the 13 skills read in full (delivered tree `/home/daihu/.config/4genthub/state/omp/4genthub-min-architect@4genthub-min/agent/skills/`,
`~/.claude/skills/` for `refocusing`/`client-skills`, and the client source `agenthub_client/skills/`), plus the
existing feedback channel and the oversight governance loops.

### 2.1 `share/friction-report` — **EXTEND the existing channel** (not a new channel)

**Collision (name it):** the friction channel already exists — CLIENT `internal/clientfeedback/feedback.go` (the ONE
writer; `:1-7` "ONE WRITER CONTRACT WITH THE MCP TOOL … the same five fields"; `:57-62` `4genteam feedback --layer
<layer> --text <text> [--room R] [--seat S] [--session X]`; "The owner reads the reports grouped by layer"). Its
`layer` vocabulary is closed: `runtime | client | cloud | seat-context | workspace | other`
(`ai_docs/api-integration/surface-inventory.md:339-350`). The **transport rules** are owned by `comm-guard-skill`
(`--intent <task|escalation|report|question|notice>`); the **durable-item vocabulary** by `queue-handoff`.

**Ruling:** the *content* of a friction report is new; the *transport and the store are not*. So:
- Write the skill as a **pointer + shape**, not a new tool: "when you hit friction, call `4genteam feedback --layer …
  --text …` (or `submit_feedback`), one command, then continue." **Do not invent a second friction channel.**
- The owner's extra field (cost in time or tokens, suggested fix, severity) becomes a **fixed text skeleton** inside
  the `--text` body, not a new payload field — the channel's five fields are a finished contract.
- The owner's "**plus a board item tagged `friction`**" is the genuinely new half: a queue row / board item tagged
  `friction` carrying the same text, so the item is *trackable* where work is tracked while the report itself is
  *read* by the owner in the channel. Keep them one report with two views, never two reports.
- The `layer` values are reused as-is; the owner's `tool` tag maps onto `runtime`/`client`/`cloud` — do not add a
  parallel vocabulary.

### 2.2 `share/self-check-while-working` — **MERGE INTO the existing checks** (thin checklist, no restatement)

**Collision (name it):** each checklist line already has an owner — worktree/branch: `seat-worktree`; changelog:
`changelog-updater`; tests: `test-driven-development` + `verification-before-completion` (its iron law governs
end-of-work claims; a *mid-work* check is a different moment, so the spirit overlaps but the rule does not); tools
and skills: the launch check `F1 cwd / F2 foreign / F3 missing / F4 path / F5 stale` — specified in
`ai_docs/core-architecture/seat-skills.md` §6 (4genthub repo) to run by `up` after every seat launch and by `doctor`
over running seats, implemented on `4genthub-min/go-dev` (`63bf909`) and **not yet landed** — a seat cannot
self-check what `doctor` will measure, and must not restate its codes.

**Ruling:** **merge** — one short start/close checklist that *names the existing checks* rather than copying them
(`seat-worktree` before the first edit; `doctor`'s F-check for tools/skills; `verification-before-completion` before
the claim; `changelog-updater` for the entry). Its only new content is the *moment* (start and close) and the *feed*
into `friction-report`. If it grows past a screen, it has failed and should be cut back.

### 2.3 `lead/friction-triage` — **NEW** (reconcile with oversight, do not duplicate it)

No skill on disk defines triage: dedupe, rank by cost and frequency, name the fix owner, open the board task, close
the loop back to the reporter. **Reconcile:** the closest existing governance is the oversight pod's intervention
ladder (orchestrator-ping → refocus → human escalation, OR `pods/oversight-team/SKILL.md`) and the
`human-in-the-loop` closeout classes (auto-continue / human gate / park, OR `core/human-in-the-loop/SKILL.md`). Triage
must route **through** those, not around them: a friction cluster that is really a lost outcome is a `refocusing`
signal; one that needs a human decision is a `human-in-the-loop` **human gate**, landing as a durable attention
item, never a chat line. A minimum room has no oversight pod; on this room the lead *is* the ladder's first rung.

### 2.4 `lead/architect-ecosystem-review` — **NEW**

No existing skill defines a recurring lead+architect review over the friction board, stuck queue rows and cost rows
producing one ranked improvement list. **Reconcile:** its inputs are existing surfaces (`rig parked`, `the task queue`
stuck rows, the board, the feedback channel grouped by `layer`, the cost rows); its output is a ranked list, which is
new. Keep the cadence decision in §8 — not a fixed daily in the skill text.

### 2.5 `architect/system-improvement-analysis` — **NEW**

How the architect turns a friction cluster into a design ruling, a tool change or a skill edit, with a size and a
builder. No existing skill covers it (`plan-review` is pre-development plan review, human/exec-summary-terminated;
`systematic-debugging` is bug root-cause). It **extends** the architect's existing decision-note format (the
`DECISION-*` notes and the `architect-output-format`): the ruling carries the evidence, at least two options, the
recommendation, the interfaces, and the risks — the same shape the `e2948011` ruling used today.

### 2.6 `lead/autonomy-charter` — **NEW, and a governance change (owner-gated)**

No existing skill states what the lead decides alone versus what MUST go to the owner. Most of the owner's list is
already house law and should be **cited, not restated**: the owner approves every push (project rule), clean code
and a changelog entry per shipped change (`changelog-updater`, project rules), commit locally by pathspec
(`seat-worktree`), no forced/destructive git. The genuinely new content is the **boundary list** and the **digest
shape** (§7). **Because it changes governance, the owner approves it yes/no before it takes effect** (brief §2;
brief acceptance 2).

### 2.7 `reviewer/improvement-review` — **NEW** (must not become a gate)

The reviewer checks that a skill or tool edit actually lowered the friction it cites. No existing skill covers it.
**Reconcile:** the reviewer already owns a verdict in the merge routine (`seat-worktree`: merge routine with
reviewer verdict) — this skill must reuse that path, not add a second gate. And `development-team` explicitly
forbids manufactured obligations ("Do not create obligations just to keep an idle QA, guard or reviewer occupied"),
so the review is **evidence-backed and optional per change**, never a standing committee: measured before/after, or
it does not happen.

### 2.8 Summary table

| # | Proposed | Verdict | Collision it must respect |
|---|---|---|---|
| 1 | `share/friction-report` | **EXTEND** (existing channel) | `internal/clientfeedback/feedback.go`; `comm-guard-skill` transport; `queue-handoff` item vocabulary; `surface-inventory.md:339-350` |
| 2 | `share/self-check-while-working` | **MERGE** | `seat-worktree`, `changelog-updater`, `test-driven-development`, `verification-before-completion`, `doctor` F1–F5 (`seat-skills.md` §6) |
| 3 | `lead/friction-triage` | **NEW** | reconcile oversight ladder + `human-in-the-loop` |
| 4 | `lead/architect-ecosystem-review` | **NEW** | inputs are `rig parked`/queue/board/cost rows; reconcile oversight |
| 5 | `architect/system-improvement-analysis` | **NEW** | extends the architect decision-note format; not `plan-review` |
| 6 | `lead/autonomy-charter` | **NEW, owner-gated** | cites the push/changelog/worktree rules; does not restate them |
| 7 | `reviewer/improvement-review` | **NEW** | reviewer verdict path (`seat-worktree`); `development-team`'s no-manufactured-obligations |

**Also touched (must not be bypassed):** `client-skills` is the shipped index — any new skill is registered there
(EXTEND, not a parallel index); `token-economy` shapes the report text; `changelog-updater` records the landed change.

## 3. Routing: report → triage → fix → close (reuse, don't invent)

```
seat hits friction
  └─ 4genteam feedback --layer <climate> --text <skeleton>        (existing channel; owner reads by layer)
  └─ queue row / board item tagged friction                        (existing queue; trackable)
        └─ lead triage: dedupe · rank by cost × frequency · name the fix owner
              └─ board task → fix owner: go-dev (client `tool`) | fe-dev (UI) | architect (ruling/skill) | lead
                    └─ fix lands (local commit, changelog entry, reviewer verdict where it is code)
                          └─ reviewer/improvement-review: did the cited friction drop? (measured before/after)
                                └─ close the loop back to the reporting seat (queue-handoff, `handed_off_to`)
```

Every arrow is an existing mechanism. The only new artifacts are the funnel's *decision points* (triage,
ecosystem review, improvement review), which is exactly the gap §0 names.

## 4. Triage rules (lead)

1. **Dedupe on the `layer` + the symptom**, not on the reporter: the same missing tool reported by three seats is
   one item with frequency 3.
2. **Rank by cost × frequency**, in the four currencies the report already carries (time, tokens, blocked work,
   risk). A one-off cosmetic is dropped without ceremony.
3. **Name one fix owner** (never a committee) and **one size** (ruling / tool edit / skill edit / doc fix / drop).
4. **Close the loop back to the reporter** — the seat that filed it hears the outcome, or the loop dies and the next
   report is silent.
5. **A rule that blocks good work is a first-class report**, not a workaround (owner's "no silent workarounds"): the
   seat reports and continues; if the rule is genuinely wrong, triage sends it to the owner as a rule change.

## 5. The review cadence and its inputs (lead + architect)

**Inputs (all existing):** the feedback channel grouped by `layer`; the board's `friction` items; stuck queue rows
(`rig parked`, blocked items); cost rows.
**Output:** one ranked improvement list — new skills, tool edits, constraint changes, doc fixes — each with a size
and a builder.
**Cadence:** a lead decision (§8); per batch is the cheapest first cut, daily only if the trial shows it earns its
cost. The brief's own guard applies: the review must not become busywork.

## 6. Cost rules (part C, as design)

- A report is **one command** (`4genteam feedback …`) or **one board call** — never a form.
- The **owner digest is capped at the top 3 decisions**; the rest wait for the next digest. A digest line is:
  *decision needed · options · recommendation · deadline*.
- Nothing in the loop may require a new daemon route, a new service, or a standing meeting.

## 7. The digest shape (owner-facing)

```
Top 3 decisions this cycle            (never more; overflow waits)
1. <decision needed>
   options: <a | b>   recommendation: <x>   by: <deadline>
2. …
3. …
Held: <n> lower-ranked items (see the friction board)
```
No narrative, no status theatre. Anything the owner does not decide is not in the digest.

## 8. Open decisions

**Only the owner can decide (governance, irreversible-ish):**
- **The autonomy charter (skill 6), yes/no, before it takes effect.** It moves the boundary of what the lead decides
  alone. (Owner-gated per the brief.)

**The lead must ratify (mechanics):**
- Accept the **dedupe**: `friction-report` **extends the existing `feedback` channel** rather than adding a command,
  and `self-check-while-working` **merges** into the existing checks (i.e. no new channel, no restated rules).
- The **triage rules** (§4), the **cadence** (§5), the **digest cap** (§6/§7), and the `friction` tag mechanics
  (queue row + board item, one report two views).
- The **levels** in §1 (including the first-ever `rooms/<room>/<seat>/` occupants).

**Step 2 (lead, board `48281f6a`):** ratify the charter boundaries, create one board task per skill, assign —
architect drafts the skill text, reviewer checks it, go-dev wires the delivery.
**Step 3 (lead, board `ec172e05`):** land the skills, run one trial batch, do the first ecosystem review, send the
owner the digest.

## 9. What this step does NOT do

No skill text, no code, no new route, no board task. Design only — acceptance 3.

## 10. Measured inventory (what "the 16 on disk" is)

- `share/` (client-owned source, `agenthub_client/skills/share/`), **11** when measured: agent-browser,
  changelog-updater, development-team, dogfood, safe-file-removal, seat-worktree, systematic-debugging,
  test-driven-development, token-economy, unused-code-cleanup, verification-before-completion. **18** on 2026-10-18:
  those plus flow-summary, jev-decisions, queue-row-schema, responsible-engineer, room-decision-request, short-output,
  typesafe-ai.
- `client/` (never delivered to a seat), **5** when measured: offpeak-gate, rig-runtime-switch, seat-runtime-switch,
  spawn-team, watch-team — the seat-skills ruling §1 listed four and was one short. **6** on 2026-10-18: those plus
  install.
- `rooms/` (the room- and seat-level location): an **empty placeholder** when measured; `rooms/4genthub-min/` held
  7 skills across 5 seats on 2026-10-18 (architect-role, fe-4genthub-driven, fe-dev-role, taste-skill, go-dev-role,
  lead-role, reviewer-role), so the set in §1 is no longer its first occupants. The layout is `resolve_for_seat`
  (`agenthub_client/rust/agenthub-runtime/src/skills/mod.rs`).
- Delivered but not yet client-owned (cloud snapshot / 4genteam vendored), among the 18 skills in the architect's
  delivered tree: comm-guard-skill, queue-handoff, plan-review, refocusing, client-skills, plus four cloud leftovers
  the per-start install drops, since a skill absent from the tree is not installed. The seat-skills ruling §1 plans
  to fold comm-guard-skill and queue-handoff into `share/`;
  that copy has not landed (no `agenthub_client/skills` source exists for them).

## 11. References

- Placement/delivery/check: `ai_docs/core-architecture/seat-skills.md` (ruling 2026-10-11).
- Existing friction channel: `agenthub_client/internal/clientfeedback/feedback.go`;
  `ai_docs/api-integration/surface-inventory.md` §1.21.
- Handoff vocabulary: skill `queue-handoff`. Transport policy: skill `comm-guard-skill`.
- Oversight loops: 4genteam `pods/oversight-team`, `core/human-in-the-loop`.
