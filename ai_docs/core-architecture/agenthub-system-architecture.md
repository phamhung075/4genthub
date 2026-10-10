# 4genthub: architecture, product and decisions (single source of truth)

Consolidated 2026-10-08 from the architect's orchestration architecture, the product requirements, the technical reference, the earlier product-architecture overview and eight decision notes. Those files are deleted in the next commit; their text is in git history (see section 10). This file is rewritten, not pasted: where two sources said the same thing it says it once, and where a source was stale it states the current fact.

**How to read it.** Section 1 is what the product is for. Section 2 is the architecture and what is built. Section 3 is the platform reference (stack, API, MCP tools, websocket, auth, database, workflow). Section 4 holds the decisions as dated sections, each with its status. Section 5 lists what was proposed and never built. Section 6 lists the owner decisions still open. Two working trackers stay separate and are linked from section 10: `agenthub_go/NEXT_GEN.md` (the work queue) and `agenthub_go/MIGRATION.md` (the Python-to-Go parity record).

**Labels used for components:**

- **BUILT**: the code exists and is wired into the running server or client.
- **PARTIAL**: some of it exists; the missing half is named.
- **NEW**: not in the tree. The work item is in `agenthub_go/NEXT_GEN.md`, group O.

Facts here were measured on 2026-10-08. Counts (routes, tables, tools) are owned by `ai_docs/api-integration/surface-inventory.md`, which re-derives them with `COUNTS-AUDIT.py`; this file names them only where a decision depends on one, and dates them.

---

## 1. Product

### 1.1 Purpose and KPI

4genthub turns a software goal into tasks that are executed, verified and continued by several AI models working as a team. It does not need to be the strongest model; its job is to make the models work together correctly.

**KPI: verified software per unit of human attention.** Lines of code produced is not progress. Section 2.12 defines both terms as counts over the execution ledger, so the KPI is computed and not estimated.

The lasting value is in context, the task graph, agent routing, execution state, verification, observability, resume and project memory. Code generation alone is becoming a commodity.

### 1.2 Problems it addresses

- **Context loss**: an AI forgets earlier sessions and decisions.
- **Tool fragmentation**: several disconnected AI tools.
- **Workflow isolation**: AI work happens in isolation, so a team cannot share or review it.
- **Progress invisibility**: no view of what agents did or how several coordinate.
- **Self-certification**: an agent's account of its own work is a claim, not a fact (this is the reason for the evidence and gate design in 2.6 and 2.7).

### 1.3 Users

| Persona | Needs | What 4genthub gives |
|---|---|---|
| Solo developer | Ship faster with AI, keep quality | Persistent context, seats per role, visible progress |
| Tech lead (5-10 developers) | Coordinate AI-assisted work, audit AI contributions | Seats and rooms, the task ledger, review through the gate |
| Non-technical product owner | Understand progress without a terminal | The web dashboard, plain-language task views, the KPI panel |

Secondary: DevOps engineers (deployment automation), security auditors (audit trail), documentation writers.

### 1.4 Capabilities and their state

| Capability | State |
|---|---|
| Web dashboard (React): projects, branches, tasks, subtasks, seats, topology, sessions | BUILT |
| Four-level context records with inheritance and delegation | BUILT |
| Task graph with dependencies, status machine, assignees, subtasks | BUILT (assignees are legacy role names, see 2.3) |
| Seats, rooms, versioned seat types, overlays, rendered seat files | BUILT |
| MCP interface at `POST /mcp` | BUILT |
| Keycloak authentication, multi-tenant isolation | BUILT |
| Real-time sync over websocket v2.0 | BUILT |
| Execution ledger, evidence, validation gate, wake, task resume | NEW (section 2.5-2.9) |
| Work survives a 4genthub cloud outage: with the cloud unreachable and the model API (DeepSeek or Claude) reachable, seats would keep working through a local MCP endpoint in the client, record facts, queue decisions, and sync on reconnect | DEFERRED by the owner 2026-10-08, not a current goal: a design only (D9 part 3), not built and not scheduled. Fully offline inference with local models is also deferred |
| Agent library of 42+ specialised role templates | RETIRED. Agents are registry rows managed through `manage_agent`; roles come from seat types |
| "Dynamic Tool Enforcement v2.0" through `call_agent` | RETIRED. Per-seat tool scope comes from the seat's `tool`, `mcp` and `policy` modules |
| AI "vision system" enrichment and in-server AI planning | Not wired (section 2.3 and 2.13) |
| Agent knowledge and skill management (RAG) | Proposal only, never built (section 5) |

### 1.5 Non-functional targets

These come from the original product requirements and are targets, not measurements: under 200 ms average API response; context operations under 5 ms of sync overhead; 99.9% uptime for the core MCP service; 10-50 concurrent users at the current capacity; user isolation on every query; audit logging for operations. The scaling tiers in the old requirements (1K, 10K and 1M requests per second, microservices, service mesh, multi-region, edge) were dated 2025, none was started, and none is part of the current plan. The status of the product at the last requirements revision was "production not ready".

### 1.6 Open product questions (from the requirements, unanswered)

Pricing model; third-party agent marketplace; on-premise or air-gapped deployment; UI languages; native mobile apps. Not committed: model selection per user, user-trained agents, workflow templates, an integration marketplace (GitHub, Jira, Slack), direct code generation from natural language, voice.

---

## 2. Architecture

### 2.1 The flow, and where each step lives

```
Human: goal / requirement
  |
  v
Orchestrator  = lead seat (brain model) + task graph in the cloud          [BUILT: seats, tasks; PARTIAL: routing]
  |  manage_project / manage_git_branch / manage_task / manage_subtask
  v
Brain seats   (Claude: requirements, architecture, review;                 [BUILT as seats; NEW: escalation target use]
               Gemini/agy: alternative reasoning, large context)
  |  MCP: manage_task, manage_subtask, manage_context, call_seat
  v
Worker seats  (DeepSeek via omp / deepseek-offload, Codex, Claude)         [BUILT as seats]
  |  edit files, commit locally
  v
Git + tests on the user's machine                                          [outside 4genthub]
  |  agenthub-client evidence  (the client collects; the agent does not report)
  v
Evidence in the cloud                                                      [NEW]
  |
  v
Validation gate: deterministic checks, then Jev                            [NEW]
  |-- ACCEPT    -> task done; the verified facts are appended to branch memory
  |-- REJECT    -> task back to in_progress with the reasons; the same seat is woken
  '-- UNCERTAIN -> the escalates_to seat (a brain); a human only if the brain cannot settle it
  |
  v
Every step above is written to the execution ledger (task_events)
  -> observable state machine, resume brief, wake-on-open-work, KPI
```

### 2.2 Responsibility split

