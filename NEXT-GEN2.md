# NEXT-GEN2.md — 4genthub Next Generation: The Native Multi-Room Orchestration Engine

Supersedes `NEXT_GEN.md`. All completed/historical tasks from `NEXT_GEN.md` (`[x]` items, Python migration notes, archived agent-library removals) have been purged. All remaining open tasks are adapted here for the **native Rust + Go architecture that eliminates OpenRig entirely**.

---

## 1. Architectural Foundation & Direction

### Core Principle: Zero OpenRig Dependency, Pure Native Execution

1. **4genthub Cloud (Go + PostgreSQL)**: Ground truth for orchestration data: rooms, seats, tasks, ledger events (`task_events`), context hierarchy, policies, and MCP tools (`/mcp`, 10 tools).
2. **4genthub Client (`4genteam` in Go)**: Thin CLI and cloud bridge supervisor. Handles cloud sync, Keycloak auth, offpeak billing gates, human commands, MCP bridging, and watch/grid layouts (`herdr` / tmux view).
3. **4genthub Native Runtime (`agenthub-runtime` in Rust)**: High-performance local engine for the hot path:
   - **Terminal Seat Sessions**: Headless PTYs, direct socketpairs for RPC harnesses (`omp`), and tmux bridge for terminal attachment.
   - **Context Engine**: Fast token tracking (<0.1ms), 4-tier context hierarchy assembly, rolling window thresholds, and active compaction (`forcecompact`).
   - **Skill Engine**: Fast AST / frontmatter parser (`SKILL.md`), 4-tier hierarchical skill resolution (`share/`, `rooms/<room>/`, `rooms/<room>/<seat>/`, `client/`).
   - **Rules Engine**: Zero-allocation regex pattern matching (`RegexSet`) for command guardrails, tool denial rails, and seat policies (`locked`, `standard`, `open`, `yolo`).
   - **Hook System**: Typed async event pipeline (`tokio::sync::broadcast`) for pre/post-turn hooks, activity tracking, telemetry, and audit logging.
4. **Native Multi-Room Isolation**: Rooms execute in complete parallel isolation under `~/.config/4genthub/rooms/<room>/` with dedicated namespaces (`agenthub--<room>--<seat>`), eliminating daemon locks and port contention.
5. **Drop-in Compatibility**: A thin `rig` shim binary/symlink maps legacy commands (`rig whoami`, `rig send`, `rig queue`, `rig ps`) directly to `4genteam` / `agenthub-runtime`, ensuring existing seat prompts and skills work without modification.

---

## 2. System Topology

```
                  ┌──────────────────────────────────────────────┐
                  │           4genthub Cloud Backend             │
                  │   - REST API (/api/v2/...)                   │
                  │   - FastMCP Server (/mcp, 10 tools)          │
                  │   - Connector Endpoint (/ws/connector)       │
                  │   - Task Event Ledger (task_events)          │
                  └───────────────────────▲──────────────────────┘
                                          │ WSS (/ws/connector)
                  ┌───────────────────────▼──────────────────────┐
                  │        4genthub Client (`4genteam` in Go)     │
                  │   - Cloud Sync & Spec Materialization        │
                  │   - Offpeak Schedule Gate (DeepSeek)         │
                  │   - Bridge & Safeguard Supervision           │
                  │   - TUI / Watch Grid (herdr / tmux)          │
                  └───────────────────────▲──────────────────────┘
                                          │ Unix Domain Socket IPC
                  ┌───────────────────────▼──────────────────────┐
                  │    4genthub Native Core (`agenthub-runtime` in Rust)
                  │                                              │
                  │  ┌──────────────────┐  ┌──────────────────┐  │
                  │  │  PTY / Sessions  │  │  Context Engine  │  │
                  │  │  - Headless PTY  │  │  - Token Counter │  │
                  │  │  - Socketpair RPC│  │  - 4-Tier Tree   │  │
                  │  │  - Tmux Bridge   │  │  - Compaction    │  │
                  │  └──────────────────┘  └──────────────────┘  │
                  │  ┌──────────────────┐  ┌──────────────────┐  │
                  │  │   Rules Engine   │  │   Skill Engine   │  │
                  │  │  - RegexSet Rails│  │  - Frontmatter   │  │
                  │  │  - Tool Denials  │  │  - Tier Resolver │  │
                  │  └──────────────────┘  └──────────────────┘  │
                  │  ┌──────────────────────────────────────┐  │
                  │  │            Hook & Event Bus          │  │
                  │  │ Pre/Post Turn • Audit • Telemetry    │  │
                  │  └──────────────────────────────────────┘  │
                  └──────────────────────────────────────────────┘
```

