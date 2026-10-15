# Six safeguards, one scope rule, and the connector's error field is `message`

The `rig_safeguards` store accepted four safeguard names and refused three the client reports on every
connect, and the connector's error frame carried the reason under a key no reader reads. Both are fixed
on the server, which is the side the architect's ruling (`seats/architect/RULING-item4-safeguard-
vocabulary-and-error-field.md`, 2026-10-15) rules the change onto. The client changes nothing: no
rebuild, no pin bump.

**D1 - the server adopts the client's six names, and `rigd` is deleted.** The set was
`compact, watchdog, bridge, rigd`; it is now `compact, watchdog, messages, roomguard, bridge, agent`.
A closed set has one owner, and the owner is the side that produces the rows: the client's `Verify` and
`publishRows` write every row, and the server's only name reference is the dead-man alert. So the three
missing names were refused at every connect ("bad safeguard" for `messages`/`roomguard`/`agent`), three
supervised safeguards were invisible to the alert path, and the dead-man alert (7.3) was keyed to a name
no producer has sent since `bc725e6` (2026-10-15) renamed the client's machine-level supervisor to
`agent`. `rigd` is retired with OpenRig, so it is deleted rather than aliased - a compatibility name is
what the repo's clean-code rule forbids.

**D2 - the rig rule follows each name's scope.** The four rig-scoped names need a rig of 1..255; the two
machine-scoped ones (`bridge`, `agent`) need EXACTLY an empty rig, not "any rig". `rig` is part of the
primary key `(user_id, connector_id, rig, safeguard)`, so an arbitrary rig on a machine row would let one
machine-level row exist under several spellings and the upsert would stop being idempotent. `validate()`
checks the NAME first (the name's scope decides the rig rule) and the three messages are unchanged, so
the socket still answers `bad_rig` / `bad_safeguard` / `bad_state`.

**D3 - the error frame's field is `message`, and the server is the side that changes.** `wsConnectorError`
wrote the human text under `error`; the client's reader reads `frame["message"]`
(`agenthub_client/internal/clientsync/agent.go:666`), the doc-of-record's 2.2 row has named the field
`message` since the ruling of 2026-10-11 (`2004877a`), and the browser socket's own error payload uses it
(`wsErrorData`). The lone dissenter was a builder older than that ruling. So every connector refusal now
carries `message` and the client's log line names its reason instead of being empty.

## Changed

- `agenthub_go/fastmcp/rig_safeguard/infrastructure/database/rig_safeguard_orm.go`: the six name
  constants, with `SafeguardRigd` -> `SafeguardAgent` and the scope split in the block comment.
- `.../repositories/orm/rig_safeguard_repository.go`: `validate()` per D2, the name checked before the
  rig rule.
- `.../schema/rig_safeguard_postgresql.sql` and `.../database/rig_safeguard_tables.go`: the name CHECK
  widened to the six and the new `ck_rig_safeguards_rig` stating the scope rule, in both DDL sources.
- `agenthub_go/fastmcp/task_management/infrastructure/database/migrations/0001_baseline.sql`: the same
  two CHECKs, which is what the baseline's generator produces from the TableDef registry - the parity
  guard compares CHECK expressions, so a registry change not carried here is a red guard.
- `agenthub_go/fastmcp/server/httpapp/ws_connector_safeguard.go`: `raiseRigdDeadmanAlert` ->
  `raiseAgentDeadmanAlert`, naming `SafeguardAgent`; the dead-man alert's entity id is unchanged in
  shape (the connector and the machine-scoped name, no rig).
- `agenthub_go/fastmcp/server/httpapp/ws_mount.go`: `wsConnectorError` writes `message`.

## Added

- `agenthub_go/fastmcp/task_management/infrastructure/database/migrations/0004_six_safeguards_and_machine_scope.sql`,
  the step a DEPLOYED database needs - the schema file cannot help one, because every statement in it is
  `CREATE ... IF NOT EXISTS`. It drops the two constraints it replaces, renames the stored `rigd` row to
  `agent` with the empty rig its scope demands, deletes the rows no scope rule can accept, and re-adds
  both constraints from the ruled sets.
  - **THE ORDER IS NOT COSMETIC, AND THE FIRST VERSION WAS WRONG.** With the rename written before the
    old name CHECK was dropped, PostgreSQL refuses it: `ERROR: new row for relation "rig_safeguards"
    violates check constraint "ck_rig_safeguards_safeguard" (SQLSTATE 23514)`. The constraints come off
    first. Each step is one transaction (the runner holds its SQL and its ledger row together), so no
    other connection reads the table without them. This was caught by the new integration case, not by
    reading.
  - **IT DELETES ROWS RATHER THAN MERGING THEM.** The old constraint stated no rig rule, and the old
    `validate()` demanded a rig for EVERY name, so a legacy `bridge` row carries one; a rig-scoped name
    with an empty rig could have been stored only by a writer that bypassed `validate()`. Both shapes are
    dropped, because the client republishes all six rows after every ready (7.2) and a merge would invent
    a state no reporter sent. The table is dev data.
  - **THE RULING NAMED A DIFFERENT PATH FOR THIS FILE, AND THE PATH IT NAMED IS NOT READ BY ANY CODE.**
    The ruling's step 5 puts it in `rig_safeguard/infrastructure/database/migrations/`; the runner embeds
    exactly one directory (`migration_runner.go:29`, `//go:embed migrations` under
    `task_management/infrastructure/database`), and `migrations/README.md` states the one-set rule. In the
    rig_safeguard directory the step would be dead bytes that no boot applies. It is `0004` in the set
    the runner reads, which is what makes it a migration rather than a file.

