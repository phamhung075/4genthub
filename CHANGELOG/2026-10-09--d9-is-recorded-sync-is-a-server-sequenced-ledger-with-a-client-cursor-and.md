## D9 is recorded: sync is a server-sequenced ledger with a client cursor and outbox, and the local runtime stays the Go client, not Rust

### Added
- `ai_docs/core-architecture/agenthub-system-architecture.md`, section 4: **D9**, accepted by the owner on 2026-10-08. Part 1, the sync and event model: a per-user gapless `user_seq` on `task_events`, `GET /api/v2/ledger?after=`, `POST /api/v2/ledger/intents` keyed by `client_event_id`, and a `ledger_tip` nudge frame on `/ws/connector`. The conflict rule is "facts sync, decisions sequence". Part 2: no Rust runtime; `agenthub-client` (Go) stays the one local runtime, on the measured split of turn time (model 33-75%, tools in their own subprocesses, a compaction stall is a model call). Part 3, surviving a 4genthub cloud outage through a local MCP endpoint, is **DEFERRED** by the owner: a design only, not built, not scheduled, and it implies no NEXT_GEN items.
- Section 6: rows **15** (does 4genthub own the agent loop: closed, no) and **16** (outage survival: closed, deferred). Section 1.4: a DEFERRED capability row for outage survival. Section 8: the history row.

### Changed
- Section 2.15: the "no Rust" reason is replaced with the D9 measurements and the two conditions that reopen it.

### Tested
- Committed through a temporary index built from HEAD, so `git diff HEAD~1 HEAD` shows only additions to `CHANGELOG.md` and only the D9 hunks in the architecture file. The paths staged in the shared index and the uncommitted lines of `CHANGELOG.md` in the worktree were not taken.
