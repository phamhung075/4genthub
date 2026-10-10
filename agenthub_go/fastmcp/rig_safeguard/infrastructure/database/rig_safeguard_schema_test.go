package database

// TestRigSafeguardSchemaAgreesWithTheORMRow is this table's DDL guard, in the shape seat_management
// uses: the row struct is the source of truth, and the schema file a human applies and the runtime
// TableDef createAll executes must both say the same columns and the same two closed sets.
//
// WHY IT EXISTS: a column in one source and not the other is a schema that differs by CREATION PATH
// - a database made from the file is not the one the runtime builds - and the CHECKs are the parts
// that decide what can be stored at all.
//
// It compares, per the file's and the runtime's CREATE TABLE for rig_safeguards: the column name set
// (against the struct's db tags AND against each other) and the CHECK expressions. Primary-key
// spelling and defaults are deliberately not compared: the file's `PRIMARY KEY (user_id, ...)` line
// and the runtime's are the same statement, while the seat_management parity test records why the
// two sources legitimately differ on defaults.

import (
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"testing"
)

const rigSafeguardSchemaFile = "rig_safeguard_postgresql.sql"

var (
	rigSafeguardCreateTable = regexp.MustCompile(`(?is)create table (?:if not exists )?"?rig_safeguards"?\s*\((.*?)\n\)`)
	rigSafeguardCheck       = regexp.MustCompile(`(?i)check\s*\((.*)\)`)
)

// tableBody is the column-and-constraint body of the file's CREATE TABLE for the table.
func rigSafeguardFileBody(t *testing.T, raw string) string {
	t.Helper()
	match := rigSafeguardCreateTable.FindStringSubmatch(raw)
	if match == nil {
		t.Fatalf("%s has no CREATE TABLE rig_safeguards", rigSafeguardSchemaFile)
	}
	return match[1]
}

func rigSafeguardRuntimeBody(t *testing.T) string {
	t.Helper()
	for _, def := range rigSafeguardTables {
		if def.Name != "rig_safeguards" {
			continue
		}
		for _, stmt := range def.DDL {
			if match := rigSafeguardCreateTable.FindStringSubmatch(stmt); match != nil {
				return match[1]
			}
		}
		t.Fatal("rig_safeguards has no CREATE TABLE in its runtime DDL")
	}
	t.Fatal("rig_safeguards is not registered in rigSafeguardTables")
	return ""
}

// bodyColumns reads the leading identifier of every line that is not a table-level constraint or a
// SQL comment.
func rigSafeguardBodyColumns(body string) []string {
	cols := []string{}
	for _, line := range strings.Split(body, ",\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "--") ||
			strings.HasPrefix(strings.ToUpper(line), "PRIMARY KEY") ||
			strings.HasPrefix(strings.ToUpper(line), "CONSTRAINT") ||
			strings.HasPrefix(strings.ToUpper(line), "UNIQUE") {
			continue
		}
		name, _, _ := strings.Cut(line, " ")
		cols = append(cols, name)
	}
	return cols
}

func rigSafeguardBodyChecks(body string) []string {
	checks := []string{}
	for _, match := range rigSafeguardCheck.FindAllStringSubmatch(body, -1) {
		checks = append(checks, strings.Join(strings.Fields(match[1]), " "))
	}
	return checks
}

// rigSafeguardStructColumns is the row struct's column list, from its db tags.
func rigSafeguardStructColumns(t *testing.T) []string {
	t.Helper()
	typ := reflect.TypeOf(RigSafeguardORM{})
	cols := make([]string, 0, typ.NumField())
	for i := range typ.NumField() {
		field := typ.Field(i)
		tag := field.Tag.Get("db")
		if tag == "" {
			t.Fatalf("field %s carries no db tag", field.Name)
		}
		cols = append(cols, tag)
	}
	return cols
}

func rigSafeguardSorted(values []string) []string {
	out := append([]string{}, values...)
	sort.Strings(out)
	return out
}

func TestRigSafeguardSchemaAgreesWithTheORMRow(t *testing.T) {
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	raw, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "..", "schema", rigSafeguardSchemaFile))
	if err != nil {
		t.Fatalf("read schema file: %v", err)
	}
	fileBody := rigSafeguardFileBody(t, string(raw))
	runtimeBody := rigSafeguardRuntimeBody(t)

	fromStruct := rigSafeguardSorted(rigSafeguardStructColumns(t))
	for _, source := range []struct {
		name string
		body string
	}{{rigSafeguardSchemaFile, fileBody}, {"the runtime TableDef", runtimeBody}} {
		if got := rigSafeguardSorted(rigSafeguardBodyColumns(source.body)); !reflect.DeepEqual(got, fromStruct) {
			t.Errorf("%s columns = %v, want the row struct's %v", source.name, got, fromStruct)
		}
	}

	// The closed sets are stated in both sources, and the test composes them FROM the constants the
	// store and the socket validate against: a state or a safeguard added to the code without the
	// DDL is a failure here rather than a value storable by only one creation path.
	states := []string{StateRunning, StateStopped, StateSilent, StateFailing}
	safeguards := []string{SafeguardCompact, SafeguardWatchdog, SafeguardBridge, SafeguardRigd}
	wantChecks := rigSafeguardSorted([]string{
		"state IN ('" + strings.Join(states, "', '") + "')",
		"safeguard IN ('" + strings.Join(safeguards, "', '") + "')",
	})
	fileChecks := rigSafeguardSorted(rigSafeguardBodyChecks(fileBody))
	if !reflect.DeepEqual(fileChecks, wantChecks) {
		t.Errorf("%s CHECKs = %v, want the ruled sets %v", rigSafeguardSchemaFile, fileChecks, wantChecks)
	}
	runtimeChecks := rigSafeguardSorted(rigSafeguardBodyChecks(runtimeBody))
	if !reflect.DeepEqual(runtimeChecks, fileChecks) {
		t.Errorf("runtime CHECKs = %v, want the schema file's %v", runtimeChecks, fileChecks)
	}
}
