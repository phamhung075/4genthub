package database

// The init SQL is an ASSET the binary must carry. Reading it by a source path is what failed on a
// fresh database inside the distroless image (row b231a84b), so these tests hold the properties that
// failure broke: a false return is never silent, and what the initializer runs is what the binary
// holds rather than what happens to sit next to a source file.

import (
	"context"
	"errors"
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

// TestExecuteInitSQLFileLogsTheUnreadableAsset is the not-a-directory case: the parent of the
// resolved path is a FILE, which is the shape the distroless image has for /agenthub and therefore
// the shape in which the container's read fails. It must return false, touch no database, and say so.
func TestExecuteInitSQLFileLogsTheUnreadableAsset(t *testing.T) {
	buf := captureLog(t)
	f := &fakeDB{tables: map[string][]string{}}
	inst := newFakeInitializer(t, f)

	if ok := inst.ExecuteInitSQLFile("init_schema_postgresql.sql/nested.sql"); ok {
		t.Fatal("ExecuteInitSQLFile returned true for an asset it cannot read")
	}
	if len(f.statements) != 0 {
		t.Fatalf("an unreadable asset still touched the database: %v", f.statements)
	}
	if !strings.Contains(buf.String(), "nested.sql") {
		t.Fatalf("the read failure is silent: log=%q", buf.String())
	}
}

// TestExecuteInitSQLFileLogsAFailedStatement is the same silence on the execution path.
func TestExecuteInitSQLFileLogsAFailedStatement(t *testing.T) {
	buf := captureLog(t)
	f := &fakeDB{tables: map[string][]string{}}
	f.failExec = func(string) error { return errors.New("injected exec failure") }
	inst := newFakeInitializer(t, f)

	if ok := inst.ExecuteInitSQLFile("init_schema_postgresql.sql"); ok {
		t.Fatal("ExecuteInitSQLFile returned true although a statement failed")
	}
	if !strings.Contains(buf.String(), "injected exec failure") {
		t.Fatalf("the statement failure is silent: log=%q", buf.String())
	}
}
