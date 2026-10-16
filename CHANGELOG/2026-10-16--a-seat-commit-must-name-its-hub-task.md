# A seat commit must name its hub task

### Added
- `scripts/git-hooks/task-trailer-guard` and its `task-trailer-guard` entry in `scripts/git-hooks/pre-commit-config.yaml` (stage `commit-msg`; install line now includes `--hook-type commit-msg`): when `AGENTHUB_SESSION_NAME` is set (a seat), a commit message without a `Task: <uuid>` trailer is refused (uuid shape check only). Owner commits and merge commits are exempt.
- Why: the task can only be closed from a commit that names it.

### Testing
- Script run directly with a seat env: no trailer rc=1; valid `Task:` uuid rc=0; malformed id rc=1; `Task:` in prose rc=1; Merge message rc=0; no seat env rc=0.
- `pre-commit run --hook-stage commit-msg task-trailer-guard --commit-msg-filename <file>` refused/passed accordingly. No test file exists for docs-only-guard either; none added.
