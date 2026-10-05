package database

import (
	"bytes"
	"context"
	"errors"
	"log"
	"strings"
	"testing"
)

func captureLog(t *testing.T) *bytes.Buffer {
	t.Helper()
	var buf bytes.Buffer
	previous := log.Writer()
	log.SetOutput(&buf)
	t.Cleanup(func() { log.SetOutput(previous) })
	return &buf
}

func TestMissingTablesListsOnlyAbsentRegisteredTables(t *testing.T) {
	ResetInstance()
	t.Cleanup(ResetInstance)
	f := newFakeDB() // has tasks and subtasks only
	cfg, err := GetInstance(context.Background(), fakeAutoMigrateDeps(f))
	if err != nil {
		t.Fatal(err)
	}
	missing, err := MissingTables(context.Background(), cfg.Engine)
	if err != nil {
		t.Fatal(err)
	}
	// Derive the expectation from the registry so a new table does not break the count.
	want := 0
	for _, def := range Tables {
		if _, ok := f.tables[def.Name]; !ok {
			want++
		}
	}
	have := map[string]bool{}
	for _, name := range missing {
		have[name] = true
	}
	if have["tasks"] || have["subtasks"] || !have["projects"] || len(missing) != want {
		t.Fatalf("missing = %v, want the %d registered tables absent from the fake database", missing, want)
	}
}

func TestMissingTablesNilEngine(t *testing.T) {
	ctx := context.Background()
	for _, engine := range []*Engine{nil, &Engine{}} {
		if _, err := MissingTables(ctx, engine); !errors.Is(err, errNoEngine) {
			t.Errorf("MissingTables(%v) err = %v, want errNoEngine", engine, err)
		}
		if _, err := ColumnDrift(ctx, engine); !errors.Is(err, errNoEngine) {
			t.Errorf("ColumnDrift(%v) err = %v, want errNoEngine", engine, err)
		}
	}
}

func TestLogMissingTablesReportsACheckFailure(t *testing.T) {
	// A nil engine fails the table check before the column check runs.
	out := captureLog(t)
	logMissingTables(context.Background(), &DatabaseConfig{Engine: nil})
	logged := out.String()
	if !strings.Contains(logged, "could not check for missing tables") {
		t.Errorf("log %q lacks the missing-table failure", logged)
	}

	// The table check succeeds but the column drift query fails.
	ResetInstance()
	t.Cleanup(ResetInstance)
	out = captureLog(t)
	f := newFakeDB()
	f.failQuery = func(string) error { return errors.New("boom") }
	cfg, err := GetInstance(context.Background(), fakeAutoMigrateDeps(f))
	if err != nil {
		t.Fatal(err)
	}
	logMissingTables(context.Background(), cfg)
	logged = out.String()
	for _, want := range []string{"could not check table columns", "boom"} {
		if !strings.Contains(logged, want) {
			t.Errorf("log %q lacks %q", logged, want)
		}
	}
}

func TestInitDatabaseNamesMissingTablesWithoutAutoMigrate(t *testing.T) {
	clearAutoMigrate(t)
	ResetInstance()
	t.Cleanup(ResetInstance)
	out := captureLog(t)
	f := newFakeDB()
	if err := InitDatabase(context.Background(), fakeAutoMigrateDeps(f)); err != nil {
		t.Fatalf("a missing schema must not stop startup: %v", err)
	}
	logged := out.String()
	for _, want := range []string{"table(s) missing", "projects", "AUTO_MIGRATE=true"} {
		if !strings.Contains(logged, want) {
			t.Errorf("log %q lacks %q", logged, want)
		}
	}
	if ddl := firstDDL(f.statements); ddl != "" {
		t.Errorf("the check created something: %q", ddl)
	}
}

func TestInitDatabaseLogsColumnDriftWithoutAutoMigrate(t *testing.T) {
	clearAutoMigrate(t)
	ResetInstance()
	t.Cleanup(ResetInstance)
	out := captureLog(t)
	f, def, omitted := driftingFakeDB(t)
	if err := InitDatabase(context.Background(), fakeAutoMigrateDeps(f)); err != nil {
		t.Fatalf("a drifting schema must not stop startup: %v", err)
	}
	logged := out.String()
	for _, want := range []string{
		"lacks column(s)",
		omitted,
		"NOT NULL column(s) without a default",
		"status",
		"AUTO_MIGRATE does not alter existing tables",
		def.Name,
	} {
		if !strings.Contains(logged, want) {
			t.Errorf("log %q lacks %q", logged, want)
		}
	}
	if ddl := firstDDL(f.statements); ddl != "" {
		t.Errorf("the check created something: %q", ddl)
	}
}

func TestInitDatabaseWithAutoMigrateDoesNotReportMissingTables(t *testing.T) {
	t.Setenv("AUTO_MIGRATE", "true")
	ResetInstance()
	t.Cleanup(ResetInstance)
	out := captureLog(t)
	f, _, _ := driftingFakeDB(t)
	if err := InitDatabase(context.Background(), fakeAutoMigrateDeps(f)); err != nil {
		t.Fatal(err)
	}
	logged := out.String()
	if strings.Contains(logged, "missing") {
		t.Errorf("AUTO_MIGRATE creates the schema, yet the log says: %s", logged)
	}
	if strings.Contains(logged, "lacks column(s)") {
		t.Errorf("AUTO_MIGRATE must not report existing-table drift, yet the log says: %s", logged)
	}
}