| Layer | Owns | Never does |
|---|---|---|
| **Cloud** (`agenthub_go`, Postgres) | The system of record: projects, branches, tasks, subtasks, contexts, seats and rooms, the execution ledger, gate verdicts. Renders seat files and runs the gate. | Calls brain or worker models (the gate's Jev call is the one model call), reads the user's repository, reaches into the user's machine (the pull model, NEXT_GEN "Direction"). |
| **Client** (OpenRig `rig` and daemon, `scripts/openrig_*.py`, later the `agenthub-client` binary) | Launching and supervising seats, rendering seat files to disk, reporting seat status, collecting git and test evidence, delivering wake messages with `rig send`. | Decides task state on its own. Claims and verdicts come from the cloud. |
| **Models** (seats) | Planning, implementing, reviewing. They reach the cloud only through MCP tools. | Write to the database directly, or certify their own work. |

**Why the cloud does not run models.** The in-server AI planning path (`fastmcp/ai_task_planning`, about 3,000 lines, and the five `ai_*` actions of `manage_task`) is not wired. Since `a8ff89da` it refuses with "the AITaskIntegrationService seam is not wired in this build" (`ai_handler.go:301`). Brains and workers already run as seats on the client, where their tools, files and credentials are; a server-side model runtime would be a second place that plans work. Whether the dead path is deleted is the owner's open decision (NEXT_GEN directive 3).

### 2.3 Seats, MCP interface, task graph, context

**Seats and rooms: BUILT.** `fastmcp/seat_management`. A seat is a durable position (a key in a room); the occupant is runtime plus model. Seat types are versioned. Overlays fold in at company, room and seat level with `add`, `remove`, `override` and `pin`. Module kinds are `instruction`, `document`, `skill`, `tool`, `mcp`, `memory` and `policy` (`resolver.go:17-29`, `ck_modules_kind`). The renderer emits OpenRig AgentSpec and RigSpec files. `seat_links` carries `delegates_to`, `spawned_by`, `can_observe`, `collaborates_with` and `escalates_to`. Supported runtimes are `claude-code`, `codex`, `omp` and `agy` (decision D5); `codex` and `agy` receive no Claude fragments. "Brain" and "worker" are roles given by seat type and occupant, not a separate mechanism: a brain is a seat whose occupant is a reasoning model and that is the `escalates_to` target of worker seats.

**MCP interface: BUILT, with two gaps.** Transport is `POST /mcp` (JSON-RPC 2.0) and `GET /mcp` (SSE). Tools registered in the Go server: `manage_project`, `manage_git_branch`, `manage_task`, `manage_subtask`, `manage_context`, `manage_agent`, `manage_seat`, `call_seat`, `submit_feedback`, `manage_connection`. The earlier technical reference listed nine and omitted `submit_feedback`; the tool list is owned by `surface-inventory.md` section 2 and checked against `interface/testdata/tools_golden.json`. `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list` and `notifications/initialized` are protocol methods, not tools. The `call_agent` tool is removed; it survives only as a field of `manage_agent`; the seat model (`call_seat`, `manage_seat`) replaces it.

- **`manage_rule` is not registered.** A facade exists (`rule_application_facade.go`). Rules are delivered as seat modules (`instruction`, `policy`), so rules stay there and no `manage_rule` tool is added; with both, a rule would have two homes.
- **Calls carry no seat identity.** Only the user is known (bearer token). The ledger needs the acting seat, so item O2 adds a header `X-Agenthub-Seat: <room>/<seat>` to each rendered MCP block. It is used for attribution, not authorization.

**Task graph: BUILT; routing PARTIAL.** Project, git branch, task, subtask, with `task_dependencies` and cycle checks (`Task.HasCircularDependency`). Statuses and transitions (`value_objects/task_status.go:12-37`):

```
todo -> in_progress | cancelled | done
in_progress -> blocked | review | testing | cancelled | done
blocked -> in_progress | cancelled
review -> in_progress | testing | done | cancelled
testing -> in_progress | review | done | cancelled
done -> in_progress        cancelled -> todo        archived: final
```

Gaps:

1. **Assignees are legacy agent role names**, such as `@coding-agent` (`entities/task.go:326`, `ResolveLegacyRole`), not seat keys, so a task cannot be routed to a seat. The recommended fix (assignee is the user's seat key) is not built.
2. **No structured acceptance criteria.** `manage_task` accepts `completion_summary` and `testing_notes` only. The column `ai_completion_criteria` belongs to the dead AI path.
3. **`todo -> done` and `in_progress -> done` are allowed directly.** When the gate enforces, `done` must be reachable only through a gate verdict (item O5).

**Context: BUILT; composition PARTIAL.** Four levels: global (per user), project, branch, task (`*_contexts` tables), served at `/api/v2/contexts/{level}`. Each level inherits from its parent, is identified by UUID, is created on demand and is isolated per user. `manage_context` provides `create`, `get`, `update`, `delete`, `list`, `resolve` (inheritance applied), `delegate`, `add_insight` and `add_progress`. The task context has slots for `implementation_notes`, `test_results`, `blockers` and `local_decisions` (`models.go:537`). The platform's composition model for a seat is the overlay chain company, room, seat; the four context levels are not that model. The context-pack algebra (`seat_management/domain/contextpacks`: FRESH, HANDOVER and POST-COMPACTION profiles with token budgets) is built and tested but **has no caller outside its tests**. Because context may matter more than the model, the architecture makes the resume brief (2.9) the main product of context, not a dump of the context row.

### 2.4 Components at a glance

| # | Component | State | Where |
|---|---|---|---|
| 1 | Seats and rooms | BUILT | 2.3 |
| 2 | MCP interface | BUILT, 2 gaps | 2.3 |
| 3 | Task graph | BUILT, routing PARTIAL | 2.3 |
| 4 | Context | BUILT, composition PARTIAL | 2.3 |
| 5 | Execution ledger (`task_events`) | NEW; table, controller and routes exist in the tree, the single-writer discipline and parity test are the open part | 2.5 |
| 6 | Evidence (git and tests) | NEW | 2.6 |
| 7 | Validation gate | NEW | 2.7 |
| 8 | Wake-on-open-work | NEW | 2.8 |
| 9 | Resume brief | NEW | 2.9 |
| 10 | Project memory | PARTIAL | 2.10 |
| 11 | Observability surfaces | BUILT / NEW | 2.11 |

### 2.5 Execution ledger and the observable state machine (NEW)

One append-only table, `task_events`, is the history of every task and subtask. **The task row keeps the current status; the ledger keeps how it got there.** Both are written in one transaction by the task application service, the only writer of either. `progress_history` and `progress_count` on `tasks` stop being written; `add_progress` becomes a `progress` event. This is a clean break, not a parallel store.

| Column | Meaning |
|---|---|
| `id`, `user_id`, `task_id`, `subtask_id` (nullable), `seq` (per task, gapless) | identity and order |
| `kind` | closed vocabulary with a CHECK: `planned`, `assigned`, `claimed`, `delivered`, `context_loaded`, `progress`, `status_changed`, `evidence_submitted`, `gate_verdict`, `escalated`, `human_decision`, `handover` |
| `actor_kind`, `actor` | `seat` (seat key from the MCP header), `client` (machine id from the request), `gate`, or `human` (user id) |
| `payload` JSONB | kind-specific; evidence and verdicts live here, so no second table holds them |
| `created_at` | server time |

Worked example (owner's TASK-142: plan, context, implement, test with 2 failures, fix, test, Jev, complete). It reads off the ledger as: `planned`, `assigned`/`claimed`, `context_loaded`, `progress`, `evidence_submitted` (2 failed), `gate_verdict` REJECT, `progress`, `evidence_submitted` (0 failed), `gate_verdict` ACCEPT, `status_changed` done. **The phase a viewer sees is derived from the last events and is never stored as a second status.**

Existing streams stay as they are: `agent_session_events` (session transcripts), `seat_status` (what a machine reports), `missed_notifications` (websocket replay). The ledger is about work; those are about sessions and seats.

### 2.6 Evidence: git and tests (NEW)

The server cannot see the repository, and an agent's account of its work is a claim. So evidence is **produced by the client binary, not reported by the agent**: `agenthub-client evidence --task <id> --base <sha> --test "<command>"` runs `git diff --numstat <base>..HEAD` and the test command itself, then posts the result authenticated by the user token `AGENTHUB_TOKEN`:

```json
{"base_sha": "...", "head_sha": "...", "branch": "...",
 "files_changed": [{"path": "a.go", "added": 12, "deleted": 3}],
 "tests": [{"command": "go test ./fastmcp/x/...", "exit_code": 0, "failed": [], "duration_ms": 8123}],
 "machine_id": "...", "collected_at": "..."}
```

Stored as an `evidence_submitted` event. File contents and test output bodies stay on the machine; only paths, counts, names and exit codes reach the cloud (whether paths and test names may go to the Jev provider is an owner decision, section 6).

The client binary (`cmd/agenthubclient`, verbs in `internal/clientsync`, bridge in `internal/clientbridge`) runs `sync status`, `sync pull`, `sync connector` and the bridge. `sync rig`, `bundle`, `switch` and `watch` refuse with a pointer to `openrig_seat_sync.py`; `feedback` and `seatcheck` are pending (measured 2026-10-08). Evidence is a new subcommand beside them.

**CORRECTED 2026-10-10 (writer seat, measured by building and running the client at the pin `80cc766`: `go build -o /tmp/4genteam ./cmd/4genteam`): four claims in the paragraph above are false of this tree.** (1) The client binary is **`4genteam`** (`cmd/4genteam`), not `cmd/agenthubclient`. (2) Its command surface is the registry at `agenthub_client/cmd/4genteam/main.go:98-108` — **nine Go packages** (`clientsync`, `clientbridge`, `clientlifecycle`, `clientoffpeak`, `clientseat`, `clientpolicy`, `clientteam`, `clientwatch`, `clientfeedback`, `clientrestore`) **plus one deliberate refusal** (`pending("seatcheck", …)`) — which `4genteam --help` prints together with `up`, `compact`, `stop`, `status`, `log`, `ui`, `compact-run`, `grid`, `feed`, `inputs`, `input`, `continue`, `watchdog` and `version`. (3) **`sync rig`, `sync bundle` and `sync switch` are BUILT, not refusals** — each answers with its own usage (`4genteam sync rig ROOM [--out DIR] [--update] [--state-root DIR] [--skills-root DIR]`), and the verb the client does **not** have is `sync watch` (`4genteam sync: unknown verb "watch"; the verbs are status, pull, messages, connector, rig, bundle, switch, install-checker, offline-install, respawn`). **Nothing points at `openrig_seat_sync.py`:** the pinned client tree holds **zero** `.py` files (`git -C agenthub_client ls-files '*.py' | wc -l` → `0`) and **zero** `scripts/openrig*` paths. (4) **`4genteam evidence` DOES NOT EXIST** — the binary answers `4genteam: unknown command evidence`, and there is no `clientevidence` package (`ls agenthub_client/internal/` lists `clientbridge`, `clientcmd`, `clientenv`, `clientfeedback`, `clientlifecycle`, `clientoffpeak`, `clientpolicy`, `clientrestore`, `clientseat`, `clientskills`, `clientsync`, `clientteam`, `clientwatch`, `commpolicy`, `seatlog`, `secretscan`), so **the command and the JSON payload above describe a design that is not built in the client**; the **server** half is real (`evidence_submitted` is in the kind vocabulary at `task_event_ensurer.go:59` and the domain entity at `task_event.go:45`). `feedback` is **built** (`internal/clientfeedback/feedback.go`; `4genteam feedback --layer <layer> --text <text>` posts the same payload the MCP tool `submit_feedback` sends), and `seatcheck` is a **deliberate refusal rather than an unfinished verb** (`4genteam seatcheck` → its own binary `cmd/seatcheck`: "This name refuses instead of forwarding, so nothing is half-implemented here").

### 2.7 Validation gate (NEW; the old "G7")

Called directly by the task application service when a seat completes a task or subtask. It is not wired through an event bus: the bus registration `HandleTaskCompleted` was deleted in `e1970dc5`.

1. **Deterministic checks first, in code, with no model:**
   - D1: an evidence event newer than the last `status_changed` exists, from a machine of the same user.
   - D2: `head_sha != base_sha` and `files_changed` is not empty, unless the task is labelled `no-code`.
   - D3: every test `exit_code == 0`.
   - D4: a test named as failed in this task's previous evidence now passes.
   - D5: if the task declares a `scope` (path globs), no changed file falls outside it; a file outside it is flagged.

   A failure of D1, D2 or D3 is a REJECT naming the check; Jev is not called.
2. **Jev answers what code cannot**: does this evidence plus the completion summary satisfy each acceptance criterion? Jev receives the criteria, the summary, the testing notes and the evidence payload, with no transcripts and no file contents. Thresholds live in code.
3. **Verdict:**
   - ACCEPT: every criterion clearly yes, D4 and D5 clean. The task moves `review -> done`.
   - REJECT: any criterion clearly no. The task moves `review -> in_progress`, the reasons go into the event, and the assigned seat is woken (2.8).
   - UNCERTAIN: anything else. An `escalated` event goes to the worker seat's `escalates_to` seat. That brain records its verdict as `actor_kind=seat`. A human is involved only if the brain also returns uncertain.

**Rollout:** (a) shadow mode, logging verdicts without acting; (b) calibrate against the reviewer seat's verdicts; (c) enforce. The Jev API facts (`POST /v1/systemone`, typed questions, confidence on Choice and Score) were recorded on 2026-10-03 and are re-verified against live documentation when the build starts, not assumed.

**Interface.** In: `task_id`, the latest `evidence_submitted` payload, the task's `acceptance_criteria []string`, `completion_summary`, `testing_notes`, and the previous evidence for D4. Out: a `gate_verdict` event with payload `{verdict: accept|reject|uncertain, checks: {D1..D5: pass|fail|flag|skip}, criteria: [{text, answer, confidence}], reasons: [string], mode: shadow|enforce}`, plus the status transition in enforce mode only. Errors: Jev unreachable or over budget gives `uncertain` with reason `jev_unavailable`; a missing gate never becomes an accept. Ownership: the cloud owns verdicts and status; the client owns raw evidence and reports only its summary; Jev receives the input above and nothing else.

### 2.8 Wake-on-open-work (NEW)

Today a seat works only when someone runs `rig send` or a local OpenRig queue item reaches it; the cloud does not know a seat is idle while work assigned to it is open.

- **Assignment** is a seat key (`room/seat`) on the task (gap 1 in 2.3).
- **Claim** goes through the cloud (`manage_task action=claim`). The owner's 2026-10-05 ruling "claims route through the cloud; they are not reported to it" is applied to the task itself: the task is the cloud's work item, with `claimed_by` and `claimed_at`.
- **Wake is a pull.** The client's bridge loop asks `GET /api/v2/openrig/machines/{machine}/work` for open, unclaimed or rejected tasks assigned to seats it runs. For a seat whose `seat_status.state` is idle, it runs `rig send <session> "<one-line pointer: task id and 'manage_task action=resume'>"` and posts a `delivered` event. Delivery is idempotent per (task, last event seq), so a wake is sent once per change. The cloud never pushes.

### 2.9 Resume / continue (NEW)

`manage_task action=resume task_id=...` returns one brief built from the ledger and the resolved context, so the next agent does not undo the previous agent's work: the task, its status and acceptance criteria; the last gate verdict with reasons; the last evidence (files touched, failing tests, head sha); open subtasks and blocking dependencies; the resolved task context; the last `handover` note; and the next action derived from these (for example "fix: D3 failed, `TestX` still fails"). A size budget applies. The brief is the same for a fresh seat, a restarted seat and a different model, which is what makes switching an occupant safe.

### 2.10 Project memory (PARTIAL)

Project and branch contexts already serve as memory, and seat `memory` modules carry seat-level memory. **Added:** on ACCEPT the gate appends one verified line to the branch context (task, head sha, files, tests run), so the branch context shows what is done from verified facts only. Decisions are recorded with `add_insight` category `decision`. No new memory store is introduced.

### 2.11 Observability surfaces

| Surface | State | Source |
|---|---|---|
| Seats, topology, drift | BUILT | `SeatsPage`, `TopologyPage`, `seat_status`, `GET /api/v2/openrig/machines` |
| Session transcripts, live | BUILT | `SessionsPage`, `/ws/sessions`, `agent_session_events` |
| Task timeline (the state machine) | NEW | `task_events` over REST (`GET /api/v2/tasks/{id}/events?after_seq=`), live through the existing task websocket |
| KPI panel | NEW | 2.12 |

### 2.12 KPI, computed from the ledger

- **Verified tasks** = tasks with a `gate_verdict` ACCEPT in enforce mode during the period.
- **Human touches** = events with `actor_kind = human` (decisions, overrides) plus owner approvals recorded as `human_decision`.
- **KPI** = verified tasks / human touches. Two companion figures are reported beside it so the ratio cannot be gamed by skipping review: **rework rate** (REJECT verdicts per ACCEPT) and **escape rate** (tasks reopened `done -> in_progress` after ACCEPT).

The panel (item O8) is computed by one backend query so the counts agree everywhere. This is also why the statistic that two removed routes could not answer is not built separately (D3).

### 2.13 Model additions (migrations first, then Go definitions)

- `task_events`, as in 2.5. `user_id` is on every row; there are no cascading foreign keys (the application deletes events with the task).
- `tasks.acceptance_criteria` (JSONB array of strings), `tasks.scope` (JSONB array of globs), `tasks.claimed_by`, `tasks.claimed_at`. The same four columns go on `subtasks`.
- `tasks.assignees` holds seat keys. The legacy role resolution is removed; the `ai_*` columns follow the owner's decision on NEXT_GEN directive 3.
- `tasks.progress_history` and `tasks.progress_count` are removed once the ledger is the only writer.

### 2.14 Gaps between the vision and the code (measured 2026-10-08)

| Vision element | State in code |
|---|---|
| Orchestrator | The lead seat exists. Routing to seats does not: assignees are legacy role names. |
| Brain/worker roles | Seats and occupants exist. `escalates_to` links exist, but nothing reads them at run time. |
| MCP task/subtask/context | Built. `manage_rule` is not registered (by design). Calls carry no seat identity. |
| Context as the key asset | Four levels and inheritance built. Context packs built with no caller. No resume brief. |
| Git and tests | The cloud holds no git or test facts. `completion_summary` and `testing_notes` are free text from the agent. |
| Jev gate | Not built. Its recorded hook point no longer exists (`e1970dc5`). |
| Observable state machine | The `task_events` table, controller and routes exist; the single-writer rule, `status_changed` parity and the timeline view are the open work (O1, O8). |
| Wake-on-open-work | Not built. OpenRig's local queue wakes seats; the cloud cannot. |
| Resume/continue | Seat-level resume is built by OpenRig (snapshots, session files). Task-level resume is not built. |
| Project memory | Contexts and memory modules built. Nothing writes verified facts into them. |
| Go as the platform | The server is Go. **CORRECTED 2026-10-10 (writer seat): so is the client, and the clause this cell carried — "the client binary is partial (2.6); the remaining sync verbs and `feedback` are still Python scripts" — is false of the pinned tree `80cc766`, which holds zero `.py` files and no `scripts/openrig*` path; the client's surface is the nine Go packages plus the deliberate `seatcheck` refusal at `agenthub_client/cmd/4genteam/main.go:98-108`, and `feedback` is `internal/clientfeedback/feedback.go`.** The Python backend `agenthub_main/` is **REMOVED** (`a50929c6`, 2026-10-09): this cell read "archived and its removal is decided (D2)" when the table was measured on 2026-10-08, and D2's stage 4 has since landed. |

### 2.15 Deliberately not in this architecture

- A server-side LLM runtime for planning (2.2).
- A cloud copy of OpenRig's `queue_items` for task work. The task is the cloud's work item and the local queue stays OpenRig's coordination channel. This affects NEXT_GEN directive (F) item F3 and needs the owner's confirmation (D1).
- `manage_rule` as a tool.
- A second local runtime, in Rust or any other language. Measured 2026-10-08: model generation is 33–75% of active turn time, tools are their own subprocesses, and a compaction stall (about 50 s) is a model call. Sync needs a cursor, an outbox and a cache, which the Go `agenthub-client` provides (D9). The decision reopens only if the owner reverses the 2026-10-08 "no" to 4genthub owning the agent loop, or if a local bottleneck is measured.
- Python parity as a goal. With the backend archived there is no server left to match (D2, D3).

---

## 3. Platform reference

### 3.1 Stack

| Layer | Technology | Port |
|---|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query, React Router, React Hook Form | 3800 |
| Backend | Go (`agenthub_go`, `cmd/agenthub`), `net/http`, FastMCP-compatible MCP layer; DDD layers (domain, application, infrastructure, interface) | 8000 |
| Database | PostgreSQL only (no SQLite, no ORM; `pgx`) | 5432 |
| Auth | Keycloak, JWT bearer tokens | - |
| Websocket | `/ws/realtime`, `/ws/connector`, `/ws/sessions/{id}`, `/ws/metrics`, protocol v2.0 | 8000 |
| Container | Docker, docker-compose; image `Dockerfile.backend.go` | - |

Data flow: user, React frontend, API or MCP tool, application facade, use case, repository, database; domain events flow back through the event broadcaster and the websocket to the frontend's React Query cache.

### 3.2 Frontend

Source tree `agenthub-frontend/src/`: `api/` (clients per resource), `components/` (lazy project, task and subtask lists, `ui/` for shadcn), `hooks/` (`useRealtimeSync.ts`, `useTaskWebSocket.ts`, `useWebSocketV2.ts`), `services/` (`WebSocketClient.ts`, `WebSocketAnimationService.ts`), `types/`, `utils/` (`responseValidator.ts`, `queryClient.ts`), `pages/`. Type declarations are consolidated in `src/types`.

Patterns that matter:

- **Server state lives in React Query.** The websocket does not replace it; it updates the cache.
- **Cache updates merge.** A minimal completion payload lacks fields such as `git_branch_id` and `created_at`, so the handler spreads the existing cached object and then the payload and sets the status explicitly. Replacing the cached object loses fields.
- **One toast per operation.** The backend marks automatic updates with `metadata.source = "system"` against `"user"`; the frontend does not toast system-sourced updates, so the websocket is the single source of notifications.
- **Lazy loading and infinite scroll** for project, task and subtask lists; payloads are validated (`responseValidator.ts`) before they reach the cache.
- **Animation timing**: create 500 ms, update and delete 150 ms (`WebSocketAnimationService.ts`).

### 3.3 Backend layering

Domain (entities, value objects, repository interfaces) has no outward dependency. Application holds use cases and facades; a use case does one thing (create task, complete task) and calls repository interfaces. Infrastructure holds the repository implementations over `pgx`. Interface holds the HTTP routes, the MCP controllers and the websocket mounts (`fastmcp/server/httpapp`). Cross-cutting rules: every query filters by `user_id`; there are no cascading foreign keys, and the application layer performs cascading deletes; configuration comes from environment variables and a missing required variable is an error.

### 3.4 REST

Base `http://localhost:8000`. Resource families under `/api/v2/`: `projects`, `branches`, `tasks` (list, create, get, update, delete, `complete`), `subtasks` (create, list by task, get, update, delete, `complete`), `contexts/{level}`, plus the seat, room, machine and OpenRig routes. Create-task request: `title`, optional `description`, `git_branch_id`, `assignees`, optional `priority` (`low`, `medium`, `high`, `urgent`, `critical`). Responses use `{success, data, meta{persisted, id, timestamp, operation}}`. The full route list and its count are in `surface-inventory.md` section 1.

Removed on purpose: `GET /api/v2/tasks/stats/summary` and `GET /api/tasks/{task_id}` (D3), `/ws/{user_id}`, `/ws/health`, `/ws/stats` (declared out of scope by the owner on 2026-10-06), and `/api/v2/branches/{id}/task-counts` and `/assign-agent` (`c08063d5`, `f33db13a`).

### 3.5 MCP tools

All tools take an `action` field. `manage_task` covers task CRUD, search and dependencies (the `ai_*` actions refuse, 2.2); `manage_subtask` covers subtask CRUD, progress and completion (parent progress updates automatically; subtasks inherit assignees); `manage_project` covers lifecycle and health checks; `manage_git_branch` covers branch CRUD and statistics; `manage_context` covers the four context levels, resolution with inheritance, and delegation upward; `manage_agent` is the agent registry; `manage_seat` lists, gets and sets the occupant of a seat; `call_seat` resolves one seat and its rendered files; `manage_connection` is the health check; `submit_feedback` records seat feedback. Boolean arguments accept `true`, `1`, `yes`, `on`; array arguments accept JSON strings, comma-separated text, or arrays. Completing a task auto-creates its context if missing. Planned additions: `manage_task` actions `claim` and `resume` (2.8, 2.9).

### 3.6 Websocket v2.0

Connect to `ws://localhost:8000/ws/realtime`. Message: `{event, data, metadata{source: user|system, timestamp, operation}}`. Events: `task.created`, `task.updated`, `task.completed`, `task.deleted`, `subtask.created`, `subtask.updated`, `subtask.completed`, `project.created`, `branch.created`. Payloads are minimal on purpose (a completion payload is under 500 bytes against 2 KB or more for the full object). Subtask payloads carry the timestamp fields the frontend validates. Fan-out is `BroadcastDataChange` in `fastmcp/server/routes/websocket_routes.go`; endpoints are mounted in `fastmcp/server/httpapp/ws_mount.go`.

The 2025-11-07 fix established the behaviour above: an error-handling wrapper so one bad message does not stop the handler, merge-style cache updates, the dual cache update on delete, single-source toasts, and a deletion of about 1,000 lines of dead code. The in-memory hub with more than one replica (A8) is an open production-topology decision, tracked in NEXT_GEN and not a gate for anything here.

### 3.7 Authentication and isolation

Keycloak is the source of truth for identity. Login yields a JWT (`sub`, `email`, `preferred_username`, `realm_access.roles`, `exp`, `iat`); the frontend sends it as `Authorization: Bearer`; the server validates it through JWKS on every request (`fastmcp/auth/keycloak_dependencies.go`; environment `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`). The `sub` is the user id on every row and every query. Clients and bridges authenticate with the same user token (`AGENTHUB_TOKEN`); there is no per-machine token. Credentials are in `.env` only and are never read or created by agents.

### 3.8 Database

The Go server describes tables with generated `TableDef` metadata (`database.Tables`), not an ORM. As of `ee71488b` (re-derived 2026-10-08) `database.Tables` holds **39 tables**: 20 core, 3 auth, 14 seat, 2 team. `ProductionTables` declares 6 more that are deliberately not created. The `task_events` table is appended from `task_event_tables.go`. Definition files sit in three trees: `task_management/infrastructure/database/models.go` and `models_prod.go`, `auth/infrastructure/database/models_auth.go`, `seat_management/infrastructure/database/seat_tables.go` and `team_tables.go`.

| Family | Tables |
|---|---|
| Task domain | `tasks`, `subtasks`, `task_assignees`, `task_dependencies`, `task_labels`, `task_contexts`, `task_events` |
| Projects | `projects`, `project_git_branchs` (the actual table name) |
| Contexts | `global_contexts`, `project_contexts`, `branch_contexts`, `task_contexts` |
| Agents | `agents`, `agent_sessions`, `agent_session_events` |
| Auth | `users`, `user_token_balances`, `email_tokens` |
| Seats (13) | `modules`, `module_versions`, `seat_types`, `seat_type_versions`, `rooms`, `seats`, `overlays`, `seat_links`, `resolved_seats`, `seat_settings`, `seat_feedback`, `machines`, `seat_status` |
| Teams (2) | `teams`, `team_members` |

Every runtime table carries `user_id` except the `applied_migrations` ledger. Foreign keys use no `CASCADE`; this is intentional DDD design, with the application layer performing cascades.

**Schema today.** `DatabaseConfig.CreateTables` creates the schema from `database.Tables` plus a PostgreSQL init SQL file inside the Python tree, only when `AUTO_MIGRATE=true`; existing tables are not altered, and patchers fill the gaps. **SUPERSEDED AND CORRECTED 2026-10-10 (writer seat, measured at `652895fc`): it read "four patchers" (`column_ensurers.go`, `ensure_ai_columns.go`, `missing_tables.go`, `auto_migration.go`), and TWO of those files are now deleted — `auto_migration.go` in `a2050430` and the startup runner `fastmcp/database_migrations.go` in `57b9bb3b` — so the live set is THREE: `column_ensurers.go`, `ensure_ai_columns.go`, `missing_tables.go`. `CreateTables` calls `EnsureAIColumnsExist` and then `RunColumnEnsurers` and nothing else (`database_config.go:458`-`:459`). The clause "a PostgreSQL init SQL file inside the Python tree" is overtaken twice: the tree is gone (`a50929c6`) and the file it meant is `agenthub_go/fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql`. And the tree as it now is, stated plainly: `agenthub_go/migrations/` does not exist (`ls` → No such file or directory), the DDL comes from the Go table registry, and the `applied_migrations` ledger is DECLARED WITH NO WRITER — `models_prod.go:29` names it and `:118`-`:125` is its `TableDef` and DDL, while nothing in Go reads or writes it, so it becomes the ledger only when T12's runner writes it.** **Schema after D2 stage 1:** versioned SQL migrations in `agenthub_go/migrations/` (not yet created as of 2026-10-08) become the authority.

**Source-of-truth hierarchy (replaces "ORM model > database > tests").**

1. Prompt input: the owner's explicit requirement.
2. Migrations: `agenthub_go/migrations/*.sql`, append-only; an applied file is never edited, a fix is a new file.
3. Go domain entities and row definitions, which must equal the migrations (`TestSchemaMatchesGoDefinitions` enforces it).
4. The database. A database that differs from the migrations is a defect in the database.
5. Tests: they check behaviour and do not define it.
6. Code.

A character limit, for example, is read from the migration's `VARCHAR(n)` and the entity's validation. When a test fails, fix the code to match the definition, then fix the test; never add a compatibility layer.

### 3.9 Development workflow

- **Start:** backend `cd agenthub_go && go run ./cmd/agenthub`; frontend `cd agenthub-frontend && npm install && npm run dev`; Docker through `docker-system/docker-menu.sh` (S start, R restart, D stop).
- **After a backend change, restart the process.** The Go server is a compiled binary and a running process keeps the old code (`echo "R" | ./docker-system/docker-menu.sh`). Frontend changes reload through Vite HMR.
- **Tests:** backend `cd agenthub_go && go test ./...` (with `-race -count=1` for races; PostgreSQL tests need `AGENTHUB_TEST_PG_URL` or they skip); frontend `cd agenthub-frontend && npm test`; fleet-script tests `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` run from the repository root — **they MOVED out of the archived tree to `scripts/tests/` on 2026-10-08** (D2 stage 2, row `5050cfc8`), so the old `cd agenthub_main && ... src/tests/scripts/` form is UNRUNNABLE now, not merely empty: the tree was removed on 2026-10-09 (`a50929c6`), so the `cd` itself fails and the command exits **2**, and the bare path exits **4** (`file or directory not found`), while at the moment of the move it exited **5, "no tests ran"** against the emptied directory. **Read the exit code WITHOUT a pipe:** a pipeline reports the LAST command's status, so `... | tail` reports 0 whatever pytest said; the run is green only when pytest itself exits 0 and prints the count (**14 passed, 1 warning in 0.14s**, measured 2026-10-09). `--noconftest` matters: without it the repository conftest reaches for PostgreSQL and the run hangs. Write a failing test first.
- **Commits:** Conventional Commits (`feat`, `fix`, `refactor`, `test`, `chore`, `style`, `ai_docs`); update the changelog (ONE new file under `CHANGELOG/`, and `TEST-CHANGELOG.md` when tests change) in the same commit; in the shared repository commit by pathspec (D8).
- **Documentation:** files in `ai_docs/`, kebab-case folders, `index.json` generated by hooks; only an allow-list of root markdown files is allowed (the changelog is the `CHANGELOG/` directory).

---

## 4. Decisions

Every decision below was made or recommended on 2026-10-08 unless a different date is given. Status is what the tree showed on that day; "owner pending" lists what only the owner can approve.

### D1. 4genthub becomes an orchestration layer on one ledger, client-collected evidence and a two-stage gate

**Context.** The owner's vision of 2026-10-08 positions 4genthub as the layer that makes several models build verified software (KPI in 1.1). The code at HEAD `eaa41d18` already had seats, the task graph, four-level context and MCP tools. It had no transition history, no evidence of work, no gate, no cloud-side wake and no task resume. The server never reaches into the user's machine.

**Options.**

- **A. Phases as statuses.** Extend the status enum with `plan`, `context`, `implement`, `test`, `validate`; agents report evidence in `complete`. No new table, but only a current value and no history; agents certify their own work; the enum grows with every phase; phases cannot repeat (test, fix, test).
- **B. Append-only `task_events` ledger with the status kept on the task; evidence produced by the client; the gate runs deterministic checks, then Jev.** One history serves timeline, resume, wake, KPI and calibration; repeated phases are natural; the evidence is facts the agent did not write; existing transitions already fit the gate. Costs a table, one transaction discipline and a new client subcommand.
- **C. Server-side orchestration.** Wire `ai_task_planning`, let the server call models and run tests in a cloud runner. Most control in one place, but it contradicts the pull model, puts model keys and repository access in the cloud and creates a second planner beside the lead seat.

**Decision: B.** It is the only option where the gate checks facts rather than claims and where "observable" means a history. It changes to A only if the owner rules that history is not wanted, and to C only if the owner wants 4genthub to run without OpenRig clients.

**Sub-decisions taken with B.**

1. The task is the cloud's work item; claims live on the task; NEXT_GEN directive (F) F3 (porting OpenRig `queue_items` to the cloud) is not needed for task work. Two ledgers of the same work would diverge. **Needs the owner's confirmation**, because it changes the owner's F2, F4, F3 sequence.
2. Phases are derived from events and never stored as a second status.
3. `progress_history` and `progress_count` stop being written; `add_progress` writes a `progress` event.
4. No `manage_rule` tool; rules are seat modules.
5. Wake is a pull by the client; the cloud does not push.

**Interfaces.** `task_events` (2.5); `GET /api/v2/tasks/{id}/events?after_seq=` (404 on a foreign task); `POST /api/v2/tasks/{id}/evidence` with the user token (401 without one, 409 when `head_sha` is not new); the gate as an in-process service (2.7); `manage_task` actions `claim` and `resume`, and `complete` moving to `review` rather than `done` when the gate enforces; `X-Agenthub-Seat` header (2.3); `GET /api/v2/openrig/machines/{machine}/work` (2.8).

**Risks and detection.**

- Status and event written separately would diverge. Detect: a test that every status write path emits `status_changed` in the same transaction, plus a CI parity query (last `status_changed.new` equals `tasks.status`).
- Gate false accepts from a convincing summary. Detect: shadow-mode calibration against reviewer verdicts and a random audit sample.
- Jev cost and limits are undocumented. Detect: count and log calls per verdict, with a hard daily budget that degrades to `uncertain`.
- Privacy: paths and test names go to the Jev provider. The owner's product choice (section 6).
- Wake storms. Detect: idempotency per (task, last_seq) and a `delivered` count per hour on the KPI panel.

**Status.** Work items are NEXT_GEN group O, in order O1 to O7, with O8 (frontend, KPI panel) once O1 lands and O9 put to the owner. The `task_events` table definition, controller and routes are in the tree; evidence, gate, wake and resume are not. Owner pending: sub-decision 1, the privacy choice.

### D2. Remove the Python backend (`agenthub_main/`) in four stages; migrations become the schema authority

**Provenance.** The owner decided on 2026-10-08, with the rule "all code must be written in Go; whatever the Python server does that Go does not yet do must be ported first". The deletion comes last, alone, in its own commit.

**Premise corrected.** The parity record does not live in the tree being deleted: `agenthub_go/MIGRATION.md` and `agenthub_go/PROD_READINESS_REPORT.md` are tracked outside it and survive. What breaks is the citations from surviving files into `agenthub_main/`: 120 tracked files outside the tree contain the string (45 lines in 31 Go files, 33 lines in eight Markdown files under `agenthub_go/`, 29 files in `ai_docs/`), and the `agenthub_go/*.md` files carry 14 `file.py:N` citations.

**Gate: the gaps that must read PORTED or declared out of scope before deletion.** `MIGRATION.md` still had eight unchecked boxes; each was resolved as follows.

| Box | Verdict |
|---|---|
| Slice 1c-iii-c (domain services, validators, enums) | PORTED; the box is stale. Services 19 and 19, validators 1 and 1, the seven enums live in `domain/value_objects/`. |
| Slice 2 (schema) | UNPORTED: gaps G1 and G2. |
| Slice 3 (application) | PORTED for what the server reaches, apart from G3. Not gaps: the template engine (referenced by no mounted route or tool), the event-handler initialiser (only returns true), `task_event_handlers.py` (reachable only through that initialiser). |
| Slice 4 (routes, MCP tools) | PORTED, apart from G4. The three `/api/v1/analytics/*` routes are not mounted by Python; two branch routes were deleted from Go on purpose; the rest of the nine unmatched paths are prefix-served or appear only in docstrings. MCP tools are checked by `TestToolDefinitionsMatchPythonToolRegistry`; `call_agent` was removed on purpose. |
| Slice 5 (auth) | PORTED at route level; behaviour is proved in G5. |
| Slice 6 (websocket v2, session stream) | PORTED, apart from G4. `/ws/{user_id}`, `/ws/health`, `/ws/stats` were declared out of scope on 2026-10-06. |
| Final (comparison against the running Python server) | REPLACED by G5; the oracle is what is being removed. |
| A8 (in-memory hub with more than one replica) | NOT A GAP; carries over to NEXT_GEN as an open owner decision and does not gate the deletion. |

The gap rows:

- **G1, the init SQL.** Go reads its fresh-database schema from inside `agenthub_main` (`db_initializer.go:72,239`), and `models.go` is "generated" by `tools/gen_models/gen_models.py`, which imports the Python `Base`. Closed by stage 1.
- **G2, path detection keyed on the tree.** Go finds the project root by looking for an `agenthub_main` directory and builds SQLite paths inside it (`directory_utils.go:33,44`, `database_source_manager.go`, `subtask_repository_factory.go`, `dual_mode_config.go:82`). Once the tree is gone this changes answer silently. The Go server is Postgres-only, so remove the SQLite branches; do not re-key them on another directory. Nine Go test files also name the tree; each either reads a file from it (the fixture moves into its own frozen `testdata/`) or only names it (no change).
- **G3, behaviour Go dropped.** Dropped websocket notifications in `delete_branch.go:56` and `delete_project.go:64`; dropped agent created and deleted broadcasts (`agent_application_facade.go:64,149`); `HintManager` not ported; three facade factories returning "is not ported" when their builder seam is unset. For each: show it is unreachable in the running server, or port it. The other ~150 markers get a one-word class (logging, unused-arg, unreachable, ported-elsewhere) in a table.
- **G4, `/ws/task-polling`.** Python serves it; Go does not; no caller was found in the frontend, `scripts/` or `agenthub_go`. Owner question: port it or declare it out of scope. Recommended: out of scope, for the same reason as the three declared on 2026-10-06.
- **G5, proof on the running Go server** (replaces "Final"), against a server built from the stage-3 tree on a scratch database created only by the stage 1 migrations: every path in the inventory answers its documented status for an authorised user and 401 or 403 without auth; MCP `tools/list` matches `tools_golden.json`; Keycloak login and refresh work end to end; `/ws/realtime`, `/ws/connector` and `/ws/sessions/{id}` each deliver one event; `go test ./...` passes with `AGENTHUB_TEST_PG_URL` set so the PostgreSQL tests run and do not skip. The report records the command and its output for each line. A gate that is never run reads as green while it is red.
- **G6, deviations whose oracle disappears.** `MIGRATION.md` records T1, T2, P1, N1 and N2, places where Go chose saner behaviour pending the owner's decision. One owner line closes them: "Go behaviour stands" (recommended). The same applies to the two always-500 task routes (D3).

**Schema authority: options.**

- **A. Versioned SQL migrations** (the owner's shape). `agenthub_go/migrations/NNNN_<name>.sql`, append-only, embedded with `embed.FS`, applied in order by a small runner in the `database` package, recorded in a ledger. Go row structs and `TableDefs` are hand-written and must agree; a Go test enforces it. One file defines each change and the change is reviewable; no ORM; removes the four patchers.
- **B. Go `TableDefs` as authority.** No new mechanism, but `TableDefs` with `createAll` is an ORM-shaped metadata layer that cannot express an `ALTER`, so the patchers stay and grow.
- **C. The live database as authority** (introspect, generate). Rejected: production becomes the definition and a change has no reviewed form before it is applied.

**Decision: A, with three refinements.**

1. "Live schema" in the test means a scratch database built by the migrations inside the test (`AGENTHUB_TEST_PG_URL`), never production. It reads `information_schema` columns, foreign keys and CHECK constraints and compares them with the Go definitions per table: names, SQL type, nullability, referenced tables, CHECK expressions. Comparing names alone would pass a type drift. Checking production for drift is a separate, read-only step the owner runs.
2. `0001_baseline.sql` is captured from the schema Go actually runs on (a `pg_dump --schema-only` of a scratch database created by today's `AUTO_MIGRATE` path), not copied from the Python file. It is reconciled with production in the owner's read-only step; the six `ProductionTables` go in only if production has them. A production database that already exists is marked at `0001` and not re-created; that marking is a production change and needs the owner.
3. The ledger is the already declared `applied_migrations` table (`migration_name` unique, `applied_at`, `success`, `error_message`). No second one. Standard library and `pgx` only: `go.mod` has no migration library and the runner is small.

Removed once the test is green: `createAll` as the creation path, the four patchers, `ExecuteInitSQLFile` and its path function, `tools/gen_models/`, the "generated, do not edit" header, the Python-SQL comparison in `models_prod_test.go`, and `seat_management_postgresql.sql` (folded into `0001`). `seat_ddl_parity_test.go` is superseded by the general test. `AUTO_MIGRATE` keeps its meaning (opt-in); only what it runs changes.

**The stages.** Stages 1 to 3 can run in parallel with G2 to G6; stage 4 waits for all of them.

1. **Source of truth and its test (G1).** go-dev. May touch `agenthub_go/migrations/` (new), the `database` package, `seat_management/infrastructure/`, `tools/gen_models/` (delete), changelogs, NEXT_GEN (A8 moved there). Must not touch `agenthub_main/`, any production database or configuration, `captain-definition*`. Failing first: `TestSchemaMatchesGoDefinitions` with a fixture migration adding a column the Go definitions lack. Negatives: a type drift (`VARCHAR(255)` against `TEXT`) is red; re-running the runner on a migrated database applies nothing; a database with tables but no ledger row is refused, not re-created. Done when `grep -rn agenthub_main agenthub_go/fastmcp/task_management/infrastructure/database --include=*.go` prints nothing.
2. **Script tests move.** skills-dev. `git mv agenthub_main/src/tests/scripts/*.py scripts/tests/` (twelve files; module path `parents[4]` becomes `parents[2]`). Run with `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q`; the criterion is **THE SAME COUNT AS THE OLD PATH AT THE COMMIT IMMEDIATELY BEFORE THE MOVE**, not the literal 315 this plan was written with — measured 319, and the four are attributed per commit (2 from `1a1ae32c`/`7c1270d3`, 2 from `db9d2bc3`, every other file unchanged). The canonical command in the guide-common and guide-reviewer copies changes, with the seed-library lock re-recorded. Owner step: `scripts/tests` is added to the hook's valid-test-path list in the separate `.claude` repository.
3. **CI, docker, hooks, rules.** go-dev for CI and docker; the lead or the principal for the owner's `CLAUDE.local.md`.
   - **The pre-commit config first, and it is load-bearing.** The installed `.git/hooks/pre-commit` points at `agenthub_main/.pre-commit-config.yaml`; with pre-commit 4.4.0 a missing config makes `git commit` exit 1 with no commit, so deleting the tree first would stop every seat's commit, including the revert. Move the config to `scripts/git-hooks/pre-commit-config.yaml`, drop its two `ruff` hooks, keep the generic hooks and the seat-trailer hook; re-installing is an owner step.
   - `.github/workflows/test_coverage.yml`: replace the Python jobs with a Go job (build, vet, test with a PostgreSQL service) and a script-test job; ~~drop the `skip-dirs: 'agenthub_main'` line in `production-deployment.yml` (a deployment workflow edit needs the owner)~~. 2026-10-09: overtaken. The workflow is the never-deploying pipeline (50 of 50 runs failed; build and deploy never ran), so row 8 now asks the owner to delete it with its four scripts instead. The deletion is prepared in `48c0bf71`, which is not on `main`, and lands only with the owner's answer.
   - Docker removed: `Dockerfile.backend.dev`, `Dockerfile.backend.production` and the compose files that build them, plus `docker-compose.yml` and `docker-compose.optimized.yml`, which already point at Dockerfiles that do not exist. Kept: `Dockerfile.backend.go`, `docker-compose.backend-go-frontend.yml`, db-only, pgadmin and the frontend files. `docker-menu.sh` and its libraries lose their Python paths; the Go option becomes the default. The CapRover definitions already build the Go Dockerfile.
   - Python backend scripts removed (`batch-test-runner.py`, `run-tests.py`, `validate_suite.py`, `test-menu.sh`, `start_backend_dev.sh`, and the schema tools `verify_init_schema.py`, `deep_verify_schema.py`, `generate_schema_sql.py`, `compare_schema.py`, `check_fk_cascade.py`, `inspect_database.py`); `backup-production.sh` and the security script lose their Python paths and are reviewed by the owner because they touch production.
   - `CLAUDE.local.md` takes the hierarchy from 3.8 and loses the ORM paths, the Python quick commands and the schema table; the no-compatibility rules stay.
   - **Parity record.** `MIGRATION.md` and `PROD_READINESS_REPORT.md` stay as history with one pointer line at the top: closed by this decision, a Python path cited below resolves at tag `python-backend-final`. That line repairs the 14 citations without rewriting history. The 45 "ports X.py" Go comments stay as provenance. Living guides that name the tree are edited; history stays.
4. **Tag, then deletion, last and alone.** Precondition: G1 to G6 closed, stage 1 to 3 commits on main, G5's report filed. `git tag -a python-backend-final` on the stage-3 head (the owner approves the tag; it stays local until the owner pushes). The deletion commit is `git rm -r --quiet agenthub_main` and nothing else (1,595 tracked files), with the changelog in a separate commit after it, so `git revert` restores exactly the tree. Untracked contents (`.venv`, `venv`, `agenthub_dev.db`, logs, caches) remain on disk and are the owner's to move aside, since `agenthub_dev.db` may hold data. Recovery: `git revert <deletion>` or `git checkout python-backend-final -- agenthub_main`. Acceptance: `go build ./... && go test ./...` with `AGENTHUB_TEST_PG_URL` set; the script tests still pass at the same count; a seat commit succeeds; G5 re-run on the post-deletion build.

**Out of scope for every stage:** `captain-definition*`, production databases, CapRover configuration, `.git/hooks` (owner), `.claude/` (separate repository), the frontend apart from help text, `agenthub_go/internal/clientbridge/testdata/*` (frozen fixtures).

**Python tooling outside the backend (owner answered: backend only).** The eight fleet scripts (`openrig_bridge`, `openrig_compact_supervisor`, `openrig_scrub`, `openrig_seat_client`, `openrig_seat_policy`, `openrig_seat_sync`, `openrig_team_setup`, `openrig_watch_tools`) and their tests survive the backend removal unchanged and move in stage 2. The code-mod tools (`add_future_annotations`, `fix_code_quality`, `modernize_type_hints`) lose their target; the API probes (`test_mcp_crud_suite.py`, `test-keycloak-auth.py`) are candidates for G5's proof; `.claude/hooks/*.py` is a different repository and runtime.

**SUPERSEDED 2026-10-09 (writer seat): THE MOVE HAS HAPPENED, AND THE SCRIPT PATHS ARE GONE.** The eight modules are now in the client package — `agenthub_client/src/agenthub_client/`: `bridge.py`, `compact.py` (was `openrig_compact_supervisor`), `scrub.py`, `seat_client.py`, `seat_policy.py`, `seat_sync.py`, `team_setup.py`, `watch.py` (was `openrig_watch_tools`) — and are reached through the console script `4genteam` (`agenthub_client.cli:main`). **CORRECTED 2026-10-10 (writer seat, at the pinned client commit `eaa6ba7`): THE CLIENT'S PYTHON IS RETIRED IN TURN, SO EVERY MODULE PATH THIS PARAGRAPH NAMES IS GONE TOO.** `git -C agenthub_client ls-tree -r --name-only eaa6ba7 | grep -E '\.py$|pyproject\.toml'` is empty. The eight modules' live homes are `internal/clientbridge`, `internal/clientlifecycle` (compact), `internal/secretscan` (scrub), `internal/clientseat`, `internal/clientpolicy`, `internal/clientsync`, `internal/clientteam` and `internal/clientwatch`, reached through the console script whose dispatch table is `cmd/4genteam/main.go:98`-`:106`. **Every `scripts/openrig_*.py` path and all nine `scripts/tests/test_openrig_*.py` files are absent from the working tree AND the index**: `find scripts -maxdepth 1 -name 'openrig_*.py'` prints nothing, `ls scripts/tests/` is `pytest.ini`, `test_prepare_commit_msg_seat.py`, `test_seat_policy_commit_form.py` and `test_team_roster.py`, and `git ls-files --error-unmatch scripts/openrig_seat_sync.py` exits 1. **The deletion is STAGED, not committed — it is held with the pending line decision — so `git show HEAD:scripts/openrig_seat_sync.py` still resolves while the file on disk does not**, which is why a reader of git history keeps seeing scripts no developer has. So the clause above reads as history: the modules did not move "in stage 2" as separate files, they moved into the package and the script paths were deleted.

**Status — re-verified 2026-10-09 (writer seat), because every item below is a condition and a condition must not be quoted without its date.** G1 is still OPEN, so **stage 1 has not landed**: `ls agenthub_go/migrations/` → *No such file or directory* (2026-10-09). **CORRECTED 2026-10-09 (context-dev) — this clause read "G2's code sites are still live and still key the answer on the tree" when this paragraph was written, and that is no longer true of the tree**: `agenthub_go/fastmcp/task_management/infrastructure/repositories/subtask_repository_factory.go:58,65` **probed** for an `agenthub_main` directory at runtime, which **was** the silent-answer change G2 names. `d1114170` re-keyed that probe the same day, so all five sites (`:58`, `:65`, `:70`, `:79`, `:84`) now name `agenthub_go` and none names `agenthub_main` — read at `5871152b`, which was the tip when this correction was written, and re-checked at `f9886cbe`, the tip before it landed (the file is unchanged between them); `git show HEAD:agenthub_go/fastmcp/task_management/infrastructure/repositories/subtask_repository_factory.go | grep -n 'agenthub_go\|agenthub_main'` prints those five lines and no line naming the archived tree. **Stage 2 IS landed** (this file's own Tests line records it): the twelve script tests left the archived tree at `0ea06c77`, and the canonical command is `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` from the repository root. **CORRECTED 2026-10-09 (writer seat): that command still runs, but it no longer covers the script tests** — the eight `scripts/openrig_*.py` went with the client relocation and the nine `scripts/tests/test_openrig_*.py` files are not in `scripts/tests/` any more, so the directory now holds `pytest.ini` and three files (`test_prepare_commit_msg_seat.py`, `test_seat_policy_commit_form.py`, `test_team_roster.py`). The dated note above carries the measurement; a reader who runs this command expecting twelve tests will see three files collected and should not read the difference as a deleted suite. **The gates live in this section, and nothing live cites the absorbed path**: a `grep -rn architecture-design` over `.md`, `.json`, `.ts`, `.tsx`, `.go`, `.yaml` and `.sh` returns CHANGELOG history lines, one comment inside `agenthub_main/.pre-commit-config.yaml` (a file this decision deletes) and hook logs — **no surviving document** — so the absorbed-path question is a history question, not a link to repair. **The governing constraint is unchanged: the deletion is LAST AND ALONE** — `git rm -r --quiet agenthub_main` and nothing else, with the changelog entry in a separate commit after it. Owner pending: G4, G6, A8 non-gating, the tag, the pre-commit re-install, the CI deployment edit, the production schema read and ledger marking.

**AT HEAD (2026-10-09, writer seat): STAGE 4 HAS LANDED AND THREE CLAUSES ABOVE ARE NOW FALSE — corrected here rather than rewritten in place, so the dated readings stand beside what overtook them.** Measured at `ff94cb83`, by reading the tree and the commits:

- **The deletion is COMMITTED, not staged.** `a50929c6` ("chore: remove agenthub_main, the retired Python backend") removed the tree and `ff94cb83` carries its changelog; `git ls-tree -r --name-only HEAD -- agenthub_main` returns 0 entries and the directory is absent from disk. **The SUPERSEDED paragraph above, which reads "The deletion is STAGED, not committed … `git show HEAD:scripts/openrig_seat_sync.py` still resolves while the file on disk does not", is superseded in turn** — those `git show HEAD:` lookups fail now. **And stage 4's "LAST AND ALONE" constraint is DISCHARGED**: `a50929c6` carries the deletion and `ff94cb83` the changelog in a separate commit, which is the shape the plan required.
- **G2's CODE half landed in the same sweep, so the sentence above is no longer true.** `d1114170` re-keyed every project-root probe from `agenthub_main` to `agenthub_go`: `agenthub_go/fastmcp/task_management/infrastructure/utilities/directory_utils.go:33` (the probe itself: `has := func(dir string) bool { return e.Exists(filepath.Join(dir, "agenthub_go")) }`), `.../repositories/subtask_repository_factory.go:58,65,70,79,84`, `.../database/database_source_manager.go:69,80,88` and `fastmcp/dual_mode_config.go:82` all test for the `agenthub_go` marker now, so nothing in Go probes for a directory the tree no longer has. **TWO CORRECTIONS INSIDE THIS BULLET, both in the class it exists to correct — a citation that RESOLVES while supporting only half its sentence (rule 63). (i) `directory_utils.go:44` was grouped with the probes and is NOT one at this HEAD**: it is a COMMENT inside the block that records the deleted walk ("A second walk used to return the parent of any directory literally named `agenthub_go`"), while `:29` is the function's own doc comment; **at `ff94cb83`, where this paragraph was measured, `:44` WAS the ungated NAME MATCH — so the citation is historically true and it READ AS A PROBE, which is exactly the failure this paragraph was written to correct. `30dfd7e9` deleted that walk, and deleted rather than gated it, because gating would leave an unreachable branch.** **(ii) THE ENUMERATION ABOVE READS AS SETTLED AND IS NOT — THERE IS A FIFTH PROJECT-ROOT RESOLVER, measured rather than inferred.** `agenthub_go/fastmcp/task_management/infrastructure/unified_logging.go:165` `GetProjectRoot()` (the `/app` shortcut at `:166-167`, the comment at `:173`, the loop at `:175-177`) consults **no marker, no `Env.Exists` and no data path**: it returns `/app` when that directory exists, and otherwise walks up a **FIXED FIVE LEVELS** from `os.Executable()` under the comment **"Navigate up from `agenthub_main/src/fastmcp/task_management/infrastructure/`"** — **a DEPTH ASSUMPTION INHERITED FROM THE REMOVED TREE. WHAT IS CLAIMED: that it is a fifth resolver, that its depth is fixed at five, and that the removed tree's nesting is the only reason written beside that number. WHAT IS NOT CLAIMED: that it MISRESOLVES — nobody has shown that, and whether it does is go-dev's question, routed there by the lead (2026-10-09).** **REPORTED, NOT ADJUDICATED, because it reads against a plan clause: G2 said "do not re-key them on another directory", and the sweep re-keyed the project-root finder onto `agenthub_go` — the tree's real marker. Whether that satisfies the clause or departs from it is the lead's to rule**, and it is recorded here rather than settled by the seat that noticed it.
- **G1's "reads its schema from inside `agenthub_main`" is likewise overtaken.** `d1114170` moved the SQL to `agenthub_go/fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql` (744 lines added there) and `db_initializer.go` follows it. **The migrations half is still open**: `ls agenthub_go/migrations/` → *No such file or directory* (measured 2026-10-09), so stage 1 as a whole has not landed and the row's "G1 is still OPEN" reading survives.
- **What did not change, re-measured rather than assumed:** the canonical script-test command still runs from the repository root and reports **14 passed, 1 warning in 0.14s, rc=0** — **a WORKTREE reading dated at `69f7f3a4`, and it travels with its tree now: re-measured 2026-10-09 in the same pass that landed rule 68, the SAME command reads 20 passed, and `scripts/tests/` holds `pytest.ini` plus FOUR test files in the worktree, THIRTEEN at HEAD and NINE staged for deletion (`git status --porcelain -- scripts/tests`). Three counts of one command and all three are correct, because a test count is shared-tree state rather than a property of a commit (rule 68); the three files the CORRECTED note above names were the worktree's set at the earlier reading.**
- **Deliberately LEFT, with the reason for each:** the stage list (1 to 4), the G1–G6 gap text and the stage-3 touch list are the 2026-10-08 **plan** — a plan is a record of what was decided, and rewriting it into past tense would destroy what a reader compares the outcome against; **Provenance** and **Premise corrected.** are dated premises of that decision; the two Go provenance comments that cite `agenthub_main` paths (`agenthub_go/internal/clientsync/sync.go:2`, `status_test.go:12`) are the port's own history and say so; and `agenthub_go/MIGRATION.md:865` is history by the plan's own ruling.

### D3. Remove the two task routes that can only fail; the statistic comes from the ledger

**Context.** `GET /api/v2/tasks/stats/summary` and `GET /api/tasks/{task_id}` always returned 500: their adapter methods (`GetTaskStatistics`, `GetTaskWithRelations`) panicked with Python's AttributeError text, ported deliberately for parity (`agenthub_go/MIGRATION.md:951`, `agenthub_go/PROD_READINESS_REPORT.md:182`, which cover the stats route only). Neither route had a caller: the frontend mentioned them only in its API reference, and the task view loads through `GET /api/v2/tasks/{id}`. The parity reason expired with the archive of the Python backend, and the statistic the product needs is already planned as the O8 KPI panel over the ledger.

**Options.** A. Keep parity, with the 500s documented: two advertised routes that can never answer, legacy code for a server that no longer runs. B. Build a per-status count statistic now: a response shape nobody specified, no caller, and a second source of task numbers before O8 builds the first. C. Remove both routes and both panicking methods.

**Decision: C.** It is the only option where a listed route can also answer, it removes code, and it leaves O8 as the one source of task statistics. B becomes right only if the owner names a consumer needing counts before O8; A only if Python parity is still a goal.

**Shape.** Behaviour-changing for two routes (500 becomes 404), no data model change. Removed in one commit: the two `HandleFunc` registrations, `routes.GetUserTaskStats` and `routes.GetFullTask` with their interface methods, the adapters behind them, `TaskSearchHandler.GetTaskStatistics` and `.GetFullTask`, both methods on `TaskHandlerFacade` and its implementation, and the test fakes; leftovers found by the compiler. Inventory rows updated; the frontend API reference loses its two entries (separate frontend commit). One test caveat measured at implementation: the stats path sits under the prefix route `GET /api/v2/tasks/`, which answers 403 before auth in Go's `ServeMux`, so a 404 can never be observed there and the evidence for that half is the build plus a grep, with the reason written in the test. Must not touch: `GET /api/v2/tasks/{id}`, `GET /api/tasks/{task_id}/context/summary`, `/api/tasks/summaries`.

**Status: executed** in `e6829b32`. At `db9d2bc3` `grep -rq "stats/summary"` over the Go server sources exits 1. The follow-up that stood open here — the frontend `apiReference.ts` entries — was closed in `d624780f` ("fix(apiref): the reference no longer carries the two removed always-500 task routes"): at HEAD `grep -Fc '"/api/tasks/{task_id}"' agenthub-frontend/src/docs/apiReference.ts` -> **0** and `grep -Fc 'stats/summary'` -> **0**.

### D4. `openrig_seat_client.py` retires into `agenthub-client sync`, verb by verb; no fold

**Context.** A queue row asked go-dev to fold `openrig_seat_client.py` (298 lines; verbs `status`, `sync`, `watch`) into `openrig_seat_sync.py` (1,617 lines). The owner's ONE-CLIENT decision (`NEXT_GEN.md:317`) replaces both scripts with one Go binary, with no second copy once parity is shown. The Go client already declares the verbs `status, pull, rig, bundle, switch, watch, connector`; `status` is ported from this script and its test is the parity spec (`internal/clientsync/status.go`, `64f8ecde`); `rig` and `watch` refuse and name `openrig_seat_sync.py` as the authority. The script already delegates `sync` to `openrig_seat_sync.py rig --update`, so no duplicated pinning logic exists to remove.

**Options.** A. Fold now: about 300 lines move into a file that is itself retiring, the doc changes twice, and no duplicated logic is removed. B. No fold: each verb retires into its Go counterpart and the script is deleted in the commit that ports its last verb.

**Decision: B.** The fold contradicts the standing ONE-CLIENT decision by building a Python copy that decision rules out; A is right only if `sync rig` and `sync watch` were never ported, and `NEXT_GEN:317` says they will be.

**Consequences.** The fold row is closed as superseded; nothing a caller depends on is retired now. The sync doc carries one interim sentence: the script is retiring, `status` is already `agenthub-client sync status <room>`, and `sync` and `watch` stay on the script until their Go verbs land. When the port is scheduled, acceptance is: May touch `internal/clientsync`, the script and its test (deleted) and the doc's references; must not touch `openrig_seat_sync.py`; failing first Go tests that port the script's `sync` and `watch` cases, red against the current refusal; an unported verb still refuses with `ExitUnavailable`; exit code `EXIT_BEHIND = 4` is kept; command `cd agenthub_go && go test ./internal/clientsync/... ./cmd/agenthubclient/... -count=1`; afterwards `git grep openrig_seat_client` returns only changelog history.

**Status.** Decided; the script and its test were still in the tree on 2026-10-08, as intended. The retirement belongs to the ONE-CLIENT work.

### D5. Add the `agy` (Gemini/Antigravity) runtime to the Go backend

**Context.** The backend must accept the `agy` runtime for Gemini-powered seats so `manage_seat set_occupant` can record it. Like `codex`, it needs no Claude fragments.

**Options.** A. Reject `codex` and `agy` explicitly in the renderer through a shared predicate. B. Add `agy` to the same validation points and rely on the renderer's existing positive check (`seat.Runtime == RuntimeClaudeCode` gets Claude fragments), updating only comments.

**Decision: B.** The renderer already works positively; keeping that is simpler and less error-prone. Claude models are also rejected on `agy` in `names.ValidateOccupant`, for safety.

**Interfaces.** `resolver.CheckRuntime` accepts `"agy"` and its error message widens; `names.ValidateOccupant` rejects `claude-` models for `agy`; the `seatRuntimes` map in `seat_status_mount.go` accepts `"agy": true`; the `manage_seat` schema description lists `"agy"`. Risk: tests pinning the exact two-runtime error message fail and are updated; a machine reporting `agy` status is rejected if the API enum is missed. Detect through the `resolver`, `names`, `seatrenderer`, `httpapp` and `mcp_controllers` tests.

**Status.** Implemented: `"agy"` appears in seven Go files. The source note recorded no date.

### D6. Every commit carries a `Seat:` trailer added by a git hook

**Context.** Every commit in the tree has the same author name and email, so git cannot name the seat that made it. Two shared-file incidents (`1d6c09d4`, `e66607a9`) had no nameable owner. Every seat shell exports `OPENRIG_SESSION_NAME` (for example `4genthub-min-architect@4genthub-min`), the same address `rig send` uses. `web-dev` already wrote a `Seat:` trailer by hand in 6 of 200 commits, as `4genthub-min.web-dev`, which is not the `rig send` address.

**Options.** A. A board row per workstream: names the owner of a topic, not the seat behind a commit, and works only if every seat files a row. B. A hand-written trailer: relies on ten seats remembering it on every commit, and the format is already inconsistent. C. A `prepare-commit-msg` hook running `git interpret-trailers --in-place --if-exists doNothing --trailer "Seat: $OPENRIG_SESSION_NAME" "$1"`, only when the variable is set.

**Decision: C.** Every seat's commit attributes itself with nothing to remember, the value is a messageable address, and a human's commit (variable unset) gets no trailer and is not refused. The script lives in the repository (`scripts/git-hooks/prepare-commit-msg`); installing it into `.git/hooks` is one owner-approved step. The board stays the record of who owns a workstream. The hook coexists with the runtime's own `Claude-Session:` trailer (a different field naming a session, written only by one runtime). A runtime writing `Seat:` itself (option D) is the owner's to raise with the runtime's maintainers and does not compete; `--if-exists doNothing` keeps one trailer if it ever does.

**Limit.** A trailer names the seat that ran `git commit`, not the author of every line in it; `0c8122a9` carried another seat's two staged lines under go-dev's name. So the trailer and the pre-commit reading (D8) are one fix in two parts.

**Reading.** `git log --format='%h %(trailers:key=Seat,valueonly)'`. After the install, a commit without a `Seat:` trailer positively means "not a seat" (the owner commits from the host); before it, an absence means nothing, so compare the commit date with the install commit. Tests must read the trailer through git's parser, not a `^Key:` grep: prose lines such as `Gates: ...` look like trailers and are not.

**Test.** `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_prepare_commit_msg_seat.py -q` (6 passed on 2026-10-08), covering the variable set and unset, a hand-written trailer not duplicated, and merge or amend messages.

**Status.** The script exists in `scripts/git-hooks/`. Owner pending: installing it into `.git/hooks`, after checking no `prepare-commit-msg` hook exists there already.

### D7. The 4genthub-min room definition follows the live roster

**Context.** The live rig has ten seats: lead, architect, go-dev, fe-dev, web-dev, reviewer, writer, skills-dev, context-dev, feedback-dev. The architect runs on `claude-code` (model `opus`); every other seat runs on `omp`. `go-dev2` had been removed that day, but `team.json` declared a different ten (go-dev2 present, no architect), `openrig_seat_policy.py` listed `"go-dev2": "dev"`, and the seed library shipped a go-dev2 guide. Neither `apply` deletes anything: the team setup `apply` only creates (a first run would have built go-dev2 and never the architect, describing a team that does not exist), and the policy `apply` stops at the first seat with a missing state directory. **Order matters:** if the stale go-dev2 state directory is removed before `SEAT_ROLES` is fixed, the run stops at go-dev2 and never checks the seats after it in the dict.

**Options.** A. Align the definition with the live roster now. B. Hold until an apply is scheduled (keeps the wrong first apply armed). C. Remove go-dev2 only, without declaring the architect (shrinks the mismatch, does not fix it).

**Decision: A.** The definition exists to rebuild the live team, so it lists the live team.

**Shape.** `team.json`: remove the go-dev2 seat, overlay and the two module entries; add `{"seat_key": "architect", "seat_type": "architect", "runtime": "claude-code", "model": "opus"}` with no `pinned_version` (the other seats' `1.3.0` traces to no version field in the seat-type files) and no overlay (the seat type carries the role, and a `policy-*.json` is an omp bash-pattern document). `openrig_seat_policy.py`: remove the go-dev2 line and do not add the architect (the script writes omp config under `~/.openrig/state/omp`, where the architect has no directory, so `apply` would exit at it). Delete `guide-go-dev2.md`, `policy-go-dev2.json`, the seed-library block, its lock entry, the `guides_test.go` entry and the source guide. History files stay as written. The stale state directory `~/.openrig/state/omp/4genthub-min-go-dev2@4genthub-min` is moved aside (not deleted; it may hold transcripts) in a separate owner-approved step after the code commit.

**Guard test.** `test_team_roster.py` asserts the seat keys equal the live ten, the architect is `claude-code`, every overlay key is a declared seat, every module file exists, and the `omp` seats of `team.json` equal the keys of `SEAT_ROLES["4genthub-min"]`, which stops the two writes drifting apart. A seat whose state directory is missing still makes `apply` exit with `EXIT_USAGE`; the guard is not loosened.

**Status.** Applied in the tree: no tracked file in `scripts/team`, the policy script, the seat-management package or the seat guides names go-dev2 any more, and `team.json` declares the architect. Owner pending: moving the stale state directory, and both `apply` runs (separate decisions that nothing here authorises).

### D8. Every seat's instructions say "commit by pathspec, do not stage first"

**Context.** On 2026-10-08 the fleet changed its commit form to `git commit -m "..." -- <paths>` with no earlier `git add`, after four seats lost or took lines through the shared index in under an hour (`0c8122a9`, `e42fdbdc`, and cases in the lead's broadcasts). The change did not hold because the instructions each seat reads first still prescribed the old form: a rule that lives in a message loses to one in the file a seat reads first. The sentence lived in the policy modules' `sibling` text (ten files, nine identical siblings each) and in `guide-common` (three copies: source `ai_docs/operations/seat-guides/_common.md`, `scripts/team/4genthub-min/guide-common.md`, and the embedded shelf under `seedlibrary/shared-modules/`, pinned by sha256 in `guides.lock.json`, which `Load` refuses on mismatch). The live `AGENTS.md` files in each seat's state directory are orphans: their generator was withdrawn in `288fe6ac` and nothing regenerates them.

**Options.** A. Change every copy to the no-prestage form. B. Leave the pre-stage form and rely on the `M ` marker. B fails against the incident's own shape: a whole-file `git add -- <file>` sweeps another seat's unstaged lines into the index and yields `M `, identical to "mine alone". A closes the index window and needs the same reading for the tree window, so A dominates.

**Decision: A.** The wording:

> Commit with `git commit -m "..." -- <paths>` and do not `git add` first: the index is shared, and a staged line can be taken by another seat's commit. A new file is the one exception: mark it with `git add -N -- <new>` (intent-to-add, no content enters the index), then commit it by pathspec like any other file. Just before committing, read `git status --porcelain -- <paths>` (MM: stop) and `git diff HEAD -- <paths>`, and name every line, because the commit takes each file's whole content, including another seat's unsaved edits. If a line is not yours, do not commit that file: commit your other paths, and hold your lines in it until its owner has committed. Never `git add .`, `-A` or `--amend`, and never reset, clean or discard.

Why each clause is there: "just before" because a reading taken after a failed commit reports another seat's work; the new-file exception because `git commit -- <path>` refuses an untracked path, and `git add -N` leaves only the empty blob in the index, so nothing of the seat's is there for another commit to take (measured: a bare `git commit -m` by a second writer after `git add -N` committed only its own file, and the pathspec commit carried the new file; the same commit passed under pre-commit 4.4.0). After `-N`, `git status --porcelain` and `git diff --cached` show nothing for the file by design, so a new file is read with `git diff HEAD -- <paths>`. The existence precondition (`ls <file> && git ls-files --error-unmatch <file>`) stays in the fleet note because it fails by design for a new file.

Siblings need not be identical across the ten policy files: the renderer folds each seat's own modules, so the fold never compares two files; `policy-lead` differs on the lifecycle siblings by design ("the principal does that; ask it."). The test therefore asserts identity on the commit-form matches only.

**Shape.** One repository commit: the ten policy modules, the three `guide-common` copies (the shelf re-copied from the source, ending the existing drift), the lock's `sha256` and `source_sha256` re-recorded, the changelogs. A separate lead-approved step edits the two lines in each of the ten live `AGENTS.md` files, keeping a `AGENTS.md.before-2026-10-08` copy beside each; a running seat takes it at next launch or compaction restore. Tests: a Go test that the embedded `guide-common` contains `do not stage first` and not the old `git add -- <path>` then form; a Python test over `policy-*.json` that no sibling contains `stage explicit paths` and the commit-form siblings are identical; a negative run of `VerifyGuidePairing` through `Load` with the old digest, which must refuse.

**Status.** Applied in the repository: all three `guide-common` copies carry `do not stage first`. The live-file step needs the lead's approval and was not verified here.

### D9. Sync is a server-sequenced ledger with a client cursor and outbox; the local runtime stays the Go `agenthub-client`, not a Rust engine

**This decision went against the owner's original direction, and the owner accepted it on 2026-10-08.** The owner asked for a local Rust runtime as session engine and context optimizer. Part 1 adopts the sync and event model the idea asks for. Part 2 recommended against the Rust runtime and keeping the Go client, on the measurements given there. It was put to the owner as a recommendation, not as an implementation of the request, and the owner accepted it as drafted, including "no" on whether 4genthub owns the agent loop (owner decision 15, closed as no).

**Order of this decision.** The owner asked (2026-10-08) for a "next level" built on a local Rust runtime, and ruled that the sync protocol and event model matter more than Go versus Rust. This note therefore decides the sync and event model first (part 1). The language and runtime question follows in part 2, and is answered from what part 1 needs. This order was chosen on purpose: the language follows from the protocol, not the reverse.

**Context.** The idea ("4gent Runtime/Edge") puts orchestration, tasks, routing, MCP and auth in the Go cloud. A local Rust runtime would own sessions, the context manager, compaction, files, tools, streaming and cache. Context would sync as versioned deltas (`{task_id, context_version, events}`) instead of being resent. Concurrent workers would prepare the next context while the model is still generating. With local models the system would keep working offline. What exists on 2026-10-08:

- `task_events` exists but is not the ledger 2.5 describes. Its kinds are `created`, `updated`, `status_changed`, `completed` and `deleted`, and its actors are `user`, `system` and `agent`. It has no `subtask_id`. `seq` is gapless per task, assigned under `pg_advisory_xact_lock(hashtext(task_id))` with `MAX(seq)+1`. There is no cursor across tasks. Reads are `GET /{task_id}/events?after_seq=`. *Checked by reading* `infrastructure/database/task_event_tables.go`, `task_event_repository.go` and `server/routes/task_event_routes.go`.
- **Nothing emits events.** `TaskEventRecorder` opens its own transaction, so it cannot share the task row's transaction. *Checked by:*
  - `grep -rnE '\.Record\(' --include=*.go agenthub_go`, excluding `_test.go`: the only hit is inside the Go toolchain in `.gomodcache`;
  - `TaskEventRecorder` appears in no non-test file except its own;
  - that file says `NOTHING EMITS EVENTS YET` at line 18.
- The context tables (`global_`, `project_`, `branch_`, `task_contexts`) each carry an integer `version`. *Checked in* `infrastructure/database/models.go` (the `version` column definitions at lines 708, 800, 840 and 948).
- A local runtime already exists in Go: `agenthub-client` (`cmd/agenthubclient`, `internal/clientsync`, `internal/clientbridge`). Its `/ws/connector` client already speaks a cursor protocol: `hello`/`ready`, then `session`/`session_ack {last_seq}`, then `events`/`events_ack {last_seq}`, over `agent_sessions.last_seq` and `agent_session_events (session_id, seq)`. The owner's directive is ONE CLIENT for the local-to-cloud bridge. *Checked by reading* `server/httpapp/ws_mount.go` (the `session` and `events` cases, about lines 334–389), the `agent_sessions` and `agent_session_events` definitions in `models.go`, and the directive in the header comment of `internal/clientsync/connector.go`.
- The model's context never passes through the cloud. Seats run Claude Code or omp, which send the full prompt to a stateless provider API each turn. Prefix caching on the provider side is what makes that cheap, and neither the cloud nor a local runtime of ours sits on that path. *Source:* how the seats are set up, and the providers' prompt-caching documentation as known in 2026. The provider documentation was not re-checked for this note.
- Where turn time goes. *Measured by* a script over three Claude Code transcripts dated 2026-10-08 (sessions `ccd12a01`, `64e2e5da`, `0d77a692`):
  - Model time is the gap from a user or tool-result record to the next assistant record.
  - Tool time is the gap from an assistant `tool_use` record to its `tool_result`.
  - Gaps that start with human or rig input, and gaps of 600 s or more, are excluded.

  Model generation was 75%, 53% and 33% of active time, and tools took the rest. The tool time is subprocesses such as `pytest`, `go test` and builds.
- Compaction stalls. *Measured from* the 17 `compact_boundary` records in two of those transcripts, as the gap from the previous record: 13 were 39–76 s (median 51 s) at about 168k tokens, and 4 were under 10 s. Those 4 are probably gaps the script did not attribute correctly, and they are left out of the median. That time is the model writing the summary.
- Compaction belongs to the harness. `agenthub_client/src/agenthub_client/compact.py` — what `scripts/openrig_compact_supervisor.py` became; run as `4genteam compact`, whose foreground loop is `4genteam compact-run` — tells a seat at 150k to find a safe point, compacts it when quiet, compacts it at once at 250k and aborts its turn at 300k (omp seats through the RPC tool `agenthub_client/rust/forcecompact`; other runtimes through `/compact` and Escape). See `ai_docs/operations/seat-compaction-supervisor.md`. **CORRECTED 2026-10-10 (writer seat, at the pinned client commit `eaa6ba7`): the loop is now `agenthub_client/internal/clientlifecycle/supervisor.go`, the tiers' limits are read by `internal/seatlog/seatlog.go:35` (`ApplyLimits`), and the RPC tool `agenthub_client/rust/forcecompact/` is still present at the pin (four files) — so only the Python names in this bullet are stale.** The context packs (FRESH, HANDOVER, POST-COMPACTION in `seat_management/domain/contextpacks`) are built but have no caller. *Checked by reading* the supervisor (lines 1–60) and from the earlier caller search for the packs, which found no caller.

#### Part 1: the sync and event model

**Options.**

- **A. Server-sequenced ledger, client cursor, idempotent client outbox.** The cloud is the only sequencer. `task_events` gains a per-user gapless `user_seq`, and a client reads "everything after N" across all its tasks. The client writes through an outbox of intents keyed by `client_event_id`. The server accepts each intent with its sequence numbers, or rejects it with a reason and the current task `seq`.
- **B. CRDT, multi-master.** Every client applies its own events locally and states merge.
- **C. Versioned documents with JSON-patch deltas** (the idea's `context_version: 43` shape) as the primary model, one version counter per task or context.

B fails on what the system is for. Claims, status transitions and gate verdicts do not commute. Two clients that each claim a task offline both succeed locally, and no merge rule makes "two owners" or "ACCEPT then REJECT" correct. The gate (2.7) needs one order. C gives each document its own order but none across documents, and the gate needs the order of evidence relative to a verdict on the same task, and of a context change relative to the evidence produced under it. C also turns every reader into a patch applier for a gain nobody has measured: the context documents are small JSON, and their `version` already supports a "changed since" check. A is the only option that keeps the gate correct. It is also the shape the connector already uses for sessions.

**Decision: A, with C kept only as a version check on context documents.** The rule that decides conflicts: **facts sync, decisions sequence.**

- *Facts* are `progress`, `evidence_submitted`, `handover` and `context_loaded`. They are append-only observations, and the client may record them offline. When the client reconnects, the server accepts them in arrival order and keeps the client's time in the payload. A fact is never rejected for being late.
- *Decisions* are `claimed`, `status_changed`, `gate_verdict`, `assigned` and `human_decision`. Each carries `base_seq`, the task `seq` the client had seen. The server rejects one whose `base_seq` is behind the task's current `seq`, unless every event since then is a fact. Offline, a client cannot claim, transition or judge. It queues the intent, and the intent is decided when the client reconnects.
- *Context changes* append a `context_updated {level, id, version}` event, so one cursor covers work and context together. A client holding an older version fetches the whole document; there are no patches.

**Interfaces and shape.**

- Migration on `task_events`:
  - add `user_seq BIGINT NOT NULL` with `UNIQUE (user_id, user_seq)`;
  - add `client_event_id UUID NULL` with `UNIQUE (user_id, client_event_id)`;
  - add `subtask_id UUID NULL`;
  - widen the kind CHECK to the vocabulary in 2.5 plus `context_updated`;
  - change the actor CHECK to 2.5's `seat`, `client`, `gate`, `human`.

  `user_seq` is assigned under a **per-user** advisory lock with `MAX+1`, the same mechanism as today's per-task lock, and the per-task `seq` is computed under the same lock. A `bigserial` cursor is rejected on purpose: values become visible in commit order, not number order, so a reader that has passed N can miss a transaction that took a lower number and committed later.
- `TaskEventRepository.AppendInTx(tx, ev)` lets the task service write the row and its event in one transaction, as 2.5 requires. `Append` remains a wrapper that opens its own transaction.
- `GET /api/v2/ledger?after=<user_seq>&limit=` returns events oldest first, plus the current tip.
- `POST /api/v2/ledger/intents`, body `[{client_event_id, task_id, subtask_id?, kind, base_seq?, payload}]`. For each item it returns `{accepted, user_seq, seq}` or `{rejected, reason, task_seq}`. Resending a `client_event_id` returns the first answer, so the outbox can retry without risk.
- `/ws/connector` gains one server frame, `ledger_tip {user_seq}`. It is a nudge only: the client still pulls with `GET` from its cursor. Correctness has one path, pull, as 2.8 already decides, and the socket only shortens the delay. QUIC is not needed; a nudge is a few bytes.
- `agenthub-client` keeps `{cursor, outbox}` in its state directory. Its bridge loop drains the outbox, pulls past the cursor, and runs the wake in 2.8 from the pulled events instead of a separate `/work` poll. **"Next context ready when the turn ends"** is met here and without a new runtime: when the client pulls an event on a task held by one of its seats, it prefetches that task's resume brief (2.9) and POST-COMPACTION pack. The supervisor or the seat then reads the cached pack after `/compact`, instead of re-reading files.

#### Part 2: the local runtime and its language

**Options.**

- **R1. Keep `agenthub-client` (Go) as the one local runtime** and add the cursor, the outbox and the pack prefetch from part 1 to it.
- **R2. A new Rust runtime as session engine and context optimizer.** It would own the model loop, compaction, tools and streaming.
- **R3. Rust for one measured hot component only** (for example a local file or embedding index), as a separate process or library behind the Go client.

What part 1 needs locally is a cursor, an outbox, a JSON cache and a WebSocket. None of that is bound by CPU or memory, and the Go client already does each kind of work. R2 does not shorten the costs measured above:

- Model time is the provider's.
- Tool time is the tools' own subprocesses.
- A compaction stall is a model call.

R2 can only hide compaction by running the model loop itself, which means replacing Claude Code and omp with a harness of our own. That reverses D1 (4genthub is an orchestration layer over seats), and beside the Go client it would be a second client, against the ONE CLIENT directive. Surviving a 4genthub cloud outage (part 3, a deferred design) would need a local stand-in for the cloud's MCP endpoint, and that fits in the Go client; the model API is not affected. R3 is a fair answer to a measured local bottleneck, but none has been measured.

**Decision: R1. This went against the owner's request for a Rust runtime; the owner accepted it on 2026-10-08.** Section 2.15 keeps "no Rust", and its reason is replaced with these measurements. **Two conditions reopen the decision:**

1. 4genthub takes ownership of the agent loop (owner decision 15). That is the real decision inside the idea. The owner closed it as no on 2026-10-08, so this reopens only by a new owner decision. Language comes after it and is judged against that loop.
2. A measured local bottleneck in `agenthub-client` or a local index costs a significant share of active turn time; this would lead to R3, not R2.

#### Part 3: work that survives the 4genthub cloud being unreachable (DEFERRED design: not built, not scheduled)

**Deferred by the owner on 2026-10-08 (principal relay 20:54Z).** Do not build the local MCP endpoint. This part is recorded as a design only and reopens only if the owner asks. It is not a current goal and implies no NEXT_GEN work items. Parts 1 and 2 stand and are buildable without it.


**How the question was framed before the deferral.** On 2026-10-08 the owner first decided that offline work with local models is a product goal. Later the same day, on learning that no local model is served (below), the owner narrowed it:
- the goal is work that survives the **4genthub cloud** being unreachable while the **model API** (DeepSeek or Claude) is still reachable;
- it is NOT fully offline model inference;
- local models are deferred, to revisit only if one is actually served.

In this decision, "offline" means exactly that: the 4genthub cloud is unreachable, and the model API is not affected. Part 1's offline rule (facts sync; claims, status changes and verdicts wait for the cloud) is unchanged. Owner decision 15 (own the agent loop) is NOT reopened by this goal: the seats keep their harnesses and providers.

**What is true today.** *Measured 2026-10-08:*
- Seats reach the 4genthub cloud through the `agenthub_http` MCP server (`.mcp.json`). With the cloud unreachable, every `manage_task` and `manage_context` call fails, even though the model keeps answering.
- No model is served locally: `curl http://localhost:11434/api/tags` is refused (exit 7), and `ollama` is not on the WSL `PATH`. This is why local models are deferred. For when they are revisited:
  - omp's model cache lists `ollama-cloud` (hosted) and no local provider;
  - the omp binary contains an `ollama` provider and the `llama.cpp`, `lm-studio` and `litellm` discovery types (*checked by* `strings` on the binary, a weaker check than running it).

So surviving a cloud outage needs a local answer to the seats' MCP calls. It needs no change to how seats reach their model.

**Options for the MCP side.**
- **O1. A local MCP endpoint in `agenthub-client`**, which seats use instead of the cloud URL. Online, it forwards every call unchanged. Offline, it:
  - answers reads from the client's cache, labelled with the cursor they were read at;
  - accepts fact writes (`progress`, `evidence_submitted`, `handover`) into the outbox;
  - answers decisions (claim, status change, verdict) with "queued: cloud unreachable" and holds them in the outbox for the cloud to decide.
- **O2. Seats keep the cloud URL, and gain client CLI verbs for offline use** (for example, record a fact into the outbox).

O2 makes a seat behave differently depending on connectivity, so every seat's instructions would need an offline branch. That is a second path that drifts from the first, the same kind of defect as the stale rendered seat files D8 found: a rule kept in two places goes wrong in one of them. O1 keeps one set of instructions for the seat and puts the connectivity difference in one place, the client.

**Design choice, if part 3 is ever reopened: O1.** It would stay in Go, in the one client. This is a recorded preference, not a scheduled build.

**Interfaces.**
- `agenthub-client` serves MCP on a local port, and the seats' `agenthub_http` entry points at it.
- The cache holds:
  - the pulled ledger since the cursor;
  - the context documents at their last `version`;
  - the prefetched resume briefs and packs (part 1).
- An offline read is never presented as current: each answer carries `as_of_user_seq` and `cloud_unreachable: true`.
- On reconnect, the client drains the outbox (facts first, then decisions with their `base_seq`) before forwarding new calls. Rejected decisions are shown to the seat with the server's reason.
- The gate does not run offline. Evidence is recorded as facts, and verdicts wait for the cloud.

**Acceptance test for part 3 (NOT SCHEDULED; it runs only if the owner reopens part 3 and asks for it).** It needs a network block, which the owner does not want now. If it is ever run, it must prove that a seat keeps working on a task with the 4genthub cloud blocked and the model API reachable, through the local MCP endpoint, the cache, the outbox and the queued claims:
- block the client's route to the cloud only, leaving the provider reachable;
- the seat reads its task and context from the cache, records progress and evidence, and has its "done" queued;
- unblock; the outbox drains, the facts appear in the ledger in order, and the queued decision is accepted or rejected with a reason.

**Note on that test: the session hooks, read 2026-10-08.** *Checked by reading the code only; nothing was run against a blocked route.*
- *Proven by reading:* the hooks fail open on errors. `pre_tool_use.py:645-655` wraps context injection in `except Exception: pass`, and its `main` exits 0 on any exception (`:931-943`). `post_tool_use.py:196-205` catches context-sync errors, and its `main` exits 0 (`:339-350`). In `utils/mcp_client.py:559-594`, `_execute_with_retry` returns `None` after its retries and does not raise. `.claude/settings.json` sets no `timeout` on any of its nine hooks.
- *Inferred, not measured:* the hooks are not bounded in wall time on a route that drops packets rather than refusing them. The client's per-request timeout is 10 s (`mcp_client.py:272`) with 3 retries and exponential backoff (`:273-274`), and `OptimizedMCPClient` adds a urllib3 `Retry` on top. `context_updater.py:38` sets `update_timeout_ms` to 1000, but `:571` only compares it after the call has finished, so it is not a bound. `context_injector.py:805,809` waits 1 s, but whether that cancels a blocking `requests` call underneath has not been checked.
- *Requirement if part 3 is reopened:* every hook call to the cloud gets a hard wall-time bound (a hook `timeout` in settings, or one bounded attempt with no retries), so that "fails open" also means "does not stall".

**Risks.**

- **D9 depends on 2.5 being built.** Nothing emits events today, so the cursor has nothing to carry until the task service writes events through `AppendInTx`. That is step one of the build.
- **Lock contention.** The per-user lock serializes all of one user's ledger writes. With about ten seats per user this is acceptable; measure lock wait in the build, and fall back to a per-user sequence row updated in the same transaction if it shows up.
- **Late facts.** A fact recorded offline can arrive after a verdict it predates, and the order is server arrival. The gate judges by arrival order and shows the client's time from the payload. A late `evidence_submitted` after an ACCEPT opens a new gate round and does not rewrite the old one.
- **Offline drift.** A seat working through a long cloud outage acts on a cache the cloud has moved past. Answers carry `as_of_user_seq`, and the reconnect drain shows each rejected decision to the seat. The longer the outage, the more rework.
- **Pack staleness.** A prefetched pack can be one event old when it is used. The pack carries its `user_seq`, and the reader re-pulls if the tip has moved.

**Status.** Accepted by the owner 2026-10-08 (relayed by the principal session), including the offline rule in part 1. Owner decision 15 (own the agent loop) is closed as no. Owner decision 16 is closed 2026-10-08. Work that survives the 4genthub cloud being unreachable while the model API is reachable is deferred, and so is fully offline inference with local models. Parts 1 and 2 are adopted and buildable. Part 3 is a deferred design (owner, 2026-10-08): not built, not scheduled, and it reopens only if the owner asks. Build order for parts 1 and 2: (1) the `task_events` migration and `AppendInTx`, with the task service emitting events (2.5); (2) the ledger routes and the `ledger_tip` frame; (3) the cursor, outbox and wake-from-ledger in `agenthub-client`, replacing the `/work` poll; (4) the pack prefetch, plus a caller for the POST-COMPACTION pack in the supervisor. Update 2.4 and 2.14 as each step lands. NOT BUILT AND NOT SCHEDULED, part 3 only: (5) the local MCP endpoint with offline reads, the fact outbox and the reconnect drain; (6) the network-block acceptance test above. Neither is a NEXT_GEN work item.

---

## 5. Proposed and never built

**Agent knowledge and skill management (design of 2025-11-13).** A proposal for agents to query private knowledge bases through retrieval (local sentence-transformer embeddings, a separate RAG server), load skills on demand, generate new skills for unfamiliar domains, and improve through effectiveness feedback; four phases, 14 to 18 days, with new tools `manage_skill`, `manage_knowledge`, `search_skills` and tables `agent_skills`, `agent_knowledge`, `skill_assignments`, `knowledge_access_log`. It was an extension of the retired `call_agent` tool and the removed agent library. As of 2026-10-05 none of it exists: the tools are not published, no route exists, the tables are not created. Seat `skill`, `document` and `memory` modules are the live mechanism. If the idea returns it starts from a fresh decision note against the seat model; the 102 KB original is in git history (section 10).

---

## 6. Open owner decisions

| # | Decision | Needed by | Recommendation |
|---|---|---|---|
| 1 | Is the task the cloud's work item, so OpenRig `queue_items` are not ported to the cloud for task work (D1 sub-decision 1; changes the F2, F4, F3 sequence)? | O1 onward | Yes |
| 2 | May file paths and test names go to the Jev provider, or only counts (D1)? | Gate build | Owner's product choice |
| 3 | Port `/ws/task-polling` or declare it out of scope (D2 G4)? | Stage 4 | Out of scope |
| 4 | "Go behaviour stands" for T1, T2, P1, N1, N2 (D2 G6)? | Stage 4 | Yes |
| 5 | Is A8 (hub with more than one replica) non-gating (D2)? | Stage 4 | Yes, tracked in NEXT_GEN |
| 6 | Approve the tag `python-backend-final` and its later push (D2 stage 4) | Stage 4 | Yes |
| 7 | Re-install pre-commit against the moved config (D2 stage 3) | Stage 3 | Yes |
| 8 | Approve DELETING the production-deployment workflow and the four scripts only it calls, instead of editing it (D2 stage 3): 50 of 50 runs failed (2025-11-22 to 2026-10-08), build and deploy never ran, and the Security Scan, the only Trivy gate, goes with it | Stage 3 | Yes |
| 9 | Approve the production schema read and marking production at `0001` (D2) | Stage 1 end | Yes, read-only first |
| 10 | Delete the dead in-server AI planning path (NEXT_GEN directive 3) | Anytime | Delete |
| 11 | Install `prepare-commit-msg` into `.git/hooks` (D6) | Anytime | Yes, after checking the hook slot is empty |
| 12 | Move the stale go-dev2 state directory aside (D7); run the two `apply` commands (separate) | Anytime | Move yes; applies owner's call |
| 13 | Approve editing the ten live `AGENTS.md` files (D8) | Anytime | Yes, keeping the before copies |
| 14 | Pricing, marketplace, on-premise, mobile (1.6) | Product | Not yet asked |
| 15 | CLOSED 2026-10-08: does 4genthub own the agent loop (model calls, compaction, tools), or stay an orchestration layer over Claude Code and omp (D1, D9)? | Closed | Owner decided NO on 2026-10-08, accepting D9: 4genthub stays an orchestration layer, with no Rust runtime |
| 16 | CLOSED 2026-10-08: is work that survives an outage a product goal, and in which form? | Closed | Owner decided on 2026-10-08: DEFERRED, not a current goal. Work that survives a 4genthub cloud outage while the model API (DeepSeek or Claude) is reachable is kept as a design only (D9 part 3), not built and not scheduled, and reopens only if the owner asks. Fully offline inference with local models is also deferred |

---

## 7. Where things live

| Question | File |
|---|---|
| Routes, MCP tools, tables, counts | `ai_docs/api-integration/surface-inventory.md` (re-derived by `COUNTS-AUDIT.py`) |
| The work queue, groups O, F, T, directives and owner rulings | `agenthub_go/NEXT_GEN.md` (working tracker) |
| Python-to-Go parity record, deviations T1, T2, P1, N1, N2 | `agenthub_go/MIGRATION.md`, `agenthub_go/PROD_READINESS_REPORT.md` (history) |
| Seat guides, and the commit form for seats | `agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-<seat>.md` with `shared-modules/guide-common.md` and `guides.lock.json` (the repo-side `ai_docs/operations/seat-guides/` copies were removed by `cb998795`, 2026-10-10); `ai_docs/agent-system/repo-agent-rules.md` |
| Seat sync with the cloud | `ai_docs/operations/syncing-seats-with-the-cloud.md` |
| Rules for agents working in the repository | `AGENTS.md` (renamed from `CLAUDE.md` in `f7a809dc`), `CLAUDE.local.md` (the owner's file) |

## 8. Document history

| Date | Change |
|---|---|
| 2025-10-16 | First product requirements document. |
| 2025-11-07 | Technical reference validated (websocket v2.0 fix). |
| 2025-11-09 | Python-era architecture file deleted (`dad51589`). |
| 2026-10-08 | Orchestration architecture written by the architect against `eaa41d18`, with decisions D1 to D8. |
| 2026-10-08 | Consolidated into this file; the source files were deleted in a separate, revertible commit. |
| 2026-10-09 | D9 added (sync ledger, no Rust runtime, outage survival deferred); owner decisions 15 and 16 recorded as closed. |

## 9. Maintenance rules for this file

- One owner per fact. Counts belong to `surface-inventory.md`; the work queue belongs to NEXT_GEN. State a number here only with its date and the command that re-derives it.
- A new decision is a new dated section D<n> in section 4 with the same shape: context, options, decision, interfaces or shape, risks, status. Do not add a separate decision file; the owner chose a single source.
- When a decision is executed, update its **Status** line and the component state in 2.4 and 2.14 in the same commit.
- Keep `file:line` citations only with the revision they were read at; a line number is a pointer that rots.

## 10. Absorbed sources (recoverable from git)

The following were deleted in the commit after the one that added this file. Restore any with `git show <commit-before-deletion>:<path>`.

- `ai_docs/architecture-design/PRD.md`
- `ai_docs/architecture-design/Architecture_Technique.md`
- `ai_docs/architecture-design/product-architecture-complete.md`
- `ai_docs/architecture-design/decision-orchestration-layer.md` (D1)
- `ai_docs/architecture-design/decision-remove-python-backend.md` (D2)
- `ai_docs/architecture-design/decision-task-stats-endpoint.md` (D3)
- `ai_docs/architecture-design/decision-seat-client-fold.md` (D4)
- `ai_docs/architecture-design/decision-agy-runtime.md` (D5)
- `ai_docs/architecture-design/decision-seat-attribution.md` (D6)
- `ai_docs/architecture-design/decision-team-json-live-roster.md` (D7)
- `ai_docs/architecture-design/decision-commit-form-in-seat-instructions.md` (D8)
- `ai_docs/core-architecture/agent-knowledge-skill-system-specs.md` and `agent-knowledge-skill-system-summary.md` (section 5)
