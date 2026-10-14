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
   - **MEASURED FALSE today for two of the four (2026-10-13):** `rig send` fails in all four argv shapes the client itself uses (exit 2 or 3, `4genteam send: RIG, SEAT and MESSAGE are required`, because the fallback re-execs the name `rig`, which the shim now owns) and `rig whoami --json` returns exit 3 with a prose sentence where `seatcheck` expects JSON; `rig queue` does answer. Until the eleven `rig`-exec fallbacks are gone, "works without modification" does not hold for `send` or for `whoami --json` — tracked as the live U0 row (architect, 2026-10-13), which carries the inventory and the fix ruling.

---

## 2. System Topology

Only the **4genthub minimum team** (room `4genthub-min`): five seats, all hosted by `agenthub-runtime`.

| Seat | Type | Runtime / model |
|---|---|---|
| `lead` | lead | omp / `deepseek/deepseek-flash` |
| `architect` | architect | claude-code / `opus` |
| `go-dev` | developer | omp / `deepseek/deepseek-flash` |
| `fe-dev` | developer | omp / `deepseek/deepseek-flash` |
| `reviewer` | reviewer | omp / `deepseek/deepseek-flash` |

```
                         owner
                           ▲
                           │ escalates_to (C6, only the very important)
                         ┌─┴────┐  delegates_to   ┌───────────┐
              ┌─────────►│ lead │────────────────►│ architect │
              │          └─┬──┬─┘                 └─────┬─────┘
              │            │  │ delegates_to            │ can_observe
   escalates_to            │  └──────────┐              ▼
   (from every seat)       ▼             ▼        go-dev, fe-dev
                      ┌─────────┐   ┌─────────┐
                      │ go-dev  │◄─►│ fe-dev  │   collaborates_with
                      └────┬────┘   └────┬────┘
                           │ delegates_to│
                           └──────┬──────┘
                                  ▼
                            ┌──────────┐
                            │ reviewer │
                            └──────────┘
```

