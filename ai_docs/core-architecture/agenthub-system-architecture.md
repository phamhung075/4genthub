# 4genthub system architecture: an AI software orchestration layer

Written 2026-10-08 by the architect seat (`4genthub-min.architect`) against HEAD `eaa41d18`, from the owner's vision of the same day and a read of `agenthub_go`. It replaces the file of the same name deleted in `dad51589` (2025-11-09), which described the Python backend.

Every component below carries one of three labels, and each BUILT or PARTIAL label names the code it rests on:

- **BUILT**: the code exists and is wired into the running server or client.
- **PARTIAL**: some of it exists; the missing half is named.
- **NEW**: not in the tree. The work item is in `agenthub_go/NEXT_GEN.md`, group O.

The decision behind the new parts is `ai_docs/architecture-design/decision-orchestration-layer.md`.

## 1. Purpose and KPI

4genthub turns a software goal into tasks that are executed, verified and continued by several AI models working as a team. It does not need to be the strongest model. Its job is to make the models work together correctly.

**KPI: verified software per unit of human attention.** Lines of code produced is not a measure of progress. Section 9 defines both terms of the KPI as counts over the execution ledger, so the KPI can be computed instead of estimated.

The product's lasting value is in context, the task graph, agent routing, execution state, verification, observability, resume/continue and project memory. Code generation by itself is becoming a commodity.

## 2. The flow, and where each step lives

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
  |  agenthub-client evidence  (client collects; the agent does not report)
  v
Evidence in the cloud                                                      [NEW]
  |
  v
Validation gate: deterministic checks, then Jev                            [NEW, was G7]
  |-- ACCEPT    -> task done; the verified facts are appended to branch memory
  |-- REJECT    -> task back to in_progress with the reasons; the same seat is woken
  '-- UNCERTAIN -> the escalates_to seat (a brain); a human only if the brain cannot settle it
  |
  v
Every step above is written to the execution ledger (task_events)          [NEW]
  -> observable state machine, resume brief, wake-on-open-work, KPI
