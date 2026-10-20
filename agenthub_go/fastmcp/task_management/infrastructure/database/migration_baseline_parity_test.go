package database_test

// The parity guard for the T12 fold: migrations/0001_baseline.sql against the TableDef registry.
//
// WHY IT EXISTS. The baseline was GENERATED from the registry, so the two can drift apart silently:
// a column added to a TableDef that the baseline is not regenerated for is a schema that differs by
// creation path. Nothing else in this package would notice - createAll reads the TableDefs, the
// runner applies the file, and neither asks the other.
//
// THE REGISTRY IS BUILT BY init(). taskdb.Tables is ONE slice every package appends its own set to in
// init() (task_event_tables.go, models_auth.go, email_token_repository.go, seat_tables.go,
// rig_safeguard_tables.go), and ProductionTables (models_prod.go) is deliberately outside it. This
// file therefore carries the SAME blank imports the generator (tmp_foldgen) does - without them the
// binary registers only the base package's tables, and the guard would report every seat, room and auth
// table as "in the baseline but not registered", which is the guard failing to see the registry
// rather than the registry being wrong. Importing them is legal here because this is the EXTERNAL test
// package: those packages import taskdb, which an internal (package database) test file could not do.
//
// THE COMPARISON, per table: the column-NAME set, the referenced-TABLE multiset and the CHECK
// expressions, normalised for whitespace and case - the approach fastmcp/seat_management's
// seat_ddl_parity_test.go uses, and for the same reason (a FOREIGN KEY or a CHECK is what a rollback
// or an ALTER trips on, and the two sources legitimately differ in layout). Primary-key and DEFAULT
// spellings are deliberately NOT compared there and are not compared here.

import (
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"

	// The imports are the point: each package's init() appends its TableDefs to the one registry.
	_ "agenthub/fastmcp/auth/infrastructure/database"
	_ "agenthub/fastmcp/auth/infrastructure/repositories"
	_ "agenthub/fastmcp/room_safeguard/infrastructure/database"
	_ "agenthub/fastmcp/seat_management/infrastructure/database"
)

const parityBaselineMigrationFile = "0001_baseline.sql"

var (
	baselineCreateTableHeader = regexp.MustCompile(`(?i)create table (?:if not exists )?"?([a-z_]+)"?\s*\(`)
	baselineReferencesClause  = regexp.MustCompile(`(?i)references\s+"?([a-z_]+)"?\s*\(`)
	baselineCheckClause       = regexp.MustCompile(`(?i)check\s*\(`)
)

// TestBaselineMatchesEveryRegisteredTableDef holds the registry to the baseline, table by table. A
// table added to a TableDef set and not regenerated makes this fail; so does a hand-edited baseline.
func TestBaselineMatchesEveryRegisteredTableDef(t *testing.T) {
	raw := parityReadBaselineSQL(t)

	// The baseline only ever builds a schema, so it may not tear one down or alter one: the init SQL's
	// DROP TABLE IF EXISTS is the recorded instance of what that costs.
	parityAssertBaselineHasNoDropOrAlter(t, raw)
	fileTables := baselineTableBodies(t, raw)

	registered := map[string]bool{}
	var order []database.TableDef
	for _, set := range [][]database.TableDef{database.Tables, database.ProductionTables} {
		for _, def := range set {
			if registered[def.Name] {
				t.Errorf("table %s is registered twice across Tables and ProductionTables", def.Name)
				continue
			}
			registered[def.Name] = true
			order = append(order, def)
		}
	}
	if len(order) == 0 {
		t.Fatal("no TableDef is registered, so this guard measured nothing")
	}
	t.Logf("searched: %d registered table(s) (%d aggregate, %d production), %d in %s",
		len(order), len(database.Tables), len(database.ProductionTables), len(fileTables), parityBaselineMigrationFile)

	for _, def := range order {
		body, ok := fileTables[def.Name]
		if !ok {
			t.Errorf("table %s: registered at runtime but absent from %s - regenerate the baseline",
				def.Name, parityBaselineMigrationFile)
			continue
		}
		runtimeBody := runtimeCreateTableBody(t, def)
		if got, want := baselineColumnNames(runtimeBody), baselineColumnNames(body); !equalStringSets(got, want) {
			t.Errorf("table %s: columns differ between the baseline and the runtime DDL\n file: %v\nruntime: %v",
				def.Name, want, got)
		}
		if got, want := baselineReferences(runtimeBody), baselineReferences(body); !equalStringSets(got, want) {
			t.Errorf("table %s: referenced tables differ between the baseline and the runtime DDL\n file: %v\nruntime: %v",
				def.Name, want, got)
		}
		if got, want := baselineChecks(runtimeBody), baselineChecks(body); !equalStringSets(got, want) {
			t.Errorf("table %s: CHECK expressions differ between the baseline and the runtime DDL\n file: %v\nruntime: %v",
				def.Name, want, got)
		}
		// An enum CREATE TYPE must precede the table whose columns use it, exactly as createAll emits
		// it: the CREATE TABLE fails on an unknown type otherwise, and the baseline is applied alone.
		for _, c := range def.Columns {
			if c.EnumName == "" {
				continue
			}
			typeAt := strings.Index(raw, "CREATE TYPE "+c.EnumName+" ")
			tableAt := strings.Index(raw, "CREATE TABLE "+def.Name+" (")
			if typeAt < 0 {
				t.Errorf("table %s column %s: enum %s has no CREATE TYPE in the baseline",
					def.Name, c.Name, c.EnumName)
				continue
			}
			if tableAt >= 0 && typeAt > tableAt {
				t.Errorf("table %s: enum %s is created AFTER the table that uses it", def.Name, c.EnumName)
			}
		}
	}
	// A CREATE TABLE in the baseline that no TableDef registers is drift in the other direction.
	for name := range fileTables {
		if !registered[name] {
			t.Errorf("table %s: present in %s but no TableDef registers it", name, parityBaselineMigrationFile)
		}
	}
}

