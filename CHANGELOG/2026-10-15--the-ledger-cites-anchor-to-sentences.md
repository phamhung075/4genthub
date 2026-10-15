# The ledger's cites name the architecture's sentences, not its line numbers

Four Go files cited `ai_docs/core-architecture/agenthub-system-architecture.md` by bare line number, and
the numbers had rotted: eight of them resolved to a different sentence than the one the comment named.
The doc's D9 region drifts a few lines per docs commit - Part 1's heading was `:576` at `4f753d2d`, `:614`
at `2c72a8fb~1` and `:616` at `04fcd5d7` - so a renumber is stale on the next docs commit. The lead's
ruling is the fix applied here: anchor each cite to the sentence it names, and drop the number.

## Changed

- **`agenthub_go/fastmcp/ledger/application/services/ledger_service.go`** - D9's part 1 is cited as the
  doc's "#### Part 1: the sync and event model" heading, and the rule sentence as the D9 decision's own
  "facts sync, decisions sequence" (was `:597-:617`, `:601`, `:608`).
- **`agenthub_go/fastmcp/ledger/domain/entities/intent.go`** - part 1 is the same heading (was
  `:597-:617`, and the `committed 4f753d2d` pin goes with it: at `4f753d2d` itself `:597-:617` was not
  part 1); the classification's rule is the Decisions bullet's "unless every event since then is a fact"
  (was `:599`, twice); `DecisionKinds` is the "*Decisions* are ..." bullet (was `:606`); `FactKinds` is the
  "*Facts* are ..." bullet (was `:604`).
- **`agenthub_go/fastmcp/server/httpapp/task_wiring.go`** - the shared transaction is the doc's "Status and
  event written separately would diverge" rule (was `:614`, which is the "Compaction stalls." bullet).
- **`agenthub_go/fastmcp/server/routes/ledger_routes.go`** - the cursor-across-all-tasks read is D9's
  option A, "a client reads "everything after N" across all its tasks" (was `:615`, the "Compaction
  belongs to the harness." bullet).

## Not in this change

- **`agenthub-frontend/src/lib/taskTimeline.ts:4` keeps its `:175` and `:393`.** Both land on a sentence
  that carries the claim, so they are the form that works; the frontend is untouched.
- **`intent.go:160` carries a bare `` `:677` `` and is left alone.** It names no file in its comment block,
  and the architecture doc's `:677` is the offline decision's "What is true today", which has nothing to
  do with "a client shows one to a seat". It is not one of the eight that were measured, and its target
  cannot be resolved from the comment, so it is reported rather than guessed at.
- **No code and no test changed:** four Go comment blocks, no statement.

## Verify

`grep -rn 'agenthub-system-architecture\.md' --include=*.go` over the four files shows no `:<number>` into
that file, and `gofmt -l` on all four is empty.
