## The D2 entry's test count was wrong, and the roster section claimed a fix that lands in the next commit

### Fixed
- `ai_docs/core-architecture/agenthub-system-architecture.md` (D2's SUPERSEDED paragraph, and the status line below it) and this file's `aac25c96` entry — **three homes, one wrong number: "seven" tests of the relocated scripts.** **The tree carries NINE `scripts/tests/test_openrig_*.py` files**, measured 2026-10-09: `git ls-tree -r --name-only HEAD scripts/tests/ | grep -c test_openrig` -> `9`, and all nine are staged for deletion (`git diff --cached --name-status | grep -c '^D.*scripts/tests/test_openrig_'` -> `9`), beside the eight `scripts/openrig_*.py` module deletions (`8`). The reviewer sent `aac25c96` back on exactly this number; it is corrected in all three homes.
- The `aac25c96` section "A second caller of the relocation" claimed the roster repoint as that commit's work. The repoint is the NEXT commit's (`ec220212`), and the section now says so — the reviewer's second finding, repaired without rewriting another seat's commit.

### Verified
- `cd scripts/tests && python3 -m pytest test_team_roster.py -q` -> `4 passed, 1 warning in 0.01s` (the entry's "after" number, re-run here); the reviewer's gate on `ec220212` measured the same `4 passed` and `14 passed` for the directory.
- `find scripts -maxdepth 1 -name 'openrig_*.py'` -> nothing; `ls scripts/tests/` -> `pytest.ini`, `test_prepare_commit_msg_seat.py`, `test_seat_policy_commit_form.py`, `test_team_roster.py`.