---

## 3. Active Work Checklist

Legend:
- `[ ]` Open work item
- `[~]` Superseded / deferred

---

### Group R: Native Rust Runtime Engine (OpenRig Elimination)

*Builds `agenthub_client/rust/agenthub-runtime/` to completely replace the Node.js/TypeScript OpenRig daemon, `pi-runner.js`, and `openrig.sqlite`.*

- [x] **R1: Terminal & PTY Session Engine** (`agenthub-runtime::pty`)
  - Headless PTY runner supporting `omp --mode rpc`, `claude-code`, `agy`, and `codex`.
  - Direct socketpair creation for RPC-mode agents (`omp`) with backpressure control.
  - Bracketed paste text delivery (`\x1b[200~` ... `\x1b[201~`) for reliable multi-line/markdown input without terminal mangling.
  - Optional tmux window bridge so human operators can attach or view live panes via `4genteam grid`.
  - **Check**: Agent processes boot into PTYs with correct env and cwd; bracketed paste delivers 10KB multi-line markdown without dropped characters.
  - *Delivered & verified*: `agenthub_client/rust/agenthub-runtime/src/pty/mod.rs` compiled and tested.

- [x] **R2: High-Performance Context & Compaction Engine** (`agenthub-runtime::context`)
  - Sub-millisecond token counting per turn using `tiktoken-rs` / fast BPE tokenizers.
  - 4-tier context hierarchy assembler (Account/Company Overlay → Room Guidelines → Seat Role → Task/Subtask Context).
  - Rolling window context monitor against thresholds: `COMPACT_LIMIT_TOKENS` (150k), `COMPACT_WARN_TOKENS` (250k), and `COMPACT_HARD_TOKENS` (300k).
  - Native integration of `forcecompact` (sending direct JSON-RPC `{"type":"compact"}` to `omp` socketpair) without external ptrace workarounds.
  - **Check**: An agent hitting 300k tokens is force-compacted in-flight; token counts match OpenAI/Anthropic tokenizers within ±0.5%.
  - *Delivered & verified*: `agenthub_client/rust/agenthub-runtime/src/context/mod.rs` compiled and tested (`cargo test`).

- [x] **R3: Fast Skill Loader & Hierarchical Resolver** (`agenthub-runtime::skills`)
  - High-speed YAML frontmatter parser for `SKILL.md` using `serde_yaml`.
  - 4-tier skill resolution logic:
    1. Global shared (`skills/share/`)
    2. Room-specific (`skills/rooms/<room>/`)
    3. Seat-specific (`skills/rooms/<room>/<seat>/`)
    4. Client-operator (`skills/client/`)
  - Dynamic skill projection into seat configurations on boot or hot-reload.
  - **Check**: Validates 50 skill frontmatters in <5ms; correctly isolates room-level skills so seats in Room B never receive Room A skills.
  - *Delivered & verified*: `agenthub_client/rust/agenthub-runtime/src/skills/mod.rs` compiled and tested (`cargo test`).

- [x] **R4: Zero-Allocation Rules & Policy Engine** (`agenthub-runtime::rules`)
  - Policy enforcement levels: `locked`, `standard`, `open`, and `yolo`.
  - Shell railguard: compiles denied shell commands (`rm -rf /`, `git push`, unstaged `git add -A`, raw `openrig` commands) into a zero-allocation `regex::RegexSet`.
  - Pre-execution tool deny rails: filters MCP and CLI tool requests before execution (`nonLeadBashDeny`, `reviewerToolDeny`).
  - **Check**: Refused command pattern is intercepted in <10µs with a structured refusal; `yolo` allows permitted commands without prompts.
  - *Delivered & verified*: `agenthub_client/rust/agenthub-runtime/src/rules/mod.rs` compiled and tested (`cargo test`).

