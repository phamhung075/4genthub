package database_test

// Integration tests for the migration runner against a real PostgreSQL: applying an ordered set,
// recording each applied step in the same transaction as its effect, and the two behaviours the
// record depends on - a second run applying nothing, and a failed step recording nothing at all.
//
// They need AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skip loudly without it, like the
// other DB-gated cases in this package.

import (
	"context"
	"database/sql"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// newMigrationRunnerEnv builds a throwaway database carrying the production schema - so
// applied_migrations exists, exactly as it does on a boot - and returns a session manager over it.
func newMigrationRunnerEnv(t *testing.T) (*database.SessionManager, *sql.DB) {
	t.Helper()
	dsn := newTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2, PoolRecycle: 60})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db, URL: dsn}}
	if err := cfg.CreateTables(context.Background()); err != nil {
		t.Fatal(err)
	}
	return database.NewSessionManager(cfg), db
}

func recordedMigrations(t *testing.T, sessions *database.SessionManager) []string {
	t.Helper()
	var names []string
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, `SELECT migration_name FROM applied_migrations ORDER BY migration_name`)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var n string
			if err := rows.Scan(&n); err != nil {
				return err
			}
			names = append(names, n)
		}
		return rows.Err()
	}); err != nil {
		t.Fatal(err)
	}
	return names
}

func probeRows(t *testing.T, sessions *database.SessionManager) int {
	t.Helper()
	count := 0
	if err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT count(*) FROM migration_runner_probe`).Scan(&count)
	}); err != nil {
		t.Fatal(err)
	}
	return count
}

func relationExists(t *testing.T, db *sql.DB, name string) bool {
	t.Helper()
	exists := false
	if err := db.QueryRowContext(context.Background(),
		`SELECT to_regclass($1) IS NOT NULL`, name).Scan(&exists); err != nil {
		t.Fatal(err)
	}
	return exists
}

func TestApplyRecordsEachStepAndASecondRunAppliesNothing(t *testing.T) {
	sessions, db := newMigrationRunnerEnv(t)
	ctx := context.Background()
	// The throwaway database is built by the registry alone, which does NOT create the production
	// tables - so this case also covers the runner meeting a database that has no ledger yet.
	if relationExists(t, db, "applied_migrations") {
		t.Fatal("this database already has the ledger, so the case cannot show the runner creating it")
	}
	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{
		{Name: "0001_probe_table", SQL: `CREATE TABLE migration_runner_probe (id INTEGER PRIMARY KEY)`},
		{Name: "0002_probe_row", SQL: `INSERT INTO migration_runner_probe (id) VALUES (1)`},
	}}

	applied, err := runner.Apply(ctx)
	if err != nil {
		t.Fatalf("the first run failed: %v", err)
	}
	if !relationExists(t, db, "applied_migrations") {
		t.Error("the ledger table does not exist after a run that recorded steps: the writer must own its bookkeeping")
	}
	if want := []string{"0001_probe_table", "0002_probe_row"}; !reflect.DeepEqual(applied, want) {
		t.Fatalf("the first run reported %v, want %v", applied, want)
	}
	if got := recordedMigrations(t, sessions); !reflect.DeepEqual(got, applied) {
		t.Fatalf("applied_migrations holds %v, want the steps that ran, %v", got, applied)
	}
	if got := probeRows(t, sessions); got != 1 {
		t.Fatalf("the probe table holds %d rows after the first run, want 1", got)
	}

	applied, err = runner.Apply(ctx)
	if err != nil {
		t.Fatalf("the second run failed: %v", err)
	}
	if len(applied) != 0 {
		t.Fatalf("the second run applied %v: a recorded step must not run again", applied)
	}
	if got := probeRows(t, sessions); got != 1 {
		t.Fatalf("the probe table holds %d rows after the second run, want still 1: the insert ran twice", got)
	}
	if got := recordedMigrations(t, sessions); len(got) != 2 {
		t.Fatalf("applied_migrations holds %v after the second run, want the same two names", got)
	}
}

func TestAFailedStepRecordsNothingAndLeavesNoneOfItsOwnEffect(t *testing.T) {
	sessions, db := newMigrationRunnerEnv(t)
	ctx := context.Background()
	// The DO block does both halves inside ONE statement: it creates a table and then raises, so the
	// table's absence afterwards is the transaction rolling back with the step, not a tidy-up.
	const doomed = `DO $$ BEGIN CREATE TABLE migration_runner_doomed (id INTEGER); PERFORM 1 / 0; END $$`
	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{
		{Name: "0001_probe_table", SQL: `CREATE TABLE migration_runner_probe (id INTEGER PRIMARY KEY)`},
		{Name: "0002_doomed", SQL: doomed},
	}}

	applied, err := runner.Apply(ctx)
	if err == nil {
		t.Fatal("a step whose SQL fails was applied without an error")
	}
	if !strings.Contains(err.Error(), "0002_doomed") {
		t.Errorf("the failure does not name the step that failed: %v", err)
	}
	if want := []string{"0001_probe_table"}; !reflect.DeepEqual(applied, want) {
		t.Fatalf("the run reported %v, want %v: the step before the failure stays applied and recorded", applied, want)
	}
	if got := recordedMigrations(t, sessions); !reflect.DeepEqual(got, []string{"0001_probe_table"}) {
		t.Fatalf("applied_migrations holds %v, want only the step that succeeded", got)
	}
	if relationExists(t, db, "migration_runner_doomed") {
		t.Error("the failed step's table exists: its statements did not roll back together with it")
	}
	if !relationExists(t, db, "migration_runner_probe") {
		t.Error("the succeeded step's table is gone: one step's failure rolled back another step's work")
	}
}

func TestMarkBaselineRecordsAStepWithoutRunningIt(t *testing.T) {
	sessions, db := newMigrationRunnerEnv(t)
	ctx := context.Background()
	runner := &database.Runner{Sessions: sessions, Set: []database.Migration{
		{Name: "0001_baseline", SQL: `CREATE TABLE migration_runner_baseline_probe (id INTEGER)`},
	}}

	marked, err := runner.MarkBaseline(ctx, "0001_baseline")
	if err != nil {
		t.Fatalf("marking the baseline failed: %v", err)
	}
	if want := []string{"0001_baseline"}; !reflect.DeepEqual(marked, want) {
		t.Fatalf("marked %v, want %v", marked, want)
	}
	if relationExists(t, db, "migration_runner_baseline_probe") {
		t.Error("marking a step EXECUTED its SQL: a baseline marks a database that already has the schema")
	}
	if got := recordedMigrations(t, sessions); !reflect.DeepEqual(got, []string{"0001_baseline"}) {
		t.Fatalf("applied_migrations holds %v, want the marked baseline", got)
	}

	applied, err := runner.Apply(ctx)
	if err != nil {
		t.Fatalf("the run after the mark failed: %v", err)
	}
	if len(applied) != 0 {
		t.Fatalf("the run after the mark applied %v: a marked step is done and must not be re-run", applied)
	}

	if _, err := runner.MarkBaseline(ctx, "0009_not_in_the_set"); err == nil {
		t.Error("marking a name this binary's set does not contain was accepted: a typo would look like a successful stamp")
	}
	if got := recordedMigrations(t, sessions); !reflect.DeepEqual(got, []string{"0001_baseline"}) {
		t.Fatalf("applied_migrations holds %v after the refused mark, want only the baseline", got)
	}
}
