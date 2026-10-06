package database

// TestSeatDDLParity is the second half of the DDL guard. seat_orm_test.go compares the schema
// FILE against the row STRUCTS (column names); this compares the two DDL SOURCES against each
// other — the file a human applies, and the runtime TableDefs createAll executes (which
// ensure_seat_columns.go also has to keep agreeing with).
//
// WHY IT EXISTS: a column in one source and not the other is a schema that differs by creation
// path, and the parts that decide behaviour are not only the column names. A FOREIGN KEY and a
// CHECK are what a rollback, an ALTER or a bad probe trips on — the ck_modules_kind widening is
// the recorded instance of exactly that drift — and nothing else in this package would notice if
// one source carried a constraint and the other did not.
//
// It compares, per table: the column NAME set, the referenced-TABLE multiset, and the CHECK
// expressions. Primary-key and DEFAULT spellings legitimately differ between the two sources
// (`id UUID PRIMARY KEY DEFAULT uuid_generate_v4()` in the file is `id UUID NOT NULL` plus a
// `PRIMARY KEY (id)` line at runtime), so those are deliberately NOT compared.

import (
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"testing"
)

const seatSchemaFile = "seat_management_postgresql.sql"

var (
	seatCreateTableHeader = regexp.MustCompile(`(?i)create table (?:if not exists )?"?([a-z_]+)"?\s*\(`)
	seatReferencesClause  = regexp.MustCompile(`(?i)references\s+"?([a-z_]+)"?\s*\(`)
	seatCheckClause       = regexp.MustCompile(`(?i)check\s*\(`)
)

// TestSeatDDLParity compares every registered table's DDL with the same table in the schema file.
func TestSeatDDLParity(t *testing.T) {
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	raw, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "..", "schema", seatSchemaFile))
	if err != nil {
		t.Fatalf("read schema file: %v", err)
	}
	fileTables := seatFileTableBodies(t, string(raw))

	for _, def := range seatManagementDatabaseTables {
		body, ok := fileTables[def.Name]
		if !ok {
			t.Errorf("table %s: registered at runtime but absent from %s", def.Name, seatSchemaFile)
			continue
		}
		runtimeDDL := ""
		for _, stmt := range def.DDL {
			if seatCreateTableHeader.MatchString(stmt) {
				runtimeDDL = stmt
				break
			}
		}
		if runtimeDDL == "" {
			t.Errorf("table %s: no CREATE TABLE statement in its runtime DDL", def.Name)
			continue
		}
		// The runtime statement is compared from its own text; only the file's needs unwrapping.
		runtimeBody := runtimeDDL[strings.Index(runtimeDDL, "(")+1 : strings.LastIndex(runtimeDDL, ")")]

		if got, want := seatColumnNames(runtimeBody), seatColumnNames(body); !equalSets(got, want) {
			t.Errorf("table %s: columns differ between the schema file and the runtime DDL\n file: %v\nruntime: %v",
				def.Name, want, got)
		}
		if got, want := seatReferences(runtimeBody), seatReferences(body); !equalSets(got, want) {
			t.Errorf("table %s: referenced tables differ between the schema file and the runtime DDL\n file: %v\nruntime: %v",
				def.Name, want, got)
		}
		if got, want := seatChecks(runtimeBody), seatChecks(body); !equalSets(got, want) {
			t.Errorf("table %s: CHECK expressions differ between the schema file and the runtime DDL\n file: %v\nruntime: %v",
				def.Name, want, got)
		}
	}
}

// seatFileTableBodies returns each CREATE TABLE body in the schema file, keyed by table name.
func seatFileTableBodies(t *testing.T, ddl string) map[string]string {
	t.Helper()
	bodies := map[string]string{}
	lines := strings.Split(ddl, "\n")
	for i := range lines {
		trimmed := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(strings.ToLower(trimmed), "create table ") {
			continue
		}
		m := seatCreateTableHeader.FindStringSubmatch(trimmed)
		if m == nil {
			t.Fatalf("cannot parse CREATE TABLE header %q", trimmed)
		}
		name := strings.ToLower(m[1])
		var body []string
		depth := strings.Count(trimmed, "(") - strings.Count(trimmed, ")")
		for j := i + 1; j < len(lines) && depth > 0; j++ {
			line := strings.TrimSpace(lines[j])
			depth += strings.Count(line, "(") - strings.Count(line, ")")
			if depth <= 0 {
				break
			}
			if line != "" && !strings.HasPrefix(line, "--") {
				body = append(body, line)
			}
		}
		bodies[name] = strings.Join(body, "\n")
	}
	return bodies
}

// seatColumnNames returns the column names of a CREATE TABLE body: a top-level item that is not a
// table constraint (CONSTRAINT/PRIMARY/UNIQUE/CHECK/FOREIGN/EXCLUDE) starts with its name.
func seatColumnNames(body string) []string {
	var out []string
	for _, item := range seatTopLevelItems(body) {
		fields := strings.Fields(item)
		if len(fields) == 0 {
			continue
		}
		head := strings.ToLower(strings.Trim(fields[0], `"`))
		switch head {
		case "constraint", "primary", "unique", "check", "foreign", "exclude":
			continue
		}
		out = append(out, head)
	}
	return out
}

// seatReferences returns the referenced table of every REFERENCES clause, as a sorted multiset.
func seatReferences(body string) []string {
	var out []string
	for _, m := range seatReferencesClause.FindAllStringSubmatch(body, -1) {
		out = append(out, strings.ToLower(m[1]))
	}
	sort.Strings(out)
	return out
}

// seatChecks returns every CHECK expression, normalised (lower case, no whitespace), so the two
// sources can spell the same set of values with different line breaks.
func seatChecks(body string) []string {
	var out []string
	for _, loc := range seatCheckClause.FindAllStringIndex(body, -1) {
		open := strings.Index(body[loc[0]:], "(")
		if open < 0 {
			continue
		}
		start := loc[0] + open
		depth := 0
		for i := start; i < len(body); i++ {
			switch body[i] {
			case '(':
				depth++
			case ')':
				depth--
				if depth == 0 {
					out = append(out, strings.Join(strings.Fields(strings.ToLower(body[loc[0]:i+1])), " "))
					i = len(body)
				}
			}
		}
	}
	sort.Strings(out)
	return out
}

// seatTopLevelItems splits a CREATE TABLE body on the commas that are not inside parentheses.
func seatTopLevelItems(body string) []string {
	var (
		items []string
		depth int
		start int
	)
	for i := range len(body) {
		switch body[i] {
		case '(':
			depth++
		case ')':
			depth--
		case ',':
			if depth == 0 {
				items = append(items, strings.TrimSpace(body[start:i]))
				start = i + 1
			}
		}
	}
	if tail := strings.TrimSpace(body[start:]); tail != "" {
		items = append(items, tail)
	}
	return items
}

// equalSets reports whether two slices hold the same values, order ignored, duplicates counted.
func equalSets(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	as := append([]string(nil), a...)
	bs := append([]string(nil), b...)
	sort.Strings(as)
	sort.Strings(bs)
	for i := range as {
		if as[i] != bs[i] {
			return false
		}
	}
	return true
}
