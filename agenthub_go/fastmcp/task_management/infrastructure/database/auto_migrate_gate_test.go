package database

// Schema-safety gate: startup DDL only runs when AUTO_MIGRATE=true. These tests use the
// scripted fake driver (fakedriver_test.go) to record every statement.

import (
	"context"
	"os"
	"strings"
	"testing"
	"time"
)

func fakeAutoMigrateDeps(f *fakeDB) Deps {
	env := map[string]string{
		"DATABASE_TYPE":     "postgresql",
		"DATABASE_HOST":     "h",
		"DATABASE_USER":     "u",
		"DATABASE_PASSWORD": "p",
	}
	return Deps{Getenv: envFrom(env), Sleep: func(time.Duration) {}, Open: f.open}
}

// clearAutoMigrate unsets AUTO_MIGRATE for the test and restores the previous state afterwards.
func clearAutoMigrate(t *testing.T) {
	t.Helper()
	old, had := os.LookupEnv("AUTO_MIGRATE")
	if err := os.Unsetenv("AUTO_MIGRATE"); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if had {
			_ = os.Setenv("AUTO_MIGRATE", old)
			return
		}
		_ = os.Unsetenv("AUTO_MIGRATE")
	})
}

// firstDDL returns the first recorded CREATE/ALTER/DROP statement, or "".
func firstDDL(statements []string) string {
	for _, s := range statements {
		up := strings.ToUpper(strings.TrimSpace(s))
		if strings.HasPrefix(up, "CREATE") || strings.HasPrefix(up, "ALTER") || strings.HasPrefix(up, "DROP") {
			return s
		}
	}
	return ""
}

func TestInitDatabaseNoDDLWithoutAutoMigrate(t *testing.T) {
	clearAutoMigrate(t)
	ResetInstance()
	t.Cleanup(ResetInstance)
	f := newFakeDB()
	if err := InitDatabase(context.Background(), fakeAutoMigrateDeps(f)); err != nil {
		t.Fatal(err)
	}
	if ddl := firstDDL(f.statements); ddl != "" {
		t.Fatalf("AUTO_MIGRATE unset but startup DDL ran: %q (statements: %v)", ddl, f.statements)
	}
}

func TestEnsureAIColumnsRespectsAutoMigrateGate(t *testing.T) {
	clearAutoMigrate(t)
	f := newFakeDB()
	db, _ := f.open("", EngineOptions{})
	if !EnsureAIColumnsExist(context.Background(), db) {
		t.Fatal("expected no-op success when AUTO_MIGRATE is off")
	}
	if len(f.statements) != 0 {
		t.Fatalf("expected no statements, got %v", f.statements)
	}

	t.Setenv("AUTO_MIGRATE", "true")
	f2 := newFakeDB()
	db2, _ := f2.open("", EngineOptions{})
	if !EnsureAIColumnsExist(context.Background(), db2) {
		t.Fatal("expected success when AUTO_MIGRATE is on")
	}
	adds := 0
	for _, s := range f2.statements {
		if strings.HasPrefix(s, "ALTER TABLE") {
			adds++
		}
	}
	if adds != 13 {
		t.Fatalf("adds=%d statements=%v", adds, f2.statements)
	}
}

func TestDBInitializerSkipsInitSQLWithoutAutoMigrate(t *testing.T) {
	clearAutoMigrate(t)
	f := &fakeDB{tables: map[string][]string{}}
	db, _ := f.open("", EngineOptions{})
	inst, err := NewDatabaseInitializer(context.Background(),
		Deps{Getenv: envFrom(map[string]string{}), Sleep: func(time.Duration) {}},
		&DatabaseConfig{Engine: &Engine{DB: db}})
	if err != nil {
		t.Fatal(err)
	}
	if inst.Initialize() {
		t.Fatal("expected false when the schema is missing and AUTO_MIGRATE is off")
	}
	if ddl := firstDDL(f.statements); ddl != "" {
		t.Fatalf("AUTO_MIGRATE unset but init SQL DDL ran: %q (statements: %v)", ddl, f.statements)
	}
}
