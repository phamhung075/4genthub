package database_test

// TestSchemaMatchesGoDefinitions is the guard that holds Go's runtime table definitions against the
// MIGRATION SET, which is the schema's source of truth. The runner applies those files to every
// database, so a table that exists as a TableDef and not as a migration is a table the runner never
// creates - the shape the owner's stage 1 exists to remove.
//
// IT IS AN EXTERNAL TEST PACKAGE ON PURPOSE. taskdb.Tables is a package-level union that every
// feature package appends to in its own init (task_management, auth, seat_management, rig_safeguard),
// and the server sees the union only because it imports them all. A test inside the package cannot
// reach them - importing a package that imports taskdb would be a cycle - so the imports below are
// the point of the file: with them present, this test sees exactly the set createAll walks, and
// without them it would quietly see a fifth of the schema and pass while the rest drifted.
//
// It reads the EMBEDDED set through taskdb.LoadMigrations, so it needs no database and no file path,
// and it compares the same four dimensions its sibling guard in seat_management compares
// (TestSeatDDLParity): the column NAME set, the referenced-TABLE multiset, the CHECK expressions and
// the column DEFAULTs. Those are the axes that decide behaviour when a rollback, an ALTER or a probe
// meets the two sources, and they are exactly the axes on which the seat schema had already drifted.
//
// WHAT THIS MEANS BY "COMPLETE", because it is the word the acceptance turns on: every table in
// taskdb.Tables must be created by some step of the set. The 0001 baseline is the step that carries
// the tables a live database already has (migrations/README.md), and it is that step now: the file was
// generated from the runtime registry, and this test is the guard that keeps the two equal from here
// on. It was shown failing FIRST, on every registered table, by perturbing a Go definition - a schema
// guard never seen to fail is what the rig spent a night finding. A later step may narrow the baseline
// again (0003 drops the two progress columns the carry empties); that narrowing is each step's own
// subject, covered by its own test, not by this guard.
//
// A DELIBERATE BOUNDARY, so the next reader does not think it is an omission: taskdb.ProductionTables
// is NOT in taskdb.Tables - nothing appends it to the runtime set - so the six production tables this
// guard does not see are exactly the six the runtime does not create. Whether the 0001 baseline
// carries them is the dump comparison's question (what a live database actually holds), not this
// test's.
//
// The demonstration the acceptance requires is the other direction: perturb a Go definition - add a
// column to a TableDef's DDL, or register a table without its baseline statement - and this test must
// go red. A schema guard never seen to fail is what the rig spent a night finding.

import (
	"regexp"
	"sort"
	"strings"
	"testing"

	taskdb "agenthub/fastmcp/task_management/infrastructure/database"

	// The registerers. Each one appends its own set to taskdb.Tables in its init, which is what makes
	// the union the server creates equal to the set this test reads.
	_ "agenthub/fastmcp/auth/infrastructure/database"
	_ "agenthub/fastmcp/auth/infrastructure/repositories"
	_ "agenthub/fastmcp/rig_safeguard/infrastructure/database"
	_ "agenthub/fastmcp/seat_management/infrastructure/database"
)

var (
	goDefCreateTableHeader = regexp.MustCompile(`(?i)create table (?:if not exists )?"?([a-z_]+)"?\s*\(`)
	goDefReferencesClause  = regexp.MustCompile(`(?i)references\s+"?([a-z_]+)"?\s*\(`)
	goDefCheckClause       = regexp.MustCompile(`(?i)check\s*\(`)
)

// TestSchemaMatchesGoDefinitions compares every registered table's DDL with the step that creates it.
func TestSchemaMatchesGoDefinitions(t *testing.T) {
	steps, err := taskdb.LoadMigrations()
	if err != nil {
		t.Fatalf("load the embedded migration set: %v", err)
	}
	if len(steps) == 0 {
		t.Fatal("the embedded migration set is empty: the runner would create nothing")
	}
	if len(taskdb.Tables) == 0 {
		t.Fatal("the runtime registry is empty: the registerers did not run, so this guard would pass vacuously")
	}

	created := map[string]string{}
	order := []string{}
	for _, step := range steps {
		bodies, err := goDefStepTableBodies(step)
		if err != nil {
			t.Fatalf("%v", err)
		}
		for _, name := range goDefSortedKeys(bodies) {
			if _, seen := created[name]; !seen {
				order = append(order, name)
			}
			created[name] = bodies[name]
		}
	}

	for _, def := range taskdb.Tables {
		body, ok := created[def.Name]
		if !ok {
			t.Errorf("table %s: a Go definition no migration creates (the 0001 baseline is the step that must carry it; the set is %v)",
				def.Name, strings.Join(goDefStepNames(steps), ", "))
			continue
		}
		runtimeDDL := ""
		for _, stmt := range def.DDL {
			if goDefCreateTableHeader.MatchString(stmt) {
				runtimeDDL = stmt
				break
			}
		}
		if runtimeDDL == "" {
			t.Errorf("table %s: no CREATE TABLE statement in its runtime DDL", def.Name)
			continue
		}
		// The runtime statement is compared from its own text; the migration's body was unwrapped by
		// goDefStepTableBodies.
		runtimeBody := runtimeDDL[strings.Index(runtimeDDL, "(")+1 : strings.LastIndex(runtimeDDL, ")")]

		if got, want := goDefColumnNames(runtimeBody), goDefColumnNames(body); !goDefEqualSets(got, want) {
			t.Errorf("table %s: columns differ between the migration set and the runtime DDL\n migrations: %v\n runtime:    %v",
				def.Name, want, got)
		}
		if got, want := goDefReferences(runtimeBody), goDefReferences(body); !goDefEqualSets(got, want) {
			t.Errorf("table %s: referenced tables differ between the migration set and the runtime DDL\n migrations: %v\n runtime:    %v",
				def.Name, want, got)
		}
		if got, want := goDefChecks(runtimeBody), goDefChecks(body); !goDefEqualSets(got, want) {
			t.Errorf("table %s: CHECK expressions differ between the migration set and the runtime DDL\n migrations: %v\n runtime:    %v",
				def.Name, want, got)
		}
		if got, want := goDefDefaults(runtimeBody), goDefDefaults(body); !goDefEqualMaps(got, want) {
			t.Errorf("table %s: column DEFAULTs differ between the migration set and the runtime DDL\n migrations: %v\n runtime:    %v",
				def.Name, want, got)
		}
	}

	// The other direction, so a baseline can never carry a table Go has stopped defining.
	for _, name := range order {
		if _, ok := goDefTableByName(name); !ok {
			t.Errorf("table %s: a migration creates it but no Go definition registers it", name)
		}
	}
}