- [x] **R5: Async Hook & Telemetry Bus** (`agenthub-runtime::hooks`)
  - Broadcast event pipeline (`tokio::sync::broadcast`) for seat events: `SessionStarted`, `PreTurn`, `PostTurn`, `ToolRequested`, `ToolCompleted`, `ContextLimitReached`, `SessionTerminated`.
  - Non-blocking audit logger writing append-only `audit.jsonl` per seat.
  - Telemetry hook feeding live seat activity to `4genteam rigd` for cloud WebSocket streaming.
  - **Check**: Under high tool-call volume, audit logging adds zero measurable latency to turn execution.
  - *Delivered & verified*: `agenthub_client/rust/agenthub-runtime/src/hooks/mod.rs` compiled and tested.

- [x] **R6: Multi-Room Process Supervisor & Local State**
  - Room directory layout: `~/.config/4genthub/rooms/<room>/` (holding `spec.json`, `seats/`, `logs/`, `queue.sqlite`).
  - Concurrent multi-room execution: allows running Room 1, Room 2, and Room 3 simultaneously without socket or database lock collisions.
  - Local IPC server over Unix domain socket (`/run/user/$UID/agenthub.sock`) allowing `4genteam` (Go) to control seat lifecycles.
  - **Check**: Starting 3 rooms with 5 seats each boots 15 independent processes with isolated working directories and zero state crosstalk.
  - *Delivered & verified*: `agenthub_client/rust/agenthub-runtime/src/supervisor/mod.rs` and `ipc/mod.rs` running.

- [x] **R7: Native Identity (`whoami`), `send`, and `rig` Compatibility Shim**
  - Implements `4genteam whoami --json` natively from session env and room metadata (returns `{ identity, peers, edges, transcript }`).
  - Implements `4genteam send <room> <seat> <text>`.
  - Provides a lightweight `rig` binary/symlink (`~/.local/bin/rig -> 4genteam`) that forwards:
    - `rig whoami` -> `4genteam whoami`
    - `rig send`   -> `4genteam send`
    - `rig queue`  -> `4genteam queue`
    - `rig ps`     -> `4genteam ps`
  - **Check**: A seat running `rig whoami --json` receives identical JSON output to OpenRig without the OpenRig daemon running.
  - *Delivered & verified*: `agenthub_client/internal/clientruntime/command.go` and `4genteam rig-shim` tested live.

---

### Group O: Orchestration Layer (Adapted from NEXT_GEN)

*The owner vision of 2026-10-08: AI software orchestration layer where goals become tasks executed by brain and worker seats, verified by gates against evidence.*

- [x] **O1c: Progress Becomes Events (Task Event Ledger Transition)**
  - Drop `progress_history` and `progress_count` from database and ORM; migrate all notes into `task_events` as `progress` events.
  - Update frontend dialogs (`TaskDetailsDialog.tsx`, `SubtaskDetailsDialog.tsx`) to read from the O8 event timeline instead of `progress_history`.
  - **Check**: `grep -rn progress_history agenthub_go agenthub-frontend/src` returns zero matches outside migrations/tests; TypeScript compiler exits 0; progress notes display correctly.
  - *Delivered & verified*: `0002_progress_notes_backfill.sql` and `0003_progress_history_carry_and_drop.sql` executed; `tsc --noEmit` exits 0.

- [x] **O3: Automated Evidence Collection from Client**
  - Client subcommand `4genteam evidence --task <id> --base <sha> --test "<cmd>"`.
  - Runs `git diff --numstat` and the test suite, posting `evidence_submitted` event with commit hashes, numstat deltas, and test exit codes (no file contents or secret leakage).
  - **Check**: Submitting evidence returns 201; resubmitting identical `head_sha` returns 409; test failures are faithfully recorded in the ledger.
  - *Delivered & verified*: `agenthub_go 5ab853d1` + `agenthub_client 63fd184`.

