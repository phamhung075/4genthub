# NFR register

The one NFR doc of record. Every requirement carries a **status** and a **verification**; a status
without a verification is a claim, and this file does not carry claims.

Provenance: derived from `ai_docs/reports-status/NFR-analysis-2026-10-19.md`, a claim catalogue whose
mechanisms were checked against committed code — 15 of its 43 rows named a mechanism, scope or number
the code contradicts, 20 were policy or weaker than claimed, 8 held. The catalogue stays where it is as
provenance; this register is what a reader rules from.

Measured at: hub `d45aa05d`, client `c46812c`, 2026-10-19.

## Vocabulary

| Status | Means |
|---|---|
| **GATE** | A test, hook or script fails when the property stops holding. |
| **CONFIG** | A runtime setting enforces it; any published number is a default, never a property. |
| **POLICY** | A rule a human or agent review enforces. No machine check. |
| **TARGET** | A goal with no mechanism yet. |
| **GAP** | The claimed enforcement does not exist. |
| **STALE** | The report named a mechanism that was retired. |
| **PARTIAL** | The mechanism exists but is weaker or narrower than claimed. |

Two rules keep this file honest:

1. **A published limit is a default.** The code reads the environment; any number in this file or in a
   doc is the default, and the rig's value is read with the command in the row's verification.
2. **A benchmark baseline names its host and is a range, not a promise.** Two runs on the same CPU model differed by 30% here; a move beyond that range is what a reader should treat as drift.
3. **A row whose mechanism moves without its `measured` date moves is drift.** The verification column is
   how the next reader checks the row; a row with `none` is a GAP or a TARGET, not a promise.

Verification forms: `test:` and the test's run pattern · `cmd:` and a shell command · `file:` and a repo
path with its line (a static fact a reader can open) · `review` (the policy has no machine check) · `none`
(no mechanism).

## Performance

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| PERF-01 | Database access is pooled over pgx, and the API answers within a published latency envelope. | PARTIAL | `database/sql` pool over pgx stdlib; `SetMaxOpenConns(PoolSize+MaxOverflow)`. | `file:agenthub_go/fastmcp/task_management/infrastructure/database/pgx_opener.go:45`; measured `test:go test ./fastmcp/task_management/application/services -bench BenchmarkResolveContext -benchmem` -> 19.7-26.0 us/op over two runs, 212 allocs/op (2026-10-19, commit `81074bd6`, i7-12700F); no published latency envelope | agenthub_go | 2026-10-19 |
| PERF-02 | Context read and resolution stay under the 5 ms provenance budget, with the inheritance merge in memory and no cache layer. | PARTIAL | `GetContext` reads the requested level's repository and `resolveInheritanceSync` walks the parent repositories in order; the never-wired cache service and the dead `force_refresh` argument are gone (gate T6). The 5 ms budget is measured by the benchmark, not gated. | `file:agenthub_go/fastmcp/task_management/application/services/unified_context_service.go:315`; `file:agenthub_go/fastmcp/task_management/application/services/unified_context_service.go:1173`; measured `test:go test ./fastmcp/task_management/application/services -bench BenchmarkResolveContext -benchmem` -> 18.5-26.3 us/op over three runs (architect two, lead one), 25881-25882 B/op, 212 allocs/op (2026-10-19, commit `d45aa05d`, i7-12700F) | agenthub_go | 2026-10-19 |
| PERF-03 | IPC frames are unix-socket, length-prefixed. | PARTIAL | Unix socket, **newline-delimited JSON** frames, not length-prefixed. | `file:agenthub_client/rust/agenthub-runtime/src/ipc/mod.rs:101` | runtime | 2026-10-19 |
| PERF-04 | Realtime fan-out reaches a client promptly under load. | PARTIAL | `/ws/realtime` is mounted and fan-out exists; server-side fan-out is measured, the wire and the render are not. | `file:agenthub_go/fastmcp/server/httpapp/ws_mount.go:70`, `file:agenthub_go/fastmcp/server/routes/websocket_fanout_bench_test.go`; measured `cmd:go test ./fastmcp/server/routes -bench BenchmarkRealtimeFanout -benchmem` -> 1 socket 14.8 us/op, 10 sockets 126-127 us/op, 100 sockets 1.24-1.31 ms/op (12.4-13 us/socket, 13841 allocs/op) over three runs; the 500 ms ceiling at 100 sockets holds (2026-10-19, commit `86da875e`, i7-12700F) | agenthub_go | 2026-10-19 |
| PERF-05 | A task event carries a delta of changed fields under a 2048-byte cap. | GATE | `updated` and `completed` events carry `{id, updated_at}` plus only the changed fields; `created` carries the payload without `details`; `deleted` carries `{id, title}`; a changed `details` is `details_changed: true`, never carried; any primary over 2048 B becomes `{id, refetch: true}`; the dedup key carries `updated_at`. | `test:go test ./fastmcp/task_management/application/services -run '^$' -bench '^BenchmarkTaskEventDelta$' -benchmem` -> status 90 B, completion 208 B, details 91 B, wide over-cap -> 42 B refetch, 3.7-33.1 us/op (2026-10-19, commit `0f2c67fd`, i7-12700F); client merge `file:agenthub-frontend/src/hooks/useRealtimeSync.ts` on main at `6b465040` (branch `b6ab0203`) | agenthub_go | 2026-10-19 |
| PERF-06 | The watch wall has no line-buffering delay. | GATE | A line reaches the pane's writer within 2 x `feedPollInterval` (1 s), in a `Write` of its own, uncoalesced. | `test:go test ./internal/clientwatch -run TestFeedWritesEachLineWithinOnePoll`; measured green in 1.00 s at client `c21e702`: the delay and the one-`Write` shape are both asserted (2026-10-19) | client | 2026-10-19 |

