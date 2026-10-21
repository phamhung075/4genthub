# 4genthub: architecture, product and decisions (single source of truth)

**How to read it.** Section 1 is what the product is for. Section 2 is the architecture and what is built. Section 3 is the platform reference (stack, API, MCP tools, websocket, auth, database, workflow). Section 4 lists the decisions, one line each. Section 5 says where things live. The work queue, backlog and open decisions are 4genthub tasks.

**Labels used for components:**

- **BUILT**: the code exists and is wired into the running server or client.
- **PARTIAL**: some of it exists; the missing half is named.
- **NEW**: not in the tree. The work item is a 4genthub task.

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
| Agent library of 42+ specialised role templates | RETIRED. The role templates, the `agents` registry table and the `manage_agent` tool are all gone (`76b800b9`, 2026-10-10); roles come from seat types and `@<seat_key>` is the only assignee identity |
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
| **Client** (4genteam `rig` and daemon, `scripts/*.py`, later the `agenthub-client` binary) | Launching and supervising seats, rendering seat files to disk, reporting seat status, collecting git and test evidence, delivering wake messages with `4genteam send`. | Decides task state on its own. Claims and verdicts come from the cloud. |
| **Models** (seats) | Planning, implementing, reviewing. They reach the cloud only through MCP tools. | Write to the database directly, or certify their own work. |

**Why the cloud does not run models.** The in-server AI planning path (the `fastmcp` AI-planning package, about 3,000 lines, and the five `ai_*` actions of `manage_task`) was never wired: since `a8ff89da` it refused with "the AITaskIntegrationService seam is not wired in this build". Brains and workers already run as seats on the client, where their tools, files and credentials are; a server-side model runtime would be a second place that plans work. The owner's directive 3 decided the dead path goes: the package, the five actions and their handler/service/use-case are DELETED (2026-10-18, task O9c); only the `ai_*` task columns remain, a separate lane. The five names are now refused as unknown actions, and a guard (`fastmcp/server/httpapp/ai_actions_absent_test.go`) fails if any is advertised or dispatched again.

### 2.3 Seats, MCP interface, task graph, context

**Seats and rooms: BUILT.** `fastmcp/seat_management`. A seat is a durable position (a key in a room); the occupant is runtime plus model. Seat types are versioned. Overlays fold in at company, room and seat level with `add`, `remove`, `override` and `pin`. Module kinds are `instruction`, `document`, `skill`, `tool`, `mcp`, `memory` and `policy` (`seat_management/domain/resolver/resolver.go:17-29`, `ck_modules_kind`). The renderer emits 4genteam AgentSpec and RigSpec files. `seat_links` carries `delegates_to`, `spawned_by`, `can_observe`, `collaborates_with` and `escalates_to`. Supported runtimes are `claude-code`, `codex`, `omp` and `agy` (decision D5); `codex` and `agy` receive no Claude fragments. "Brain" and "worker" are roles given by seat type and occupant, not a separate mechanism: a brain is a seat whose occupant is a reasoning model and that is the `escalates_to` target of worker seats.

**MCP interface: BUILT, with two gaps.** Transport is `POST /mcp` (JSON-RPC 2.0) and `GET /mcp` (SSE). Tools registered in the Go server (nine): `manage_project`, `manage_git_branch`, `manage_task`, `manage_subtask`, `manage_context`, `manage_seat`, `call_seat`, `submit_feedback`, `manage_connection` — `manage_agent` was retired 2026-10-10 with the `agents` table and the 32-role registry (`76b800b9`), and `fastmcp/server/httpapp/manage_agent_absent_test.go` fails the build if it is published again. The tool list is owned by `surface-inventory.md` section 2 and checked against `interface/testdata/tools_golden.json`. `initialize`, `ping`, `tools/list`, `tools/call`, `resources/list`, `prompts/list` and `notifications/initialized` are protocol methods, not tools. The `call_agent` tool is removed with the Python agent library, and the seat model (`call_seat`, `manage_seat`) replaces it.

- **`manage_rule` is not registered.** A facade exists (`rule_application_facade.go`). Rules are delivered as seat modules (`instruction`, `policy`), so rules stay there and no `manage_rule` tool is added; with both, a rule would have two homes.
- **Calls carry no seat identity.** Only the user is known (bearer token). The ledger needs the acting seat, so item O2 adds a header `X-Agenthub-Seat: <room>/<seat>` to each rendered MCP block. It is used for attribution, not authorization.

**Task graph: BUILT; routing PARTIAL.** Project, git branch, task, subtask, with `task_dependencies` and cycle checks (`Task.HasCircularDependency`). Statuses and transitions (`value_objects/task_status.go:42-51`):