- [x] **O4: Acceptance Criteria, Scope, and Task Resumption**
  - Add `acceptance_criteria` (JSONB string array) and `scope` (JSONB glob array) to `tasks` and `subtasks`.
  - Implement `manage_task action=resume` returning structured briefs: criteria, last verdict, reasons, evidence diff, blockers, and derived next action within a token budget.
  - **Check**: Resuming a rejected task returns the exact failure reasons as immediate action items; brief generation stays within token limits.
  - *Delivered & verified*: `task_resume_service.go` and schema validated.

- [x] **O5: Validation Gate (Shadow Mode)**
  - Implement validation gate service evaluating deterministic checks D1–D5 (syntax, types, tests, clean diff, numstat sanity) followed by Jev criterion verification.
  - Shadow mode records `gate_verdict` events (`accept`, `reject`, `uncertain`) without blocking task completion.
  - Pin Jev model to `jev-1.13.0`; implement token budget caps ($0.042/Mtok).
  - **Check**: Deterministic rejections trigger without calling Jev; Jev timeouts or budget limits default safely to `uncertain` (never `accept`).
  - *Delivered & verified*: `ValidationGateService` in `agenthub_go/fastmcp/task_management/domain/services/validation_gate_service.go` implementing D1-D5, Jev evaluation, daily token caps, fail-safe uncertain, and shadow mode recording. Verified in `validation_gate_service_test.go` and `complete_task_validation_gate_test.go`.

- [x] **O6: Gate Enforcement**
  - When enforcement is enabled, completing a task moves it to `review`.
  - Verdict handling:
    - `accept` → moves task to `done`, appends verified summary line to branch context.
    - `reject` → returns task to `in_progress` with recorded reasons.
    - `uncertain` → escalates to seat specified in `escalates_to` link or human operator.
  - **Check**: No task can reach `done` without an authentic `gate_verdict` event.
  - *Delivered & verified*: Integrated into `CompleteTaskUseCase` (`complete_task.go`), wiring ledger `RecordGateVerdict` and verdict enforcement transitions (`done`, `in_progress`, `review`). Verified via `complete_task_validation_gate_test.go` (`TestCompleteTaskGateEnforcementRejection`, `TestCompleteTaskGateEnforcementUncertainEscalates`).

- [x] **O7: Routing & Wake-on-Open-Work**
  - Assignees become strict seat keys (`room/seat`), eliminating legacy role strings.
  - Support `manage_task action=claim` with `claimed_by`/`claimed_at`.
  - Expose `GET /api/v2/machines/{machine}/work` listing unclaimed or rejected tasks.
  - Supervisor wakes idle seats via `4genteam send` with a direct resumption brief.
  - **Check**: Unclaimed task wakes the designated idle seat; claiming suppresses duplicate wakeups.
  - *Delivered & verified*: `Task.ClaimedBy`/`ClaimedAt` and `Task.Claim()` added in `agenthub_go/fastmcp/task_management/domain/entities/task.go`. `GET /api/v2/machines/{machine}/work` route added in `fastmcp/server/routes/machine_work_routes.go` and mounted in `task_routes.go`. Client work discovery and duplicate-suppressed seat waking implemented in `agenthub_client/internal/clientoutbox/manager.go` (`FetchWork`, `WakeSeatsForWork`) and `4genteam ledger work`.

- [x] **O8: Task Timeline & Event Ledger UI**
  - Replace static progress tabs in `agenthub-frontend` with a live event ledger timeline driven by the WebSocket stream.
  - Dynamically derive task lifecycle phases from ledger events rather than mutable columns.
  - **Check**: Timeline reflects full sequence (`created` → `in_progress` → `evidence_submitted` → `gate_verdict` → `done`).
  - *Delivered & verified*: `de7fd5f7` (`TaskEventTimeline.tsx`), with KPI panel deferred per lead ruling.

- [ ] **O9: Owner Product Decisions**
  - [ ] *(a) Privacy boundary*: Confirm whether file paths and test names may be sent to Jev / TypeSafe, or only counts.
  - [ ] *(b) Queue unification*: Confirm that 4genthub tasks fully supersede local `queue_items` for cross-seat work.
  - [ ] *(c) AI Seam Cleanup*: Confirm deletion of `ai_task_planning` and dead `ai_*` stub routes.
  - [ ] *(d) Daily budget cap*: Set the daily input token ceiling for Jev gate evaluations.

