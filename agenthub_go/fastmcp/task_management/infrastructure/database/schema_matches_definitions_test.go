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
// THE REGISTRY THIS GUARD READS IS THE UNION, and the merge is what made that necessary rather than
// optional: `taskdb.ProductionTables` is NOT in `taskdb.Tables` (nothing appends it to the runtime
// set), and the 0001 baseline that arrived from main was folded from BOTH - 41 aggregate tables plus
// the six production ones - so a guard that read only the aggregate reported all six as drift ("a
// migration creates it but no Go definition registers it") on the merged tree. Both directions read
// the same union now, which also means the six get their columns, CHECKs, DEFAULTs and indexes
// compared like any other table.
//
// The demonstration the acceptance requires is the other direction: perturb a Go definition - add a
// column to a TableDef's DDL, or register a table without its baseline statement - and this test must
// go red. A schema guard never seen to fail is what the rig spent a night finding.

import (
	"os"
	"path/filepath"
	"regexp"
	"runtime"
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
	indexed := map[string][]string{}
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
		stepIndexes, err := goDefStepIndexes(step)
		if err != nil {
			t.Fatalf("%v", err)
		}
		for table, statements := range stepIndexes {
			// The same index may be created by more than one step - 0001 for an empty catalogue, 0005
			// for one that predates its column - and an index is its name and definition, not the
			// number of steps that mention it.
			for _, statement := range statements {
				if !containsString(indexed[table], statement) {
					indexed[table] = append(indexed[table], statement)
				}
			}
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
		// Indexes are the axes a rollback, an ALTER and a probe do NOT see: the column set can be
		// identical while a UNIQUE index that holds an invariant is gone, and a unique index IS the
		// invariant for the seat and team tables (uq_overlays_target, uq_team_members_one_owner). The
		// registry declares them in the same DDL slice as the CREATE TABLE, so losing one from the
		// baseline keeps every other comparison here green.
		if got, want := goDefIndexStatements(def.DDL), indexed[def.Name]; !goDefEqualSets(got, want) {
			t.Errorf("table %s: indexes differ between the migration set and the runtime DDL\n migrations: %v\n runtime:    %v",
				def.Name, want, got)
		}
	}

	// The other direction, so a baseline can never carry a table Go has stopped defining.
	for _, name := range order {
		if _, ok := goDefTableByName(name); !ok {
			t.Errorf("table %s: a migration creates it but no Go definition registers it", name)
		}
	}
	// ... and the same for an index whose table nobody registers.
	for _, table := range goDefSortedKeys(indexed) {
		if _, ok := goDefTableByName(table); !ok {
			t.Errorf("table %s: a migration creates indexes for it but no Go definition registers it", table)
		}
	}
}

// schemaInventoryTableCount is today's registry size: taskdb.Tables (the aggregate union) plus
// taskdb.ProductionTables (deliberately outside it). It is asserted because every property below is
// vacuous over a partial registry - without the four blank imports above the registry is 27 of these
// 49 tables (Tables 21, ProductionTables 6) and both properties pass while 22 tables go unchecked.
const schemaInventoryTableCount = 49

