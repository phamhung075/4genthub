## The G3 table moves to a live docs path and is regenerated against the merged tip

### Changed

- `ai_docs/core-architecture/G3-drop-classification.md` — the table now lives here, out of
  `ai_docs/reports-status/`. That directory is frozen for seats, so a generated check input kept
  there can only be re-greened by the owner, and it went red exactly that way: the table was derived
  at `404229f4`'s base, and after main `929b2a4d` deleted four Go files and moved eight candidate
  lines the default check exited 1 with 12 stale rows and 8 unclassed candidates.
- The regenerated table drops the four rows whose files main deleted (`database_source_manager.go`,
  `ensure_ai_columns.go`, `task_event_ensurer.go`, `ai_task_creation_use_case.go`) and renumbers the
  eight moved rows (`create_task.go` 154→155 and 180→181, `task.go` 715→722, 718→725 and 1155→1172,
  `task_repository.go` 818→833 and 2097→2212, `unified_logging.go` 161→163). Dispositions are
  unchanged and were re-read: `ORMTaskRepository.InvalidateCache` is still `unreachable` (the only
  `InvalidateCache(` call sites hit `CachedRepository.InvalidateCache`, a different method) and
  `WithGroup` is still `logging`.
- `scripts/G3-DROP-CLASSIFY.py` — `REPORT` and the docstring path line now name the new path; no
  other line changes.

### Testing

`python3 scripts/G3-DROP-CLASSIFY.py` on the tree before the move exits 1 with 12 stale rows and 8
unclassed candidates; from the repository root at the new path it exits 0 and prints `swept 744`
files, `candidates=92 markers=46 non-markers=46`, classes `logging=15, ported-elsewhere=10,
unreachable=11, unused-arg=10`, not markers `agrees=20, domain=22, named=4`. `--self-test` exits 0
and names both a dropped row and an invented one.

The counts in "The G3 drop-classification table is committed and re-runnable" (96/48/48) were
measured at that commit's own base and are superseded by these.