---

### Group P: Sync Protocol, Cursor Ledger & Outbox

*D9 sync protocol: making the task event ledger the sole source of truth between cloud and client.*

- [x] **P2: Cross-Task Ledger Cursor Endpoint**
  - Expose `GET /api/v2/ledger?after=<user_seq>&limit=N` returning user-isolated events ordered by `user_seq`.
  - Allows the client to track global project activity across all tasks in a single stream.
  - **Check**: Paging with `after` returns strict sequential events; access across tenants returns 404/403.
  - *Delivered & verified*: `ae2995e7` / `f285bdf6` in `agenthub_go/fastmcp/ledger/` and `server/routes/`.

- [x] **P3: Intent Submission Route with Optimistic Concurrency**
  - Expose `POST /api/v2/ledger/intents` accepting `[{client_event_id, task_id, kind, base_seq, payload}]`.
  - Validates decisions against `base_seq`: rejects stale decisions if concurrent changes occurred, while append-only facts are accepted.
  - Resending a known `client_event_id` returns the original response idempotently.
  - **Check**: Batch with one fact, one stale decision, and one duplicate returns accept, reject, and cached result respectively.
  - *Delivered & verified*: `ae2995e7` / `bccf893d` / `33965657` in `fastmcp/ledger/`.

- [x] **P4: Realtime Ledger Nudge Frame**
  - Emit server WebSocket frame `ledger_tip {user_seq}` to clients advertising the `ledger` capability.
  - Acts as a wake nudge: the client still pulls via `GET /api/v2/ledger`, ensuring network hiccups never cause data loss.
  - **Check**: Client converges purely by pulling if WebSocket drops; socket frame triggers immediate cursor pull.
  - *Delivered & verified*: `fcc8a2fc` in `fastmcp/server/websocket/`.

- [x] **P5: Client Outbox & Ledger-Based Wakeup**
  - `agenthub-client` maintains local persistent `cursor` and `outbox`.
  - Reconnection workflow: drains local outbox intents, fetches new events beyond `cursor`, and wakes seats from ledger updates instead of polling `/work`.
  - **Check**: Client killed mid-outbox reconnects and delivers queued intents without duplication.
  - *Delivered & verified*: `agenthub_client/internal/clientoutbox/` (`manager.go`, `store.go`, `commands.go`) with persistent state, facts-first drain ordering, and unit tests passing. Built into `4genteam outbox` / `4genteam ledger`.

- [x] **P6: Turn-End Context Prefetching**
  - When the client detects turn activity on a task, it prefetches the task resumption brief and post-compaction context in the background.
  - **Check**: Compacted seats resume instantly from disk cache without waiting for cloud fetch roundtrips.
  - *Delivered & verified*: Backend `GET /api/v2/tasks/{id}/resume` added in `task_routes.go`. Client prefetch and local disk caching (`~/.config/4genthub/cache/resumes/`) delivered in `internal/clientoutbox/prefetch.go`, background prefetch hooked on event pull, and verified via `prefetch_test.go` and CLI `4genteam outbox prefetch/cached`.

- [x] **P7: Context Updates Unified on Ledger Cursor**
  - Context modifications emit `context_updated {level, id, version}` into `task_events`.
  - Clients pull full updated context packs upon seeing the event version bump (no fragile JSON diff patches).
  - **Check**: Updating a room context emits an event; clients one version behind download the full document.
  - *Delivered & verified*: `ContextEventWriter` added to `update_context.go`, `ContextEventAppender` wired in `unified_context_service.go`, `unified_context_facade_factory.go` and `app.go`. Client `internal/clientoutbox/manager.go` extracts `context_updated` and triggers automatic background refresh/prefetch of resume contexts. Verified with tests in `fastmcp/` and `clientoutbox/`.

---

### Group D & F: Communication, Remote Commands & Ingest

