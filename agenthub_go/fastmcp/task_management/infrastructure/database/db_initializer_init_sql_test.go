package database

// The init SQL is an ASSET the binary must carry. Reading it by a source path is what failed on a fresh
// database inside the distroless image (row b231a84b), so the schema is embedded and these tests hold
// the properties that failure broke: the asset creates the tables Initialize verifies, the statements
// reach the database in one committed transaction, and a false return says why.

import (
	"context"
	"errors"
	"regexp"
	"strings"
	"testing"
	"time"
)

// newFakeInitializer builds an initializer over the scripted fake driver.
func newFakeInitializer(t *testing.T, f *fakeDB) *DatabaseInitializer {
	t.Helper()
	db, err := f.open("", EngineOptions{})
	if err != nil {
		t.Fatal(err)
	}
	inst, err := NewDatabaseInitializer(context.Background(),
		Deps{Getenv: envFrom(map[string]string{}), Sleep: func(time.Duration) {}},
		&DatabaseConfig{Engine: &Engine{DB: db}})
	if err != nil {
		t.Fatal(err)
	}
	return inst
}

// createsTable reports whether sqlText creates the named table. The word boundary matters: `labels`
// must not be satisfied by `task_labels`, and every name passed here is a real table name.
func createsTable(sqlText, table string) bool {
	return regexp.MustCompile(`CREATE TABLE[^;]*\b` + regexp.QuoteMeta(table) + `\b`).MatchString(sqlText)
}

// TestEmbeddedInitSQLCreatesEveryRequiredTable guards the asset itself: the schema the binary carries
// must create each table VerifyTableStructure demands, so a truncated or stale embed cannot pass as a
// good one and leave a fresh database half-built. It needs no server - the check is on the bytes.
func TestEmbeddedInitSQLCreatesEveryRequiredTable(t *testing.T) {
	if len(databaseInitializerInitSQL) == 0 {
		t.Fatal("the embedded init SQL is empty")
	}
	schema := string(databaseInitializerInitSQL)
	for _, table := range databaseInitializerRequiredTables {
		if !createsTable(schema, table) {
			t.Errorf("the embedded schema does not create %s, which VerifyTableStructure requires", table)
		}
	}
}

// TestExecuteInitSQLFileRunsTheEmbeddedStatements replaces the source-path case this file was opened
// on: what runs must be the bytes the binary carries, in one committed transaction. The scripted fake
// driver records each statement, so no server is needed. The set of statements that reaches the driver
// is asserted against the asset itself in TestExecuteInitSQLFileExecutesEveryCreateTableTheAssetCarries.
func TestExecuteInitSQLFileRunsTheEmbeddedStatements(t *testing.T) {
	f := &fakeDB{tables: map[string][]string{}}
	inst := newFakeInitializer(t, f)

	if !inst.ExecuteInitSQLFile() {
		t.Fatal("ExecuteInitSQLFile returned false for the embedded schema")
	}
	if last := f.statements[len(f.statements)-1]; last != "COMMIT" {
		t.Fatalf("the schema did not run in one committed transaction, last statement %q: %v", last, f.statements)
	}
	schema := string(databaseInitializerInitSQL)
	executed := 0
	for _, statement := range f.statements {
		switch statement {
		case "BEGIN", "COMMIT", "ROLLBACK":
			continue
		}
		executed++
		if !strings.Contains(schema, statement) {
			t.Fatalf("a statement that is not in the embedded schema reached the driver: %q", statement)
		}
	}
	if executed == 0 {
		t.Fatal("no statement from the embedded schema reached the driver")
	}
	t.Logf("the embedded schema sent %d statements to the driver in one transaction", executed)
}

// TestExecuteInitSQLFileExecutesEveryCreateTableTheAssetCarries is the fail-first case for the chunk
// rule. The rule the port inherited - split on ";", then SKIP a chunk that starts with "--" or "/*" -
// discards the statement together with its comment, and every table in this schema is preceded by a
// `-- Table: X` line, so a run over a fresh database created nothing while reporting success. The
// expectation is DERIVED from the asset, so a statement the asset carries but the run drops fails
// here, and a table added to the schema is covered without editing this test.
func TestExecuteInitSQLFileExecutesEveryCreateTableTheAssetCarries(t *testing.T) {
	wanted := regexp.MustCompile(`(?i)CREATE TABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)`).
		FindAllStringSubmatch(string(databaseInitializerInitSQL), -1)
	if len(wanted) == 0 {
		t.Fatal("the embedded asset carries no CREATE TABLE statement")
	}
	f := &fakeDB{tables: map[string][]string{}}
	inst := newFakeInitializer(t, f)

	if !inst.ExecuteInitSQLFile() {
		t.Fatal("ExecuteInitSQLFile returned false for the embedded schema")
	}
	executed := strings.Join(f.statements, "\n")
	for _, match := range wanted {
		if !createsTable(executed, match[1]) {
			t.Errorf("the schema never executed the CREATE TABLE for %s", match[1])
		}
	}
}

// TestExecuteInitSQLFileLogsAFailedStatement holds the other half of row b231a84b: a false return is
// never silent.
func TestExecuteInitSQLFileLogsAFailedStatement(t *testing.T) {
	buf := captureLog(t)
	f := &fakeDB{tables: map[string][]string{}}
	f.failExec = func(string) error { return errors.New("injected exec failure") }
	inst := newFakeInitializer(t, f)

	if ok := inst.ExecuteInitSQLFile(); ok {
		t.Fatal("ExecuteInitSQLFile returned true although a statement failed")
	}
	if !strings.Contains(buf.String(), "injected exec failure") {
		t.Fatalf("the statement failure is silent: log=%q", buf.String())
	}
}
