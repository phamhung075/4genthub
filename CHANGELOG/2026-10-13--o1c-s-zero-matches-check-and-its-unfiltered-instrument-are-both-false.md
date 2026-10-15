## O1c's "zero matches" check and its unfiltered instrument were both false

### Fixed

- `NEXT-GEN2.md` O1c's **Check** line claimed `grep -rn progress_history agenthub_go agenthub-frontend/src`
  "returns zero matches outside migrations/tests". Two things were wrong and both are now recorded under the
  line:
  - **the instrument** — it carries no `--include`, so it also walks `agenthub_go/.gocache` build bytes: 999
    lines returned, **864 of them `.gocache`**, i.e. 135 source lines;
  - **the claim** — with `--include=*.go` the tree holds **51 `progress_history`** and **26 `progress_count`**
    (frontend `src` adds 5 and 3), so "zero matches outside migrations/tests" is false as written.
- The same line now names **the named open question** the measurement leaves behind, rather than a verdict:
  which producer feeds the converters' subtask/task dicts at this commit — a post-0003 database row (whose
  details then read as silent nil) or the ledger/union read that `0003_progress_history_carry_and_drop.sql`'s
  own header describes as intended.

### Notes

- **No code path changed**, and specifically `fastmcp/task_management/infrastructure/database/models.go` was
  **not** edited: its DDL is the `0001` baseline's own definition, which `0003` narrows by design in one
  transaction (carry, check the carry, then drop, leaving the columns intact and recording no
  `applied_migrations` row on failure). Editing it to satisfy the sentence would break the baseline parity
  guard — `schema_matches_definitions_test.go` holds the intent in words.
- Measured 2026-10-13 in this working copy; the counts are reproducible with
  `grep -rn progress_history agenthub_go --include=*.go | wc -l` and the same for `progress_count`.