// TestSchemaInventoryPinsTenancyAndCascades is gate G2: two properties of the registry that nothing
// else checks, each pinned by a golden file that names live columns in both directions.
//
// PROPERTY 1 (tenancy): a table that carries a user_id declares it NOT NULL, unless
// testdata/user_id_nullable.txt records it with a reason (table:reason). Two tables are nullable
// today, and neither is a defect: templates is the global template library (created_by is NOT NULL),
// and email_tokens exists before an account does. A NEW nullable user_id therefore needs a reviewed
// line rather than passing silently.
//
// PROPERTY 2 (cascade set): every column with a non-empty OnDelete has a line in
// testdata/schema_fks.txt (table:column:on_delete:owner, owner = the referenced table), and every
// line names a live cascade column with its on_delete and owner. task_events deliberately has no
// cascade - the application layer cascades - so its absence is asserted by the golden file rather
// than left to the silence a reader would have to interpret.
//
// The goldens are review artifacts, not a compatibility layer: a line is valid only while the column
// it names exists, and removing a cascade without removing its line fails this test too.
func TestSchemaInventoryPinsTenancyAndCascades(t *testing.T) {
	registry := goDefRegistry()
	if len(registry) != schemaInventoryTableCount {
		t.Fatalf("the registry is %d tables, want %d: a property tested over part of the side-effect union passes vacuously. If a table was legitimately added, update this count and the files under testdata/",
			len(registry), schemaInventoryTableCount)
	}

	nullable := goDefReadGolden(t, filepath.Join("testdata", "user_id_nullable.txt"), 2)
	seenNullable := map[string]bool{}
	for _, line := range nullable.lines {
		table, reason := line.fields[0], line.fields[1]
		if seenNullable[table] {
			t.Errorf("%s:%d: table %s is listed twice", nullable.path, line.number, table)
		}
		seenNullable[table] = true
		if strings.TrimSpace(reason) == "" {
			t.Errorf("%s:%d: table %s records no reason; a nullable user_id needs one", nullable.path, line.number, table)
		}
		def, ok := goDefTableByName(table)
		if !ok {
			t.Errorf("%s:%d: table %s is not registered in the 49-table union", nullable.path, line.number, table)
			continue
		}
		column, ok := goDefColumn(def, "user_id")
		if !ok || !column.Nullable {
			t.Errorf("%s:%d: table %s has no nullable user_id, so the line is stale", nullable.path, line.number, table)
		}
	}
	for _, def := range registry {
		column, ok := goDefColumn(def, "user_id")
		if !ok || !column.Nullable {
			continue
		}
		if !seenNullable[def.Name] {
			t.Errorf("table %s: user_id is nullable and testdata/user_id_nullable.txt records no reason; a nullable tenancy column is a reviewed decision, not a default", def.Name)
		}
	}

	fks := goDefReadGolden(t, filepath.Join("testdata", "schema_fks.txt"), 4)
	type fkKey struct{ table, column string }
	pinned := map[fkKey]goDefGoldenLine{}
	for _, line := range fks.lines {
		key := fkKey{line.fields[0], line.fields[1]}
		if previous, dup := pinned[key]; dup {
			t.Errorf("%s:%d: %s:%s is pinned twice (first at line %d)", fks.path, line.number, key.table, key.column, previous.number)
		}
		pinned[key] = line
	}
	for _, def := range registry {
		for _, column := range def.Columns {
			if column.OnDelete == "" {
				continue
			}
			line, ok := pinned[fkKey{def.Name, column.Name}]
			if !ok {
				t.Errorf("table %s column %s: OnDelete %q is not pinned in testdata/schema_fks.txt; a cascade is a reviewed decision", def.Name, column.Name, column.OnDelete)
				continue
			}
			if line.fields[2] != column.OnDelete {
				t.Errorf("%s:%d: %s:%s pins on_delete %s, the registry says %s", fks.path, line.number, def.Name, column.Name, line.fields[2], column.OnDelete)
			}
			if owner := goDefReferencedTable(column.ForeignKey); line.fields[3] != owner {
				t.Errorf("%s:%d: %s:%s pins owner %s, the foreign key references %s", fks.path, line.number, def.Name, column.Name, line.fields[3], owner)
			}
		}
	}
	for _, line := range fks.lines {
		def, ok := goDefTableByName(line.fields[0])
		if !ok {
			t.Errorf("%s:%d: table %s is not registered in the 49-table union", fks.path, line.number, line.fields[0])
			continue
		}
		column, ok := goDefColumn(def, line.fields[1])
		if !ok {
			t.Errorf("%s:%d: table %s has no column %s, so the line is stale", fks.path, line.number, line.fields[0], line.fields[1])
			continue
		}
		if column.OnDelete != line.fields[2] {
			t.Errorf("%s:%d: %s:%s pins on_delete %s, the registry has %q, so the line is stale",
				fks.path, line.number, line.fields[0], line.fields[1], line.fields[2], column.OnDelete)
		}
		if owner := goDefReferencedTable(column.ForeignKey); owner != line.fields[3] {
			t.Errorf("%s:%d: %s:%s pins owner %s, the foreign key references %q, so the line is stale",
				fks.path, line.number, line.fields[0], line.fields[1], line.fields[3], owner)
		}
	}
}

