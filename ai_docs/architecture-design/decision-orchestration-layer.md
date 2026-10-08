Decision: 4genthub becomes an orchestration layer built on one execution ledger, evidence collected by the client, and a two-stage validation gate

Context: The owner's vision of 2026-10-08 positions 4genthub as the layer that makes several models build verified software, with KPI = verified software per unit of human attention. The code (HEAD `eaa41d18`) already has seats, the task graph, four-tier context and MCP tools. It has no transition history, no evidence of work, no gate, no cloud-side wake and no task resume. The server never reaches into the user's machine (NEXT_GEN "Direction"). The G7 hook point (`HandleTaskCompleted`) was deleted in `e1970dc5`. Full picture: `ai_docs/core-architecture/agenthub-system-architecture.md`.

Options:
- A. Phases as statuses. Extend the task status enum with `plan`, `context`, `implement`, `test`, `validate`, and let agents report evidence in the `complete` call. Pros: no new table; the frontend shows the phase as today. Cons: there is still no history, only the current value. Agents certify their own work, so the gate checks a claim. The enum and the transition table grow for every new phase, and the phases cannot repeat (TEST, FIX, TEST).
- B. Append-only `task_events` ledger, with the status kept on the task. Evidence is produced by the client binary. The gate runs deterministic checks, then Jev. Pros: one history serves the timeline, resume, wake, KPI and gate calibration. Repeated phases are natural. The evidence is facts the agent did not write. The existing transitions (`in_progress→review→done|in_progress`) already fit the gate. Cons: a new table, plus one transaction discipline (the status and the event are written together by one service). Evidence needs a new client subcommand; the client binary runs three sync verbs today and has no evidence verb.
- C. Server-side orchestration. Wire `ai_task_planning`, let the server call brain models and run tests in a cloud runner. Pros: the most control in one place. Cons: it contradicts the pull model and puts model keys and repository access in the cloud. It creates a second planner beside the lead seat. The seam needs an adapter across five method shapes (directive 3), and a cloud runner is a large new system.

Recommendation: B. It is the only option where the gate checks facts rather than claims, and the only one where "observable" means a history and not a single current value. It adds one table and fits the existing structure: status transitions, machine tokens (T4), `seat_links.escalates_to`, contexts. The recommendation changes to A only if the owner rules that history is not wanted, and to C only if the owner wants 4genthub to run without OpenRig clients.

Sub-decisions taken with B:
1. The task is the cloud's work item. Claims (`claimed_by`) live on the task, and NEXT_GEN directive (F) F3's port of OpenRig `queue_items` to the cloud is not needed for task work. Two ledgers of the same work would diverge, which is the failure the owner's 2026-10-05 ruling was meant to prevent. **Needs the owner's confirmation**, because it changes their F2 → F4 → F3 sequence.
2. Phases are derived from events and never stored as a second status.
3. `progress_history` and `progress_count` stop being written. `add_progress` writes a `progress` event. This is a clean break.
4. No `manage_rule` tool. Rules are seat modules.
5. Wake is a pull by the client (`rig send` to an idle seat). The cloud does not push.

Interfaces:
- `task_events` (new, ORM first): in `{user_id, task_id, subtask_id?, seq, kind, actor_kind, actor, payload, created_at}`. Kinds and actor kinds are closed CHECK vocabularies. Out: `GET /api/v2/tasks/{id}/events?after_seq=`. Errors: 404 on a foreign task (user isolation). Owner: the task application service is the only writer.
- Evidence: `POST /api/v2/tasks/{id}/evidence` with a machine token. In: the evidence payload (shas, numstat, tests with exit codes and failed names). Out: the event seq. Errors: 401 without a machine token, 409 when `head_sha` is not new. Owner: the client produces it, the cloud stores it.
- Gate: an in-process service. In: the task, its criteria and the evidence pair. Out: a `gate_verdict` event plus the transition in enforce mode. Errors: Jev unavailable gives `uncertain`, never `accept`.
- `manage_task` actions: `claim`, `resume`. `complete` moves to `review` (not `done`) when the gate enforces.
- Seat identity: each rendered MCP block carries `X-Agenthub-Seat: <room>/<seat>`. It is used for attribution only.
- Wake: `GET /api/v2/openrig/machines/{machine}/work`. Out: open assigned tasks per seat with `last_seq`.

Risks:
- The status and the event written separately would diverge. Detect: a test that every status write path emits `status_changed` in the same transaction, plus a parity query (last `status_changed.new` equals `tasks.status`) run in CI.
- Gate false accepts from a convincing summary. Detect: shadow-mode calibration against reviewer verdicts (G7 step b) and a random audit sample.
- Jev cost or limits are undocumented (G7). Detect: count and log calls per verdict, with a hard daily budget in config that degrades to `uncertain`.
- Privacy: paths and test names go to TypeSafe. **The owner's product choice**: is sending paths and test names acceptable, or only counts?
- Wake storms. Detect: idempotency per (task, last_seq), and a `delivered` event count per hour on the KPI panel.

Handoff: the lead (`4genthub-min-lead@4genthub-min`) assigns NEXT_GEN group O in order O1 → O7, with O8 (frontend) once O1 lands and O9 put to the owner now. First task: go-dev, O1 (`task_events` ORM, SQL, the single-writer service and the parity test).
