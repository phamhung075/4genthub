# A commit tells every running seat

### Added
- `scripts/git-hooks/notify-seats` and a `post-commit` entry in `scripts/git-hooks/pre-commit-config.yaml`: after each commit, every seat whose room reports it `running` gets a notice (`4genteam send --from git-hook --intent notice`) naming the commit, its subject and up to 15 changed files, so a seat re-reads a file before editing it. Rooms named `*.obsolete*` are skipped. The script always exits 0: a down room or an unconfirmed send never fails a commit.
- Install on a clone: `pre-commit install -c scripts/git-hooks/pre-commit-config.yaml --hook-type post-commit` (the header comment of the config now lists it).

### Testing
- Run against a stub `4genteam` with one running and one stopped seat and an obsolete room: exactly one send, to the running seat. Not yet run against the live room (it is down).
- Not covered: the client repo has its own `.git` and no post-commit hook of its own.
