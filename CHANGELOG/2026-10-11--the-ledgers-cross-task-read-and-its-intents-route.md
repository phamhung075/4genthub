## The ledger's cross-task read and its intents route: P2 and P3

`NEXT_GEN.md:441` and `:442`, built as the two halves of D9's part 1 (the architecture doc's `:595-:615`,
committed 4f753d2d): a client that has been offline PULLS everything after a cursor across all of its tasks, and
PUSHES the work it recorded while it was away, one item at a time and with a per-item answer.

### The two routes

- `GET /api/v2/ledger?after=<user_seq>&limit=` — the user's entries strictly after a `user_seq`, oldest first,
  plus the user's CURRENT TIP. The tip is not the last entry of the page and is not derived from it: it is the
  highest `user_seq` the ledger holds, so a page read while the ledger is moving still says where the end is.
  It is read AFTER the page, which is the invariant that matters: read first, a tip could name a lower
  `user_seq` than an entry the page went on to carry and tell a client it was at the end when it was not.
- `POST /api/v2/ledger/intents` — a batch, answered PER ITEM IN THE ARRIVAL ORDER, each answer one of two
  disjoint shapes told apart by one discriminator: `{"accepted":true,"user_seq":…,"seq":…}` for the entry that
  was written, `{"rejected":true,"reason":"…","task_seq":…}` for one that was not, with the seq the client
  should re-read from. A second boolean meaning "not accepted" would be a second source for the same fact.

### The rule the route implements, and where it comes from

One sentence from the architecture (`:599`, `:606`): facts sync, decisions sequence. A FACT is append-only and
is never refused for being late; a DECISION carries the task seq the client had seen and is refused exactly when
something that is NOT a fact happened after it — the client's claim or verdict was formed against a history that
has since moved. The staleness question is asked of the COMPLEMENT of the fact list (`HasNonFactAfter` takes the
fact kinds as an argument, so the repository holds no opinion about which kinds are facts).

Three behaviours that are deliberate and easy to mistake for bugs:

- **A resend is answered from its row**: the same `client_event_id` returns the FIRST answer, looked up inside
  the transaction under the per-user lock, so a second request carrying the key sees the committed row rather
  than racing it into `uq_task_event_client_event`.
- **A refusal is NOT remembered**: a refused item wrote nothing, and re-staging a decision on a fresh base is the
  client's whole remedy — memoising the refusal would make that remedy impossible.
- **The per-user lock is taken BEFORE the read** (`pg_advisory_xact_lock(hashtext(userID))`): without it two
  intents for one user could both read "the base is fresh" and both append, which is the double claim `base_seq`
  exists to prevent.

### User isolation, which is the security property here

Every query the ledger adds filters `user_id`, and the repository is scoped to one user by construction:
`ListUserAfter`, `UserTip`, `FindByClientEventID`, `CurrentTaskSeq`, `HasNonFactAfter` and `TaskVisible` each
carry `"user_id" = $1` in the statement itself, and `TaskVisible` checks the task belongs to that user before an
intent may name it. A credential whose subject is not a UUID resolves to an id no row was written under, so it
answers an empty ledger rather than another user's rows — silently, which is exactly the failure this ledger
exists to make visible, and there is a case for it.

### Files

- `fastmcp/ledger/domain/entities/intent.go` — the ledger's own vocabulary: which kinds a client may push, which
  of those are facts and which are decisions, the two answer shapes, and the refusal reasons as stable tokens a
  client branches on rather than prose. A test beside it pins every intent kind against the table's CHECK
  vocabulary so the two cannot drift.
- `fastmcp/ledger/application/services/ledger_service.go` — the decision and the read, over a `Ledger` port so the
  application layer depends on a shape rather than on the infrastructure that implements it.
- `fastmcp/server/routes/ledger_routes.go` + `fastmcp/server/httpapp/ledger_mount.go` — the two handlers and
  their adapters, in the shape `task_event_routes.go` and `task_evidence_routes.go` already use, so the ledger
  adds no third idiom. A bad integer query parameter is a 422 rather than a silently reinterpreted cursor.
- `fastmcp/task_management/infrastructure/repositories/task_event_repository.go` — the reads and the append
  primitive, plus `Transaction` and `LockUser`.
- `fastmcp/server/httpapp/app.go` — one line: `mountLedgerRoutes(mux, a.Sessions)`.

### Verified

Run in this seat's worktree (`wt/go-dev`), with
`AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres` — this seat's own test cluster,
identified by the port in its `postmaster.pid` rather than by a connect probe (a connect probe proved nothing
either way here: it reported the port closed while `ss -ltn` showed it listening).

- `gofmt -l` on every touched file prints nothing.
- `go build ./...` rc 0; `go vet` rc 0 on `./fastmcp/ledger/...`, `./fastmcp/server/routes/`,
  `./fastmcp/server/httpapp/`, `./fastmcp/task_management/infrastructure/repositories/`. Likewise clean on
  `domain/entities`, `application/services` and `application/dtos/...`, which are the reader's callers.
- `go test -count=1 -v` over the ledger packages, `server/routes`, `server/httpapp` and the task-event
  repository: **960 PASS, 0 FAIL, 0 SKIP**, every package ok. The database cases RAN rather than skipping, and
  their timings say so: `TestLedgerReadIsOneCursorAcrossAllOfAUsersTasks` 3.97s,
  `TestLedgerIntentsOneBatchDecidesEachItemAndAnswersTheResendFromItsRow` 4.06s,
  `TestLedgerIntentsStaleDecisionSucceedsOnceTheClientReReads` 4.69s,
  `TestLedgerIntentsRecordsOfflineFactsUnchangedInArrivalOrder` 2.90s. The two slow packages are
  `server/httpapp` 146.319s and `task_management/infrastructure/repositories` 214.063s.
- The SKIP count is stated on purpose: without `-v` a skipped database case prints nothing and reads exactly
  like a pass, and a green run over skipped cases is the same failure shape as a probe that never ran.