```

## 3. Responsibility split

| Layer | Owns | Never does |
|---|---|---|
| **Cloud** (`agenthub_go`, Postgres) | The system of record: projects, branches, tasks, subtasks, contexts, seats and rooms, the execution ledger, gate verdicts. It renders seat files and runs the gate. | Calling brain or worker models (the gate's Jev call is the one model call), reading the user's repository, reaching into the user's machine (the pull model, see NEXT_GEN "Direction"). |
| **Client** (OpenRig `rig` + daemon, `scripts/openrig_*.py`, later the `agenthub-client` binary) | Launching and supervising seats, rendering seat files to disk, reporting seat status, collecting git/test evidence, delivering wake messages with `rig send`. | Deciding task state on its own. Claims and verdicts come from the cloud. |
| **Models** (seats) | Planning, implementing, reviewing. They talk to the cloud only through MCP tools. | Writing to the database directly, or certifying their own work (the gate does that). |

**Why the cloud does not run models.** The in-server AI planning path (`fastmcp/ai_task_planning`, about 3,000 lines, and the five `ai_*` actions of `manage_task`) is not wired. Since `a8ff89da` it refuses with "the AITaskIntegrationService seam is not wired in this build" (`ai_handler.go:301`). Brains and workers already run as seats on the client, where their tools, files and credentials are. A second, server-side model runtime would mean two places that plan work. Whether the dead path is deleted is the owner's open decision (NEXT_GEN directive 3); this architecture does not need it.

## 4. Components

### 4.1 Seats: brains and workers — BUILT

`fastmcp/seat_management`. A seat is a durable position (a key in a room), and the occupant is runtime + model. Seat types are versioned. Overlays fold in at company, room and seat level with `add`, `remove`, `override` and `pin`. Module kinds are `instruction`, `document`, `skill`, `tool`, `mcp`, `memory` and `policy` (`resolver.go:17-29`, `ck_modules_kind`). The renderer emits OpenRig AgentSpec and RigSpec files. `seat_links` carries `delegates_to`, `spawned_by`, `can_observe`, `collaborates_with` and `escalates_to`.

"Brain" and "worker" are roles given by seat type and occupant. They are not a separate mechanism: a brain is a seat whose occupant is a reasoning model and that is the `escalates_to` target of worker seats.

### 4.2 MCP interface — BUILT, with two gaps

Registered tools (`task_management/interface/ddd_compliant_mcp_tools.go:223-249`, `server/httpapp`): `manage_project`, `manage_git_branch`, `manage_task`, `manage_subtask`, `manage_context`, `manage_agent`, `manage_seat`, `call_seat`, `submit_feedback`, `manage_connection`.

- **`manage_rule` is not registered.** A facade exists (`rule_application_facade.go`). Rules are delivered as seat modules (`instruction`, `policy`), so the architecture keeps rules there and does not add a `manage_rule` tool. If both existed, a rule would have two homes.
- **Calls carry no seat identity.** Only the user is known (bearer token). The ledger needs to know which seat acted. NEW item O2 adds a seat header to every rendered MCP block. The header is used for attribution, not authorization.

### 4.3 Task graph — BUILT; routing PARTIAL

Project → git branch → task → subtask, with task dependencies (`task_dependencies`) and cycle checks (`Task.HasCircularDependency`). The status vocabulary and its transitions are in `value_objects/task_status.go:12-37`:

```
todo -> in_progress | cancelled | done
in_progress -> blocked | review | testing | cancelled | done
blocked -> in_progress | cancelled
review -> in_progress | testing | done | cancelled
testing -> in_progress | review | done | cancelled
done -> in_progress        cancelled -> todo        archived: final
```

**Gaps:**

1. **Assignees are legacy agent role names**, such as `@coding-agent` (`entities/task.go:326`, `ResolveLegacyRole`), not seat keys. A task cannot be routed to a seat. Owner decision D6's recommendation (assignee = the user's seat key) is not built.
2. **Tasks have no structured acceptance criteria.** `manage_task` accepts `completion_summary` and `testing_notes` only. The ORM column `ai_completion_criteria` belongs to the dead AI path.
3. **`todo → done` and `in_progress → done` are allowed directly.** When the gate enforces, `done` must be reachable only through a gate verdict (item O5).

### 4.4 Context — BUILT; composition PARTIAL

Four tiers: global (per user) → project → branch → task (`*_contexts` tables). `manage_context` provides `create`, `get`, `update`, `delete`, `list`, `resolve` (with inheritance), `delegate`, `add_insight` and `add_progress`. The task context already has slots for `implementation_notes`, `test_results`, `blockers` and `local_decisions` (`models.go:537`).

The context-pack algebra (`seat_management/domain/contextpacks`: FRESH, HANDOVER and POST-COMPACTION profiles, token budgets) is built and tested but **has no caller outside its tests**.

The vision says context may matter more than the model. The architecture follows that by making the resume brief (4.9) the main product of context, not a dump of the context row.

### 4.5 Execution ledger and the observable state machine — NEW

One append-only table, `task_events`, is the history of every task and subtask. **The task row keeps the current status. The ledger keeps how it got there.** Both are written in one transaction by the task application service, which is the only writer of either. `progress_history` and `progress_count` on `tasks` stop being written; `add_progress` becomes a `progress` event. This is a clean break, not a parallel store.

| Column | Meaning |
|---|---|
| `id`, `user_id`, `task_id`, `subtask_id` (nullable), `seq` (per task, gapless) | identity and order |
| `kind` | closed vocabulary with a CHECK: `planned`, `assigned`, `claimed`, `delivered`, `context_loaded`, `progress`, `status_changed`, `evidence_submitted`, `gate_verdict`, `escalated`, `human_decision`, `handover` |
| `actor_kind`, `actor` | `seat` (seat key from the MCP header), `client` (machine id from the machine token), `gate`, or `human` (user id) |
| `payload` JSONB | kind-specific; evidence and verdicts are stored here, so no second table holds them |
| `created_at` | server time |

The owner's TASK-142 example (PLAN, CONTEXT, IMPLEMENT, TEST with 2 failures, FIX, TEST, JEV, COMPLETE) reads off this ledger as: `planned` → `assigned`/`claimed` → `context_loaded` → `progress` → `evidence_submitted` (2 failed) → `gate_verdict` REJECT → `progress` → `evidence_submitted` (0 failed) → `gate_verdict` ACCEPT → `status_changed` done. **The phase a viewer sees is derived from the last events. It is never stored as a second status.**

Existing streams stay what they are: `agent_session_events` (session transcripts, `session_stream`), `seat_status` (what a machine reports) and `missed_notifications` (websocket replay). The ledger is about work. Those are about sessions and seats.

### 4.6 Evidence: git and tests — NEW

The server cannot see the repository, and an agent's account of its own work is a claim. So evidence is **produced by the client binary, not reported by the agent**: `agenthub-client evidence --task <id> --base <sha> --test "<command>"` runs `git diff --numstat <base>..HEAD` and the test command itself, then posts the following, authenticated by the machine token (T4, built):

```json
{"base_sha": "...", "head_sha": "...", "branch": "...",
 "files_changed": [{"path": "a.go", "added": 12, "deleted": 3}],
 "tests": [{"command": "go test ./fastmcp/x/...", "exit_code": 0, "failed": [], "duration_ms": 8123}],
 "machine_id": "...", "collected_at": "..."}
