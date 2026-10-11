package database

import (
	"reflect"
	"strings"
	"testing"
	"testing/fstest"
)

// The set's order is the contract the runner applies, so the loader's ordering is the first thing
// that must hold: filename order, with the .sql suffix stripped for the recorded name, and files
// that are not migrations ignored.
func TestLoadMigrationsOrdersByFilenameAndNamesEachStepByItsFile(t *testing.T) {
	fsys := fstest.MapFS{
		"migrations/0010_ten.sql": {Data: []byte("SELECT 10")},
		"migrations/0002_two.sql": {Data: []byte("SELECT 2")},
		"migrations/0001_one.sql": {Data: []byte("SELECT 1")},
		"migrations/README.md":    {Data: []byte("not a migration")},
	}
	set, err := loadMigrations(fsys)
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, m := range set {
		names = append(names, m.Name)
	}
	// 0010 sorts after 0002 because the names are zero-padded, which is the rule the directory's
	// README states: the order is the filename's, not the file's arrival.
	want := []string{"0001_one", "0002_two", "0010_ten"}
	if !reflect.DeepEqual(names, want) {
		t.Fatalf("names %v, want %v", names, want)
	}
	if set[1].SQL != "SELECT 2" {
		t.Errorf("step %q carries %q, want its own file's body", set[1].Name, set[1].SQL)
	}
}

func TestValidateSetRefusesWhatTheRunnerCannotApplyUnambiguously(t *testing.T) {
	valid := []Migration{{Name: "0001_a", SQL: "SELECT 1"}, {Name: "0002_b", SQL: "SELECT 2"}}
	if err := validateSet(valid); err != nil {
		t.Fatalf("a valid set was refused: %v", err)
	}
	cases := map[string]struct {
		set  []Migration
		want string // the part of the message a reader needs to fix it
	}{
		"a duplicate name": {
			[]Migration{{Name: "0001_a", SQL: "SELECT 1"}, {Name: "0001_a", SQL: "SELECT 2"}},
			"appears twice",
		},
		"a name out of order": {
			[]Migration{{Name: "0002_b", SQL: "SELECT 2"}, {Name: "0001_a", SQL: "SELECT 1"}},
			"out of order",
		},
		"a step with no name": {
			[]Migration{{SQL: "SELECT 1"}},
			"has no name",
		},
		"a step with no SQL": {
			[]Migration{{Name: "0001_a", SQL: "   \n"}},
			"has no SQL",
		},
	}
	for what, c := range cases {
		err := validateSet(c.set)
		if err == nil {
			t.Errorf("%s was accepted", what)
			continue
		}
		if !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: the refusal names the wrong thing: %v", what, err)
		}
	}
}

// The embedded set is the one a boot applies, so it is the set that has to be well-formed - today
// empty, and a misnamed or blank file the moment one is added.
func TestTheEmbeddedSetIsWellFormed(t *testing.T) {
	set, err := LoadMigrations()
	if err != nil {
		t.Fatalf("the embedded set does not load: %v", err)
	}
	if err := validateSet(set); err != nil {
		t.Fatalf("the embedded set is not applicable: %v", err)
	}
}
