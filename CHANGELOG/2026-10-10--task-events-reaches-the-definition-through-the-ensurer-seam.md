# task_events reaches its definition through the column-ensurer seam

The production incident this repairs: every status change failed with `column "user_seq" does not
exist` while `/health` kept answering, because P1 added four things to `task_events` and nothing
carried them to a database that already held the table. `createAll` creates a table only when it is
ABSENT; the ensurer seam is the only path that reaches an existing database, and P1 registered
neither.

## What landed

- **`fastmcp/task_management/infrastructure/database/task_event_ensurer.go`** —
  `EnsureTaskEventColumns`, registered in `ColumnEnsurers`, covering the WHOLE delta:
  1. `user_seq BIGINT NOT NULL` with `uq_task_event_user_seq UNIQUE (user_id, user_seq)` — added
     nullable, **backfilled** per user in `(created_at, id)` order above that user's current
     maximum, then `SET NOT NULL`, then the unique;
  2. `client_event_id UUID` (nullable by definition, nothing to backfill) with
     `uq_task_event_client_event UNIQUE (user_id, client_event_id)`;
  3. the kind CHECK widened to the twelve-kind vocabulary;
  4. the actor CHECK widened to `seat|client|gate|human`.
- **Two transactions, deliberately.** The columns can be added to any table and must land even where
  the widenings cannot; recreating a CHECK validates every existing row, and a boot must not be
  blocked on a constraint when the column is what is actually missing.
- **The drift test** `task_event_ensurer_definition_test.go` compares both vocabularies, and the
  columns the ensurer adds, against the `task_events` TableDef's own DDL, so a later vocabulary
  change cannot leave the ensurer behind — which is the class of gap that caused this incident.

## The finding that decides the owner's reading

P1's delta is **four parts, not one**, and the write path needs all four: the end-to-end case first
failed on `client_event_id` (the outbox key — the repository's INSERT names it, so it is the next
42703 after `user_seq`) and then on the actor CHECK, because the recorder stamps `actor_kind 'seat'`
and the pre-wave vocabulary allows only `user|system|agent`.

**Recreating the actor CHECK IS a data move on a populated table.** Adding a CHECK validates every
existing row, and a row carrying the old actor classes cannot satisfy `seat|client|gate|human`. So on
a table WITH old rows the widening cannot apply without rewriting those values — which the incident's
order forbade — while on an EMPTY table it applies cleanly. "Nothing moves between tables and nothing
is dropped" therefore holds **only for an empty ledger**. The room's history supports that
production's ledger is empty (nothing wrote `task_events` before P1's reader landed), but that is a
measurement rather than an inference, and it is with the owner.

The code handles both: a populated old table still gets its columns, and the widening fails **loudly**
with the constraint's own message naming `ck_task_event_actor_kind` and the remedy.

## Gate

The ensurer runs only under `AUTO_MIGRATE=true` — `CreateTables` is its only caller, reached from
`InitDatabase` only under that opt-in. **Under `AUTO_MIGRATE=false` nothing runs, the columns are
never added, and the write path keeps failing exactly as it does now.** The repo records that
production runs it true; `.env.sample` defaults it false.