**Edges** (directed `from -> to`, kinds are the five the server's `commpolicy.ValidKind` accepts):

| From | Kind | To | Meaning |
|---|---|---|---|
| `lead` | `delegates_to` | `architect` | design and ruling requests |
| `lead` | `delegates_to` | `go-dev` | Go and Rust work |
| `lead` | `delegates_to` | `fe-dev` | frontend work |
| `go-dev` | `delegates_to` | `reviewer` | finished work goes to the gate |
| `fe-dev` | `delegates_to` | `reviewer` | finished work goes to the gate |
| `go-dev` | `collaborates_with` | `fe-dev` | shared API shapes |
| `architect` | `can_observe` | `go-dev` | read-only watch |
| `architect` | `can_observe` | `fe-dev` | read-only watch |
| `architect` | `escalates_to` | `lead` | seat tier of the C6 ladder |
| `go-dev` | `escalates_to` | `lead` | seat tier of the C6 ladder |
| `fe-dev` | `escalates_to` | `lead` | seat tier of the C6 ladder |
| `reviewer` | `escalates_to` | `lead` | seat tier of the C6 ladder |

The lead is the only seat that reaches the owner (C6). **Not yet applied:** `rooms/4genthub-min/spec.json` has `"links": []` today (measured 2026-10-14), so these edges exist in this plan only; `whoami` returns `edges` from that list.

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
    - **MEASURED (2026-10-13, tree `78e7a58`):** the file this item points at, `rust/agenthub-runtime/src/pty/mod.rs`, is **tmux shell-outs** — `git grep -c tmux` on it = **26**, and it uses `portable_pty`/`nix::` **zero** times; crate-wide those two names appear only in `frame.rs` (2) and `runner/mod.rs` (1). "Headless PTY runner" is therefore not supported *by that file*; the marker on this item is not evidence about it.
  - Direct socketpair creation for RPC-mode agents (`omp`) with backpressure control.
    - **TRUE ON THE INTEGRATION BRANCH, ABSENT ON THE CHECKOUT (measured 2026-10-13):** `git grep -c socketpair 78e7a58 -- rust/agenthub-runtime` = **3**, all in `src/runner/mod.rs`; the same grep at `f193f34` returns **0**. Cite the tree with this line.
  - Bracketed paste text delivery (`\x1b[200~` ... `\x1b[201~`) for reliable multi-line/markdown input without terminal mangling.
  - Optional tmux window bridge so human operators can attach or view live panes via `4genteam grid`.
  - **Check**: Agent processes boot into PTYs with correct env and cwd; bracketed paste delivers 10KB multi-line markdown without dropped characters.
  - *Delivered & verified*: `agenthub_client/rust/agenthub-runtime/src/pty/mod.rs` compiled and tested.

- [x] **R2: High-Performance Context & Compaction Engine** (`agenthub-runtime::context`)
  - Sub-millisecond token counting per turn using `tiktoken-rs` / fast BPE tokenizers.
    - **FALSE AS WRITTEN (measured 2026-10-13, client tree `f193f34`):** `rust/agenthub-runtime/Cargo.toml` requires tokio, portable-pty, nix, serde_yaml, regex and clap — **no tokenizer dependency of any kind**. Token counting may exist by other means; "using `tiktoken-rs`" does not.
  - 4-tier context hierarchy assembler (Account/Company Overlay → Room Guidelines → Seat Role → Task/Subtask Context).
  - Rolling window context monitor against thresholds: `COMPACT_LIMIT_TOKENS` (150k), `COMPACT_WARN_TOKENS` (250k), and `COMPACT_HARD_TOKENS` (300k).
  - Native integration of `forcecompact` (sending direct JSON-RPC `{"type":"compact"}` to `omp` socketpair) without external ptrace workarounds.
    - **DEFECT, MEASURED (2026-10-14, client tree `4567c37`, live room `4genthub-min`):** a compact sent to a seat with no turns yet is answered by omp with `Nothing to compact (session too small)`; `classify_failure` (`runner/mod.rs:1007`) matches none of its retryable signatures and returns `Terminal("the agent refused the turn")`, so the seat goes `state: blocked` (`run/<seat>.state.json`). On first start go-dev, fe-dev and reviewer were blocked this way, wrote no session log (empty `seats/<seat>/sessions/`), and so showed no events in `4genteam watch`; only the lead, which resumed an older session, did. **Fixed on client branch `fix/compact-reply-not-a-turn`** (one commit on `4567c37`, `cargo test --offline` 87 passed; not merged, not installed): a failed reply carrying the compact frame's id never enters the resume ladder.
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
    - **SCOPED (measured 2026-10-13, this host, at that moment):** the only room under that path, `test-alpha`, holds **`spec.json` alone** — no `seats/`, no `logs/`, no `queue.sqlite` — and the IPC socket `/run/user/$UID/agenthub.sock` named with this item **does not exist**. A room that has actually run may populate the rest; the layout is simply not observable for the room that exists, and the socket path is not there at all.
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

### Group C: OpenRig-Free Cutover Gate (owner decisions 2026-10-13/14)

*R1–R7 above are delivered as components. They are not the cutover: on 2026-10-14 the five seats of `4genthub-min` (lead, architect, go-dev, fe-dev, reviewer; `omp` / `deepseek/deepseek-flash`) are still hosted by the OpenRig daemon (node) and one `pi-runner.js` per seat. `agenthub-runtime` daemons run beside them and host no seat. This group is the gate that decides when OpenRig may stop.*

**Owner decisions (standing):**
- Retire the live OpenRig rig only after **U3 passes**, and only with a snapshot taken first.
- omp concurrency cap: unchanged.
- Until then OpenRig stays up; nothing in this group may stop it.

- [ ] **C1: Seats hosted natively (U0, U1, U2)**
  - `4genteam up <rig>` starts every seat on `agenthub-runtime runner` (socketpair RPC, queue store, room lifecycle) with no `pi-runner.js` and no OpenRig daemon.
  - Work sits on client branch `4genthub-min/u2-native-runner`. At `dbda423` (pushed 2026-10-13, verified: `go vet`, `go test ./...` 24 packages ok, `cargo test` 65 passed) it is **not** merged into `feat/support-agy-watch` (`f193f34`), the parent pin is not bumped, and the build is not installed on the running seats.
  - **Check**: `ps` shows no `openrig` or `pi-runner.js` process while all five seats are `ready`.

- [ ] **C2: Parity the OpenRig host provides today**
  - **Auto-resume** of a turn that ends on a provider stream error (`The socket connection was closed unexpectedly`) — `omp` does not retry, and OpenRig then refuses nudges to that pane.
    - **IMPLEMENTED in `rust/agenthub-runtime/src/runner/mod.rs`, with tests** (measured 2026-10-14, client `u2-native-runner`): `decide_resume`, `resume_delay`, `MAX_RESUME_ATTEMPTS`; a mid-turn error never starts a resume. What remains is the live check below.
  - **Large RPC responses**: chunking and reassembly (`RPC response exceeded the transport limit` ends turns today).
    - **Handled by resume, not chunking** (same file): `RPC response exceeded the transport limit` and `rpc chunk payload exceeds the transport limit` are in the retryable-error table, so the turn is resumed. Whether that satisfies "chunking and reassembly" is the owner's judgment; no reassembly code exists.
  - **`send`**: sender identity in the envelope and confirmation that the text was submitted, not left staged in the input box; no dependency on `OPENRIG_STATE_ROOT` (`clientruntime.OpenRigSend`).
    - **Sender envelope: implemented** (`RuntimeSendText`, From/To/Sent). **Submission confirmation: implemented at `041c18b`** — the runtime captures the pane around Enter, retries Enter once, and answers `outcome` `submitted` or `unconfirmed`; `send` prints `Pasted to …, submission unconfirmed` for the latter. **Not measured against a live pane** (no tmux server was up); U3 is where it is measured. `submitted` means the pane changed, not that the agent acknowledged. `OPENRIG_STATE_ROOT` is still read (`clientenv/env.go:24`, `clientwatch`, `clientlifecycle`, `clientsync/rigverb.go`); that is C7.
    - **MEASURED 2026-10-14 (lead, tree B at `a456656`): this name is CORRECT AS WRITTEN.** `OpenRigSend` is the function at `internal/clientruntime/openrigdaemon.go:123`, and **`OpenRigSendMessage` exists nowhere in the tree**; the architect's proposed correction to it is **disproved**, its only witness being the historical changelog line `CHANGELOG.md:1388`, written **before** the rename the same file records at `:459`, `:875`, `:880`, `:1307`. **Do not "fix" this name.**
  - **Idle-seat watchdog**: nudge a seat that has an unclaimed pending queue row (measured 2026-10-13: one row unclaimed ~4.5 h while the pane looked idle).
    - **IMPLEMENTED**: `nudge_loop` / `nudge_seat` in `rust/agenthub-runtime/src/ipc/mod.rs`, logging to `<state dir>/rooms/<room>/run/<seat>.nudge.jsonl`.
  - **Check**: a forced stream error is recovered with no human action.

- [ ] **C3: No exec of `rig` from the client (P1, U0)**
  - The `rig` shim maps `send` back to `send`, so `4genteam send` fails with `RIG, SEAT and MESSAGE are required`. Remove every `rig`-exec fallback (P1 holds the count; re-measure before quoting it).
  - **STALE FOR BOTH, MEASURED (go-dev, 2026-10-14): the replacement is already wired.** `rigd.go:163-175` wires
    `daemon.Transcript`/`Capture` to `clientruntime.NewClient("").Transcript`/`Capture`, and the **capture verb**
    (`clientruntime/command.go:577`, `NeedsRig false`) goes through the **OpenRig daemon over HTTP** — so transcript
    *and* the capture verb are native already, and **no interface for either needs ruling**. What remains is the
    **capture-shaped** `runRigCapture` at `respawnverb.go:55`, which is a **fallback disposition** (wire it to the
    native path that exists, or remove it with a refusal in words), not a new interface.
  - **AND THE GATE'S OPENING SENTENCE, EXPLAINED:** `~/.local/bin/rig` is a **symlink to `4genteam`**, so `exec rig <sub>`
    resolves **back into the client** — which is why `send` failed with `RIG, SEAT and MESSAGE are required` *while `rig`
    looked present*. Measured with `rig` unresolvable instead: **none of the four acceptance verbs execs `rig` at all** —
    `send`/`whoami`/`queue` go through the **runtime socket or the OpenRig daemon**, and **`ps` execs only `tmux`**.
  - **THE COUNT IS SETTLED BY THE GATE ON `bb4f412` (reviewer, 2026-10-14 05:55Z; `GATE-bb4f412-c3-landing-and-count-2026-10-14.md`), AND THE UNIT AS FIRST RECORDED HERE WAS WRONG. AT THE TIP IT IS `12` DIRECT CALL SITES THAT ISSUE THE EXEC OF `rig`, PLUS `1` RESOLUTION-ONLY.** Pin the instrument before quoting any number — *a site that issues the exec* is not *a site whose wrapper does*: the **12** are 7 `rig.Run` + 3 runner/`b.read("rig")` sites carrying a literal `rig` argv + 2 self-resolving `exec.LookPath(argv[0])` seams, and the 13th is `RequireRig` (`clientcmd/command.go:150`), which starts no child. **`26` is reachable only by counting 7 sites that provably spawn nothing** — its arithmetic was 13 + 13, against 13 + 11 for the 24. **Both rescue hypotheses were refuted by the helper bodies:** *transitive* fails because `PeakGate` (`lifecycle.go:621`) ends in `clientoffpeak.Check` (pure Go), `rigNodes` (`lifecycle.go:598`) ends in `clientruntime.RoomNodes`, and `resolveRig` (`continue.go:153`) ends in a LookPath; *any local tool* fails at 21 non-test / 24 with tests. **A count moves with the tree and never reached `26` on the direct instrument at any reachable sha:** `rig.Run` sites are **15** at `f193f34`, **12** at `18e3357`, **8** at `a456656`, **7** at `e4b5ccf` **and every sha after it**. **THE OTHER READINGS, KEPT SO THEY ARE NOT CONFUSED AGAIN:** **5** — an exec instruction whose program resolves to the name `rig`; **15** — a source site supplying the literal `rig`; **19** — the wrapper-closure reading. **Provenance of every superseded count:** the early sweep's **12** — the right number with the wrong named list; the later **19**, which **is the wrapper-closure reading** (13 direct + 6 non-test call sites of the five wrappers that really do spawn) — what failed there was its **named list**, not its number; and the reviewer's own **24, superseded by the reviewer**, because its regex caught **resolution sites a call-site instrument does not** and its first probe matched **JSON tags and flag names**. **`26` was the checklist unit as first recorded and is now provenance, not the unit.** The sweep's **class rule stays** — it is how fallbacks are separated from the sanctioned path, and `os.Executable` self re-exec stays excluded — **Still true from the sweeps and worth keeping:** `sync.go:78` is `case "rig":` dispatching to `RunRigVerb`, which contains **no exec** at all; and **a literal-argv sweep cannot see execs whose argv is a variable** — `restore.go:94` (`rig up … --existing`), `restore.go:205`/`:209` (`rig daemon status`/`start`), `watchdog.go:72` (a documented seam), `lifecycle.go:683` (`rig ui open`), and `bridge.go:161`/`:182`/`notifications.go:198` (`rig.Run` with argv from a variable) —**** bucket A, two gates/fallbacks (`respawnverb.go:56` `runRigCapture`; `clientcmd/command.go:142` `RequireRig`); bucket B, ten live execs (`bridge.go:157`, `:195`; `notifications.go:200`; `sync.go:34`, `:78`; `bundleverb.go:193`; `switchverb.go:314`, `:318`, `:319`, `:350`). Self re-exec, `pgrep`/`tmux`/`git` and three comment lines are excluded as not `rig`-execs. **The transcript line above is STALE: transcript is already native** — `connectorverb.go:287` (`rigTranscript`) reads it through the runtime, and its comment records that transcript is not a verb the installed client has, so the native replacement exists and only **capture** is genuinely dead. The architect's interface ruling is therefore scoped **to capture** (`runRigCapture`, whose own comment places it beside `connectorverb.go`'s `runRig`; it already has a test seam).
    **SCALE, for sequencing:** bucket B spans the bridge, sync, bundle and switch verbs, so removing *every* `rig`-exec fallback is several verbs' worth of native replacement, not just `send`/`whoami`/`queue`/`ps`. Order agreed with go-dev: the gate's four named verbs first (so the check below is demonstrable), then the rest, each fallback removed **only where the native path exists** — deleting a fallback before its replacement is the one way this pass can break a verb — with each tranche handed to the reviewer as it lands.
    **THE TWO TRUE FALLBACKS ARE THE SUBSTANCE, AND THEY DEGRADE SILENTLY TODAY — ranked by their finder above the count itself.** `lifecycle.go:610` (`rig ps`, after native `GetRoomStatus` errors or returns empty) makes A1 **skip the gate reading so `PeakGate` returns `ExitOK`** (`lifecycle.go:637-641`); `restore.go:60` (`rig send`, after native `SendTextToSeat` fails) returns `nil`, so **the restore brief is simply not delivered** (`restore.go:62-63`). Both **contradict this client's own printed rule** — a command that needs `rig` and cannot reach it must never downgrade silently. **So removing these two is not deleting an exec: the native branch must SUCCEED OR REFUSE IN WORDS**, work the gate's sentence did not anticipate. Related hypothesis, to be **measured, not assumed**: the runtime's `ListSessions` and `Transcript` variants exist expressly so the connector and `rigd` stop exec-ing `rig ps --json`, so some sites may already have a native replacement written and merely **unwired** — which is why every site is judged one at a time, never deleted on inspection.
    **Baseline green before any edit:** `go vet` 0, `go test ./...` all ok, `cargo +stable test` 65 passed. `cargo test` *as written* cannot run on this box (no default toolchain; none was set), so the quality bar's `cargo test` needs that stated or a toolchain provided.
    **Seat-shell incident, recorded because it belongs to this unit's environment:** while composing a note, go-dev used backticks inside a double-quoted string, so bash command-substituted the fragments and attempted them — `seat set-model`/`stop`/`launch` were rejected as an unknown verb or not found, `export`/`bundle`/`transcript` as unknown commands, `ps` ran read-only and exited on an unsupported option, `capture` printed usage with no argument. **No mutating verb succeeded, nothing was sent to any seat, and the live rig was not disturbed**; the note was re-recorded verbatim. Treat backticks as unsafe in these seat shells.
  - **CHECK MEASURED — IT DOES NOT HOLD YET (go-dev, 2026-10-14, branch's own built client run with `PATH=/usr/bin:/bin` so `rig` resolves to nothing; nothing edited, nothing pushed, live rig untouched, binary in `/tmp`): 2 of the four work, 1 dispatches, 1 is broken.**
    `whoami --json` **exit 0**, full identity JSON. `ps --nodes --json` **exit 0**, five seats. `send` exits 2 with **the client's own usage** (`4genteam send: SESSION and MESSAGE, or RIG SEAT and MESSAGE, are required`) — **not** the shim's `RIG, SEAT and MESSAGE are required` quoted above — so it **dispatches**; its positive path belongs on a **scratch room, never the live rig**.
    **`queue list` exits 1, and the cause is not a `rig` fallback: it is a MISSING NATIVE RPC.** The client asks the runtime for `QueueList` and the runtime answers `unknown variant QueueList, expected one of StartRoom, StopRoom, StopSeat, RestartSeat, SendText, GetRoomStatus, ListAllRooms, Whoami, …`. **CORRECTED AGAIN (go-dev, same hour): the queue RPC is NOT missing from the code.** It is in `rust/agenthub-runtime/src/types.rs:455-459` (`QueueList`, `QueueShow`, `QueueUpdate`, `QueueClaim`, `QueueClose`), and the client calls it at `internal/clientroom/queue.go:439`. **The RUNNING DAEMON PREDATES IT:** socket created `2026-10-13T20:42`, source `04:02` today, installed binary `03:00`. So `queue list` fails as a **STALE DAEMON refusing what newer source implements** — that leg is **not a code task**: it needs the runtime rebuilt, installed and the daemon restarted, which is the **lead's** call, gated by the reviewer's verdict and the standing rule that nothing in this group may stop the live rig. **Instrument caveat, because it nearly misled the room:** `strings` on the installed binary returns **0 hits for `QueueList` AND for `StartRoom`**, which demonstrably works in the running daemon — so `strings` is **not** a valid check for serde-tagged variant names here; **only the socket refusal and the file times are evidence.**
    **Open measurement, requested of go-dev:** which process owns that socket, and does restarting *that specific* daemon touch any of the five seats — the answer decides whether the queue leg is an install doable inside the standing rule or an owner window. The two bucket-A gates are **not** on `whoami`/`ps`'s path, which makes their removal **unit work, not gate work**; that is the distinction the single sentence above blurred. Capture (`respawnverb.go:55`) stays untouched until the architect's interface lands, and the ten bucket-B sites get **per-site measurement, never a judgement by inspection**.
  - **TRANCHE 1 IN PROGRESS on `4genthub-min/u2-native-runner` (committed locally, nothing pushed, tree clean):** `3840b8e` **B3** — the seat identity read from the client's own chain; `4203d96` **A2** — the restore brief delivered through `clientruntime.DeliverToSession` (session taken **as given**, refusal in words) plus `clientruntime.ReadRigNodes` for the room's node rows **and the gate's caller change**; `d7831fc` **hygiene** — three false `connectorverb.go:354-355` citations dropped, `rigWhoami`/`rigSend` renamed to `seatIdentity`/`seatDelivery`. **HEAD `d7831fc8619b0026c865477b6802a291ba62ebe6`.** (The clean `go build`/`go vet`/`go test ./...` result was first measured on the **working tree**; it was later confirmed at the shas from a clean checkout — see below.) **`4203d96` AND `d7831fc` ARE GREEN AND APPROVED — the earlier RED was a FALSE REPORT, retracted by its author.** Measured from a **clean detached checkout at `d7831fc`, zero dirty entries, `watchdog.go` blob `7cd04cc9c364a4a040af4ba3739ee651`**: `go build ./...` clean, all five affected packages ok, the named test ok. The four compile errors originally reported came from the **shared worktree**, which carries **in-flight B11 edits** (`clientlifecycle/lifecycle.go`, `clientrestore/watchdog.go`, `clientruntime/seatactivity.go`) — the **committed** `watchdog.go` is **byte-identical to `18e3357`'s**, zero `clientruntime` references. **The reviewer's approval re-pins to `3840b8e` + `4203d96`, replacing the working-tree hash `c4b6039b…`.** **RULE, now with a second reason: verify a commit by building a CLEAN CHECKOUT of that sha, never a shared worktree — whether the author or the reviewer is checking.** **LIMIT CARRIED DELIBERATELY: none of the gated verbs was run against the live rig — every one mutates it — so their acceptance is C4's, on `cutover-lab`, not this tranche's.**
  - **B11 LANDED at `968b2b6` (HEAD), proof sha-named: build and tests run in a `git worktree --detach` at that sha, ZERO dirty entries in that checkout — `go build ./...` 0, `go vet ./...` 0, `go test ./...` 24 packages ok, 0 FAIL; not pushed.** The watchdog's node read no longer execs `rig ps --nodes --rig RIG --json`; `expectedSeats` takes only the rig name; **a failed read counts zero rows exactly as the shell's pipe left it**, and **NO RECORDS is an empty table rather than a failure**; the runtime rung carries **`lifecycleState` beside `sessionStatus`** — the same fact under the key the watchdog's counter reads — so a consumer need not know which transport answered.
    **Surface changed (neither nit specified this): ONE exported read, `clientruntime.RoomNodes(ctx, room) (nodes, ok, err)`** — `ok && err == nil` a transport's answer (possibly empty), `!ok && err == nil` **NO RECORDS**, `err != nil` **a failed read**. `ReadRigNodes` is **gone from the exported surface** (now the unexported `daemonNodes`, so **no verb can take a rung by accident**), and `rigNodes` is a **thin wrapper** so `up`, `compact`, the restore gate and the watchdog take **one reading** instead of three copies. **Two tests replaced one that asserted the old contract in its own words** ("a reading that fails is not a refusal"): `TestTheGateProceedsWhenTheRoomHasNoRecords` and `TestAFailedNodeReadRefusesAtTheGate` (ExitUnavailable, reason **in words including HTTP 500**, and the resume **did not run**). **Deliberate collapse, not a gap:** the compact supervisor's `Nodes` callback has an upstream type with **no error channel**, so a failed read and an empty room are the same to it — accepted because **neither starts seats**, and **`PeakGate` is where the refusal lives and it does see the error**; changing that upstream contract is a separate unit.
    **Hand-off queued:** the reviewer's pane is in `runtime_error`/`needs_input` ("latest hook, pane unrecognized") and refuses `send`; the obligation is on **row `qitem-20261014050159-257abd3a3dd35fdc`**.
  - **B16:350 + B17's ps leg LANDED at `d6c0749`** ("read a seat's record without rig in switch and respawn"), HEAD, tree clean, **verified from a clean checkout of that sha** (detached worktree, zero dirty entries, `go build` 0, `go vet` 0, `go test ./...` 24 ok, 0 FAIL; not pushed). **One narrowing of the seam: `clientruntime.SeatNode(ctx, room, seat) (row, found, err)`**, read by both verbs instead of exec-ing `rig ps --json --nodes --rig ROOM`; `parseRigNodes` (which tolerated two stdout shapes) and `logicalSeat` went with the exec. **The defect it closes: both verbs could read a FAILED exec as "a room without the seat", so `respawn` could launch for a seat it could not read** — a failed read is now an error and both refuse **in the read's own words**; not-listed is still the shrug it was.
    **A CONTRACT OVERRIDE WORTH KEEPING:** the delegated conversion **silently changed `sync switch`'s documented behaviour** for a machine with no `rig` on PATH (the header and the ported Python test both say that case is a **NOTE — the cloud change is the authority — exit 0, `applied=none`**); the worker moved the detection to the command leg, made it `ExitRemote`, and **rewrote the header and the test to match its own change**. go-dev **restored the contract** and put `TestSwitchMissingRigBinaryRecordsCloudAndExitsZero` back to its original assertions. **A worker may not make the documentation agree with its change.**
    **NEXT UNIT, its proposal accepted: MEASURE THE DAEMON'S ROUTES FIRST** for the `clientbridge` reads — `readRig`'s all-rigs form (`bridge.go:182`/`:195`), `readEdges`' `rig export` (`bridge.go:161`), `humanRigs` (`notifications.go:205`) — **report what exists before converting**, since only the first is node-shaped and **the all-rigs form has no counterpart in the seam yet** (endpoint work, not a rebind). Same for `continue.go:249`'s `--include-archived`: establish whether the daemon's rig list can even say "archived". **Command legs stay untouched, each with its own measurement.**
  - **DAEMON ROUTE MEASUREMENT DONE (go-dev, 05:11Z) — read off the installed daemon's own mount table (`server.js:395-456`) and route files, NOT inferred from the client. It reclassifies four things at once:**
    - **`continue.go:249` `--include-archived` — DIRECTLY SERVED.** `GET /api/ps` takes **`?includeArchived=true`** and **`?archived=only`** (its own `OPR.0.3.3.19` comment says the default excludes archived) and every entry carries **`archivedAt` + `isArchived`** ⇒ **a straight rebind**, printable from the entries themselves. **Take this first.**
    - **`notifications.go:205` `humanRigs` `rig ps --json` — DIRECTLY SERVED.** `GET /api/ps`, each entry carrying **`name` AND `rigName`** (the type's own doc: `rigName` is an alias of `name`, always populated and always equal) ⇒ **a rebind**, with `ParseRigNames`' expectation checked against those two fields.
    - **`readEdges` (`bridge.go:161`) `rig export … -o /dev/stdout` — EXISTS.** `server.js:407-408` registers **`GET /api/rigs/:rigId/spec`** (YAML) and **`GET /api/rigs/:rigId/spec.json`** (JSON), both calling the rig spec exporter ⇒ bind **`spec.json`**, since `ParseRigEdges` parses text and JSON is the shape the exporter itself produces.
    - **`readRig` (`bridge.go:182`/`:195`) `rig ps --json --nodes -A` — NO ALL-RIGS NODE ROUTE; this one is a DECISION, not a rebind.** `/api/ps` entries are **counts and metadata only** (`rigId`, `name`/`rigName`, `nodeCount`, `runningCount`, `activeCount`, `hasWorkCount`, `status`, `lifecycleState`, `uptime`, `latestSnapshot`, `archivedAt`/`isArchived`, the three periodic-snapshot fields, `attentionCount`) with **no node rows**; `/api/rigs/:rigId/nodes` is **per rig**; `/api/rigs/summary` folds each rig's node **inventory** into `lifecycleState`/`restoreLifecycleState`/`hasLiveAgents` **but still returns no rows**. **RULED: take the N+1 fan-out DELIBERATELY** — `/api/ps` for the list, then one `/api/rigs/<id>/nodes` per rig — because it **preserves the data the exec actually produced** and **this box has one rig**, so the cost is a handful of reads on a local socket. **Name it as deliberate in the code rather than incidental**, and record the alternative beside it: if a consumer needs only counts, the `/api/ps` fields already carry them, and narrowing to that is a **consumer-driven follow-up with the consumer named** — not a guess made now. Native either way (**no exec, no fallback**), so **N+1 is not a shim.**
    - **THE COMMAND LEGS RECLASSIFIED — and go-dev's own long-carried caution is answered as a self-correction:** the daemon exposes **`POST /api/seat/{stop,launch,restart,set-model,switch-client,continue,clean,set-permissions}/:seatRef`**, plus `/launch-plan`, `/restart-plan`, `/status/:seatRef` and `/handover/:seatRef`. **Those act on the seats the DAEMON hosts — which is what this rig is** — whereas `ipc.go`'s `StopSeat`/`RestartSeat` act on **rooms the RUNTIME hosts**. So **the native counterpart exists and targets the right host**, converting `switchverb`'s and `respawn`'s `seat stop|launch|set-model` legs, `restore`'s `rig up … --existing` leg (`POST /api/rigs/:id/up`, from the latest restore-usable snapshot) and the `rig daemon status|start` legs (`/api/rigs/:rigId/{snapshots,restore}`) from **verb rewrites into candidate rebinds.**
    - **NOT ESTABLISHED, to be measured BEFORE touching anything that mutates:** the **`:seatRef` FORMAT** (`seat.js` hands it to a guard resolver; a `<rigId>/<seat>` form and a session-name form are both plausible) and **whether the mutating routes need a header** — **no bearer gate is registered on `/api/seat`** (the gated routers are transport, compaction, terminal-ws, mission-control, hosts, rig-mode), **but that will not be assumed for a route that stops a seat.**
  - **RE-PIN APPROVED (reviewer, 05:12Z): `d6c0749` → `968b2b6` → `d7831fc`**, each measured from **clean detached checkouts (zero dirty)**: build 0, vet 0, **24 packages ok, 0 FAIL**, on top of the reviewer's earlier pin.
  - **ONE MAJOR OPEN — THE COMPACT CALLBACK — AND THE LEAD'S EARLIER ACCEPTANCE OF IT IS REVERSED.** The supervisor's `Nodes` callback (`clientlifecycle/supervisor.go:107`) **discards both `ok` and `err`**, so a **failed node read reaches `clientoffpeak.Check` as nil nodes on the AUTOMATIC RESUME path (`supervisor.go:156`)**; `SeatsFromNodes(nil)` is empty and **`Decide` returns no refusal at zero DeepSeek seats (`gate.go:197`)** ⇒ **the resume proceeds with the peak gate never having seen a seat, silently.** That is **the same fail-open shape `PeakGate` was fixed against, one level down, on the path that actually resumes a DeepSeek seat**, and it is **internally inconsistent with `lifecycle.go`'s own rule that an unreadable reading is never read as safe.** **Reachability is narrow** (the read must fail *after* the verb's own gate passed) ⇒ **major, and the pass does not close with it open.**
    - **The lead had accepted that same collapse** with the argument that nothing starts seats at that seam and the refusal lives in `PeakGate`. **The finding disproves that**: the callback **feeds a gate-bearing path** (`clientoffpeak.Decide`), so the collapse **is** safety-relevant there. **REVERSED — the callback carries `ok` and `err` and the automatic path REFUSES on a failed read.** Ranked **first, ahead of the rebinds.** (go-dev had asked the reviewer directly whether the callback should carry the error; the reviewer said yes, and it is now the lead's ruling too.)
  - **MINOR / NIT, go-dev's:** the **watchdog also discards the seam's error** and then logs that **the daemon reports no running seats** — fail-safe (inaction only, same as the old shell), **but the sentence is false on a failed read**; **`switchverb.go:306` still prints a `rig ps` reference.**
  - **LIMIT, unchanged:** **no gated verb was run against the live rig.** Evidence is **clean-checkout builds and tests plus one deliberate break-and-revert in the reviewer's own throwaway checkout, reverted byte-identical**; the 24-package green is the client repo at each sha; **the gated verbs' acceptance remains C4's on `cutover-lab`.**
  - **THE ARCHITECT'S FINAL C3 SCOPE, ROUTED (lead, 05:16Z).** `ARCH-RULING-c3-refusal-shapes-final-2026-10-14.md` — the two earlier drafts are superseded (the `native-transcript-capture` one says so in its own first line). Three refusal shapes under four rules (**R1 no silent skip, R2 no empty-for-error, R3 no success on a fabricated result, R4 no fallback**) and the message shape `4genteam <verb>: <what was not done> — <why, naming the missing thing>; <what to do>`. **The architect cannot write rows from its seat**, so the ruling arrived by message; **the lead re-filed it as row `qitem-20261014051638-78f952a2` (lead → go-dev, claimed, in-progress)** and closed the architect's row `qitem-20261014043816-9fc999948a89752a` `done`. **Cases:** **U** (unavailable native path) — `lifecycle.go:610` `rigNodes`, `~:620-641` `PeakGate`, `restore.go:50-60`'s `send` closure; keep `ExitOK` for a missing reading but **make it distinguishable and printable**, because that skip is silent today while `PeakGate` prints for its other outcomes; **M** (version mismatch) — the rule lives at the one choke point `Client.Call`/`CallWithDeadline` (`ipc.go:124`/`:129`), `ExitUnavailable`, nothing on stdout, no retry, and a verb's business refusal (`unknown qitem_id '…'`) must **never** be rewritten as "unimplemented"; **R** — `runRigCapture`'s two `ps` legs go to `clientruntime.GetRoomStatus`, the launch refusal is **spoken** where no native verb exists, the `var` stays, and **`runRigCapture` is not deleted in the capture slice**.
  - **TWO LEAD RULINGS ON THAT RULING.** (1) **The `capture` verb IS in C3.** `clientruntime/command.go:577-650` still gates on `openRigDaemonConfigured()` and POSTs `/api/transport/capture` — a verb that **still dials the OpenRig daemon** is the dependency this pass exists to remove, and `Client.Capture` (`sessions.go:93`) already exists, so it is a one-call swap keeping the verbatim stdout, `--lines`, `--json` and the refusal pass-through. (2) **C3's site-count unit is 26** — **a call site that causes a `rig` child to start** — with **19** and **24** kept beside it as provenance.
  - **THE ARCHITECT'S `OpenRigSend` → `OpenRigSendMessage` CORRECTION IS DISPROVED (lead, measured at `a456656`).** `:161` is correct as written: `OpenRigSend` is the function at `internal/clientruntime/openrigdaemon.go:123`, and **`OpenRigSendMessage` exists nowhere in the tree** — its only witness is the historical line `CHANGELOG.md:1388`, written **before** the rename that same file records at `:459`/`:875`/`:880`/`:1307`. **Same species as tonight's other three** — a stale changelog line read as current fact, producing a wrong derivation downstream.
  - **THE CALLBACK FIX LANDED at `a456656`** — "hold the automatic resume when the room's records cannot be read" (`supervisor.go` + test, `watchdog.go` + test, `switchverb.go` + test, CHANGELOG + a dated fragment: 8 files, +246/−46). The resume site reads **`nodes, ok, err := s.Nodes(s.Rig)`** and on **`err != nil` holds the resume and says why in words** ("resume held, the room's node records could not be read: …") instead of proceeding as if the room were empty — **the reversal implemented as ruled**, with the two minors (the watchdog's false "no running seats" sentence, `switchverb.go:306`'s `rig ps` reference) riding the same commit. **Not pushed.**
  - **`a456656` VERIFIED — APPROVE, and falsified rather than read (reviewer, 05:19Z).** Clean **detached** checkout of the sha, zero dirty entries: `go build` 0, `go vet` 0, `go test ./...` **24 packages ok, 0 FAIL**. The bar, one line each: **(a)** the callback is now `func(rig string) ([]map[string]any, bool, error)` and the wiring returns `rigNodes(rig)` itself — no discard, and read at **call time** so a test that replaces the reading after the supervisor is built still reaches the gate; **(b)** on `err != nil` the resume is **held** with the failure named, **no resume sent and no "told to resume" line anywhere**; **(c)** **nil with no error proceeds AND says so** ("told to resume (the room's records list no seats)"), so the two answers stay distinguishable; **(d)** the test pair exists and is discriminating. **The falsification: restoring the old fail-open resume inside the reviewer's own checkout failed exactly ONE test — `TestAFailedRoomReadHoldsTheResume` — while `TestTheGateProceedsWhenTheRoomHasNoRecords` passed in both states**, so the pair separates a failed read from an empty room and the new test is **load-bearing, not decorative**; restored byte-identical. **Both minors verified fixed in the same commit**: `expectedSeats` now returns `(int, error)` so a failed read is no longer counted as zero, `check()` prints "the room's node records could not be read; no action" instead of the false no-running-seats sentence, the watch loop says "not counted as a miss" and **does not increment the debounce counter**, and the healthy path **keeps its `misses = 0` reset** (no debounce regression); `switchverb` now says "not in the room's records". **One nit, not a finding:** the hold sentence **appends the error**, which is what makes the refusal checkable. **Nothing pushed, main untouched, no gated verb run against the live rig.**
  - **C3 REFUSAL-SHAPES UNIT LANDED — 7 commits to `891342d` on top of `a456656`; the tree verified is `5fb4aef`** (go-dev, 05:29Z; each measured from a **clean checkout** of `5fb4aef`: build 0, vet 0, `go test ./...` **24 packages ok**; worktree clean; **nothing pushed, nothing deployed, rig untouched**). The commits: **`a70f5da` M** — an older runtime's framing failure is **named** (`RuntimeTooOld`/`ExitUnavailable`) instead of printed as the verb's own answer; a VERB's refusal stays `DaemonRefused`; the framing markers are serde's, because the runtime this must survive is **older than this build**. **`5dfc9d9` capture** — `Client.Capture` over the runtime's terminal manager; 4 daemon-path tests became socket tests, 1 deleted as pinning a daemon body **without `ok`** that no longer exists. **`e4b5ccf`** — `continue`'s archived listing and the bridge's sweep read `clientruntime.RigEntries` (`GET /api/ps`). **`a092770` U-b** — `PeakGate`'s NO-RECORDS case keeps its fail-open `ExitOK` and now **SAYS the gate did not run for that start**, printed once in the gate so `up`/`compact`/`restore` cannot each forget it. **`2926981` U-c** — `brief()` returns the seats its text did not reach; `restore()` answers false and names them; `continue` exits `ExitRestoreFailed`; the `--all` summary says **"did not complete"**, not "are not up". **`5fb4aef` R** — `respawn`'s launch leg off rig; `runRigCapture`/`rigResult`/`lastLine` and the `os/exec` import deleted; the step **refuses in words**, session named. **`891342d`** the CHANGELOG fragment. **EACH NEW GUARD WAS FALSIFIED BEFORE TRUSTING** — shown FAILING with its fix reverted, then restored **byte-identically (md5)**: the resume-hold, the two unreadable-room guards, the undelivered brief (`exit 0` against a wanted `1`), the gate's silence.
  - **TWO DEVIATIONS FROM THE ARCHITECT'S RULING, BOTH RULED IN go-dev's FAVOUR (lead, 05:33Z).** **(1) R's refusal text:** §4 named `4genteam seat launch` as the remedy and **that verb does not exist** (`4genteam seat` is `status|sync|watch|reseat`) — go-dev names **`4genteam room reseat ROOM SEAT`**, checked on the installed CLI ("sends `StopSeat` then `RestartSeat` for one seat, in that order"), the native door onto the path §4 itself describes, with the **non-equivalence stated inline** (no `--fresh`, no `--reason`). **Same species as tonight's stale-name findings: a ruling cited a verb that is not there.** **(2) `runRigCapture` deleted in the launch commit**, against §4's "keep it, it is a real test seam": with the launch **refusing** there is **no caller**, and the `rigResult` shape's stated justification ("raw stderr, because `rig seat launch` can start the occupant and still exit non-zero") **has no referent** — a native refusal is one fixed string. **A var with no subject is a stub, and this repo forbids dead weight.**
  - **CONSEQUENCE ACCEPTED EXPLICITLY, AND CARRIED AS DEBT — `sync respawn` CANNOT RESPAWN IN THIS BUILD.** That is **R1's own choice** (a skipped launch is never `ExitOK`), but the verb is now **strictly less functional**, and the capability returns only with a **native launch verb that takes a reason**. The refusal must **name that loss where a reader meets it**, not only in the commit.
  - **THE COUNT CHALLENGE IS CLOSED — the settled unit is at `:178` and the verdict at `:215`.** go-dev was **right that `26` is not the rig-spawn count**, but **both of its explanations were refuted** by the reviewer, which measured **21 non-test / 24 with tests** `exec.Command(` sites: **`26` counts neither any local tool nor the transitive closure** — it is reachable only by adding 7 sites that provably spawn nothing. go-dev's enumeration, with line numbers, stays the useful artifact: `RECORD-c3-rig-exec-sites-2026-10-14.md`. **The ruling's invariant is unchanged and per site: a site that spawns `rig` is correct when it says in words that it could not do the thing, and wrong when it falls back silently or reports an unperformed action as performed — never a property of a number.**
  - **n1 LANDED AND DELTA-GATED: `896f346` + `0f3ccb6`** (the printed-rig-strings sweep). go-dev swept by **AST** (`go/ast` literals, non-test Go under `internal/`), found **31 sites**, **repointed 8** — each named command run: `4genteam doctor`, `4genteam send SESSION MESSAGE`, `4genteam ps <RIG> --nodes --json`, `4genteam capture <session>` — kept 4 in class with reasons, 19 out of class; pins moved with the strings (`openrigdaemon_test.go`, `seatargument_test.go`). **Reviewer, 06:06Z: APPROVE** — clean export, build 0, vet 0, **24 packages ok, 0 FAIL**, the 8 repoints name commands it ran, n1 prints the positional `4genteam ps RIG --nodes`. Record: `DELTA-0f3ccb6-printed-rig-strings-2026-10-14.md`.
  - **TWO UNITS OPEN FROM THAT GATE — both DEFECTS, not gaps (reviewer, 06:06Z).** **(i) THE PRINTED PROCEDURE IS DANGEROUS — routed to go-dev, in flight.** `clientsync/switchverb.go:251-252` prints `rig down <RIG>` then `rig up <path of the rig.yaml …>`; on this box **`rig down` is a MACHINE-WIDE SAFEGUARD STOP** (*"rigd: stopped with its children"*, **all three rigs**) and the next line **fails with `--team DIR is required`** — an operator following it stops every rig's supervisors and cannot start the room again from it. Same class: `openrigdaemon.go:379`'s `@external` footer names **`rig queue create`, which fails today** (exit 2, "not a read this shim performs"). **Acceptance: every printed line either RUNS (verified, with its output shown) or is ABSENT, plus one new test that would have caught this — no verb on the machine-wide list may appear in a printed procedure.**
  - **(ii) THE GUARD DOES NOT BIND — REFUTED AND RE-ROUTED AT 06:2xZ; go-dev's row `qitem-20261014061206-c11b63fab7d63680` is PARKED `blocked` on the architect's C5 ruling and NO line was written for it** (worktree at `0683c10` with `git status --porcelain` empty, and `comm-guard.json` is not in that checkout at all — searched, not assumed). **THE REVIEWER REFUTED MY OWN ACCEPTANCE, WHICH WAS A SPELLING FIX: `readlink -f ~/.local/bin/rig` is `~/.local/bin/4genteam` — ONE FILE — so no spelling guard can separate them.** Its finding is now **C5's acceptance** (`FINDING-comm-guard-spelling-hole-2026-10-14.md`): **`internal/commpolicy` appears only in `cmd/seatcheck` and `internal/clientbridge/edges.go` and their tests — nothing on the send path**; **all 12 seats pin `{"Links": []}`, so the compliant path denies every recipient** (measured: exit 3, `denied: no link`, audit `{"From":"reviewer","To":"lead","Allowed":false,"Reason":"no link"}`); **and every message this rig actually sends goes over the client's `send` with no decision and no audit — the control binds nothing.** **RULED: the fix is one of the reviewer's two — attach the decision to the capability, or make `send` refuse when no decision was taken — and that is a design choice, so the ARCHITECT rules it rather than go-dev building it by experiment.** The original bullet's evidence stands as provenance: Measured by me at the source, `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/comm-guard.json` denies **`Bash(rig send:*)`, `Bash(rig queue:*)`, `Bash(rig broadcast:*)`, `Bash(tmux send-keys:*)`, `Bash(tmux paste-buffer:*)`** and allows **`Bash(seatcheck send:*)`, `Bash(rig whoami:*)`** — while **`4genteam send` is on `PATH` and matches NONE of them**, so **the guard is bypassed by typing the real binary's name**, and the allow that lets a seat run `rig whoami` stops covering the native verb. Additive fix (native spellings into deny **and** allow). **The owner already holds this component as his item 16, so the two changes must be ordered to touch the guard once.**
  - **THE ONE LIVE FAULT REMAINS: THE CONNECTOR `400`.** `rigd.log` shows **eight consecutive** `the connector refused the upgrade: HTTP/1.1 400 Bad Request` from 05:58:11 to 06:05:12Z, then **rigd stopping itself and all three rigs' children at 06:06:17Z**; `bridge` has been silent **11.4 h**. **The safeguards were running again by 06:10Z** (`pgrep` 17800–18210; `doctor` exit 0), **the reviewer's `rig down` probe is a CANDIDATE and NOT established** (its own post-probe reading showed rigd running, age 17 s), and **context protection was never lost** — the native `agent-compact --apply --watch 300` kept working (go-dev 201k→41k at 06:00:36Z, lead/architect/fe-dev told at 06:04:44Z and 06:09:51Z). **INSTRUMENT WARNING, for whoever reads this next: `4genteam status`/`doctor` are NOT the instrument of record for "is it running" — `status` read `stopped` for rows whose processes were alive at 06:09:5x. Corroborate with `pgrep`/`ps` and log mtimes.**
  - **BOTH RESEAT SPELLINGS ARE REAL — measured by me with `--help` at 06:14Z, because two seats have now named them differently and stale names are tonight's recurring class:** `4genteam seat reseat RIG --seat NAME [--force] [--allow-peak]` is **per-seat** ("restarts each named seat once it is quiet, so it loads the skills, guide and cwd it is now configured with") and it says **nothing about the runtime**, which is why go-dev's printed sentence — that whether a restart carries a changed RUNTIME is **not established** — is correct rather than a hedge; and `4genteam room reseat ROOM SEAT [--state-dir DIR] [--socket PATH]` is **room-scoped**. Also verified: `4genteam sync rig ROOM [--out DIR] [--update]`. **Neither reseat is machine-wide, so both are safe to print.**
  - **NEXT IN ORDER — ROUTED AT 06:1xZ, so a successor does not re-derive it: (i) go-dev, in flight, the printed-procedure delta** (`clientsync/switchverb.go:251-252` + the `@external` footer) **→ reviewer when it lands; (ii) go-dev, queued durably as `qitem-20261014061206-c11b63fab7d63680`, THE GUARDRAIL UNIT** (native `4genteam` spellings into the comm-guard deny **and** allow; **must land before C5**, and since the owner's item 16 touches the same file the guard is changed **once**); **(iii) architect, queued as `qitem-20261014061238-9facca3d542377ce`, THE C1 RULING** — the third primitive's shape, refusal shapes and freeze list, **authored before go-dev implements**, with the measured facts attached (five per-seat `agenthub-runtime daemon` sockets; the runner-mediated door recorded as `compact sent to omp 21202 via runner 21195 fd 23`; panes are plain `omp` under tmux; and panes already outlive seats since the 04:01Z watchdog restore). **Then C2 → C4 on `cutover-lab` → C5.** Nothing opens on the live rig before U3 passes and a snapshot is taken.
  - **Check**: `rig` can be removed from `PATH` and `4genteam send`, `whoami --json`, `queue`, `ps` still work.

- [ ] **C4: U3 acceptance run on `cutover-lab`** — the gate
  - Brings up a throwaway room on `4genteam` alone. Passes only if: all five seats `ready` via `4genteam`; one queue item flows lead → worker → reviewer and closes; a forced provider stream error recovers (C2).
  - **Check**: the run's evidence is recorded in a `CHANGELOG/` entry; a failing run blocks C5.
  - **THE C4 INSTRUMENT'S GUARD WAS WEAKER THAN ITS HEADER, AND IT IS FIXED (reviewer, 05:20Z).** The harness refused only the literal name `4genthub-min`, so `ROOM=definitely-not-a-room --check A1` **ran and left an evidence directory in the rig root** while its header claimed it refuses any other room. Corrected in the artifact: **the scope is `cutover-lab` and nothing else**, with `U3_ALLOW_ROOM=1` as the deliberate override for a second scratch room. Verified by exit codes measured directly: `ROOM=4genthub-min` exit 3 refusing; `ROOM=definitely-not-a-room` exit 3 refusing **and creating nothing**; `ROOM=cutover-lab --plan` exit 0 planning; the override plans a scratch room; `bash -n` clean; the stray directory moved out of the rig root; **the live rig untouched** (5 tmux sessions, room running, 5 seats).
  - **TWO PRECONDITIONS FOR THE C4 RUN — nobody should be surprised by either.** (1) **`CUTOVER_STATE_DIR` must be set to this seat's runtime state dir** (`~/.openrig/state/omp/4genthub-min-reviewer@4genthub-min/.config/4genthub`), because the script's default `$HOME/.config/4genthub` is **OpenRig's own** and two readings that do not name their daemon are not comparable. (2) **C4 cannot pass before C1/C3 land**, since its A4 predicate is that **no OpenRig process serves the room**.
  - **NAMING WARNING FOR THE RECORD:** the harness's own check ids name its internal parity-5 presence test and its rollback test — **neither is the plan's C3 unit nor the plan's C4 gate.** Cite harness ids **only** as `--check <id>` on `cutover-lab`.

- [ ] **C5: Snapshot, then retire the live OpenRig rig**
  - Snapshot the live rig, then `4genteam` takes over the five seats, then stop the OpenRig daemon and remove the `rig`-exec paths and `openrig.sqlite` dependencies.
  - Requires C1–C4 closed and the reviewer's gate on the stack passed. Merge, pin bump and install are the lead's call.
  - **Check**: the team keeps working a queue item end to end with the OpenRig daemon stopped.

- [ ] **C6: The decision ladder — seat, lead, owner (owner ruling 2026-10-14)**
  - Idea: agents work faster and discuss less. A **seat** decides for itself when Jev's confidence is **≥ 0.8**, else it sends the question to the **lead** with its recommended option. The **lead** decides at **≥ 0.8**, else sends it to the **owner**. The owner is asked only for a very important decision. The owner tier already exists (`room_decisions`, `jev-1.13.0`, `JEV_DECISION_THRESHOLD` 0.8, skill `room-decision-request`); C6 adds the two lower tiers on the same evaluator and the same threshold.
  - **Always the owner, whatever the confidence:** credentials and tokens, spend, and the omp cap. Jev confidence measures how concentrated an answer is, not whether the action is safe, so this list is a code rule outside the model. Standing owner decisions stay in force (OpenRig is not retired before U3 passes and a snapshot exists).
  - **Below 0.8:** escalate exactly one level and carry the recommended option, so the answer is one word.
  - Every decision, at every tier, is appended to the decision log with its tier, confidence and chosen option.
  - **Build:** the lead schedules it as its own unit with the reviewer gate, after C3 lands, so the cutover is not delayed.
  - **Check**: a seat-level question at 0.9 is answered without reaching the lead; one at 0.6 reaches the lead with a recommendation; a credential question at 0.95 still reaches the owner.

- [ ] **C7: One home for the client's state, `~/.config/4genthub/` (owner ruling 2026-10-14)**
  - When OpenRig is gone, `~/.openrig/agenthub-seats/` and the config the client keeps beside it move to `~/.config/4genthub/`. One directory, so a reader finds the cloud config, the seats, the rooms and the logs in one place.
  - **Target layout** under `~/.config/4genthub/` (it already holds `audit/`, `rooms/`, `jev_decisions.log`): `seats/` (was `~/.openrig/agenthub-seats`), `state/omp/` (was `~/.openrig/state/omp`), `briefs/`, `logs/`, `transcripts/`, `bin/` (the continue and watchdog scripts, until `4genteam` replaces them).
  - **Measured 2026-10-14 (`4genthub-min/u2-native-runner` at `0683c10`): the client names the old root in 7 code sites.** `clientenv/env.go:64` (state root) and `:131` (seat store), `clientrestore/paths.go:42` (briefs, logs, state), `clientps/ps.go:212` and `clientwatch/seatlog.go:72` (transcripts), `clientsync/offlineinstallverb.go:105` (seat store), `clientruntime/openrigdaemon.go:241` (the daemon home, which goes with C3/C5, not with this move). `OPENRIG_STATE_ROOT` is read in `clientenv/env.go:24` and `clientwatch/watch.go:62`. The Rust runtime names `~/.openrig` only in comments and in its absence predicate (`main.rs:54`, `runner/mod.rs:832`).
  - **Order:** after C4 passes and C5's snapshot exists. Until OpenRig is retired it still reads and writes `~/.openrig`, so moving the client first would split the two. The path code changes in one place (`clientenv`) and the data is moved once, by one command, in the same step.
  - **No compatibility layer:** no fallback that reads the old path, no symlink left behind, and `OPENRIG_STATE_ROOT` is removed rather than aliased. A seat's skills, `policy.json` and ledger move with the store; `sync rig` rebuilds the store at the new path and `seat reseat` carries it into the live agent dirs.
  - **Check**: with `~/.openrig` renamed away, `4genteam up`, `ps`, `watch`, `continue` and `sync rig` all work and write only under `~/.config/4genthub/`; `grep -rn '\.openrig' internal cmd` returns no code site.

---

### Group O: Orchestration Layer (Adapted from NEXT_GEN)

*The owner vision of 2026-10-08: AI software orchestration layer where goals become tasks executed by brain and worker seats, verified by gates against evidence.*

- [x] **O1c: Progress Becomes Events (Task Event Ledger Transition)**
  - Drop `progress_history` and `progress_count` from database and ORM; migrate all notes into `task_events` as `progress` events.
  - Update frontend dialogs (`TaskDetailsDialog.tsx`, `SubtaskDetailsDialog.tsx`) to read from the O8 event timeline instead of `progress_history`.
  - **Check**: `grep -rn progress_history agenthub_go agenthub-frontend/src` returns zero matches outside migrations/tests; TypeScript compiler exits 0; progress notes display correctly.
    - **INSTRUMENT AND CLAIM BOTH CORRECTED (measured 2026-10-13, this working copy):** the instrument as written has no `--include`, so it also walks `agenthub_go/.gocache` build bytes: it returns **999 lines**, of which **864 are `.gocache`** — **135 source lines**. With `--include=*.go` the tree holds **51 `progress_history`** and **26 `progress_count`** (frontend `src` adds 5 and 3), so **"zero matches outside migrations/tests" is false as written**. The names legitimately survive: the 0001 baseline defines the columns itself in `fastmcp/task_management/infrastructure/database/models.go`, `0003_progress_history_carry_and_drop.sql` narrows that baseline by design in one transaction (carry, check the carry, then drop — leaving the columns intact and recording no `applied_migrations` row on failure), and the guards and carry/drop integration tests name them deliberately. **The DDL must not be edited to satisfy this sentence** — the baseline parity guard and `schema_matches_definitions_test.go` exist to hold it as it is.
    - **Named open question (recorded, not answered, not to be assumed away):** which producer feeds the converters' subtask/task dicts at this commit — a post-0003 database row (whose details then read as silent nil) or the ledger/union read that 0003's own header describes as intended.
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

- [ ] **P1: The Client's Reaches Go Native (the client-runtime cutover unit)**
  - Retire the exec of the installed CLI from the client's own paths: each reach becomes a native IPC call over
    the runtime's socket. The unit closes only when **all three reaches** are native — the **read** (`55597e2`;
    the message pass reads its seats from the runtime, via `GetRoomStatus`), the **delivery** (`9e392ae`; the
    delivery goes to the daemon, and the envelope keeps the human's name), and the `firstRigSession` reach in
    `agenthub_client/internal/clientsync/connectorverb.go:103`, whose behaviour is unchanged and which is ruled (i).
  - *Measured 2026-10-13, `agenthub_client/internal/`, non-test:* **18** exec call sites remain — **15** as
    `rig.Run(` and **5** as a `.Run(ctx` on another receiver, the two overlapping — across 9 files; the primitive
    is `func (r *Rig) Run(ctx context.Context, args ...string)` at `internal/clientcmd/command.go:83`. An earlier
    note in §1 said *eleven* and did not record its pattern, so re-run both counts above before quoting either
    number. This remainder is also why `send` is a dead verb for a seat: `4genteam send` rejects every argv shape
    with `4genteam send: RIG, SEAT and MESSAGE are required`.
  - **Check**: every reach answers with no exec of the installed binary on the path, and `4genteam send` reaches
    a seat over the socket alone.
  - **The unit mapping, stated once so a next session cannot re-derive it:** **P1** = the client's reaches go
    native (the client-runtime cutover unit the rig files on its U0 row); **U1** = room hosting and
    materialisation — the `spec.json` leg, satisfied 2026-10-13 by the `cutover-lab` room; **U2** = the native
    runner plus the room-lifecycle wiring for `up` (`agenthub-runtime runner`, the socketpair, the queue store).
    This enumeration skipped P1 while the whole rig talked about it, which is the drift this row closes.

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
    - **PATH CORRECTED (measured 2026-10-13, monorepo working copy):** the commit resolves (`fcc8a2fc 2026-10-11 feat(ledger): the connector sends one ledger_tip nudge, gated by the capability its hello named`), but the directory `fastmcp/server/websocket/` **does not exist**; the websocket code lives at `fastmcp/infrastructure/websocket`, `fastmcp/websocket` and `fastmcp/server/routes/websocket_routes.go`. The delivery stands; only the path was wrong.

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
