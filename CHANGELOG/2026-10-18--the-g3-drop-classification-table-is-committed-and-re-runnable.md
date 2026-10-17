## The G3 drop-classification table is committed and re-runnable

### Added

- `ai_docs/reports-status/G3-drop-classification.md` — the bulk table G3 needs: 96 candidates from a
  sweep of 760 tracked non-test `.go` files under `agenthub_go/`, 48 of them markers each carrying a
  one-word class (`logging` 16, `unused-arg` 10, `unreachable` 11, `ported-elsewhere` 11), and the
  48 that are not markers with their reason (`agrees` 20, `domain` 24, `named` 4).
- `scripts/G3-DROP-CLASSIFY.py` — the sweep and its check. It refuses to run outside the repository
  root and prints the root and the file count, because the same sweep inside `agenthub_go/` reports a
  false clean. It fails on an unclassed candidate and on a stale row, and `--self-test` proves both
  failures by perturbing a copy.

### Changed

- The gate no longer depends on a dead seat's session: `grep -rn 'unused-arg|ported-elsewhere'` now
  finds the table in the tree instead of only the plan's prose.

### Testing

`python3 scripts/G3-DROP-CLASSIFY.py` exits 0 with `candidates=96 markers=48 non-markers=48`;
`--self-test` names a deleted row and an invented one; a run from inside `agenthub_go/` exits 2 with
the root named. Every basis in the table was checked against the tree (call-site greps, the nil
repository at `unified_context_service.go:116`, the production wiring at `task_wiring.go:154`, the
Redis-free `agenthub_go/go.mod`, and the Python no-ops the comments themselves name).
