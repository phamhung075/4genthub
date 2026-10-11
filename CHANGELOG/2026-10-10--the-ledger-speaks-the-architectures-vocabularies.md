## The ledger speaks the architecture's vocabularies, and one lock gives every user one cursor

### Changed

- `agenthub_go/fastmcp/task_management/infrastructure/database/task_event_tables.go` — `task_events` gains `user_seq BIGINT NOT NULL` with `UNIQUE (user_id, user_seq)`, `client_event_id UUID` with `UNIQUE (user_id, client_event_id)`, and `subtask_id UUID`. The kind CHECK becomes the twelve kinds owned below, and the actor CHECK becomes 2.5's `seat`, `client`, `gate`, `human`. The column definitions and the DDL move together, because the embedded runner creates this table from the registry and not from a SQL file — `init_schema_postgresql.sql` carries no `task_events` at all, which is why the tests create it through `CreateTables`.
- `.../domain/entities/task_event.go` — the kind and actor constants carry those vocabularies; `TaskEvent` carries `UserSeq`, `SubtaskID` and `ClientEventID`, and `AppendTaskEvent` carries `SubtaskID` and `ClientEventID`. `TaskEventActorSystemID` and the `system`/`agent`/`user` classes are DELETED rather than deprecated: a vocabulary that carries a class nothing may be is exactly the fallback this ledger exists to refuse.
- `.../infrastructure/repositories/task_event_repository.go` — the append transaction takes ONE per-USER advisory lock (`hashtext(user_id)`), reads `user_seq` under it, and inserts both sequences in the same statement. An absent `client_event_id` or `subtask_id` reaches PostgreSQL as NULL, and PostgreSQL's unique index treats NULLs as distinct, which is what keeps every keyless entry legal.
- `.../application/services/task_event_recorder.go` — the actor is `seat` when the request named one through the MCP header and `human` otherwise; a recorder built with NEITHER refuses with `ErrNoActor` instead of stamping something anonymous.
- The O2 records, in the same commit, because the mapping the interim needed is now permanent: `agenthub_go/fastmcp/server/httpapp/task_status_ledger_test.go`, `.../application/services/task_event_recorder_test.go`, `TEST-CHANGELOG.md` and `CHANGELOG/2026-10-10--the-seat-identity-travels-with-every-mcp-block-and-names-the-writer.md` now read `seat`/`human`, and the deviation note that lived in them was REMOVED rather than reworded.

### The twelve kinds, each with the item that writes it

The widening is the architecture's, but a kind the CHECK permits and nothing writes is dead vocabulary — the same failure as a fallback that never fires — so each value below is named with the item that writes it, and the ones that could not be named are gone.

| kind | written by | evidence |
|---|---|---|
| `assigned` | P3 | `NEXT_GEN.md:435` — the decisions the intents route accepts |
| `claimed` | P3 | `NEXT_GEN.md:435`; O7 `:427` sets the claim on the task side |
| `delivered` | O7 | `NEXT_GEN.md:427` — "posts a `delivered` event, once per (task, last_seq)" |
| `context_loaded` | P5 | architecture `:598` names it a FACT the client records; P5's outbox drains "facts first" (`:677`), P3's route accepts them |
| `progress` | O1c | `NEXT_GEN.md:421` — "`add_progress` writes a `progress` event" |
| `status_changed` | O1b | `NEXT_GEN.md:420`; the ONLY kind with a live writer today, `task_event_recorder.go:72` |
| `evidence_submitted` | O3 | `NEXT_GEN.md:423` — "stores an `evidence_submitted` event" |
| `gate_verdict` | O5 | `NEXT_GEN.md:425` — "writes a `gate_verdict` event" |
| `escalated` | O6 | `NEXT_GEN.md:426` — "UNCERTAIN writes `escalated` to the worker seat's `escalates_to` seat" |
| `human_decision` | P3 | `NEXT_GEN.md:435`; architecture `:242` |
| `handover` | P5 | architecture `:598` names it a FACT; the same client path as `context_loaded` |
| `context_updated` | P7 | `NEXT_GEN.md:439` — "A context change appends `context_updated {level, id, version}`" |

