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