// goDefStepTableBodies returns each CREATE TABLE body in one step, keyed by lower-cased table name.
// A statement whose header cannot be parsed is a failure, not a skip: an unreadable schema statement
// is precisely what a guard must not pass over.
func goDefStepTableBodies(step taskdb.Migration) (map[string]string, error) {
	bodies := map[string]string{}
	lines := strings.Split(step.SQL, "\n")
	for i := range lines {
		trimmed := strings.TrimSpace(lines[i])
		if !strings.HasPrefix(strings.ToLower(trimmed), "create table ") {
			continue
		}
		m := goDefCreateTableHeader.FindStringSubmatch(trimmed)
		if m == nil {
			return nil, &goDefParseError{step: step.Name, text: trimmed}
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
	return bodies, nil
}

// goDefParseError is what an unparsable statement returns, so the test can name the step and the line.
type goDefParseError struct {
	step string
	text string
}

func (e *goDefParseError) Error() string {
	return "step " + e.step + ": cannot parse CREATE TABLE header " + e.text
}

// goDefTableByName reports whether a name is registered in the runtime set.
func goDefTableByName(name string) (taskdb.TableDef, bool) {
	for _, def := range taskdb.Tables {
		if def.Name == name {
			return def, true
		}
	}
	return taskdb.TableDef{}, false
}

// goDefStepNames lists the set's step names, for a failure message that says what did run.
func goDefStepNames(steps []taskdb.Migration) []string {
	out := make([]string, 0, len(steps))
	for _, s := range steps {
		out = append(out, s.Name)
	}
	return out
}

// goDefSortedKeys sorts a body map's keys, so the comparison's error output is stable.
func goDefSortedKeys(m map[string]string) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// goDefColumnNames returns the column names of a CREATE TABLE body: a top-level item that is not a
// table constraint (CONSTRAINT/PRIMARY/UNIQUE/CHECK/FOREIGN/EXCLUDE) starts with its name.
func goDefColumnNames(body string) []string {
	var out []string
	for _, item := range goDefTopLevelItems(body) {
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

// goDefReferences returns the referenced table of every REFERENCES clause, as a sorted multiset.
func goDefReferences(body string) []string {
	var out []string
	for _, m := range goDefReferencesClause.FindAllStringSubmatch(body, -1) {
		out = append(out, strings.ToLower(m[1]))
	}
	sort.Strings(out)
	return out
}

// goDefChecks returns every CHECK expression, normalised (lower case, single-spaced), so the two
// sources can spell the same set of values with different line breaks.
func goDefChecks(body string) []string {
	var out []string
	for _, loc := range goDefCheckClause.FindAllStringIndex(body, -1) {
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

// goDefDefaults returns each column's DEFAULT expression, normalised, keyed by column name. A column
// with no DEFAULT is absent.
func goDefDefaults(body string) map[string]string {
	out := map[string]string{}
	for _, item := range goDefTopLevelItems(body) {
		fields := strings.Fields(item)
		if len(fields) == 0 {
			continue
		}
		name := strings.ToLower(strings.Trim(fields[0], `"`))
		switch name {
		case "constraint", "primary", "unique", "check", "foreign", "exclude":
			continue
		}
		lower := strings.ToLower(item)
		idx := strings.Index(lower, " default ")
		if idx < 0 {
			continue
		}
		expr := strings.Join(strings.Fields(lower[idx+len(" default "):]), " ")
		out[name] = strings.Trim(expr, " ,")
	}
	return out
}

// goDefEqualSets reports whether two slices hold the same values, order ignored, duplicates counted.
func goDefEqualSets(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	sortedA := append([]string(nil), a...)
	sortedB := append([]string(nil), b...)
	sort.Strings(sortedA)
	sort.Strings(sortedB)
	for i := range sortedA {
		if sortedA[i] != sortedB[i] {
			return false
		}
	}
	return true
}

// goDefEqualMaps reports whether two string maps hold the same keys and values.
func goDefEqualMaps(a, b map[string]string) bool {
	if len(a) != len(b) {
		return false
	}
	for k, v := range a {
		if b[k] != v {
			return false
		}
	}
	return true
}

// goDefTopLevelItems splits a CREATE TABLE body on the commas that are not inside parentheses.
func goDefTopLevelItems(body string) []string {
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
