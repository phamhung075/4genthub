## The context event names the seat that changed it and what changed

Owner-facing defect: a task timeline showed `context_updated` and nothing about WHO changed the context
or WHAT changed. Both writers hardcoded `ActorID: "context"`; the seat was already on the request and
thrown away.

### Changed

- `fastmcp/task_management/domain/entities/context_change.go` (new): `ContextChange{Path, Op, Old, New}`
  and the ONE builder both writers call, `ContextChanges(before, after *OrderedMap[any])`: sorted
  two-level dot-joined paths, `set`/`add`/`remove`, arrays compared as a whole, `MaxContextChangeValue`
  (512 B) per leaf - over it a `{truncated, bytes, sha256}` marker - and `MaxContextChangesPayload`
  (8 KiB) for the set, counting what it leaves out. `ContextUpdatePayload` assembles the payload in one
  place: `{level, id, version, origin, changes, changes_truncated}`.
- `application/services/task_event_recorder.go`: `RecordContextUpdate(ctx, taskID, level, version,
  origin, changes, dropped)` built on `actorFor` exactly like `RecordStatusChange`; `ActorFor` is exported
  so the HTTP appender, which opens its own transaction, resolves the actor by the same order.
- `application/services/unified_context_service.go`: the seam gains `RecordContextUpdate`, which the
  writer now calls with `origin: "unified_context_service.update"` and the diff of the read context
  against the merged one. `application/use_cases/update_context.go`: the same call as
  `manage_context.update`, over the context as read versus the dict the request produced. Neither names
  an actor any more.
- `fastmcp/server/httpapp/context_ledger_appender.go`: `RecordContextUpdate` writes the entry under the
  seat the request named, else the resolved caller, and refuses when neither exists.
- `ai_docs/core-architecture/agenthub-system-architecture.md`: the ledger line names the payload's keys,
  the attribution rule and the two caps.

### Tests

- `domain/entities/context_change_test.go`: leaf paths and ops, arrays compared whole, the 512 B marker
  (byte count + 64-hex sha256), the 8 KiB cap with `changes_truncated` and kept order, the payload keys,
  and the empty set serializing as `[]`.
- `application/services/context_update_attribution_test.go` and
  `application/use_cases/update_context_ledger_test.go`: each writer, driven through the REAL recorder,
  lands `actor_kind=seat`, `actor_id="4genthub-min/go-dev"`, its own `origin`, and the changed leaf.
- `fastmcp/server/httpapp/context_ledger_appender_test.go`: a context update with no resolved caller is
  refused, not written under an empty id.
- `create_context_single_write_test.go`: the doubles implement the widened seam; the create path still
  writes exactly one context update.

### Measured

`go test ./...` in `agenthub_go` -> rc 0 (the DB-backed suites skip without `AGENTHUB_TEST_PG_URL`).