```

The evidence is stored as an `evidence_submitted` event. File contents and test output bodies stay on the machine. Only paths, counts, names and exit codes reach the cloud.

The `agenthub-client` binary exists only as a skeleton (`cmd/agenthubclient/main.go`: `help`, `version`). The ONE-CLIENT directive already plans it, and evidence is its first subcommand that does real work.

### 4.7 Validation gate — NEW (G7, rewritten)

Called directly by the task application service when a seat completes a task or subtask. It is not wired through an event bus: the bus registration G7 named (`HandleTaskCompleted`, `event_handler_initializer.go`) was deleted in `e1970dc5`.

1. **Deterministic checks first, in code, with no model:**
   - D1: an evidence event newer than the last `status_changed` exists, from a machine of the same user.
   - D2: `head_sha ≠ base_sha` and `files_changed` is not empty, unless the task is labelled `no-code`.
   - D3: every test `exit_code == 0`.
   - D4: a test named as failed in this task's previous evidence now passes.
   - D5: if the task declares a `scope` (path globs), no changed file falls outside it; a file outside it is flagged.

   A failure of D1, D2 or D3 is a REJECT with the check named, and Jev is not called.
2. **Jev for the question code cannot answer**: does this evidence plus the completion summary satisfy each acceptance criterion? The state sent to Jev is the criteria, the summary, the testing notes and the evidence payload, with no transcripts and no file contents. Thresholds live in code.
3. **Verdict**:
   - ACCEPT: every criterion is clearly yes and D4/D5 are clean. The task moves `review → done`.
   - REJECT: any criterion is clearly no. The task moves `review → in_progress`, the reasons go into the event, and the assigned seat is woken (4.8).
   - UNCERTAIN: anything else. An `escalated` event goes to the worker seat's `escalates_to` seat. That brain records a `human_decision`-shaped verdict as `actor_kind=seat`. A human is involved only when the brain also returns uncertain.

**Rollout** (unchanged from G7): (a) shadow mode, which logs verdicts without acting; (b) calibrate against the reviewer seat's verdicts; (c) enforce. The Jev API facts in G7 (`POST /v1/systemone`, typed questions, confidence on Choice and Score) were recorded on 2026-10-03 and are re-verified against live docs when the build starts, not assumed.

### 4.8 Wake-on-open-work — NEW

Today a seat does work only when someone runs `rig send` or a local OpenRig queue item reaches it. The cloud does not know a seat is idle while work assigned to it is open.

- **Assignment** is a seat key (`room/seat`) on the task (gap 4.3.1).
- **Claim** goes through the cloud (`manage_task action=claim`). The owner's 2026-10-05 ruling, "claims route through the cloud; they are not reported to it", is applied to the task itself: the task is the cloud's work item, with `claimed_by` and `claimed_at`.
- **Wake** is a pull. The client's bridge loop asks `GET /api/v2/openrig/machines/{machine}/work` for open, unclaimed or rejected tasks assigned to seats it runs. For a seat whose `seat_status.state` is idle, it runs `rig send <session> "<one-line pointer: task id + 'manage_task action=resume'>"` and posts a `delivered` event. Delivery is idempotent per (task, last event seq), so a wake is sent once per change.

### 4.9 Resume / continue — NEW

`manage_task action=resume task_id=…` returns one brief, built from the ledger and the resolved context, so that the next agent does not undo the previous agent's work:

- the task, its status and acceptance criteria;
- the last gate verdict with its reasons;
- the last evidence: files touched, failing tests, head sha;
- open subtasks and blocking dependencies;
- the resolved task context (inheritance applied);
- the last `handover` note;
- the next action derived from the above (for example "fix: D3 failed, `TestX` still fails").

A size budget applies. The brief is the same for a fresh seat, a restarted seat and a different model, which is what makes switching an occupant safe.

### 4.10 Project memory — PARTIAL

Project and branch contexts already serve as memory, and seat `memory` modules carry seat-level memory. **Added:** on ACCEPT, the gate appends one verified line to the branch context (task, head sha, files, tests run). The branch context then shows what is done from verified facts only, never from unverified claims. Decisions are recorded with `add_insight` category `decision`. No new memory store is introduced.

### 4.11 Observability surfaces

| Surface | Status | Source |
|---|---|---|
| Seats, topology, drift | BUILT | `SeatsPage`, `TopologyPage`, `seat_status`, `GET /api/v2/openrig/machines` |
| Session transcripts, live | BUILT | `SessionsPage`, `/ws/sessions`, `agent_session_events` |
| Task timeline (the state machine) | NEW | `task_events` over REST, live through the existing task websocket |
| KPI panel | NEW | section 9 |

## 5. Gate interface (precise)

- **Input:** `task_id`, the latest `evidence_submitted` payload, the task's `acceptance_criteria []string`, `completion_summary`, `testing_notes`, and the previous evidence for D4.
- **Output:** a `gate_verdict` event with payload `{verdict: accept|reject|uncertain, checks: {D1..D5: pass|fail|flag|skip}, criteria: [{text, answer, confidence}], reasons: [string], mode: shadow|enforce}`, plus the status transition (enforce mode only).
- **Errors:** Jev unreachable or over budget gives `uncertain` with reason `jev_unavailable`. A missing gate never becomes an accept.
- **Data ownership:** the cloud owns verdicts and status. The client owns raw evidence and reports only its summary. Jev receives the input above and nothing else.

## 6. Model additions (ORM first, then SQL)

- `task_events`, as in 4.5. `user_id` is on every row, and there are no cascading foreign keys (the application deletes events with the task).
- `tasks.acceptance_criteria` (JSONB array of strings), `tasks.scope` (JSONB array of globs), `tasks.claimed_by` and `tasks.claimed_at`. The same four columns go on `subtasks`.
- `tasks.assignees` holds seat keys. The legacy role resolution is removed, and the `ai_*` columns follow the owner's decision on directive 3.
- `tasks.progress_history` and `tasks.progress_count` are removed once the ledger is the only writer.

## 7. Gaps between the vision and the code (measured 2026-10-08)

| Vision element | State in code |
|---|---|
| Orchestrator | The lead seat exists. Routing to seats does not: assignees are legacy role names. |
| Brain/worker roles | Seats and occupants exist. `escalates_to` links exist, but nothing reads them at run time. |
| MCP task/subtask/context | Built. `manage_rule` is not registered (by design, see 4.2). Calls carry no seat identity. |
| Context as the key asset | Four tiers and inheritance are built. Context packs are built with no caller. There is no resume brief. |
| Git and tests | The cloud holds no git or test facts. `completion_summary` and `testing_notes` are free text from the agent. |
| Jev gate | Not built (G7). Its recorded hook point no longer exists (`e1970dc5`). |
| Observable state machine | Not built. The status enum exists, but there is no transition history beyond `progress_history` JSON. |
| Wake-on-open-work | Not built. OpenRig's local queue wakes seats; the cloud cannot. |
| Resume/continue | Seat-level resume is built by OpenRig (snapshots, session files). Task-level resume is not built. |
| Project memory | Contexts and memory modules are built. Nothing writes verified facts into them. |
| Go as the platform | Built: the server is Go. The client binary is a skeleton; the client is still Python scripts. |

## 8. What is deliberately not in this architecture

- A server-side LLM runtime for planning (see section 3).
- A cloud copy of OpenRig's `queue_items` for task work. The task is the cloud's work item, and the local queue stays OpenRig's coordination channel. This affects NEXT_GEN directive (F) F3. See the decision note.
- `manage_rule` as a tool.
- Rust. The bottlenecks are model latency, network and tools, as the vision states.

## 9. KPI, computed from the ledger

- **Verified tasks** = tasks with a `gate_verdict` ACCEPT in enforce mode during the period.
- **Human touches** = events with `actor_kind = human` (decisions, overrides) plus owner approvals recorded as `human_decision`.
- **KPI** = verified tasks ÷ human touches. Two companion figures are reported beside it so the ratio cannot be gamed by skipping review: **rework rate** (REJECT verdicts per ACCEPT) and **escape rate** (tasks reopened `done → in_progress` after ACCEPT).