## Cost

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| COST-01 | Compaction limits are configurable; no constant is a property. | CONFIG | Defaults 150k/250k/300k; the rig's value is in the tmux environment. | `cmd:tmux show-environment -g COMPACT_*`; `file:agenthub_client/internal/seatlog/seatlog.go:40` | client | 2026-10-19 |
| COST-02 | A seat can be compacted out-of-band while it works. | STALE | A `ForceCompact` IPC request relays `{"type":"compact"}` into the seat's mailbox; the `forcecompact` binary was retired. | `file:agenthub_client/rust/agenthub-runtime/src/ipc/mod.rs:205`; `file:agenthub_client/rust/agenthub-runtime/src/runner/mod.rs:1161` | runtime | 2026-10-19 |
| COST-03 | The peak gate refuses starts and resumes inside DeepSeek's published UTC peak windows. | GATE | The gate is one decision, `clientoffpeak.Check` (`clientoffpeak/gate.go:109`; the `deepseek/` prefix test it filters seats with is `:145`), reached by eight verbs: `up` (`clientlifecycle/lifecycle.go:353`), `compact` (`:949`), `continue` (`clientrestore/continue.go:155`, `:184`), `watchdog` (`clientrestore/watchdog.go:293`), `sync respawn` (`clientsync/respawnverb.go:165`), `seat reseat` (`clientseat/reseat.go:126`), `room reseat` (`clientroom/room.go:445`) and `heal` (`clientheal/command.go:131`) - the restore verbs through the exported `PeakGate` (`clientrestore/restore.go:307`) - and by two automatic resumes, the idle guard (`clientlifecycle/idleguard.go:103`) and the compaction supervisor's held resume (`clientlifecycle/supervisor.go:229`). Peak hours are 01:00-04:00 and 06:00-10:00 UTC Mon-Fri, as `api-docs.deepseek.com/quick_start/pricing` publishes them (Chinese public holidays, read from `DEEPSEEK_HOLIDAYS`, are off-peak in full); only seats whose model starts `deepseek/` are gated. What it does not do: it refuses a start or a resume only, so a seat already running when peak begins is not stopped. Both restarts ask it before the stop, so a refused one leaves the seat exactly as it was: `room reseat` before `StopSeat` (`clientroom/room.go:445`) and `heal` before `StopSeat` inside its repair (`clientheal/command.go:131`), whose refusal rides the finding for that seat and exits 3. | `test:go test ./internal/clientoffpeak ./internal/clientlifecycle -run 'TestTheBoundariesMatchTheShellGate\|TestDecideRefusesOnThePeakBlockItSitsIn\|TestCheckRefusesOnlyWhenTheSettingIsOnTheRoomIsDeepSeekAndItIsPeak\|TestUpRefusesAtPeakWhenTheRoomRunsADeepSeekSeat' -count=1`; `test:go test ./internal/clientroom -run 'TestRoomReseatRefusesAtPeakBeforeTheSeatIsStopped\|TestRoomReseatProceedsAtPeakWithTheFlag'`; `test:go test ./internal/clientheal -run 'TestHealsGateRefusesBeforeTheStop\|TestARefusedRestartIsAnUnfixedFindingNamingTheSeat'`; `file:agenthub_client/internal/clientoffpeak/schedule.go:43`; `file:agenthub_client/internal/clientoffpeak/gate.go:145` | client | 2026-10-20 |
| COST-04 | Bulk work is offloaded to a cheap model. | POLICY | The `deepseek-offload` skill; no machine check. | `review` | policy | 2026-10-19 |
| COST-05 | A queue row is bounded and its body schema is enforced. | GATE | Row 600 chars; fields 280/110/100/78 plus prefixes; summary 120. | `test:cargo test -p agenthub-runtime queue::tests`; `file:agenthub_client/rust/agenthub-runtime/src/queue/mod.rs:179` | runtime | 2026-10-19 |
| COST-06 | Replies and docs are short. | POLICY | The `short-output` and `token-economy` skills; no machine check. | `review` | policy | 2026-10-19 |