// goDefGolden is one parsed golden file and the line number each entry came from.
type goDefGolden struct {
	path  string
	lines []goDefGoldenLine
}

type goDefGoldenLine struct {
	number int
	fields []string
}

// goDefReadGolden reads a golden file of `fieldCount` colon-separated fields per line. Blank lines
// and lines starting with # are skipped; a line with the wrong field count is a failure, not a skip.
func goDefReadGolden(t *testing.T, path string, fieldCount int) goDefGolden {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	golden := goDefGolden{path: path}
	for index, text := range strings.Split(string(data), "\n") {
		trimmed := strings.TrimSpace(text)
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		fields := strings.Split(trimmed, ":")
		if len(fields) != fieldCount {
			t.Fatalf("%s:%d: %d colon-separated fields, want %d: %q", path, index+1, len(fields), fieldCount, trimmed)
		}
		golden.lines = append(golden.lines, goDefGoldenLine{number: index + 1, fields: fields})
	}
	return golden
}

// goDefColumn returns one column of a table definition.
func goDefColumn(def taskdb.TableDef, name string) (taskdb.ColumnDef, bool) {
	for _, column := range def.Columns {
		if column.Name == name {
			return column, true
		}
	}
	return taskdb.ColumnDef{}, false
}

// goDefReferencedTable returns the table a ForeignKey ("table.column") points at.
func goDefReferencedTable(foreignKey string) string {
	table, _, _ := strings.Cut(foreignKey, ".")
	return table
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

// goDefStepIndexes returns every CREATE INDEX statement in one step, keyed by the table it is ON. The
// table is read from the statement rather than from the "-- table" comment above it, because the
// statement is what the database executes.
func goDefStepIndexes(step taskdb.Migration) (map[string][]string, error) {
	indexes := map[string][]string{}
	for _, statement := range goDefStatements(step.SQL) {
		stmt := strings.TrimSpace(statement)
		if !goDefLooksLikeIndex(stmt) {
			continue
		}
		_, _, table, ok := goDefIndexParts(stmt)
		if !ok {
			return nil, &goDefParseError{step: step.Name, text: stmt}
		}
		indexes[table] = append(indexes[table], goDefNormalizeStatement(stmt))
	}
	return indexes, nil
}

// goDefStatements splits one step's SQL into WHOLE statements, the same unit the runtime side is
// parsed in. A statement ends at its terminating semicolon and carries every line it spans, so a
// CREATE INDEX written across two lines is read with its column list instead of as a truncated first
// line. Line comments, single-quoted literals and parentheses are all respected while scanning, so a
// semicolon inside any of them does not end a statement. Comments matter twice over: the migration's
// prose carries apostrophes ("registry's"), and a comment whose text were scanned as SQL would open a
// bogus literal that swallows every statement after it - the migration's own header comment does
// exactly that, so a comment's text is dropped, not scanned. A final statement with no trailing
// semicolon is whatever text remains, returned even if it never balanced so a truncated statement
// fails the guard rather than disappearing from it.
func goDefStatements(sql string) []string {
	var statements []string
	var b strings.Builder
	depth := 0
	inQuote := false
	inComment := false
	for i := range len(sql) {
		c := sql[i]
		if inComment {
			if c == '\n' {
				inComment = false
				b.WriteByte(c)
			}
			continue
		}
		if !inQuote && c == '-' && i+1 < len(sql) && sql[i+1] == '-' {
			inComment = true
			continue
		}
		switch {
		case c == '\'':
			inQuote = !inQuote
		case !inQuote && c == '(':
			depth++
		case !inQuote && c == ')' && depth > 0:
			depth--
		case !inQuote && c == ';' && depth == 0:
			statements = append(statements, b.String())
			b.Reset()
			continue
		}
		b.WriteByte(c)
	}
	if rest := strings.TrimSpace(b.String()); rest != "" {
		statements = append(statements, rest)
	}
	return statements
}

// goDefIndexStatements returns the CREATE INDEX statements of one runtime table's DDL slice, which is
// the same slice that carries its CREATE TABLE.
func goDefIndexStatements(ddl []string) []string {
	out := []string{}
	for _, stmt := range ddl {
		if goDefLooksLikeIndex(strings.TrimSpace(stmt)) {
			out = append(out, goDefNormalizeStatement(stmt))
		}
	}
	return out
}

// goDefLooksLikeIndex says whether a statement claims to be a CREATE INDEX, so a statement that claims
// it and cannot be read is a failure rather than a statement nobody looked at.
func goDefLooksLikeIndex(stmt string) bool {
	lower := strings.ToLower(strings.Join(strings.Fields(stmt), " "))
	return strings.HasPrefix(lower, "create index ") || strings.HasPrefix(lower, "create unique index ")
}

// goDefIndexParts reads the three fields the comparison groups an index by: whether it is UNIQUE, its
// name and the table it is ON. It parses words rather than matching a pattern on purpose: the first
// attempt used one regex whose optional pieces sat next to optional quotes, and it silently matched
// nothing on the runtime statements - a guard that reports "no indexes here" for a file full of them is
// worse than no guard, because it reads as agreement. A fixed shape read word by word cannot do that.
func goDefIndexParts(stmt string) (unique bool, name, table string, ok bool) {
	words := strings.Fields(strings.ToLower(stmt))
	if len(words) < 4 || words[0] != "create" {
		return false, "", "", false
	}
	i := 1
	if words[i] == "unique" {
		unique = true
		i++
	}
	if i >= len(words) || words[i] != "index" {
		return false, "", "", false
	}
	i++
	if i+2 < len(words) && words[i] == "if" && words[i+1] == "not" && words[i+2] == "exists" {
		i += 3
	}
	// <name> ON <table>
	if i+2 >= len(words) || words[i+1] != "on" {
		return false, "", "", false
	}
	name = strings.Trim(words[i], `"`)
	table = strings.Trim(words[i+2], `"`)
	if name == "" || table == "" {
		return false, "", "", false
	}
	return unique, name, table, true
}

// goDefNormalizeStatement makes the two sources' text comparable. They write the same statement and
// differ in exactly the ways they must: the runtime DDL carries no IF NOT EXISTS and no semicolon, and
// the migration carries both, because createAll runs before the runner on this path and the step has to
// be re-runnable. Whitespace is layout and letter case in the SQL WORDS is layout, so both are
// collapsed - the words, the column list, the uniqueness and the WHERE clause that remain are the
// index. The literal inside single quotes is NOT folded: for a partial index that text is the
// invariant's scope, so `WHERE role = 'owner'` and `WHERE role = 'Owner'` are different indexes.
func goDefNormalizeStatement(s string) string {
	s = goDefFoldOutsideLiterals(strings.Join(strings.Fields(s), " "))
	s = strings.ReplaceAll(s, "if not exists ", "")
	return strings.TrimSpace(strings.TrimSuffix(strings.TrimSpace(s), ";"))
}

// goDefFoldOutsideLiterals lower-cases a statement's letter case while leaving the text inside
// single-quoted string literals exactly as written. SQL's words are case-insensitive layout, but a
// string literal's case is its value, and folding it would let two behaviourally different indexes
// normalise to the same text.
func goDefFoldOutsideLiterals(s string) string {
	var b strings.Builder
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] != '\'' {
			continue
		}
		b.WriteString(strings.ToLower(s[start:i]))
		end := strings.IndexByte(s[i+1:], '\'')
		if end < 0 {
			// An unterminated literal: leave the remainder as written.
			b.WriteString(s[i:])
			return b.String()
		}
		end += i + 1 // the closing quote's index
		b.WriteString(s[i : end+1])
		i = end
		start = i + 1
	}
	b.WriteString(strings.ToLower(s[start:]))
	return b.String()
}

