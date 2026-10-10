## The Python backend's removal has a decision note, and the note's gate is a gap list rather than the eight unticked boxes

### Added
- `ai_docs/architecture-design/decision-remove-python-backend.md` (owner decision 2026-10-08: no Python backend, no ORM, all code in Go). It reads each of the eight unchecked `agenthub_go/MIGRATION.md` boxes as PORTED, UNPORTED or NOT A GAP, and names six gate rows G1-G6. The deletion cannot be filed while any of them is open. Those rows are: Go still reads Python's init SQL at runtime (`db_initializer.go:239`); Go's root detection is keyed on the `agenthub_main` directory; behaviour-shaped "dropped" markers; `/ws/task-polling`, which Python mounts and Go does not; proof on the running Go server; and the open T/P/N deviations. It recommends versioned SQL migrations, held to the Go row definitions by a Go test against a scratch database, as the new source of truth. The stages are: the migrations, the script tests moved to `scripts/tests/`, then CI, docker, the pre-commit config and `CLAUDE.local.md`, and finally the tag `python-backend-final` with the deletion last and alone. The Python tooling scope stays an open owner question, with its own inventory.

### Fixed
- `ai_docs/architecture-design/decision-task-stats-endpoint.md`: the "failing first" line said both route assertions are red at HEAD. Only `GET /api/tasks/{task_id}` can be observed as 404. The stats path sits under the `GET /api/v2/tasks/` prefix route, which answers 403 before auth, so the note now says so and points that half's evidence at the grep and the build.

### Measured
- The script tests: `cd agenthub_main && python3 -m pytest --noconftest -p no:cacheprovider src/tests/scripts -q` → 315 passed. This is the baseline the move must reproduce.
- With pre-commit 4.4.0, a missing configured config makes `git commit` exit 1 with no commit, measured in a scratch repository. The installed hook points at `agenthub_main/.pre-commit-config.yaml`, so the config moves before the tree is deleted.