## Security

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| SEC-01 | Every tenant-scoped query filters by user; a delete of an aggregate is scoped once, at its root - the branch delete proves the project's owner, then cleans the whole aggregate. | PARTIAL | Repository-level scope; a **nil** `UserID` means system mode with no filter; the branch delete carries no per-child author filter by ruling (`RULING-int03-branch-delete-scope-2026-10-20.md`), so its project check at `infrastructure/repositories/git_branch_repository.go:440` is the whole tenancy boundary, proven by `TestGitBranchRepoUserIsolation`. 49 tables: 4 carry no `user_id`, 2 carry a nullable one. | `file:agenthub_go/fastmcp/task_management/infrastructure/repositories/base_user_scoped_repository.go:37`; `file:agenthub_go/fastmcp/task_management/infrastructure/repositories/git_branch_repository.go:440`; `test:go test ./fastmcp/task_management/infrastructure/database -run TestSchema` | agenthub_go | 2026-10-19 |
| SEC-02 | No credential rides argv or a long-lived environment. | GATE | The tmux server is bootstrapped from `env_clear()` plus `ENV_SERVER_ALLOWLIST` (host plumbing only, `LC_` by prefix) and an already-running server is cleaned by that same allowlist before every launch, so a credential nobody listed is off the global environment without a code change; a seat's `-e` pairs are scrubbed from its own session environment once the pane exists, while the pane keeps the environment the kernel gave it at `exec`, so its `mcp.json` and model client still read their values; the connector token stays denied by exact name and off the `-e` list, and the server's argv is the bootstrap client's, never a seat's. | `test:cargo test --offline launch_env_tests` in `agenthub_client/rust/agenthub-runtime` (12); `file:agenthub_client/rust/agenthub-runtime/src/main.rs:78`; `file:agenthub_client/rust/agenthub-runtime/src/pty/mod.rs:193`; `file:agenthub_client/rust/agenthub-runtime/src/pty/mod.rs:229`; `file:agenthub_client/rust/agenthub-runtime/src/pty/mod.rs:294` | runtime | 2026-10-20 `3c2d92e` |
| SEC-03 | Redaction is fail-closed per event. | GATE | Every failure mode withholds the raw bytes. | `test:go test ./internal/clientsync -run 'TestRedact\|TestEventWithholds'`; `file:agenthub_client/internal/clientsync/redaction.go:1` | client | 2026-10-19 |
| SEC-04 | A seat's tool calls pass a deny-by-policy hook. | PARTIAL | The guard is installed for omp and agy; the deny config is written only into an omp seat's dir. claude-code and codex get neither. | `file:agenthub_client/rust/agenthub-runtime/assets/seat-guard.ts:1`; `file:agenthub_client/rust/agenthub-runtime/src/supervisor/mod.rs:1016` | runtime | 2026-10-19 |
| SEC-05 | A seat cannot push any ref but `main` (or `frontend`). | GATE | The `pre-push` hook refuses every other ref; it is seat-independent. | `file:scripts/git-hooks/pre-push-branches:5` | hub | 2026-10-19 |
| SEC-06 | Evidence leaves the client redacted. | PARTIAL | Count-only wire at the client transport; the server's evidence route stores the raw `git diff --numstat` text (capped at 1 MiB). | `file:agenthub_client/internal/clientjev/countsonly.go:7`; `file:agenthub_go/fastmcp/server/routes/task_evidence_routes.go:64` | client + agenthub_go | 2026-10-19 |
| SEC-07 | Seats run unprivileged. | POLICY | Convention; no check on the seat UID. | `review` | policy | 2026-10-19 |

