## The client depends on no other repository: its own `.env.sample`, its own README for an agent, tests that moved to where the data lives

### Changed
- `agenthub_client` (now the public `4genthub-client` submodule, commit `f60a188`): `paths.py` keeps only the client's own files (`.env` at its root, `logs/`, the Rust helper). `AGENTHUB_REPO_ROOT`, the repository's hooks, `scripts/team/4genthub`, the skill inventory and `agenthub_go` are no longer reached. The project a command works on is the current directory (`4genteam watch`, `team import-project`).
- `4genteam team apply` needs `--team`, `team publish-skills` needs `--inventory`, `sync install-checker` needs `--go-dir`; none has a default any more.
- `README.md` is rewritten for an agent installing the client in another project (prerequisites, install, the `https://api.4genthub.com/mcp` connection for any project, launch, configuration, failure map); `.env.sample` is the client's own.

### Added
- `scripts/tests/test_team_definition.py` (27 cases) and `scripts/tests/test_seatcheck_guard.py` (3 cases): the tests that checked THIS repository's team files, skill inventory and Go checker through the client now live here; the client's copy of the server's secret-scan corpus is `tests/fixtures/scan_cases.json`.

### Testing
- Client copied outside any repository: `PYTHONPATH=src python3 -m pytest tests -q` -> 292 passed. Here: `PYTHONPATH=agenthub_client/src python3 -m pytest scripts/tests/test_team_definition.py scripts/tests/test_seatcheck_guard.py -q` -> 32 passed, 3 passed.
- Still tied to the 4genthub team, not yet removed: the default room name `4genthub-min` and the `SEAT_ROLES` policy table in `seat_policy.py`.