func TestMissingTablesNoticeNamesTablesAndHint(t *testing.T) {
	got := missingTablesNotice([]string{"machines", "rooms"})
	if !strings.Contains(got, "2 table(s) missing: machines, rooms") || !strings.Contains(got, "AUTO_MIGRATE=true") {
		t.Errorf("notice = %q", got)
	}
}

func TestColumnDriftNoticeNamesBothKinds(t *testing.T) {
	got := columnDriftNotice(TableDrift{
		Table:           "seats",
		MissingColumns:  []string{"permission_policy"},
		BlockingColumns: []string{"status"},
	})
	for _, want := range []string{
		"seats",
		"permission_policy",
		"status",
		"lacks column(s)",
		"NOT NULL column(s) without a default",
		"AUTO_MIGRATE does not alter existing tables",
	} {
		if !strings.Contains(got, want) {
			t.Errorf("notice %q lacks %q", got, want)
		}
	}
}

func TestColumnDriftFindsMissingAndBlockingColumns(t *testing.T) {
	ResetInstance()
	t.Cleanup(ResetInstance)
	f, def, omitted := driftingFakeDB(t)
	// A second registered table with every column present yields no drift.
	complete, ok := tableByName("tasks")
	if !ok || complete.Name == def.Name {
		complete, ok = tableByName("subtasks")
	}
	if !ok || complete.Name == def.Name {
		t.Fatal("no second registered table to prove a complete table yields no drift")
	}
	f.tables[complete.Name] = complete.ColumnNames()
	for _, c := range complete.Columns {
		f.schema = append(f.schema, fakeColumn{table: complete.Name, column: c.Name})
	}
	cfg, err := GetInstance(context.Background(), fakeAutoMigrateDeps(f))
	if err != nil {
		t.Fatal(err)
	}
	f.statements = nil
	drift, err := ColumnDrift(context.Background(), cfg.Engine)
	if err != nil {
		t.Fatal(err)
	}
	queries := 0
	for _, q := range f.statements {
		if strings.Contains(q, "information_schema") {
			queries++
			if !strings.Contains(q, "current_schema()") {
				t.Errorf("drift query is not scoped to the current schema: %s", q)
			}
		}
	}
	if queries != 1 {
		t.Errorf("ColumnDrift ran %d information_schema queries, want exactly one: %v", queries, f.statements)
	}
	if len(drift) != 1 {
		t.Fatalf("drift = %+v, want exactly one entry for %q", drift, def.Name)
	}
	got := drift[0]
	if got.Table != def.Name {
		t.Errorf("drift table = %q, want %q", got.Table, def.Name)
	}
	if len(got.MissingColumns) != 1 || got.MissingColumns[0] != omitted {
		t.Errorf("MissingColumns = %v, want [%s]", got.MissingColumns, omitted)
	}
	if len(got.BlockingColumns) != 1 || got.BlockingColumns[0] != "status" {
		t.Errorf("BlockingColumns = %v, want [status]", got.BlockingColumns)
	}
}

// tableByName returns the registered definition for name.
func tableByName(name string) (TableDef, bool) {
	for i := range Tables {
		if Tables[i].Name == name {
			return Tables[i], true
		}
	}
	return TableDef{}, false
}

// tableHasColumn reports whether def declares a column with that name.
func tableHasColumn(def TableDef, name string) bool {
	for _, c := range def.Columns {
		if c.Name == name {
			return true
		}
	}
	return false
}

// driftingFakeDB scripts a database whose only schema facts are one registered table that drifts:
// its last registered column is missing and two unknown columns exist, "status" NOT NULL without
// a default (blocking) and "note" nullable (harmless). The table is "seats" when the
// seat_management package is linked in, otherwise the first registered table with at least two
// columns that does not already define "status" or "note", so both extras are genuinely unknown.
func driftingFakeDB(t *testing.T) (*fakeDB, TableDef, string) {
	t.Helper()
	def, ok := tableByName("seats")
	if !ok || len(def.Columns) < 2 || tableHasColumn(def, "status") || tableHasColumn(def, "note") {
		ok = false
		for i := range Tables {
			if len(Tables[i].Columns) >= 2 && !tableHasColumn(Tables[i], "status") && !tableHasColumn(Tables[i], "note") {
				def, ok = Tables[i], true
				break
			}
		}
	}
	if !ok {
		t.Fatal("no registered table with at least two columns and neither a status nor a note column")
	}
	omitted := def.Columns[len(def.Columns)-1].Name
	f := newFakeDB()
	f.tables[def.Name] = def.ColumnNames()
	for _, c := range def.Columns[:len(def.Columns)-1] {
		f.schema = append(f.schema, fakeColumn{table: def.Name, column: c.Name})
	}
	f.schema = append(f.schema,
		fakeColumn{table: def.Name, column: "status", blocking: true},
		fakeColumn{table: def.Name, column: "note", blocking: false},
	)
	return f, def, omitted
}