## Reliability

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| REL-01 | The rail survives a cloud outage and board work can continue. | PARTIAL | The rail is durable local SQLite; cloud-board work during an outage is deferred by owner decision. | `file:agenthub_client/rust/agenthub-runtime/src/queue/mod.rs:524`; `file:ai_docs/core-architecture/agenthub-system-architecture.md:733` | runtime | 2026-10-19 |
| REL-02 | Seat children survive an agent kill; four safeguards hold. | PARTIAL | Children are `Setsid`-detached and survive an agent SIGKILL; board work still needs the agent. | `file:agenthub_client/internal/clientlifecycle/supervisor.go:552`; `file:agenthub_client/internal/clientlifecycle/supervisor.go:567`; `file:agenthub_client/internal/clientlifecycle/detach_unix.go:14` | client | 2026-10-20 |
| REL-03 | A dead bridge is detected: 25 s heartbeat, degraded after 3 misses, fatal 1008/4401. | GATE | The keep-alive closes after three silent heartbeats. | `test:go test ./internal/clientsync -run TestKeepAlive` | client | 2026-10-19 |
| REL-04 | Events and the cursor commit atomically, and resume replays nothing twice. | PARTIAL | One transaction moves events and `client_cursor`; there is no server replay, the client resumes. | `file:agenthub_go/fastmcp/session_stream/repository.go:425` | agenthub_go | 2026-10-19 |
| REL-05 | `continue` rebuilds a seat from durable state. | PARTIAL | It restarts seats and re-sends the brief; no tmux pane snapshot is read back. | `file:agenthub_client/internal/clientrestore/continue.go:34`; `file:agenthub_client/internal/clientrestore/continue.go:159`; `file:agenthub_client/internal/clientrestore/restore.go:271` | client | 2026-10-20 |
| REL-06 | A failure exits non-zero. | PARTIAL | A missing binary or token exits non-zero; the peak gate can return 0 with no row, and `up` ignores the watch child's exit. | `file:agenthub_client/internal/clientlifecycle/lifecycle.go:844`; `file:agenthub_client/internal/clientlifecycle/lifecycle.go:217` | client | 2026-10-19 |

