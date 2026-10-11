package database

// Row 12444cc2, second half. Running the schema is not the same as HAVING it: Initialize used to
// return true as soon as the statements were accepted, so a database the run did not actually build
// was reported as initialized - and the SQL path only runs when the catalogue reported NO tables, so
// nothing else was going to create them. The required-table check is now part of that path.

import (
	"strings"
	"testing"
)

// TestInitializeVerifiesTheTablesAfterRunningTheSchema drives the whole path over the scripted fake:
// the catalogue is empty, AUTO_MIGRATE is on, every statement of the embedded schema is accepted, and
// the tables are still missing afterwards - which must NOT be reported as initialized.
func TestInitializeVerifiesTheTablesAfterRunningTheSchema(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "true")
	buf := captureLog(t)
	f := &fakeDB{tables: map[string][]string{}} // an empty catalogue, so the SQL path is the one taken
	inst := newFakeInitializer(t, f)

	if inst.Initialize() {
		t.Fatalf("Initialize reported success although the run left no required table behind (%d statements accepted)",
			len(f.statements))
	}
	if inst.Initialized {
		t.Fatal("Initialized was set for a database whose required tables are missing")
	}
	if len(f.statements) == 0 {
		t.Fatal("the init SQL never ran, so this case proves nothing")
	}
	if !strings.Contains(buf.String(), "required tables are not all present") {
		t.Fatalf("the failure is silent: log=%q", buf.String())
	}
}

// TestInitializeRunsNoDDLOnAPopulatedDatabase is a GUARD, not a fail-first case: it passes before and
// after the change, and it is here because the parser fix turned the schema's `DROP TABLE IF EXISTS
// ... CASCADE` statements from chunks the splitter SKIPPED into chunks that run. What keeps that safe
// is the branch order - the DDL is reached only when the catalogue reported no tables - so the order
// is asserted rather than left to a comment. Nothing in this package should ever drop a live table.
func TestInitializeRunsNoDDLOnAPopulatedDatabase(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "true") // the strongest setting: the gate is open and the DDL still must not run
	f := &fakeDB{tables: map[string][]string{"tasks": {"id"}, "subtasks": {"id"}}}
	inst := newFakeInitializer(t, f)

	inst.Initialize()

	// The destructive check comes FIRST. If the branch order ever inverts, the DROP is already
	// recorded, and this is the assertion that should name it rather than the initialization flag.
	for _, s := range f.statements {
		upper := strings.ToUpper(s)
		if strings.Contains(upper, "DROP TABLE") || strings.Contains(upper, "CREATE TABLE") {
			t.Fatalf("a populated database reached the schema DDL: %q (all statements: %v)", s, f.statements)
		}
	}
	if !inst.Initialized {
		t.Fatal("a database with tables was not reported as initialized")
	}
}