```
todo -> in_progress | blocked | cancelled | done
in_progress -> blocked | review | testing | cancelled | done
blocked -> in_progress | cancelled
review -> in_progress | blocked | testing | done | cancelled
testing -> in_progress | blocked | review | done | cancelled
done -> in_progress        cancelled -> todo        archived: final
```

This block is the transition rule of `task_status.go`: every open state can reach `blocked`, so the lifecycle sweep can end a stale critical task through `Task.UpdateStatus`. **The two encodings of this rule are NOT identical, and neither may be read as the other:** the entity also allows `todo -> done`, `review -> cancelled`, `testing -> cancelled` and `cancelled -> todo`; the service's own table (`domain/services/task_state_transition_service.go`) also allows `in_progress -> todo` and `blocked -> todo`, and carries no `archived`. The ruling closed the `blocked` column and nothing else.

Gaps:

1. **Assignees are legacy agent role names**, such as `@coding-agent` (`entities/task.go:326`, `ResolveLegacyRole`), not seat keys, so a task cannot be routed to a seat. The recommended fix (assignee is the user's seat key) is not built.
2. **No structured acceptance criteria.** `manage_task` accepts `completion_summary` and `testing_notes` only. The column `ai_completion_criteria` belongs to the dead AI path.
3. **`todo -> done` and `in_progress -> done` are allowed directly.** When the gate enforces, `done` must be reachable only through a gate verdict (item O5).

**Context: BUILT; composition PARTIAL.** Four levels: global (per user), project, branch, task (`*_contexts` tables), served at `/api/v2/contexts/{level}`. Each level inherits from its parent, is identified by UUID, is created on demand and is isolated per user. `manage_context` provides `create`, `get`, `update`, `delete`, `list`, `resolve` (inheritance applied), `delegate`, `add_insight` and `add_progress`. The task context has slots for `implementation_notes`, `test_results`, `blockers` and `local_decisions` (`task_management/infrastructure/database/models.go:549-552`). The platform's composition model for a seat is the overlay chain company, room, seat; the four context levels are not that model. The context-pack algebra (`seat_management/domain/contextpacks`: FRESH, HANDOVER and POST-COMPACTION profiles with token budgets) is built and tested but **has no caller outside its tests**. Because context may matter more than the model, the architecture makes the resume brief (2.9) the main product of context, not a dump of the context row.

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

Stored as an `evidence_submitted` event. File contents and test output bodies stay on the machine; only paths, counts, names and exit codes reach the cloud (whether paths and test names may go to the Jev provider is an owner decision).

The client binary is `4genteam` (`agenthub_client/cmd/4genteam`, Go); `4genteam --help` prints its surface. `4genteam evidence` submits a task's evidence, which the server stores as an `evidence_submitted` event. The room is materialized by the launcher (`4genteam up ROOM --team DIR`), and `4genteam seat reseat` / `4genteam room reseat` restart a seat.

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

Today a seat works only when someone runs `4genteam send` or a local 4genteam queue item reaches it; the cloud does not know a seat is idle while work assigned to it is open.

- **Assignment** is a seat key (`room/seat`) on the task (gap 1 in 2.3).
- **Claim** goes through the cloud (`manage_task action=claim`). The owner's 2026-10-05 ruling "claims route through the cloud; they are not reported to it" is applied to the task itself: the task is the cloud's work item, with `claimed_by` and `claimed_at`.
- **Wake is a pull.** The client's bridge loop asks `GET /api/v2/machines/{machine}/work` for open, unclaimed or rejected tasks assigned to seats it runs. For a seat whose `seat_status.state` is idle, it runs `4genteam send <session> "<one-line pointer: task id and 'manage_task action=resume'>"` and posts a `delivered` event. Delivery is idempotent per (task, last event seq), so a wake is sent once per change. The cloud never pushes.

### 2.9 Resume / continue (NEW)

`manage_task action=resume task_id=...` returns one brief built from the ledger and the resolved context, so the next agent does not undo the previous agent's work: the task, its status and acceptance criteria; the last gate verdict with reasons; the last evidence (files touched, failing tests, head sha); open subtasks and blocking dependencies; the resolved task context; the last `handover` note; and the next action derived from these (for example "fix: D3 failed, the test named in the previous evidence still fails"). A size budget applies. The brief is the same for a fresh seat, a restarted seat and a different model, which is what makes switching an occupant safe.

### 2.10 Project memory (PARTIAL)

Project and branch contexts already serve as memory, and seat `memory` modules carry seat-level memory. **Added:** on ACCEPT the gate appends one verified line to the branch context (task, head sha, files, tests run), so the branch context shows what is done from verified facts only. Decisions are recorded with `add_insight` category `decision`. No new memory store is introduced.

### 2.11 Observability surfaces

| Surface | State | Source |
|---|---|---|
| Seats, topology, drift | BUILT | `SeatsPage`, `TopologyPage`, `seat_status`, `GET /api/v2/machines` |
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
- `tasks.assignees` holds seat keys. The legacy role resolution is removed; the `ai_*` columns follow the owner's decision on the in-server AI planning path.
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
| Wake-on-open-work | Not built. the client's local queue wakes seats; the cloud cannot. |
| Resume/continue | Seat-level resume is built by 4genteam (snapshots, session files). Task-level resume is not built. |
| Project memory | Contexts and memory modules built. Nothing writes verified facts into them. |
| Go as the platform | The server and the client are Go. The Python backend `agenthub_main/` is removed (`a50929c6`, 2026-10-09). |

### 2.15 Deliberately not in this architecture

- A server-side LLM runtime for planning (2.2).
- A cloud copy of the client's `queue_items` for task work. The task is the cloud's work item and the local queue stays the client's coordination channel. This needs the owner's confirmation (D1).
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

Base `http://localhost:8000`. Resource families under `/api/v2/`: `projects`, `branches`, `tasks` (list, create, get, update, delete, `complete`), `subtasks` (create, list by task, get, update, delete, `complete`), `contexts/{level}`, plus the seat, room, machine and 4genteam routes. Create-task request: `title`, optional `description`, `git_branch_id`, `assignees`, optional `priority` (`low`, `medium`, `high`, `urgent`, `critical`). Responses use `{success, data, meta{persisted, id, timestamp, operation}}`. The full route list and its count are in `surface-inventory.md` section 1.

Removed on purpose: `GET /api/v2/tasks/stats/summary` and `GET /api/tasks/{task_id}` (D3), `/ws/{user_id}`, `/ws/health`, `/ws/stats` (declared out of scope by the owner on 2026-10-06), and `/api/v2/branches/{id}/task-counts` and `/assign-agent` (`c08063d5`, `f33db13a`).

### 3.5 MCP tools

All tools take an `action` field. `manage_task` covers task CRUD, search and dependencies (the `ai_*` actions refuse, 2.2); `manage_subtask` covers subtask CRUD, progress and completion (parent progress updates automatically; subtasks inherit assignees); `manage_project` covers lifecycle and health checks; `manage_git_branch` covers branch CRUD and statistics; `manage_context` covers the four context levels, resolution with inheritance, and delegation upward; `manage_seat` lists, gets and sets the occupant of a seat; `call_seat` resolves one seat and its rendered files; `manage_connection` is the health check; `submit_feedback` records seat feedback. Boolean arguments accept `true`, `1`, `yes`, `on`; array arguments accept JSON strings, comma-separated text, or arrays. Completing a task auto-creates its context if missing. Planned additions: `manage_task` actions `claim` and `resume` (2.8, 2.9).

### 3.6 Websocket v2.0

Connect to `ws://localhost:8000/ws/realtime`. Message: `{id, version: "2.0", type: "update", timestamp, sequence, payload{entity, action, data{primary}}, metadata{source: user|system, userId, entity_type, entity_id, event_type, timestamp, task_title, git_branch_id, project_id, parent_branch_id, parent_branch_title}}`; `entity` is `task`, `subtask` or `branch` and `action` is `created`, `updated`, `completed` or `deleted`. A `task.created` `primary` is the task seed without `details`; a `task.updated`/`task.completed` `primary` is a flat field delta - `id`, `updated_at`, and exactly the fields the write changed, with `details_changed: true` in place of the unbounded note - which the client merges into its cached task. Every `primary` serialises to at most 2048 bytes (`WebSocketPayloadBuilder.EstimatePayloadSize`); an over-cap delta is replaced by `{id, refetch: true}`. A status-only update measures 90 B (`BenchmarkTaskEventDelta`). `wsIsDuplicateNotification` keys a task event by its `updated_at` when the payload carries one, so the same write emitted by both the use-case hook and the facade reaches the client once, while two distinct writes inside the five-second TTL both ship. Subtask payloads carry the timestamp fields the frontend validates. Fan-out is `BroadcastDataChange` in `fastmcp/server/routes/websocket_routes.go`; endpoints are mounted in `fastmcp/server/httpapp/ws_mount.go`.

The 2025-11-07 fix established the behaviour above: an error-handling wrapper so one bad message does not stop the handler, merge-style cache updates, the dual cache update on delete, single-source toasts, and a deletion of about 1,000 lines of dead code. The in-memory hub with more than one replica (A8) is an open production-topology decision and not a gate for anything here.

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

Every runtime table carries `user_id` except `users`, `applied_migrations`, `user_agent_configurations_md` and `agent_import_history`; `templates` and `email_tokens` carry a nullable one by design. 11 foreign-key columns carry `ON DELETE CASCADE` across 10 tables, and `task_events` is the one table without, by comment; the application layer performs the rest. (Measured 2026-10-19 over the 49-table registry; see `ai_docs/core-architecture/nfr-register.md`.)

**Schema.** `DatabaseConfig.CreateTables` is the single schema creator: with `AUTO_MIGRATE=true` it applies the embedded migration set (`agenthub_go/fastmcp/task_management/infrastructure/database/migrations/`, `NNNN_slug.sql` in filename order, each recorded in `applied_migrations`). `0001_baseline.sql` is generated from the Go table registry and frozen; the rules are in that directory's `README.md`.

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
- **Commits:** Conventional Commits (`feat`, `fix`, `refactor`, `test`, `chore`, `style`, `ai_docs`); the commit body says what was wrong, what changed and how it was tested (no changelog file, D11); in the shared repository commit by pathspec (D8).
- **Documentation:** files in `ai_docs/`, kebab-case folders; the tracked tree is the index (`git ls-files 'ai_docs/**/*.md'`), there is no generated catalogue; only an allow-list of root markdown files is allowed; no report, plan or status files (D11).

---

## 4. Decisions

One line each. The reasoning, options and status history are in `git log -- ai_docs/core-architecture/agenthub-system-architecture.md`; new decisions are recorded in 4genthub (task or context), and only the outcome is added here.

| # | Date | Decision |
|---|---|---|
| D1 | 2026-10-08 | 4genthub is an orchestration layer on one ledger, client-collected evidence and a two-stage gate. |
| D2 | 2026-10-08 | The Python backend (`agenthub_main/`) is removed; migrations are the schema authority. |
| D3 | 2026-10-08 | The two task routes that could only fail are removed; task statistics come from the ledger. |
| D4 | 2026-10-08 | `seat_client.py` retires into the Go client verb by verb; there is one client. |
| D5 | 2026-10-08 | The `agy` (Gemini/Antigravity) runtime is supported; Claude models are refused on it. |
| D6 | 2026-10-08 | Every seat commit carries a `Seat:` trailer added by `scripts/git-hooks/prepare-commit-msg`. |
| D7 | 2026-10-08 | The 4genthub-min room definition follows the live roster. |
| D8 | 2026-10-08 | Seats commit by pathspec and do not stage first. |
| D9 | 2026-10-08 | Sync is a server-sequenced ledger with a client cursor and outbox: facts sync, decisions sequence. Work that survives a cloud outage is deferred. |
| D10 | 2026-10-18 | The lead commits, pushes and rebuilds without asking; credentials and spend stay the owner's. |
| D11 | 2026-10-21 | No changelog file: the commit message is the change record. Plans, decisions, findings and status live in 4genthub. Docs are minimal; no report files and no local logs. |
| D12 | 2026-10-21 | `4genteam up` opens no browser; `4genteam ui` opens the web UI. `agenthub_client/scripts/respawn.sh <room>` rebuilds and restarts a room on fresh seat processes. |

---

## 5. Where things live

| Question | File |
|---|---|
| Routes, MCP tools, tables, counts | `ai_docs/api-integration/surface-inventory.md` (re-derived by `COUNTS-AUDIT.py`) |
| The work queue, backlog, owner rulings and open decisions | 4genthub: the board's tasks and context (`manage_task`, `manage_context`) |
| Change history | `git log` (the commit body is the record) |
| Seat guides, and the commit form for seats | `agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-<seat>.md` with `shared-modules/guide-common.md` and `guides.lock.json`; `ai_docs/agent-system/repo-agent-rules.md` |
| Watching a room | `agenthub_client/docs/WATCH.md`, the `watch-team` skill |
| Rules for agents working in the repository | `AGENTS.md`, `CLAUDE.local.md` (the owner's file) |

## 6. Maintenance rules for this file

- One owner per fact. Counts belong to `surface-inventory.md`; the work queue belongs to 4genthub. State a number here only with the command that re-derives it.
- A new decision gets one row in section 4. Its reasoning goes in the 4genthub task, not here.
- When a decision is executed, update the component state in 2.4 and 2.14 in the same commit.
- No dated "CORRECTED" or history paragraphs: fix the sentence; the commit says what changed.