## Integrity

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| INT-01 | A construction failure is loud; no mock reachable from the request path. | GATE | Nil session manager, nil builder or a failing builder returns an error; the mock is deleted from production. | `test:go test ./fastmcp/task_management/application/factories -run TestFactory`; `file:agenthub_go/fastmcp/task_management/application/factories/unified_context_facade_factory.go:69` | agenthub_go | 2026-10-19 `ffe4f07f` |
| INT-02 | A task's status has one writer and survives a delete. | PARTIAL | Status is dual-stored (row, then ledger append, one transaction); deleting a task deletes its ledger. | `file:agenthub_go/fastmcp/task_management/application/use_cases/status_ledger.go:92`; `file:agenthub_go/fastmcp/task_management/infrastructure/repositories/task_repository.go:703` | agenthub_go | 2026-10-19 |
| INT-03 | Foreign keys carry `CASCADE` only where the child has no independent lifecycle (Q7's seven); every join or aggregate-spanning child and every billing row is deleted by the application. | GATE | Q7 landed in five commits - `76b0d84d` removed the four cascades and added the application deletes, `a04131e3` gave the branch delete its `task_events` step, `ce3b1d87` widened that step to every author's events, `33e369a6` took the author condition out of the rest of the branch delete, and `040f6248` made that delete aggregate-scoped, so the project check is the only tenancy control. Seven `ON DELETE CASCADE` columns on six tables remain (`database/models.go:769, 810, 864, 900, 913, 950`, the last table carrying two); `task_events.task_id` (`task_event_tables.go:40`) never cascaded and is the precedent the four removals follow. Application deletes, one per reference: `task_contexts.task_id` with the task (`infrastructure/repositories/task_repository.go:677`) and in the branch delete (step 9, `infrastructure/repositories/git_branch_repository.go:514`); `task_labels.task_id` with the task (`infrastructure/repositories/task_repository.go:689`) and in the branch delete (step 7, `infrastructure/repositories/git_branch_repository.go:499`); `task_labels.label_id` at `infrastructure/repositories/label_repository.go:231`; `user_token_balances.user_id` at `user_repository.go:474`; the ledger with the task (`infrastructure/repositories/task_repository.go:703`) and in the branch delete (step 10, `infrastructure/repositories/git_branch_repository.go:523`). The branch delete is aggregate-scoped by ruling (`RULING-int03-branch-delete-scope-2026-10-20.md`): the project check at `infrastructure/repositories/git_branch_repository.go:440` is its tenancy boundary, so its child statements carry no author filter. Named residual: `ORMProjectRepository.DeleteProject` (`infrastructure/repositories/project_repository.go:616`) carries no ledger delete and is safe because `ProjectManagementService.DeleteProject` deletes each branch first (`project_management_service.go:413`). | `test:go test ./fastmcp/task_management/infrastructure/repositories -run TestGitBranchRepoDeleteBranchRemovesTaskEvents`; `test:go test ./fastmcp/task_management/infrastructure/repositories -run TestGitBranchRepoUserIsolation`; `test:go test ./fastmcp/task_management/infrastructure/database -run TestSchemaInventoryPinsTenancyAndCascades`; `file:agenthub_go/fastmcp/task_management/infrastructure/database/testdata/schema_fks.txt` | agenthub_go | 2026-10-20 |
| INT-04 | A terminal state is terminal; a handoff appends a successor and never reopens the source. | GATE | `TERMINAL_STATES` is `done`/`handed-off`; `handed_off_to` appends a successor. | `test:cargo test -p agenthub-runtime queue::tests`; `file:agenthub_client/rust/agenthub-runtime/src/queue/mod.rs:7` | runtime | 2026-10-19 |
| INT-05 | Each seat writes only in its own worktree on its own branch. | PARTIAL | Paths derive `<roomDir>/wt/<seat>`; `doctor` accepts any branch and there is no `--ff-only`. | `file:agenthub_client/internal/clientservices/worktrees.go:71`; `file:agenthub_client/internal/clientworktree/check.go:23` | client | 2026-10-19 |
| INT-06 | A commit carries only the named paths, and no seat lands a docs-only commit. | PARTIAL | The wrapper refuses an all-documentation seat commit; a direct `git commit` bypasses it. | `file:scripts/git-hooks/git_commit_capture.py:40`; `file:scripts/git-hooks/git_commit_capture.py:165` | hub | 2026-10-19 |

## Maintainability

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| MAINT-01 | No compatibility shims, aliases or legacy paths. | POLICY | Review-enforced; contradicted by live surfaces (`GET /legacy/tokens`, `legacyTaskContextRepo`). | `file:agenthub_go/fastmcp/server/httpapp/routes_mount.go:382`; `review` | policy | 2026-10-19 |
| MAINT-02 | Dependencies run one direction across the layers. | POLICY | Layering convention; no import check. | `review` | policy | 2026-10-19 |
| MAINT-03 | One `CHANGELOG/<date>--<title>.md` per task. | POLICY | Review-enforced; no check. | `review` | policy | 2026-10-19 |
| MAINT-04 | CI gates format, vet, typecheck and lint on every surface. | GATE | Hub Go runs `gofmt-check.sh`, `go vet`, `go test`; the frontend runs `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build`; the client (CI at `252c42b`, landed `8c7b7364`) runs `gofmt -l`, `go vet`, `go test`, `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test`. | `file:.github/workflows/ci.yml:28`; `file:.github/workflows/ci.yml:48`; `file:agenthub_client/.github/workflows/ci.yml:31`; `file:agenthub_client/.github/workflows/ci.yml:55`; `file:agenthub_client/.github/workflows/ci.yml:56` | hub + frontend + client | 2026-10-19 |
| MAINT-05 | A pruned path stays deleted and unreferenced. | GATE | A test pins both directions. | `test:go test ./internal/repoguards -run TestAPrunedPath` | agenthub_go | 2026-10-19 |

## Observability

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| OBS-01 | A live wall shows every seat. | GATE | `4genteam watch --room <rig>` renders the grid. | `cmd:4genteam watch --room 4genthub-min` | client | 2026-10-19 |
| OBS-02 | Tool calls, jev decisions, the daemon log and queue transitions are on disk. | GATE | `<seat>/tool-calls.jsonl`, `<state>/jev_decisions.log`, `<state>/daemon.log`, the rail's transitions. | `file:agenthub_client/internal/clientactivity/activity.go:6`; `file:agenthub_client/internal/clientlifecycle/lifecycle.go:453` | client | 2026-10-19 |
| OBS-03 | The jev threshold is configuration in (0,1]. | PARTIAL | The ladder exists; the threshold is read and validated as a number in (0,1]. The published 0.75 is a default. | `file:agenthub_client/internal/clientjev/jev.go:79` | client | 2026-10-19 |
| OBS-04 | The completion gate runs client-side; the server does not record a verdict. | GATE | `4genteam complete` asks Jev and posts the evidence; `RecordGateVerdict` stays callerless by ruling (Q2 shrink, 2026-10-19). | `file:agenthub_client/internal/clientjev/jev.go:79`; `file:agenthub_go/fastmcp/task_management/application/services/task_event_recorder.go:158` | client | 2026-10-19 |

## Portability

| ID | Requirement | Status | Enforcement or policy | Verification | Owner | Measured |
|---|---|---|---|---|---|---|
| PORT-01 | Every supported runtime gets the same guard and policy. | PARTIAL | Four runtimes exist (`omp`, `agy`, `claude-code`, `codex`); only omp and agy get the guard. | `file:agenthub_client/rust/agenthub-runtime/src/types.rs:23`; `review` of SEC-04 | runtime | 2026-10-19 |
| PORT-02 | Spawns are argv-based; no shell interpolation. | PARTIAL | Every production spawn is argv: the Rust runtime reaches tmux through `tmux_command().args([...])` and the Go client through `exec.Command`, and no production `sh -c` exists - the two `Command::new("sh")` sites are test helpers (`supervisor/mod.rs:3391,4975`). Three shell lines remain by design, none of them built with `format!`: the pane wrapper `pane_command` (`pty/mod.rs:74`) is the one string tmux hands to the pane's SHELL, `env -u <denied keys> -u TMUX -u TMUX_PANE <runner command>`, so the runner command is re-parsed by that shell rather than passed as argv; and agy's two MCP entries are `sh -c` lines that read the seat's variables at run time, not values (`supervisor/mod.rs:498` the cloud bridge, `:516` the delegation server). | `test:cargo test --offline the_pane_command_unsets_the_tmux_pane_variables_and_the_denied_keys`; `file:agenthub_client/rust/agenthub-runtime/src/pty/mod.rs:74`; `file:agenthub_client/rust/agenthub-runtime/src/supervisor/mod.rs:498`; `file:agenthub_client/rust/agenthub-runtime/src/supervisor/mod.rs:516` | runtime | 2026-10-20 `900db14` |
| PORT-03 | `--state-root` is honoured on every verb. | GATE | `activity` and `4genteam seat reseat` take the flag as of client `c46812c` (hub pin `d9c165ae`): `clientenv.StateRootFromFlags` -> `ResolveStateRoot` at `clientactivity/activity.go:134,144` and `internal/clientseat/reseat.go:64,87`. | `test:go test ./internal/clientactivity -run TestTheStateRootFlagIsReadInsteadOfTheMachineDefault`; `test:go test ./internal/clientseat -run TestReseatReadsTheStateRootFlagInsteadOfTheMachineDefault` | client | 2026-10-19 |

## Gates this task landed

| Gate | Row | State |
|---|---|---|
| G1 | INT-01 | Landed `ffe4f07f`: the factory returns an error and the mock leaves the production package. |
| G2 | SEC-01, INT-03 | Landed `02a31ec4`: the schema guard pins the nullable `user_id` set and every cascade column. The requirement itself closed at `76b0d84d` plus the branch-delete fix (row INT-03). |
| G3 | MAINT-04 | Landed `8c7b7364` (client `252c42b`): the client CI gates `gofmt`, `cargo fmt --check` and `cargo clippy -D warnings`, and the drift they exposed is fixed. |
| T5 | PERF-04, PERF-06 | Landed `86da875e` (client `c21e702`): `BenchmarkRealtimeFanout` over 1/10/100 sockets with the 500 ms ceiling, and `TestFeedWritesEachLineWithinOnePoll` bound to 2 x `feedPollInterval`. |
| T6 | PERF-02 | Landed `d45aa05d`: the cache service and its test, the `CacheService` field, the cache parameter/default and `invalidateChildCaches` leave the service, the factory stops constructing it, and `force_refresh` leaves the MCP schema, description and handler, the HTTP routes, the controller, the facades, the service, the batch use case and the regenerated `apiReference.ts`; the `context_inheritance_cache` table and the branch-delete `DELETE` stay. |
| T7 | PERF-05 | Landed `0f2c67fd` (frontend `6b465040` on main, branch `b6ab0203`): the delta builder, the 2048 B cap with the refetch shape, the `updated_at` dedup key, `BenchmarkTaskEventDelta`'s four cases (90/208/91/42 B), and the frontend merge. |

## Open gates this register expects

None open.

## Rulings

Jev at lead tier, with the owner's delegation (2026-10-19): this register is the doc of record (Q1,
0.82); OBS-04 states the client-side gate and `RecordGateVerdict` is not wired (Q2, 1.0); SEC-04/PORT-01
state the guard boundary rather than extend it (Q3, 0.96); a TARGET row carries a recorded baseline once
T5 measures one (Q4, 0.8). PERF-02 is deleted, not wired (Q5, board `a120aef2`): the cache service
was built with a nil repository (`unified_context_facade_factory.go:84` at `695e4232`, deleted at
`d45aa05d`), no production path read it, `force_refresh` was threaded through the whole resolve
surface and read by nothing, and no production path reads or inserts into
`context_inheritance_cache` (the branch-delete cleanup still deletes its rows,
`infrastructure/repositories/git_branch_repository.go:456`); the row is rebased to the provenance budget (`NFR-analysis:41`,
`< 5 ms` with the merge in memory) at the landing `d45aa05d` (gate T6). A future cache must key by
user, level and context id, invalidate on every service write with the Python cascade (global -> all
of the user, project -> branch+task, branch -> task), and prove that a second identical resolve makes
zero repository calls.

