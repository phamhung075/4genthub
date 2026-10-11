## The evidence route: a client's evidence submission becomes one ledger event

### Added
- `agenthub_go/fastmcp/server/routes/task_evidence_routes.go`: `SubmitTaskEvidence` ports O3's write half, `POST /api/v2/tasks/{id}/evidence`. It mirrors the read path next to it (`task_event_routes.go`) rather than widening `UserTaskController`: a narrow `TaskEvidenceWriter` interface, and the SAME task-first 404 seam, so a task the caller cannot see is refused before anything is decided or written. Order is the contract - validate (422 for a blank `base_sha`/`head_sha`, or a `numstat` over `EvidenceNumstatMaxBytes`), ask for the task (404), then reach the writer (409). The over-cap refusal NAMES the cap: a silently truncated numstat would describe a diff that never happened.
- `agenthub_go/fastmcp/server/httpapp/task_event_controller.go`: `taskEvidenceWriterAdapter` satisfies that interface over the ledger's ONE writer. The duplicate decision and the append happen inside one transaction, and the decision takes the ledger's own per-user append lock (`pg_advisory_xact_lock(hashtext(user_id))`, the same lock `AppendInTx` takes) BEFORE it reads the previous `evidence_submitted` head_sha - without that, two concurrent submissions of one head_sha could both read "no previous evidence" and both append, which is the double submission the 409 exists to refuse.
- `agenthub_go/fastmcp/server/httpapp/task_routes.go`: the route is mounted beside the events read, behind the SAME `authed` wrapper. There is no machine token: `e5ecff63` removed it, and the credential is `AGENTHUB_TOKEN` through `authed`.

### Fixed, found on the way
- `agenthub_go/fastmcp/server/routes/task_event_routes.go`: the read emitted `created_at` as a `time.Time`, and the compact JSON writer refuses one (`Object of type Time is not JSON serializable`), so `GET /api/v2/tasks/{id}/events` answered **500 the moment a task had one event** - the read could never work against rows, and no existing test reached it with any. It emits the RFC3339 string the rest of this server emits, the same format the POST returns, so a client parses one shape.
- The task-event READ scoped its rows by the raw token subject while both ledger writers scope by the normalized UUID (`domain.ValidateUserID`), so for any non-UUID subject - the default development identity among them - the same read matched nothing and answered `200 {"events":[]}` for a task that had events. The adapter now normalizes the same way the writes do, so one task has one history under one user id. `TestEvidenceLedgerReadIsScopedLikeItsWrites` pins it with the subject `seam-probe-user` scoped to `b352ae6a-...`: the POST is 201 and the read then returns the event.

### Verified
Measured by the seat, with `AGENTHUB_TEST_PG_URL` against a live cluster, on the tree that carries these files:
- `go test -count=1 ./fastmcp/server/httpapp/ -run Evidence` -> `ok 56.049s`, five cases, each printing what it observed:
  - credentials: `POST /evidence -> 403 {"detail":"Not authenticated"}` with none, `-> 401 {"detail":"Invalid token"}` with an invalid one, `-> 404` for a task that does not exist - each the SAME status the events read answers, which is the parity the box's guard requirement asks for (the wrapper's no-credential code is 403, not 401; parity with the read is the binding rule).
  - storage and read-back: `POST -> 201` with `seq 1, kind evidence_submitted` and the payload carrying the two shas, the raw numstat and the test block, and `GET /events -> 200` returning that same event.
  - the duplicate: first `-> 201`, the same head_sha again `-> 409 {"detail":"Evidence for this head_sha has already been submitted"}`, a different head_sha `-> 201`.
  - concurrency: two simultaneous submissions of one head_sha -> `[201 409]`, so the lock-before-read ordering above is exercised, not asserted.
  - isolation: another user's POST `-> 404`, matching the read's 404, and the owner's submission `-> 201`.
- `go test -count=1 -v ./fastmcp/server/routes/ -run Evidence` -> six cases ok (the invisible task without recording, the blank shas, the cap boundary, the 409 mapping, the created event with the request's own fields, and the empty `failed` list).
- `gofmt -l` on `fastmcp/server/routes` and `fastmcp/server/httpapp` printed nothing.

### Not done, named rather than implied
- `agenthub-frontend/src/docs/apiReference.ts` is regenerated in the same commit as this change only if the route set it renders changed; the route is new, so it IS regenerated - the artefact is the docs page's copy of the routes, and the two must not drift.
- The client half (`agenthub_client` `63fd184`, `4genteam evidence`) was NOT run against this route end to end: its HTTP seam is stubbed in every case, because a push path cannot be pointed at a cloud from the suite. What is proven here is the route's own behaviour by direct request; what is proven there is the request the client builds.
