package database

// Row 8ee196db. A FAILED catalogue read and an EMPTY DATABASE were the same value: ExistingTables
// swallowed the error from tableNames and returned the empty set, and Initialize read an empty
// catalogue as licence to run a schema whose first statements are `DROP TABLE IF EXISTS ... CASCADE`.
// The parser fix (c595f9cc) is what turned those statements from skipped into executed, so a misread
// that used to be inert now drops every table it can see. CANNOT TELL must refuse the DDL, not unlock
// it - the schema's own DROP statements are the reason the distinction is load-bearing.

import (
	"errors"
	"strings"
	"testing"
)

func TestInitializeRefusesTheDDLWhenTheCatalogueCannotBeRead(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "true") // the gate is open: only the unreadable catalogue can refuse here
	buf := captureLog(t)
	f := &fakeDB{
		tables: map[string][]string{},
		failTablesRead: func(string) error {
			return errors.New("catalogue read failed: relation information_schema.tables is not visible under this search_path")
		},
	}
	inst := newFakeInitializer(t, f)

	if inst.Initialize() {
		t.Fatal("Initialize reported success although the catalogue could not be read")
	}
	if inst.Initialized {
		t.Fatal("Initialized was set from a catalogue that could not be read")
	}
	for _, s := range f.statements {
		if strings.Contains(strings.ToUpper(s), "DROP TABLE") {
			t.Fatalf("an unread catalogue unlocked the DDL: %q", s)
		}
	}
	if !strings.Contains(buf.String(), "could not read the existing tables") {
		t.Fatalf("the refusal is silent: log=%q", buf.String())
	}
}

// TestVerifyTableStructureRefusesAnUnreadCatalogue keeps the second caller honest: it is red at the
// parent too, on the SILENCE rather than on the return value - the parent already answered false here,
// because a swallowed error meant "no tables" and the required ones then looked missing, but it said
// nothing about why. A structure that cannot be read must neither be reported as verified nor fail
// quietly.
func TestVerifyTableStructureRefusesAnUnreadCatalogue(t *testing.T) {
	buf := captureLog(t)
	f := &fakeDB{
		tables: map[string][]string{},
		failTablesRead: func(string) error {
			return errors.New("catalogue read failed")
		},
	}
	inst := newFakeInitializer(t, f)

	if inst.VerifyTableStructure() {
		t.Fatal("VerifyTableStructure reported a verified structure it could not read")
	}
	if !strings.Contains(buf.String(), "could not read the existing tables") {
		t.Fatalf("the refusal is silent: log=%q", buf.String())
	}
}