## Tests

- `rig_safeguard_repository_test.go`: `TestValidateStatesTheSixNamesAndTheirScopes` - the six names with
  their scope's rig, the four refusals, the retired `rigd` name, an unknown name and an unknown state,
  with no database in the way; `TestUpsertAcceptsEachOfTheSixNamesInItsScope` - each name stored with its
  scope's rig; `TestUpsertRefusesTheClosedSetsBeforeAnyStatement` gains the two machine-scope refusals
  (a rig on `bridge`, on `agent`) and now expects six refused frames to leave no row.
- `rig_safeguard_schema_test.go`: the expected CHECK set is composed from the constants for the six names
  AND from the machine-scoped names for the rig rule, so a name moving between the two scopes cannot
  leave the CHECK behind.
- `ws_rigd_test.go`: every connector-frame assertion moves from `got["error"]` to `got["message"]` (six
  sites), the dead-man alert asserts `safeguard == "agent"`, and the refusal case gains the socket-level
  scope rule - a machine-scoped row carrying a rig is refused `bad rig`, and an `agent` row with the empty
  rig is stored.
- `ws_connector_test.go`: the four assembled-frame assertions move to `message`.
- `rig_safeguards_migration_integration_test.go` (new, PostgreSQL): the step run through the runner
  against a database holding that table as `0001_baseline.sql` created it before the step, with one
  legacy `rigd` row, the two malformed shapes, and one rig-scoped row. It asserts the rename carries the
  row's own report, the malformed rows are gone, a second application of the SQL is a no-op, the ledger
  stops the recorded step from running again, the database itself refuses the retired name and a rig on a
  machine-scoped name (`SQLSTATE 23514`), and all six names are storable in their scopes.

## Evidence

In `/home/daihu/.config/4genthub/rooms/4genthub-min/wt/go-dev-root`, tree clean before and after:

- `go build ./...` rc 0; `go vet ./fastmcp/rig_safeguard/... ./fastmcp/server/... ./fastmcp/task_management/...` clean.
- `go test -count=1 ./...` **rc 0 with no database**.
- With `AGENTHUB_TEST_PG_URL` from `tools/testpg/start.sh`: `go test -count=1 ./fastmcp/rig_safeguard/...`
  ok (3.6 s), the socket subset `-run 'Safeguard|Deadman|Rigd|Connector' ./fastmcp/server/httpapp/` ok
  (44.7 s), and `TestTheSixSafeguardsStepMovesTheStoredVocabulary` ok (0.8 s).
- **The guards were falsified rather than assumed.** Removing `ck_rig_safeguards_rig` from the schema
  file turns `TestRigSafeguardSchemaAgreesWithTheORMRow` red (the file's CHECKs and the runtime's
  diverge); removing it from the baseline turns `TestSchemaMatchesGoDefinitions` /
  `TestBaselineMatchesEveryRegisteredTableDef` red; running `validate()` with the retired four-name set
  turns `TestValidateStatesTheSixNamesAndTheirScopes` red. Both edited files were restored byte-identically.

## Not in this change

- **The client, and therefore the pin.** D3 puts the rename on the server, so there is no client commit,
  no rebuild and no pin bump.
- **The `rigd` word in names that are not the vocabulary.** `ws_rigd_test.go` and its `rigdHello` helper
  keep the file and function names they were written with, and the doc's title, file name and its
  sections outside the six ruled deltas still say `rigd` for the supervisor process. The ruling parked
  the doc's title and file name as a separate decision; the test identifiers are the same kind of
  leftover and are named here rather than swept in.
- **The ruling's "errors.Is branch" has no counterpart in the change inventory.** No clause of it
  mentions `errors.Is`; `wsAppendError`'s typed switch is what maps a typed failure to the frame's text
  and it is unchanged.