PERF-05's delta is a flat field map (Q6, 2026-10-19): a task event's `payload.data.primary` carries
`id` and `updated_at` plus only the fields the write changed; `created` carries the task payload
without `details`; `deleted` keeps `{id, title}`. A changed `details` is signalled by
`details_changed: true` and never carried - the field is copied verbatim by the builder
(`websocket_payload_builder.go:38-46`) and has held 41k characters. Any `primary` that would exceed
**2048 bytes** is replaced by `{id, refetch: true}` and the consumer refetches. The emitter takes
the changed field names alongside the task, the notification dedup key carries the row's
`updated_at` (two distinct writes inside the 5 s window both ship, and one write emitted by both
emitter families collapses), and the frontend merges `primary` into the cached task
(`useRealtimeSync.ts:331-393` already merges for `completed`; `:224-243` replaces for `updated`).
Proven by `BenchmarkTaskEventDelta` (spec in `nfr-measurements.md`), gate T7.

INT-03's cascade set is per column (Q7, 2026-10-19), and it landed in five commits. `76b0d84d`
removed the four cascades and gave the task delete and the repository deletes their statements;
`a04131e3` gave the branch delete its `task_events` step; `ce3b1d87` widened that step to every
author's events; `33e369a6` removed the author condition from the rest of the branch delete; and
`040f6248` made that delete aggregate-scoped, leaving the project check as the only tenancy control.
The schema now carries
seven `ON DELETE CASCADE` columns on six tables: `agent_session_events.session_id` (`database/models.go:769`),
`project_git_branchs.project_id` (`:810`), `tasks.git_branch_id` (`:864`), `subtasks.task_id`
(`:900`), `task_assignees.task_id` (`:913`), and `task_dependencies.task_id` with
`depends_on_task_id` (`:950`). Each stays because the child has no independent lifecycle and belongs
to exactly one aggregate. `task_events.task_id` (`task_event_tables.go:40`) never cascaded; it is the
precedent the four removals follow. The four removed references, and the delete that owns each now:
`task_contexts.task_id` with the task (`infrastructure/repositories/task_repository.go:677`) and in the branch delete (step 9,
`infrastructure/repositories/git_branch_repository.go:514`); `task_labels.task_id` with the task (`infrastructure/repositories/task_repository.go:689`) and in
the branch delete (step 7, `infrastructure/repositories/git_branch_repository.go:499`); `task_labels.label_id` at
`infrastructure/repositories/label_repository.go:231`; `user_token_balances.user_id` at `user_repository.go:474`.

