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
| `actor_kind`, `actor` | `seat` (seat key from the MCP header), `client` (machine id from the machine token), `gate`, or `human` (user id) |
| `payload` JSONB | kind-specific; evidence and verdicts live here, so no second table holds them |
| `created_at` | server time |

Worked example (owner's TASK-142: plan, context, implement, test with 2 failures, fix, test, Jev, complete). It reads off the ledger as: `planned`, `assigned`/`claimed`, `context_loaded`, `progress`, `evidence_submitted` (2 failed), `gate_verdict` REJECT, `progress`, `evidence_submitted` (0 failed), `gate_verdict` ACCEPT, `status_changed` done. **The phase a viewer sees is derived from the last events and is never stored as a second status.**

Existing streams stay as they are: `agent_session_events` (session transcripts), `seat_status` (what a machine reports), `missed_notifications` (websocket replay). The ledger is about work; those are about sessions and seats.

### 2.6 Evidence: git and tests (NEW)

The server cannot see the repository, and an agent's account of its work is a claim. So evidence is **produced by the client binary, not reported by the agent**: `agenthub-client evidence --task <id> --base <sha> --test "<command>"` runs `git diff --numstat <base>..HEAD` and the test command itself, then posts the result authenticated by the machine token (T4, built):

```json
{"base_sha": "...", "head_sha": "...", "branch": "...",
 "files_changed": [{"path": "a.go", "added": 12, "deleted": 3}],
 "tests": [{"command": "go test ./fastmcp/x/...", "exit_code": 0, "failed": [], "duration_ms": 8123}],
 "machine_id": "...", "collected_at": "..."}
```

Stored as an `evidence_submitted` event. File contents and test output bodies stay on the machine; only paths, counts, names and exit codes reach the cloud (whether paths and test names may go to the Jev provider is an owner decision, section 6).

The client binary (`cmd/agenthubclient`, verbs in `internal/clientsync`, bridge in `internal/clientbridge`) runs `sync status`, `sync pull`, `sync connector` and the bridge. `sync rig`, `bundle`, `switch` and `watch` refuse with a pointer to `openrig_seat_sync.py`; `feedback` and `seatcheck` are pending (measured 2026-10-08). Evidence is a new subcommand beside them.

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
| Go as the platform | The server is Go. The client binary is partial (2.6); the remaining sync verbs and `feedback` are still Python scripts. The Python backend `agenthub_main/` is archived and its removal is decided (D2). |

### 2.15 Deliberately not in this architecture

- A server-side LLM runtime for planning (2.2).
- A cloud copy of OpenRig's `queue_items` for task work. The task is the cloud's work item and the local queue stays OpenRig's coordination channel. This affects NEXT_GEN directive (F) item F3 and needs the owner's confirmation (D1).
- `manage_rule` as a tool.
- Rust. The bottlenecks are model latency, network and tools.
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

Keycloak is the source of truth for identity. Login yields a JWT (`sub`, `email`, `preferred_username`, `realm_access.roles`, `exp`, `iat`); the frontend sends it as `Authorization: Bearer`; the server validates it through JWKS on every request (`fastmcp/auth/keycloak_dependencies.go`; environment `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`). The `sub` is the user id on every row and every query. Machines authenticate with machine tokens (T4); the client uses them for evidence and status. Credentials are in `.env` only and are never read or created by agents.

### 3.8 Database

The Go server describes tables with generated `TableDef` metadata (`database.Tables`), not an ORM. As of `ee71488b` (re-derived 2026-10-08) `database.Tables` holds **39 tables**: 20 core, 3 auth, 14 seat, 2 team. `ProductionTables` declares 6 more that are deliberately not created. The `task_events` table is appended from `task_event_tables.go`. Definition files sit in three trees: `task_management/infrastructure/database/models.go` and `models_prod.go`, `auth/infrastructure/database/models_auth.go`, `seat_management/infrastructure/database/seat_tables.go` and `team_tables.go`.

| Family | Tables |
|---|---|
| Task domain | `tasks`, `subtasks`, `task_assignees`, `task_dependencies`, `task_labels`, `task_contexts`, `task_events` |
| Projects | `projects`, `project_git_branchs` (the actual table name) |
| Contexts | `global_contexts`, `project_contexts`, `branch_contexts`, `task_contexts` |
| Agents | `agents`, `agent_sessions`, `agent_session_events` |
| Auth | `users`, `user_token_balances`, `email_tokens` |
| Seats (14) | `modules`, `module_versions`, `seat_types`, `seat_type_versions`, `rooms`, `seats`, `overlays`, `seat_links`, `resolved_seats`, `seat_settings`, `seat_feedback`, `machines`, `machine_tokens`, `seat_status` |
| Teams (2) | `teams`, `team_members` |

Every runtime table carries `user_id` except the `applied_migrations` ledger. Foreign keys use no `CASCADE`; this is intentional DDD design, with the application layer performing cascades.

**Schema today.** `DatabaseConfig.CreateTables` creates the schema from `database.Tables` plus a PostgreSQL init SQL file inside the Python tree, only when `AUTO_MIGRATE=true`; existing tables are not altered, and four patchers fill the gaps (`column_ensurers.go`, `ensure_ai_columns.go`, `missing_tables.go`, `auto_migration.go`). **Schema after D2 stage 1:** versioned SQL migrations in `agenthub_go/migrations/` (not yet created as of 2026-10-08) become the authority.

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
- **Tests:** backend `cd agenthub_go && go test ./...` (with `-race -count=1` for races; PostgreSQL tests need `AGENTHUB_TEST_PG_URL` or they skip); frontend `cd agenthub-frontend && npm test`; fleet-script tests `cd agenthub_main && python3 -m pytest --noconftest -p no:cacheprovider src/tests/scripts/ -q` until they move to `scripts/tests/` (D2 stage 2). `--noconftest` matters: without it the repository conftest reaches for PostgreSQL and the run hangs. Write a failing test first.
- **Commits:** Conventional Commits (`feat`, `fix`, `refactor`, `test`, `chore`, `style`, `ai_docs`); update `CHANGELOG.md` (and `TEST-CHANGELOG.md` when tests change) in the same commit; in the shared repository commit by pathspec (D8).
- **Documentation:** files in `ai_docs/`, kebab-case folders, `index.json` generated by hooks; only five root markdown files are allowed.

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

**Interfaces.** `task_events` (2.5); `GET /api/v2/tasks/{id}/events?after_seq=` (404 on a foreign task); `POST /api/v2/tasks/{id}/evidence` with a machine token (401 without one, 409 when `head_sha` is not new); the gate as an in-process service (2.7); `manage_task` actions `claim` and `resume`, and `complete` moving to `review` rather than `done` when the gate enforces; `X-Agenthub-Seat` header (2.3); `GET /api/v2/openrig/machines/{machine}/work` (2.8).

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
2. **Script tests move.** skills-dev. `git mv agenthub_main/src/tests/scripts/*.py scripts/tests/` (twelve files; module path `parents[4]` becomes `parents[2]`). Run with `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q`; baseline was 315 passed and the count must match after the move. The canonical command in the guide-common and guide-reviewer copies changes, with the seed-library lock re-recorded. Owner step: `scripts/tests` is added to the hook's valid-test-path list in the separate `.claude` repository.
3. **CI, docker, hooks, rules.** go-dev for CI and docker; the lead or the principal for the owner's `CLAUDE.local.md`.
   - **The pre-commit config first, and it is load-bearing.** The installed `.git/hooks/pre-commit` points at `agenthub_main/.pre-commit-config.yaml`; with pre-commit 4.4.0 a missing config makes `git commit` exit 1 with no commit, so deleting the tree first would stop every seat's commit, including the revert. Move the config to `scripts/git-hooks/pre-commit-config.yaml`, drop its two `ruff` hooks, keep the generic hooks and the seat-trailer hook; re-installing is an owner step.
   - `.github/workflows/test_coverage.yml`: replace the Python jobs with a Go job (build, vet, test with a PostgreSQL service) and a script-test job; drop the `skip-dirs: 'agenthub_main'` line in `production-deployment.yml` (a deployment workflow edit needs the owner).
   - Docker removed: `Dockerfile.backend.dev`, `Dockerfile.backend.production` and the compose files that build them, plus `docker-compose.yml` and `docker-compose.optimized.yml`, which already point at Dockerfiles that do not exist. Kept: `Dockerfile.backend.go`, `docker-compose.backend-go-frontend.yml`, db-only, pgadmin and the frontend files. `docker-menu.sh` and its libraries lose their Python paths; the Go option becomes the default. The CapRover definitions already build the Go Dockerfile.
   - Python backend scripts removed (`batch-test-runner.py`, `run-tests.py`, `validate_suite.py`, `test-menu.sh`, `start_backend_dev.sh`, and the schema tools `verify_init_schema.py`, `deep_verify_schema.py`, `generate_schema_sql.py`, `compare_schema.py`, `check_fk_cascade.py`, `inspect_database.py`); `backup-production.sh` and the security script lose their Python paths and are reviewed by the owner because they touch production.
   - `CLAUDE.local.md` takes the hierarchy from 3.8 and loses the ORM paths, the Python quick commands and the schema table; the no-compatibility rules stay.
   - **Parity record.** `MIGRATION.md` and `PROD_READINESS_REPORT.md` stay as history with one pointer line at the top: closed by this decision, a Python path cited below resolves at tag `python-backend-final`. That line repairs the 14 citations without rewriting history. The 45 "ports X.py" Go comments stay as provenance. Living guides that name the tree are edited; history stays.
4. **Tag, then deletion, last and alone.** Precondition: G1 to G6 closed, stage 1 to 3 commits on main, G5's report filed. `git tag -a python-backend-final` on the stage-3 head (the owner approves the tag; it stays local until the owner pushes). The deletion commit is `git rm -r --quiet agenthub_main` and nothing else (1,595 tracked files), with the changelog in a separate commit after it, so `git revert` restores exactly the tree. Untracked contents (`.venv`, `venv`, `agenthub_dev.db`, logs, caches) remain on disk and are the owner's to move aside, since `agenthub_dev.db` may hold data. Recovery: `git revert <deletion>` or `git checkout python-backend-final -- agenthub_main`. Acceptance: `go build ./... && go test ./...` with `AGENTHUB_TEST_PG_URL` set; the script tests still pass at the same count; a seat commit succeeds; G5 re-run on the post-deletion build.

**Out of scope for every stage:** `captain-definition*`, production databases, CapRover configuration, `.git/hooks` (owner), `.claude/` (separate repository), the frontend apart from help text, `agenthub_go/internal/clientbridge/testdata/*` (frozen fixtures).

**Python tooling outside the backend (owner answered: backend only).** The eight fleet scripts (`openrig_bridge`, `openrig_compact_supervisor`, `openrig_scrub`, `openrig_seat_client`, `openrig_seat_policy`, `openrig_seat_sync`, `openrig_team_setup`, `openrig_watch_tools`) and their tests survive the backend removal unchanged and move in stage 2. The code-mod tools (`add_future_annotations`, `fix_code_quality`, `modernize_type_hints`) lose their target; the API probes (`test_mcp_crud_suite.py`, `test-keycloak-auth.py`) are candidates for G5's proof; `.claude/hooks/*.py` is a different repository and runtime.

**Status.** As of 2026-10-08 `agenthub_go/migrations/` does not exist, so stage 1 has not landed. Owner pending: G4, G6, A8 non-gating, the tag, the pre-commit re-install, the CI deployment edit, the production schema read and ledger marking.

### D3. Remove the two task routes that can only fail; the statistic comes from the ledger

**Context.** `GET /api/v2/tasks/stats/summary` and `GET /api/tasks/{task_id}` always returned 500: their adapter methods (`GetTaskStatistics`, `GetTaskWithRelations`) panicked with Python's AttributeError text, ported deliberately for parity (`MIGRATION.md:951`, `PROD_READINESS_REPORT.md:179`, which cover the stats route only). Neither route had a caller: the frontend mentioned them only in its API reference, and the task view loads through `GET /api/v2/tasks/{id}`. The parity reason expired with the archive of the Python backend, and the statistic the product needs is already planned as the O8 KPI panel over the ledger.

**Options.** A. Keep parity, with the 500s documented: two advertised routes that can never answer, legacy code for a server that no longer runs. B. Build a per-status count statistic now: a response shape nobody specified, no caller, and a second source of task numbers before O8 builds the first. C. Remove both routes and both panicking methods.

**Decision: C.** It is the only option where a listed route can also answer, it removes code, and it leaves O8 as the one source of task statistics. B becomes right only if the owner names a consumer needing counts before O8; A only if Python parity is still a goal.

**Shape.** Behaviour-changing for two routes (500 becomes 404), no data model change. Removed in one commit: the two `HandleFunc` registrations, `routes.GetUserTaskStats` and `routes.GetFullTask` with their interface methods, the adapters behind them, `TaskSearchHandler.GetTaskStatistics` and `.GetFullTask`, both methods on `TaskHandlerFacade` and its implementation, and the test fakes; leftovers found by the compiler. Inventory rows updated; the frontend API reference loses its two entries (separate frontend commit). One test caveat measured at implementation: the stats path sits under the prefix route `GET /api/v2/tasks/`, which answers 403 before auth in Go's `ServeMux`, so a 404 can never be observed there and the evidence for that half is the build plus a grep, with the reason written in the test. Must not touch: `GET /api/v2/tasks/{id}`, `GET /api/tasks/{task_id}/context/summary`, `/api/tasks/summaries`.

**Status: executed** in `e6829b32`. At `db9d2bc3` `grep -rq "stats/summary"` over the Go server sources exits 1. Open follow-up: the frontend `apiReference.ts` entries (fe-dev).

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
| 8 | Approve the production-deployment workflow edit (D2 stage 3) | Stage 3 | Yes |
| 9 | Approve the production schema read and marking production at `0001` (D2) | Stage 1 end | Yes, read-only first |
| 10 | Delete the dead in-server AI planning path (NEXT_GEN directive 3) | Anytime | Delete |
| 11 | Install `prepare-commit-msg` into `.git/hooks` (D6) | Anytime | Yes, after checking the hook slot is empty |
| 12 | Move the stale go-dev2 state directory aside (D7); run the two `apply` commands (separate) | Anytime | Move yes; applies owner's call |
| 13 | Approve editing the ten live `AGENTS.md` files (D8) | Anytime | Yes, keeping the before copies |
| 14 | Pricing, marketplace, on-premise, mobile (1.6) | Product | Not yet asked |

---

## 7. Where things live

| Question | File |
|---|---|
| Routes, MCP tools, tables, counts | `ai_docs/api-integration/surface-inventory.md` (re-derived by `COUNTS-AUDIT.py`) |
| The work queue, groups O, F, T, directives and owner rulings | `agenthub_go/NEXT_GEN.md` (working tracker) |
| Python-to-Go parity record, deviations T1, T2, P1, N1, N2 | `agenthub_go/MIGRATION.md`, `agenthub_go/PROD_READINESS_REPORT.md` (history) |
| Seat guides and the commit form for seats | `ai_docs/operations/seat-guides/`, `ai_docs/agent-system/repo-agent-rules.md` |
| Seat sync with the cloud | `ai_docs/operations/syncing-seats-with-the-cloud.md` |
| Rules for agents working in the repository | `CLAUDE.md`, `CLAUDE.local.md` (the owner's file) |

## 8. Document history

| Date | Change |
|---|---|
| 2025-10-16 | First product requirements document. |
| 2025-11-07 | Technical reference validated (websocket v2.0 fix). |
| 2025-11-09 | Python-era architecture file deleted (`dad51589`). |
| 2026-10-08 | Orchestration architecture written by the architect against `eaa41d18`, with decisions D1 to D8. |
| 2026-10-08 | Consolidated into this file; the source files were deleted in a separate, revertible commit. |

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
