package database

// TestRoomSafeguardSchemaAgreesWithTheORMRow is this table's DDL guard, in the shape seat_management
// uses: the row struct is the source of truth, and the schema file a human applies and the runtime
// TableDef createAll executes must both say the same columns and the same two closed sets.
//
// WHY IT EXISTS: a column in one source and not the other is a schema that differs by CREATION PATH
// - a database made from the file is not the one the runtime builds - and the CHECKs are the parts
// that decide what can be stored at all.
//
// It compares, per the file's and the runtime's CREATE TABLE for room_safeguards: the column name set
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

const roomSafeguardSchemaFile = "room_safeguard_postgresql.sql"

var (
	roomSafeguardCreateTable = regexp.MustCompile(`(?is)create table (?:if not exists )?"?room_safeguards"?\s*\((.*?)\n\)`)
	roomSafeguardCheck       = regexp.MustCompile(`(?i)check\s*\((.*)\)`)
)

// tableBody is the column-and-constraint body of the file's CREATE TABLE for the table.
func roomSafeguardFileBody(t *testing.T, raw string) string {
	t.Helper()
	match := roomSafeguardCreateTable.FindStringSubmatch(raw)
	if match == nil {
		t.Fatalf("%s has no CREATE TABLE room_safeguards", roomSafeguardSchemaFile)
	}
	return match[1]
}

func roomSafeguardRuntimeBody(t *testing.T) string {
	t.Helper()
	for _, def := range roomSafeguardTables {
		if def.Name != "room_safeguards" {
			continue
		}
		for _, stmt := range def.DDL {
			if match := roomSafeguardCreateTable.FindStringSubmatch(stmt); match != nil {
				return match[1]
			}
		}
		t.Fatal("room_safeguards has no CREATE TABLE in its runtime DDL")
	}
	t.Fatal("room_safeguards is not registered in roomSafeguardTables")
	return ""
}

// bodyColumns reads the leading identifier of every line that is not a table-level constraint or a
// SQL comment.
func roomSafeguardBodyColumns(body string) []string {
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

func roomSafeguardBodyChecks(body string) []string {
	checks := []string{}
	for _, match := range roomSafeguardCheck.FindAllStringSubmatch(body, -1) {
		checks = append(checks, strings.Join(strings.Fields(match[1]), " "))
	}
	return checks
}

// roomSafeguardStructColumns is the row struct's column list, from its db tags.
func roomSafeguardStructColumns(t *testing.T) []string {
	t.Helper()
	typ := reflect.TypeOf(RoomSafeguardORM{})
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

func roomSafeguardSorted(values []string) []string {
	out := append([]string{}, values...)
	sort.Strings(out)
	return out
}

func TestRoomSafeguardSchemaAgreesWithTheORMRow(t *testing.T) {
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	raw, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "..", "schema", roomSafeguardSchemaFile))
	if err != nil {
		t.Fatalf("read schema file: %v", err)
	}
	fileBody := roomSafeguardFileBody(t, string(raw))
	runtimeBody := roomSafeguardRuntimeBody(t)

	fromStruct := roomSafeguardSorted(roomSafeguardStructColumns(t))
	for _, source := range []struct {
		name string
		body string
	}{{roomSafeguardSchemaFile, fileBody}, {"the runtime TableDef", runtimeBody}} {
		if got := roomSafeguardSorted(roomSafeguardBodyColumns(source.body)); !reflect.DeepEqual(got, fromStruct) {
			t.Errorf("%s columns = %v, want the row struct's %v", source.name, got, fromStruct)
		}
	}

	// The closed sets are stated in both sources, and the test composes them FROM the constants the
	// store and the socket validate against: a state or a safeguard added to the code without the
	// DDL is a failure here rather than a value storable by only one creation path. The scope rule is
	// composed the same way, from the machine-scoped names, so a name moving between the two scopes
	// cannot leave the CHECK behind.
	states := []string{StateRunning, StateStopped, StateSilent, StateFailing}
	safeguards := []string{SafeguardCompact, SafeguardWatchdog, SafeguardMessages, SafeguardRoomGuard, SafeguardBridge, SafeguardAgent}
	machineScoped := []string{SafeguardBridge, SafeguardAgent}
	wantChecks := roomSafeguardSorted([]string{
		"state IN ('" + strings.Join(states, "', '") + "')",
		"safeguard IN ('" + strings.Join(safeguards, "', '") + "')",
		"CASE WHEN safeguard IN ('" + strings.Join(machineScoped, "', '") + "') THEN room = '' ELSE length(room) BETWEEN 1 AND 255 END",
	})
	fileChecks := roomSafeguardSorted(roomSafeguardBodyChecks(fileBody))
	if !reflect.DeepEqual(fileChecks, wantChecks) {
		t.Errorf("%s CHECKs = %v, want the ruled sets %v", roomSafeguardSchemaFile, fileChecks, wantChecks)
	}
	runtimeChecks := roomSafeguardSorted(roomSafeguardBodyChecks(runtimeBody))
	if !reflect.DeepEqual(runtimeChecks, fileChecks) {
		t.Errorf("runtime CHECKs = %v, want the schema file's %v", runtimeChecks, fileChecks)
	}
}