The branch delete proves ownership once, on the branch's project (`infrastructure/repositories/git_branch_repository.go:440`),
and then deletes every child by id with no author filter: a child's `user_id` records who WROTE the
row, and where the schema does not cascade (`task_contexts`, `task_labels`, `branch_contexts`,
`task_events`) filtering by it left another author's row behind and refused the branch with 23503
(`RULING-int03-branch-delete-scope-2026-10-20.md`). Where the schema cascades the filter only
removed a subset the database takes anyway. The project delete is the one path that relies on order
rather than on its own delete: `ProjectManagementService.DeleteProject` deletes each branch through
`DeleteBranch` first (`project_management_service.go:413`) and only then the project row (`:419`,
which reaches `ORMProjectRepository.Delete` at `infrastructure/repositories/project_repository.go:305` and its `DeleteProject`
at `:616`), so the project row goes with no tasks left; `ce3b1d87` kept that order instead of giving
the project delete a ledger step of its own, and a direct `DeleteProject` call with an evented task
would still fail 23503, and there is no such caller.

The G2 golden is the mechanism: `testdata/schema_fks.txt` carries the seven lines and
`TestSchemaInventoryPinsTenancyAndCascades` (`schema_matches_definitions_test.go:196`) fails in both
directions - a stale line and an unpinned cascade. Orphan counts are load-bearing now that the
database stops deleting: `TestTaskRepoDeleteCascade` (`task_repository_test.go:492`) seeds a
`task_contexts` row and counts it by `task_id`; `TestLabelRepoDeleteRemovesTaskLabels`
(`label_repository_test.go:14`) deletes a label and counts its `task_labels` link by `label_id`; `TestGitBranchRepoDeleteBranchCascade`
(`git_branch_repository_test.go:570`) seeds a context owned only by its task, plus a label, a
dependency, a subtask, an assignee and a branch context; `TestGitBranchRepoDeleteBranchRemovesTaskEvents`
(`:700`) seeds an event under a second author; `TestGitBranchRepoUserIsolation` (`:188`) proves
another user's branch delete answers false and leaves the branch and its children;
`TestProjectRepoDeleteProjectRemovesTaskEvents` (`project_repository_test.go:120`) walks the service
order; `TestAuthUserRepositoryDeleteAndResetToken` (`auth_repositories_test.go:249`) seeds a
`user_token_balances` row and counts it after `Delete`.

A later change to a status is a ruling, not an edit in
passing: amend this file and cite the row you changed.
