## The committed API reference carries the ledger's two routes

The battery's `go test ./...` in the batch worktree returned rc=1: 140 packages ok and ONE FAIL,
`agenthub/internal/apiref`'s `TestTheCommittedArtefactMatchesTheProducer`, direction 1 — two routes
registered in the code and ABSENT from the committed artefact, so the page understated the API.
Both are the ledger's own: `GET /api/v2/ledger` and `POST /api/v2/ledger/intents`, landed by
`f285bdf6` (the cross-task cursor read and the intents route) without the artefact being regenerated
in the same commit. Every gate verdict and every seat report was green on this; it shows only when
the tree is run.

### Fixed

- `agenthub-frontend/src/docs/apiReference.ts` regenerated with the producer the test itself names:
  from `agenthub_go`, `go run ./cmd/apirefgen` — the only caller of `apiref.WriteModule`, which writes
  this file. The producer is deliberately NOT hidden behind `go:generate`; its own comment says a
  generator that writes into a different tree is a step a reader should see named, so it is named
  here rather than implied by a directive.
- The diff is 14 ADDED lines and nothing else: the two routes, written in the artefact's own route
  order (between `/api/v2/...` neighbours) with the `handler` and `description` the producer emits for
  a mounted route, and no path parameters. No route, path, handler or ordering was removed.

### Not changed, and deliberately

- The two other apiref tests, `docs_page_drift_test.go` and `reference_test.go`, were RUN and PASS
  (see below). Neither was adjusted, and no other generated artefact was regenerated.
- No ledger code, no route registration and no handler was touched: the ledger gate is mid-verdict on
  the range ending at `8e4786dd` and its subject did not move.

### Files

- `agenthub-frontend/src/docs/apiReference.ts` — the two ledger routes, +14 lines.

### Verified

- Producer run in this seat's worktree `wt/go-dev`, branch `4genthub-min/go-dev` at `8e4786dd`, with
  `GOCACHE` and `TMPDIR` inside `.gocache`/`.gotmp`: `go run ./cmd/apirefgen` printed
  `wrote ../agenthub-frontend/src/docs/apiReference.ts: 148 routes, 9 tools`, rc 0.
- It touched NOTHING else, and that was checked rather than assumed: `git status --porcelain` in the
  worktree listed this one file, so the commit carries no incidental regeneration.
- `go test ./internal/apiref/...` → `ok  agenthub/internal/apiref  0.092s`, 0 FAIL — this is the
  package whose `TestTheCommittedArtefactMatchesTheProducer` failed the battery, so the artefact and
  the code now agree in the direction that failed.
- `npx tsc --noEmit -p .` in `agenthub-frontend` → **0 errors, rc 0** (TypeScript 4.9.5), the check the
  lead named because the artefact is a TypeScript module the docs page imports. A fresh worktree carries
  no `node_modules`, so the run used the long-lived checkout's install, linked in as an untracked
  symlink; `git status --porcelain` confirms the link is not part of the commit.
- The route set regenerated here is the batch's route set: at batch tip `19b783c6` the Go tree differs
  from this branch's `8e4786dd` only in `agenthub_go/NEXT_GEN.md` (one line), and that file registers
  no route, so re-merging this commit cannot reintroduce the mismatch.
