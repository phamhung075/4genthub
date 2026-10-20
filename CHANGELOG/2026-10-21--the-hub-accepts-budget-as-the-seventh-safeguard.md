# the hub accepts `budget`, the client's seventh safeguard name, and 0009 widens the CHECK

The client publishes seven safeguard rows after every `ready` (`agenthub_client` pin `6c25e316`,
`internal/clientservices/services.go:45,114-116,166`); the hub admitted six, so the `budget` row was
answered `bad_safeguard` on every ready and never reached the table. This lands the ruling
`RULING-2026-10-21-budget-safeguard-name-and-migration.md` (architect): `budget` is the seventh name
and the fifth ROOM-SCOPED one, the closed set still lives on the producer side, and the widening is a
new migration rather than an edit to an applied step.

## What changed

- **The vocabulary.** `SafeguardBudget = "budget"` joins `room_safeguard_orm.go`'s constants after
  `SafeguardRoomGuard`, and the file's prose says seven names / five room-scoped.
- **The store's rule.** `validate` in `room_safeguard_repository.go` accepts `budget` in the
  room-scoped arm, so it needs a room of 1..255 like the other four and is refused `bad room`
  without one. No wire field is added or renamed, and nothing changes in the read path: the alert
  filters on a state transition, not on a name.
- **The three creation-path CHECKs.** `room_safeguard_postgresql.sql`, the runtime `TableDef` in
  `room_safeguard_tables.go`, and the generated `0001_baseline.sql` line all read
  `('compact', 'watchdog', 'messages', 'roomguard', 'budget', 'bridge', 'agent')`, with `budget` in
  the client's own order. The other two CHECKs, `ck_room_safeguards_room` and
  `ck_room_safeguards_state`, are untouched: `budget` is not in
  `('bridge', 'agent')`, so it needs a room.
- **`0009_room_safeguards_accept_budget.sql` is new** and widens the constraint in place: a
  `to_regclass` guard, `DROP CONSTRAINT IF EXISTS` and an `ADD` with the seven values. It is not an
  edit to `0008` or `0004`: the runner applies a step once by its base name, both are on
  `origin/main` and have run on exactly the databases whose CHECK still holds six values, and `0008`
  carries no value list. Widening a CHECK is no data move, so there is no pre-check and no delete.
- **`0001_baseline.sql` is the one legal baseline edit**: the parity guard
  (`TestBaselineMatchesEveryRegisteredTableDef`) compares CHECK expressions against the registry, and
  a CHECK's value list is what the baseline tracks from it. No column is dropped, reordered or
  altered.
- **The doc of record** `ai_docs/core-architecture/agent-boundaries.md`, both halves the ruling asks
  for. The budget edits: `budget` joins the health row's safeguard list, the vocabulary sentence is
  five room-scoped / seven, the 7.4 threshold table gains
  `budget | the pass interval, 15 s | 45 s`, and the capability table names `room_safeguard` /
  `room_safeguards` with `budget` in the list. `started_at` stays on the health row - the ruling's
  revision 2 withdrew that drift, and only the `rig` token was stale there. The live-clause sweep the
  file had never had (it was created by the rename commit `ad08932a`): every clause that says what the
  system does today now reads `room` - the phase-2 exec (`4genteam send`), the throwaway-room checks,
  `compact-run --room`, agent.json's `rooms` list, the heartbeat path `<safeguard>-<room>.json`, the
  health row's key, `doctor [room]` and its stderr line, `up --existing`, the `Scope machine|room`
  type and its table, the daemon verbs, the nudge log/event, the autofix paths, argv and payloads,
  the dead-man entity `room_safeguard`, and `ps <room> --nodes`. The daemon row's Start and Check name
  what exists - `ensureDaemon`, the runtime's `daemon` subcommand, and its IPC socket - rather than a
  `4genteam daemon` verb no client carries. Seven `rig` tokens remain on six
  lines, all history or artifact names: the preamble's file-name note, the 2026-10-11 legacy-client
  sentence, the dated incident record (`:256`, `:260`), the owner's
  `rig-continue.sh`/`rig-watchdog.sh` files (`:464`), and the dated 2026-10-11 ruling cell (`:517`).
  One more, `:411`'s "no seat edits under `rig/`", named a directory the client tree no longer has;
  the ruling's correction 3 re-points it to `agenthub_client/`, and because that line is documentation
  only a seat cannot carry it: the lead landed it as `9f5c9dcf`, so it is not among the seven here.

## Not this task

The client's `at` is RFC3339 while `wsOptUnixMillis` reads unix millis, so `last_beat_at` stores NULL.
That drift is reported separately.

## Verification

- `cd agenthub_go && go test -count=1 ./...` with
  `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55433/postgres`: green, so the
  migration cases ran against a real PostgreSQL 16 rather than skipping.
- `TestTheBudgetStepWidensTheSixNameCheck` builds the post-`0008`, six-name table by hand, proves
  `budget` is refused BEFORE the step, applies `0009`, then asserts the two stored rows are carried,
  a room-scoped `budget` row stores, `keeper` is refused with SQLSTATE 23514 on
  `ck_room_safeguards_safeguard`, `budget` with an empty room is refused on `ck_room_safeguards_room`,
  and a second application of the SQL is a no-op.
- `TestTheBudgetStepIsANoOpWithoutTheTable` proves the `to_regclass` guard: no error, and no table
  invented.
- `TestValidateStatesTheSevenNamesAndTheirScopes` names `budget` accepted with a room and refused
  `bad room` without one; `TestUpsertAcceptsEachOfTheSevenNamesInItsScope` stores it;
  `TestUpsertRefusesTheClosedSetsBeforeAnyStatement` refuses it without a room. The schema test
  composes its expected CHECK from `SafeguardBudget`, so the file and the `TableDef` cannot drift
  from the constant.
- `TestBaselineMatchesEveryRegisteredTableDef` passes over 50 registered tables: the baseline's
  `ck_room_safeguards_safeguard` equals the registry's.
- `TestSafeguardFrameAcceptsTheRoomScopedBudgetRow` (socket, real store) is the code-verifiable form
  of the live acceptance: a `budget` frame with an empty room is answered `bad room` and stores
  nothing, and a room-scoped `budget` frame stores exactly one row for its key.
- `grep '\brig\b' ai_docs/core-architecture/agent-boundaries.md`: 43 lines and 49 tokens before,
  6 lines and 7 tokens after, every one in the keep-list the Doc of record bullet names.
- The pre-`0008` fixtures (`six_safeguards_migration_integration_test.go`,
  `room_safeguards_rename_integration_test.go`) are untouched, as ruled.
- The live log stays red until the lead rebuilds and reboots the hub: the acceptance for the stored
  row is one `budget` row per room per connector and no `bad_safeguard` on `ready`.
