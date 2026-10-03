package database

// TestSeatORMMatchesDDL parses the seat_management DDL file next to this test and checks
// that every table's column set equals the set of `db` struct tags on its row struct.
// It needs no database.

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"strings"
	"testing"
)

// seatTableTypes maps each DDL table to the row struct that mirrors it.
var seatTableTypes = map[string]reflect.Type{
	"modules":            reflect.TypeOf(ModuleORM{}),
	"module_versions":    reflect.TypeOf(ModuleVersionORM{}),
	"seat_types":         reflect.TypeOf(SeatTypeORM{}),
	"seat_type_versions": reflect.TypeOf(SeatTypeVersionORM{}),
	"rooms":              reflect.TypeOf(RoomORM{}),
	"seats":              reflect.TypeOf(SeatORM{}),
	"overlays":           reflect.TypeOf(OverlayORM{}),
	"seat_links":         reflect.TypeOf(SeatLinkORM{}),
	"resolved_seats":     reflect.TypeOf(ResolvedSeatORM{}),
}

func TestSeatORMMatchesDDL(t *testing.T) {
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	ddlPath := filepath.Join(filepath.Dir(thisFile), "..", "schema", "seat_management_postgresql.sql")
	raw, err := os.ReadFile(ddlPath)
	if err != nil {
		t.Fatalf("read DDL %s: %v", ddlPath, err)
	}
	tables := parseSeatDDLTables(t, string(raw))
	if len(tables) != len(seatTableTypes) {
		t.Fatalf("DDL has %d tables, %d structs registered", len(tables), len(seatTableTypes))
	}

	for name, typ := range seatTableTypes {
		cols, ok := tables[name]
		if !ok {
			t.Errorf("table %s: struct registered but table missing from DDL", name)
			continue
		}
		ddlCols := set(cols)
		structCols := seatStructColumns(t, name, typ)
		for _, c := range diff(ddlCols, structCols) {
			t.Errorf("table %s: column %q in DDL but no struct tag", name, c)
		}
		for _, c := range diff(structCols, ddlCols) {
			t.Errorf("table %s: struct tag %q but no DDL column", name, c)
		}
	}
	for name := range tables {
		if _, ok := seatTableTypes[name]; !ok {
			t.Errorf("table %s: in DDL but no struct registered", name)
		}
	}
}

// seatStructColumns returns the set of db tag values on typ's fields.
func seatStructColumns(t *testing.T, table string, typ reflect.Type) map[string]bool {
	t.Helper()
	out := map[string]bool{}
	for i := 0; i < typ.NumField(); i++ {
		tag := typ.Field(i).Tag.Get("db")
		if tag == "" {
			t.Errorf("table %s: field %s has no db tag", table, typ.Field(i).Name)
			continue
		}
		if out[tag] {
			t.Errorf("table %s: duplicate db tag %q", table, tag)
		}
		out[tag] = true
	}
	return out
}

// parseSeatDDLTables extracts, for each CREATE TABLE IF NOT EXISTS block, its column names.
// Constraint lines (CONSTRAINT/PRIMARY/UNIQUE/CHECK/FOREIGN) are skipped, including
// constraints whose body spans multiple parenthesised lines.
func parseSeatDDLTables(t *testing.T, ddl string) map[string][]string {
	t.Helper()
	tables := map[string][]string{}
	const header = "CREATE TABLE IF NOT EXISTS "
	var current string
	depth := 0
	for _, raw := range strings.Split(ddl, "\n") {
		line := strings.TrimSpace(raw)
		if current == "" {
			if !strings.HasPrefix(line, header) {
				continue
			}
			rest := strings.TrimSpace(strings.TrimPrefix(line, header))
			name := strings.TrimSpace(strings.TrimSuffix(rest, "("))
			if name == "" || strings.ContainsAny(name, " \t") {
				t.Fatalf("cannot parse table header %q", line)
			}
			current = name
			depth = 0
			continue
		}
		if line == ");" {
			current = ""
			continue
		}
		if line == "" || strings.HasPrefix(line, "--") {
			continue
		}
		if depth > 0 {
			depth += parenDelta(line)
			continue
		}
		field := line
		if i := strings.IndexAny(line, " \t"); i >= 0 {
			field = line[:i]
		}
		field = strings.TrimSuffix(field, ",")
		switch strings.ToUpper(field) {
		case "CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK", "FOREIGN", "EXCLUDE":
			depth += parenDelta(line)
			continue
		default:
			if field == "" {
				t.Fatalf("table %s: empty column name in %q", current, line)
			}
			tables[current] = append(tables[current], field)
			depth += parenDelta(line)
		}
	}
	if current != "" {
		t.Fatalf("unterminated table %s in DDL", current)
	}
	return tables
}

func parenDelta(s string) int {
	return strings.Count(s, "(") - strings.Count(s, ")")
}

func set(items []string) map[string]bool {
	out := make(map[string]bool, len(items))
	for _, it := range items {
		out[it] = true
	}
	return out
}

// diff returns the items in a that are not in b, sorted.
func diff(a, b map[string]bool) []string {
	var out []string
	for k := range a {
		if !b[k] {
			out = append(out, k)
		}
	}
	sort.Strings(out)
	return out
}
