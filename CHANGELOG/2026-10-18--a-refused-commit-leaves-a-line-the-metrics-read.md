## A refused commit leaves a line the metrics read

`4genteam room metrics` could not see a refused commit: a refusal never runs `git`, so there is no
`git log` entry and no run directory to extract from. The `commit_refused` extractor
(`agenthub_client/internal/clientroom/metrics.go`, client `fc006f0`) reads
`<git dir>/parked-diffs/refusals.jsonl` - a file until now **nobody wrote**.

### Added

- `scripts/git-hooks/git_commit_capture.py`: `record_refusal` appends one JSON line per refusal,
  before the refusal is printed, so a caller that reads the message can audit the refusal too. The
  line carries `id` (unique per refusal), `ts`, `seat`, `session`, `rule`, and the path **classes**
  (`docs`, `code`) - never the paths themselves (O9a): a review needs to tell a docs-only refusal
  from a code one, not which files a seat tried.

### Changed

- `scripts/tests/test_git_commit_capture.py`: a new case proves the line the extractor reads (classes
  `(2, 0)`, seat and session recorded, distinct ids, no path in the raw spool).
  `test_the_check_judges_the_commits_path_set_and_not_the_index` now expects `refusals.jsonl` to be
  the only entry in the parked directory: a refused commit parks no capture, only its line.

### Testing

- `python3 -m pytest scripts/tests/test_git_commit_capture.py -q` -> 15 passed.
- `git apply --check` of this change against the hub worktree at `main` -> rc 0.