- [x] **D1 & D3: Human Notification Producer & Direct Agent Messaging**
  - D1 confirmed: agent-to-agent AND agent-to-human.
  - Produce real-time `notification` frames for human dashboard bell (`NotificationBell.tsx`).
  - Native seat-to-seat delivery via `4genteam send` using local socket/PTY buffers.
  - **Check**: Agent escalations appear in the web dashboard notification bell; inter-seat messages land directly in peer terminals.
  - *Delivered & verified*: `agenthub_client/internal/clientbridge/notifications.go` (`TestNotify*` passing), `internal/clientruntime/ipc.go` (`SendTextToSeat`), and `agenthub-frontend/src/components/NotificationBell.tsx`.

- [x] **D4 & F5: Remote Execution via Connector (Opt-In)**
  - Support remote `send_to_seat`, `up`, and `down` commands over `/ws/connector` with capability `commands`.
  - Strict security guardrails: human-only issuer, token scope `sessions:command`, local whitelist of allowed rooms/commands, fail-closed audit log.
  - **Check**: Unauthorized command or unrecognized session is refused with structured refusal code.
  - *Delivered & verified*: `agenthub_client/internal/clientsync/` updated with `CapabilityCommands`, `handleRemoteCommand` guardrails (human-only, scope `sessions:command`, action whitelist `send_to_seat`/`up`/`down`, room whitelist), and verified via `remote_commands_test.go` (`TestRemoteCommandsRefusalGuardrails`, `TestRemoteCommandsExecutionSuccess`, `TestRemoteCommandsExecutionFailureReportsError`).

- [x] **F4: Native Ingest Streaming in `rigd`**
  - Point `4genteam rigd` to read session logs and events directly from native Rust runtime PTY outputs.
  - Stream redacted events over `/ws/connector` to 4genthub Cloud with server-side client cursor tracking.
  - **Check**: Streaming survives network disconnection; reconnect resumes from exact byte cursor without duplicate events.
  - *Delivered & verified*: `agenthub_client/internal/clientsync/rigd.go` and `connector.go` (`TestStopAndWaitCursorAndGap`, `TestHelloCarriesProtocolVersionAndCapabilities` passing).

---

### Group T: Database Schema & Technical Cleanups

- [x] **T12: Single Ordered Embedded Migrations Baseline**
  - Unify all 7 `TableDef` schemas and `init_schema_postgresql.sql` into an ordered embedded migration suite (`0001_baseline.sql` via `go:embed`).
  - Replace ad-hoc column ensurers with a versioned migration table.
  - **Check**: Fresh database boots from zero to current schema using embedded migrations alone.
  - *Delivered & verified*: `2c2b1af3` / `0aa23a75` (`0001_baseline.sql`, `0002_progress_notes_backfill.sql`, `0003_progress_history_carry_and_drop.sql`).

- [ ] **T13: Repoint Integration Tests & Verification Guards**
  - Repoint all Python-era test fixtures (`scripts/tests/`) to native Go and Rust entrypoints.
  - Ensure zero tests shell out to obsolete Python scripts.
  - **Check**: `pytest scripts/tests -q` and `go test ./...` both pass cleanly.

---

## 4. Phased Execution Roadmap

```
  Phase 1: Rust Core Engine (R1, R2, R4)
    ├── Terminal PTY Runner & Socketpair RPC (omp, claude, agy, codex)
    ├── Token Tracking & Native Active Compaction
    └── Zero-Allocation Regex Policy Guardrails
                           │
  Phase 2: Local Integration & Parity (R3, R5, R7)
    ├── Skill Loader & 4-Tier Resolver
    ├── Native whoami & send Commands + rig Shim
    └── Async Hook Bus & Audit Logger
                           │
  Phase 3: Multi-Room Lifecycle (R6, F4)
    ├── Room Directory Layout (~/.config/4genthub/rooms/)
    ├── Concurrent Multi-Room Execution via 4genteam
    └── Native Event Streaming via rigd (No OpenRig Daemon)
                           │
  Phase 4: Orchestration & Ledger (O1c, O3, O4, P1-P5)
    ├── Event Ledger Cursor & Outbox Sync
    ├── Client Automated Evidence Submission
    └── Structured Task Resume Briefs
                           │
  Phase 5: Gate Enforcement & Final Decommission (O5, O6, D1-D4)
    ├── Validation Gate with Jev Evaluation
    ├── Review -> Done Transition Enforcement
    └── Complete Removal of OpenRig from Host System
```