// goDefParseError is what an unparsable statement returns, so the test can name the step and the line.
type goDefParseError struct {
	step string
	text string
}

func (e *goDefParseError) Error() string {
	return "step " + e.step + ": cannot parse CREATE TABLE header " + e.text
}

// goDefRegistry is the runtime registry this guard holds the set to: the aggregate `Tables` plus
// `ProductionTables`, which is the same union main's baseline was folded from.
func goDefRegistry() []taskdb.TableDef {
	out := make([]taskdb.TableDef, 0, len(taskdb.Tables)+len(taskdb.ProductionTables))
	out = append(out, taskdb.Tables...)
	out = append(out, taskdb.ProductionTables...)
	return out
}

// goDefTableByName reports whether a name is registered in the runtime set.
func goDefTableByName(name string) (taskdb.TableDef, bool) {
	for _, def := range goDefRegistry() {
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
func goDefSortedKeys[V any](m map[string]V) []string {
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

// baselineMigrationFile is the step whose own text the baseline-scoped checks below read.
const baselineMigrationFile = "0001_baseline.sql"

// TestTheBaselineStepOnlyCreatesAndItsTypesPrecedeTheirTables holds `0001_baseline.sql` ITSELF to the
// three properties the set-wide guard above cannot see, because a LATER step is allowed to do what the
// baseline never may. The baseline is the schema as it already exists, so it must never drop or alter
// anything; every enum type it uses must be created BEFORE the table that uses it, because the baseline
// is the step a database receives alone; and no table may be registered twice across the two runtime
// sets. A later step MAY narrow the baseline - `0003` drops the two progress columns the carry empties
// - so this test is scoped to the file and cannot be read as forbidding that.
func TestTheBaselineStepOnlyCreatesAndItsTypesPrecedeTheirTables(t *testing.T) {
	raw := readBaselineSQL(t)
	assertBaselineHasNoDropOrAlter(t, raw)

	registered := map[string]bool{}
	var order []taskdb.TableDef
	for _, set := range [][]taskdb.TableDef{taskdb.Tables, taskdb.ProductionTables} {
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
	for _, def := range order {
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
}

// readBaselineSQL returns the baseline's text from the SOURCE TREE rather than through the embedded
// set, so a failure names the file a human edits.
func readBaselineSQL(t *testing.T) string {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	raw, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "migrations", baselineMigrationFile))
	if err != nil {
		t.Fatalf("read %s: %v", baselineMigrationFile, err)
	}
	return string(raw)
}

// assertBaselineHasNoDropOrAlter checks the file's SQL, ignoring comment lines so the header's prose
// cannot hide one.
func assertBaselineHasNoDropOrAlter(t *testing.T, raw string) {
	t.Helper()
	for i, line := range strings.Split(raw, "\n") {
		if strings.HasPrefix(strings.TrimSpace(line), "--") {
			continue
		}
		up := strings.ToUpper(line)
		if strings.Contains(up, "DROP ") || strings.Contains(up, "ALTER ") {
			t.Errorf("%s line %d is a DROP or ALTER, which a baseline may never carry: %s",
				baselineMigrationFile, i+1, strings.TrimSpace(line))
		}
	}
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
