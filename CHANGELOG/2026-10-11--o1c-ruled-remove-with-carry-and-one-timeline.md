## O1c ruled: progress_history is removed WITH CARRY, and the ledger timeline replaces the old one

### Added
- `ai_docs/core-architecture/agenthub-system-architecture.md`: D1 sub-decision 3a (architect; lead qitems `ffc3ea27` and `d47a217e`; board rows `f9bbdd0f` and `0cf37f6f`).
  - **The column is REMOVED WITH CARRY.** One T12 runner step, after `0001`, does all of the following in ONE transaction:
    1. Writes every `progress_history` entry of tasks and subtasks into `task_events` as a `progress` event, with the content verbatim and the entry's own timestamp.
    2. Asserts the event count and the content.
    3. Only then drops `progress_history` and `progress_count`.
    4. On any failure, rolls back: no drop and no `applied_migrations` row.
  - **Keeping the column is rejected:** two stores for one concept. `details` is rendered from the column (`task_response.go:103`), so it is not a second home.
  - **The O8 ledger timeline REPLACES `ProgressHistoryTimeline`** in one commit; the two never coexist. Until the subtask's own `details` are served, the subtask dialog shows no progress section. `06410692`, which serves them, is on no branch and is to be re-landed.

### Changed
- `agenthub_go/NEXT_GEN.md`: the O1c box records the ruling and its added Check. The ordering ledger row and the owner-gated list say the DROP runs only inside the carry step.

### Verified
- The architect measured:
  - `git branch -a --contains 06410692` prints nothing, and it is not an ancestor of HEAD.
  - Nothing in production code writes kind `progress`.
  - The runner is SQL files applied one per transaction, each with its ledger row (`migration_runner.go`, `migrations/README.md`).
- No code changed, so no tests apply. Board item `08739d36` was updated and read back.
