package database

import (
	"bytes"
	"context"
	"log"
	"strings"
	"testing"
)

func captureLog(t *testing.T) *bytes.Buffer {
	t.Helper()
	var buf bytes.Buffer
	previous := log.Writer()
	log.SetOutput(&buf)
	t.Cleanup(func() { log.SetOutput(previous) })
	return &buf
}

func TestMissingTablesListsOnlyAbsentRegisteredTables(t *testing.T) {
	ResetInstance()
	t.Cleanup(ResetInstance)
	f := newFakeDB() // has tasks and subtasks only
	cfg, err := GetInstance(context.Background(), fakeAutoMigrateDeps(f))
	if err != nil {
		t.Fatal(err)
	}
	missing, err := MissingTables(context.Background(), cfg.Engine)
	if err != nil {
		t.Fatal(err)
	}
	have := map[string]bool{}
	for _, name := range missing {
		have[name] = true
	}
	if have["tasks"] || have["subtasks"] || !have["projects"] || len(missing) != len(Tables)-2 {
		t.Fatalf("missing = %v, want every registered table except tasks and subtasks", missing)
	}
}

func TestInitDatabaseNamesMissingTablesWithoutAutoMigrate(t *testing.T) {
	clearAutoMigrate(t)
	ResetInstance()
	t.Cleanup(ResetInstance)
	out := captureLog(t)
	f := newFakeDB()
	if err := InitDatabase(context.Background(), fakeAutoMigrateDeps(f)); err != nil {
		t.Fatalf("a missing schema must not stop startup: %v", err)
	}
	logged := out.String()
	for _, want := range []string{"table(s) missing", "projects", "AUTO_MIGRATE=true"} {
		if !strings.Contains(logged, want) {
			t.Errorf("log %q lacks %q", logged, want)
		}
	}
	if ddl := firstDDL(f.statements); ddl != "" {
		t.Errorf("the check created something: %q", ddl)
	}
}

func TestInitDatabaseWithAutoMigrateDoesNotReportMissingTables(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "true")
	ResetInstance()
	t.Cleanup(ResetInstance)
	out := captureLog(t)
	if err := InitDatabase(context.Background(), fakeAutoMigrateDeps(newFakeDB())); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(out.String(), "missing") {
		t.Errorf("AUTO_MIGRATE creates the schema, yet the log says: %s", out.String())
	}
}

func TestMissingTablesNoticeNamesTablesAndHint(t *testing.T) {
	got := missingTablesNotice([]string{"machines", "rooms"})
	if !strings.Contains(got, "2 table(s) missing: machines, rooms") || !strings.Contains(got, "AUTO_MIGRATE=true") {
		t.Errorf("notice = %q", got)
	}
}