// parityReadBaselineSQL returns the embedded baseline's text. It is read from the source tree rather than
// through LoadMigrations so a diff shows the file a human edits, which is the artifact this guards.
func parityReadBaselineSQL(t *testing.T) string {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	raw, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "migrations", parityBaselineMigrationFile))
	if err != nil {
		t.Fatalf("read %s: %v", parityBaselineMigrationFile, err)
	}
	return string(raw)
}

// parityAssertBaselineHasNoDropOrAlter checks the file's SQL, ignoring comment lines so the header's prose
// cannot hide one.
func parityAssertBaselineHasNoDropOrAlter(t *testing.T, raw string) {
	t.Helper()
	for i, line := range strings.Split(raw, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "--") {
			continue
		}
		up := strings.ToUpper(line)
		if strings.Contains(up, "DROP ") || strings.Contains(up, "ALTER ") {
			t.Errorf("%s line %d is a DROP or ALTER, which a baseline may never carry: %s",
				parityBaselineMigrationFile, i+1, strings.TrimSpace(line))
		}
	}
}

// baselineTableBodies returns each CREATE TABLE body in the baseline, keyed by lower-case table name.
// A duplicate CREATE TABLE is reported: the guard holds each registered table to appearing ONCE.
func baselineTableBodies(t *testing.T, ddl string) map[string]string {
	t.Helper()
	bodies := map[string]string{}
	lines := strings.Split(ddl, "\n")
	for i := range lines {
		trimmed := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(strings.ToLower(trimmed), "create table ") {
			continue
		}
		m := baselineCreateTableHeader.FindStringSubmatch(trimmed)
		if m == nil {
			t.Fatalf("cannot parse CREATE TABLE header %q", trimmed)
		}
		name := strings.ToLower(m[1])
		if _, dup := bodies[name]; dup {
			t.Errorf("table %s appears more than once in %s", name, parityBaselineMigrationFile)
			continue
		}
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

// runtimeCreateTableBody returns the body of a TableDef's CREATE TABLE statement.
func runtimeCreateTableBody(t *testing.T, def database.TableDef) string {
	t.Helper()
	for _, stmt := range def.DDL {
		if baselineCreateTableHeader.MatchString(stmt) {
			return stmt[strings.Index(stmt, "(")+1 : strings.LastIndex(stmt, ")")]
		}
	}
	t.Errorf("table %s: no CREATE TABLE statement in its runtime DDL", def.Name)
	return ""
}

// baselineColumnNames returns the column names of a CREATE TABLE body: a top-level item that is not a
// table constraint (CONSTRAINT/PRIMARY/UNIQUE/CHECK/FOREIGN/EXCLUDE) starts with its name.
func baselineColumnNames(body string) []string {
	var out []string
	for _, item := range baselineTopLevelItems(body) {
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

// baselineReferences returns the referenced table of every REFERENCES clause, as a sorted multiset.
func baselineReferences(body string) []string {
	var out []string
	for _, m := range baselineReferencesClause.FindAllStringSubmatch(body, -1) {
		out = append(out, strings.ToLower(m[1]))
	}
	sort.Strings(out)
	return out
}

// baselineChecks returns every CHECK expression, normalised (lower case, whitespace collapsed), so the
// two sources can spell the same constraint with different line breaks.
func baselineChecks(body string) []string {
	var out []string
	for _, loc := range baselineCheckClause.FindAllStringIndex(body, -1) {
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

// baselineTopLevelItems splits a CREATE TABLE body on the commas that are not inside parentheses.
func baselineTopLevelItems(body string) []string {
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

// equalStringSets reports whether two slices hold the same values, order ignored, duplicates counted.
func equalStringSets(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	as, bs := append([]string(nil), a...), append([]string(nil), b...)
	sort.Strings(as)
	sort.Strings(bs)
	for i := range as {
		if as[i] != bs[i] {
			return false
		}
	}
	return true
}
