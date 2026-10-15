# The six-safeguards step is a no-op without its table

`0004_six_safeguards_and_machine_scope.sql` opened with two `ALTER TABLE rig_safeguards` statements, and
on a database that does not hold that table the step died with `SQLSTATE 42P01` and took the **whole
boot** down with it. The fix is one guard: the step returns without doing anything when
`to_regclass('rig_safeguards')` is null.

## Measured, not inferred

`TestDatabaseInitializerCreateDefaultProject` failed with the step unguarded:

```
database_init_integration_test.go:63: the boot after the owner's mark failed:
migration 0004_six_safeguards_and_machine_scope: the migration's SQL failed:
ERROR: relation "rig_safeguards" does not exist (SQLSTATE 42P01)
```

## Why the absent table is the ordinary case

The engine creates its tables from the TableDef registry **last** (the init SQL, then `createAll`), while
the runner skips `0001_baseline` whenever the catalogue is not empty - so a boot reaches this step with a
populated catalogue and no `rig_safeguards` yet. There is nothing to move in that database: the table is
created from the TableDef and from `infrastructure/schema/rig_safeguard_postgresql.sql`, and both state
the two ruled constraints, so the step's subject does not exist and the step must not invent it.

## Changed

- **`0004_...sql`**: all of its statements moved inside one `DO` block behind the existence guard, and the
  file's header states the rule. The step is unchanged on a database that holds the table: same
  `DROP CONSTRAINT IF EXISTS`, then the `rigd` rename, then the two deletes, then the two ruled
  constraints, in the order the ruling's step 5 needed correcting into.
- **`rig_safeguards_migration_integration_test.go`**: `TestTheSixSafeguardsStepIsANoOpWithoutItsTable`
  pins it - the run applies the step, the database is left without the relation, and the case refuses to
  run against a fixture that already holds it. `TestDatabaseInitializerCreateDefaultProject` is the
  end-to-end check of the same thing through a real boot.

## Verified

- Both cases go **red** with the guard removed (`SQLSTATE 42P01`, the same message the boot printed) and
  green with it back; the file was restored byte-identically (sha256
  `567928e7cd94a1d03ef8f328473341234d57c982931ea8d04561cb3cc222b0da` before and after) - so the case
  tests the guard rather than the file's state.
- `go test -count=1 -run 'TestTheSixSafeguards' ./fastmcp/task_management/infrastructure/database/` and
  `-run 'TestDatabaseInitializer' ./fastmcp/` both ok.

## How it was missed, stated plainly

The first pass measured the no-database tree and three PostgreSQL packages, and only the step's own case
on a fixture that builds the table first - so no run in that pass ever reached the step on a database
without it. The class is "a step whose subject may not exist yet", and the check that closes it is a full
`go test ./...` against PostgreSQL, which is what found it.
