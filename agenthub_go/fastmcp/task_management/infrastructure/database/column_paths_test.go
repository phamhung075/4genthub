package database_test

// The guard the lead's ruling asks for, in the recorded-migration form rather than a declared
// coverage list beside each ensurer.
//
// THE INVARIANT IT MEASURES. A column reaches a database by one of three paths: the fresh-create
// DDL (createAll executes each TableDef's DDL, but only for tables the database LACKS), a
// registered ensurer (RunColumnEnsurers, which is the only path that reaches an EXISTING table),
// or a recorded migration step (Runner.Apply, run last). A column in a TableDef that none of them
// reaches is the incident this row exists for: production answered status unhealthy and
// manage_task update died on column "user_seq" does not exist, because the column had been added
// to the definition and no path had been built for a database that already held the table.
//
// WHY IT DOES NOT ASK THE ENSURERS. It cannot: ColumnEnsurers is []ColumnEnsurer - opaque function
// values - so no test can ask one which columns it covers. That is the reason this guard compares
// the SCHEMA the whole path produces against the registry instead of trusting declared metadata.
//
// WHAT IT SEARCHED, printed on every run whether or not it finds anything, because an instrument
// that returns nothing must say what it looked at: the number of TableDefs, registered columns,
// registered ensurers and recorded migration steps, plus the tables registered by other packages.
//
// WHAT IT CANNOT SEE, and this is the honest limit, not a TODO:
//   - A column added to a TableDef AFTER a live database was created. This fixture is a FRESH
//     database, so createAll builds such a column from the DDL and it looks reachable. Catching
//     that shape needs a recorded baseline - a folded 0001 that says what the schema was when the
//     database was made - so that a column newer than the baseline can be required to appear in a
//     migration step or an ensurer. The migration set is empty today (migrations/ holds only its
//     README), so there is no baseline and this instrument cannot make that comparison.
//   - WHICH path provided a column. It proves a column reached the schema, never that an ensurer
//     or a migration step was the thing that carried it.
//
// It therefore fails on a registered table the boot path does not create, and on a registered
// column the boot path leaves out - the self-inconsistency between Tables and the DDL - and says
// plainly that the existing-database half is still unchecked.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestEveryTableDefColumnHasAPath(t *testing.T) {
	// newMigrationRunnerEnv builds a throwaway database through the production path -
	// CreateTables: createAll, EnsureAIColumnsExist, the ensurers, then the recorded migrations -
	// and skips loudly when AGENTHUB_TEST_PG_URL is unset. Reusing it keeps this guard honest
	// about what it measures: the schema that path leaves behind.
	_, db := newMigrationRunnerEnv(t)
	ctx := context.Background()
	engine := &database.Engine{DB: db}

	set, err := database.LoadMigrations()
	if err != nil {
		t.Fatalf("the recorded migration set could not be read, so this guard cannot name it: %v", err)
	}
	columns := 0
	for _, def := range database.Tables {
		columns += len(def.Columns)
	}
	t.Logf("searched: %d registered table(s), %d registered column(s), %d registered ensurer(s), %d recorded migration step(s)",
		len(database.Tables), columns, len(database.ColumnEnsurers), len(set))

	missing, err := database.MissingTables(ctx, engine)
	if err != nil {
		t.Fatalf("the missing-table check could not run, so the count below would be meaningless: %v", err)
	}
	for _, name := range missing {
		t.Errorf("%s is registered but the boot path did not create it: a fresh database cannot hold its columns, so none of them has a path", name)
	}

	drift, err := database.ColumnDrift(ctx, engine)
	if err != nil {
		t.Fatalf("the column check could not run, so the count below would be meaningless: %v", err)
	}
	for _, d := range drift {
		for _, col := range d.MissingColumns {
			t.Errorf("%s.%s is registered but the boot path left it out of the schema, so no path reaches it", d.Table, col)
		}
	}

	if len(missing) == 0 && len(drift) == 0 {
		t.Logf("measured: 0 registered column(s) without a path; the existing-database half stays unchecked - "+
			"no baseline is recorded (the migration set holds %d step(s)), so a column added after a live database "+
			"was created is indistinguishable here from one that was always there", len(set))
	}
}