**`planned` is DROPPED.** 2.5 lists it and its worked example opens with it, but no O/P item writes it: the "Deliberately NOT queued" paragraph says the emit sites belong to the items that own them, O1a is the table/entity/repository/route and no item claims a creation emit. Per the ruling, a kind with no writer and no named owner does not get carried: when a creation emit is queued it comes back with its owner and one word of DDL. The reason is written at the vocabulary in `task_event.go` so a reader meets it there rather than in a CHECK that silently refuses.

### Why one lock, not two

Both cursors are read under the SAME key on purpose. A per-user lock for `user_seq` beside a per-task lock for `seq` would hand every append two locks to take in an order someone will eventually get wrong, and that failure mode is a deadlock — much worse to find, and much worse to run, than a duplicate. One lock, keyed on the user, both sequences; the reason is written at the function so the next reader does not "improve" it into two.

### Why there is no `system` actor

Every entry is attributed to whoever acted. When the platform performs a write on a caller's behalf — completing a task unblocks a dependent task — the entry carries the CALLER, because the caller is who acted; the old `system` stamp was an artifact of the dependent write not carrying the actor forward, not a fact about the world. A recorder with no actor to name refuses, and production always builds it with a user (`task_wiring.go`), so the refusal costs nothing and converts a silent lie into a loud failure.

### Testing

From `agenthub_go` with `GOCACHE`/`TMPDIR` inside `.gocache`/`.gotmp`, against the throwaway PostgreSQL on 55432 (`bash tools/testpg/start.sh`), where each case creates its own database and its schema comes from `CreateTables`:

- `gofmt -l` on `task_management` and `server/httpapp` printed nothing; `go vet` on both clean; the ledger's database cases: `TestTaskEventAppendAssignsGaplessSeq`, `TestTaskEventAppendRefusesBogusKind`, `TestTaskEventAppendGivesOneGaplessUserCursorAndRefusesAResend` → all PASS, `ok repositories`; the DDL case and the recorder case → `ok`.
- **The cursor claim, observed**: `user_seq across two tasks = [2 1], per-task seq = [1 1]` — two concurrent appends for one user on DIFFERENT tasks took distinct `user_seq` values and left no gap, while each task's first entry is still that task's `seq` 1.
- **RED FIRST for the belt, measured**: with `uq_task_event_client_event` removed from the DDL (restored immediately), the same case failed `the same client_event_id was accepted twice: the unique constraint must refuse a resend`. That is the claim the outbox rests on — a resend after a reconnect lands once — proved by its absence.
- **The actor vocabulary lands at the table**: the case inserts `actor_kind = 'bogus'`, a value the Go constants never offer, and requires the database to refuse it.

### Not covered, named rather than implied

- **One red did NOT reproduce, and it is recorded as such rather than as a pass**: keying the advisory lock per TASK instead of per user (restored immediately) still produced `user_seq = [2 1]` and the case PASSED. The window between the `MAX(user_seq)` read and the insert is narrow, and the unique constraint refuses a loser rather than letting it duplicate, so the test cannot manufacture that failure on demand. The per-user lock is therefore justified by its REASONING and by the constraint's belt, not by a reproduced red.
- **The first attempt at the belt's red was invalid** and is not used as evidence: the run was backgrounded and interleaved with the restore edit, so the binary it compiled is unknowable. The measurement above was re-taken with the run and the edits strictly sequential.
- No case here exercises P2's cross-task read or a real client outbox; those are P2's and P5's.
- `agenthub_go/NEXT_GEN.md` is NOT in this commit — another seat's held edit lives in its working tree — so P1's box and O2's box are still unticked.
- Nothing is pushed and `/health` was not touched.
