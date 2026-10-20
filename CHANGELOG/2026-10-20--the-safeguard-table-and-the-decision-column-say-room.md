# the safeguard table and the decision column say room, and the boundaries doc drops its old path

Slice B of `DECISION-2026-10-20-rig-gone.md`: the server stops storing and naming the retired unit.
`agenthub_client` is pinned to `133bbc7` (client main, slice A landed and pushed).

## What changed

- **The package and its files.** `fastmcp/rig_safeguard/**` is `fastmcp/room_safeguard/**`
  (`room_safeguard_orm.go`, `room_safeguard_tables.go`, `room_safeguard_postgresql.sql`,
  `room_safeguard_repository.go` and its tests).
- **The table, its columns and its constraints.** `rig_safeguards` is `room_safeguards`; its `rig`
  column is `room`; `ck_rig_safeguards_{state,safeguard,rig}` are
  `ck_room_safeguards_{state,safeguard,room}`; the index is `ix_room_safeguards_user_connector` and
  the primary key `room_safeguards_pkey`.
- **`room_decisions.rig_name` is `room_name`, and its answer-leg index follows it** to
  `ix_room_decisions_user_room_state_acked`. The DDL, the schema file, the Go `TableDef`, the
  migration set and the decision service's own column list all say the new name.
- **The pull's room filter survives the rename.** `GET /api/v2/decisions/answers` takes `?room=<slug>`,
  `Pull` and `ListAnswers` take the room and filter on `room_name`, and a pull that names no room is
  refused with `invalid-pull` rather than widened to the tenant: the ack is destructive, so a daemon
  handed another room's answers could not apply them and its ack would close a decision nobody
  applied. `room_id` stays as the FK the joins read and `room_name` as the daemon's delivery key; the
  ORM row says why both exist so a later cleanup does not unfilter the pull.
- **`0001_baseline.sql` is regenerated** from the `TableDef` registry, which is the source of truth;
  `0008_the_safeguard_and_decision_names_say_room.sql` carries the rename to a database whose
  catalogue already exists, guarded so a boot that reaches it before the registry creates the tables
  is a no-op rather than SQLSTATE 42P01.
- **One earlier step changes one word.** `0005` names the decisions column in an index statement, so
  the column rename makes a fresh boot fail before `0008` can run (`CREATE INDEX ... (rig_name)` on a
  baseline that no longer has that column, and PostgreSQL resolves the column list before its
  `IF NOT EXISTS` check). The statement carries `room_name`. It is a no-op on any database that
  applied the step (the runner skips it) and on a fresh database (0001 has already created the index
  under that name); only a database that stopped between 0004 and 0008 could miss the column, and
  that state does not survive a boot.
- **The retired `rig` case is deleted from the comm-guard**, with its test rows: a `room` command with
  `send|queue|broadcast` does not exist, so the arm could never fire and a rename would have invented
  a rule. The `tmux` arm, which is the channel a seat can actually reach, carries the rows.
- **`ai_docs/core-architecture/rigd-boundaries.md` is `agent-boundaries.md`**, and its eight hub
  citations (six Go files, `NEXT_GEN.md`, the doc's own naming note) name the new path. The
  frontend's nine citations are fe-dev's, already updated on their branch; they resolve when that
  branch lands.

## Verification

- `cd agenthub_go && go test ./...` - green, and green again with
  `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55433/postgres`, which runs the
  migration cases against a real PostgreSQL 16 instead of skipping them.
- `TestSchemaMatchesGoDefinitions` compares the migration set's indexes, constraints and columns with
  the runtime DDL: it is what caught `0005`'s stale column.
- `TestTheRoomNamesStepRenamesTheSafeguardTableAndTheDecisionColumn` builds the pre-rename shape by
  hand, applies `0008`, and asserts the table, the column, the three CHECK names, the primary key, the
  connector index, `room_decisions.room_name` and its renamed answer-leg index, that the stored rows
  are carried, and that a second application is a no-op.
- `TestPullMintsTheShippedCursorAndRefusesOneItDidNot` proves the argument the service passes, and
  `TestRoomDecisionPgThePullHandsOverOnlyTheRoomItNames` proves the SQL: one tenant, two rooms, one
  answered ask each, and a pull of one room's name carries that room's answer, never the other's,
  while an unnamed pull is the `invalid-pull` refusal. The fixture that writes an ask straight into
  the table now stores the room's own slug in `room_name` rather than the retired literal, because
  the pull keys on it. `TestTheRoomNamesStepIsANoOpWithoutItsTables` pins the guard.
- `TestTheSixSafeguardsStep*` still pass against the shapes `0004` was written for: that fixture keeps
  `rig_safeguards` and `rig` deliberately, because it reproduces history and `0008` is the rename.
- `python3 scripts/DOC-CITATIONS.py`: 49 docs, 732 citations, 0 violations.
