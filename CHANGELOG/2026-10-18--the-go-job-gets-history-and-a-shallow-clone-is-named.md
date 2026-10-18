# The go CI job gets history, and a shallow clone is named instead of accused

CI was red on `main` (run `39156598706`, hub `536df7d6`, job `go`) while the same suite was green locally
at `7345368b`. Cause, read at source: `TestAPrunedPathWasDeletedByACommit` asks
`git log --all --diff-filter=D` for every entry of `testdata/pruned_paths.txt`, and the workflow checked out
at the default depth 1, so the clone held no deletion commits. The guard then reported seven live entries as
"a typo or a path that was never tracked" — a false accusation of the data file, from a checkout that could
not answer the question.

## What changed

- **`.github/workflows/ci.yml`**: the `go` job's `actions/checkout@v4` takes `fetch-depth: 0`. The guard
  needs history; the job now provides it. The `frontend` job does not run this test and is untouched.
- **`agenthub_go/internal/repoguards/pruned_paths_test.go`**: before the listing is judged, the test asks
  `git rev-parse --is-shallow-repository` and, on a shallow clone, fails with the cause named — "this
  checkout is a SHALLOW clone, so `git log --all` cannot see the deletion commits … the entries below are
  not typos, the history is missing" — plus the one flag that fixes it. The teeth stay: a shallow clone
  still fails, and a genuine typo still fails with the typo sentence.

## Runs at this change

- Shallow clone, reproduced from scratch: `git clone --depth 1 --no-local file://<hub> /tmp/shallow-ci-…`,
  then `go test -count=1 ./internal/repoguards/ -run TestAPrunedPathWasDeletedByACommit` — before the fix,
  nine entries reported as typos; after it, the shallow sentence at `pruned_paths_test.go:53`, exit 1.
- The fixed checkout simulated: `git -C <clone> fetch --unshallow --tags`, then the whole
  `./internal/repoguards/` package = `ok`, exit 0 — so `fetch-depth: 0` is what the job needed.
- Teeth kept: appending `scripts/definitely-never-existed.py` to the full clone's
  `testdata/pruned_paths.txt` fails with `has no deletion commit in history: the entry is a typo or a path
  that was never tracked`, naming only that entry (file restored after the run).
- Local: `go -C agenthub_go test -count=1 ./internal/repoguards/` = ok, exit 0.
