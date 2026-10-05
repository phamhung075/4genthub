package database

import (
	"context"
	"errors"
	"fmt"
	"log"
	"sort"
	"strings"
)

var errNoEngine = errors.New("database engine is not initialised")

// MissingTables lists the registered tables that do not exist in the current schema, sorted.
// Tables holds every table the server queries, including those registered by other packages.
func MissingTables(ctx context.Context, engine *Engine) ([]string, error) {
	if engine == nil || engine.DB == nil {
		return nil, errNoEngine
	}
	existing, err := tableNames(ctx, engine.DB)
	if err != nil {
		return nil, err
	}
	present := make(map[string]bool, len(existing))
	for _, name := range existing {
		present[name] = true
	}
	var missing []string
	for _, def := range Tables {
		if !present[def.Name] {
			missing = append(missing, def.Name)
		}
	}
	sort.Strings(missing)
	return missing, nil
}

// missingTablesNotice names the missing tables and how to create them; it creates nothing.
func missingTablesNotice(missing []string) string {
	return fmt.Sprintf("database: %d table(s) missing: %s; queries on them fail with 500 until the schema exists. Start once with AUTO_MIGRATE=true to create it",
		len(missing), strings.Join(missing, ", "))
}

// TableDrift is how an existing table differs from its registered definition.
type TableDrift struct {
	Table string
	// MissingColumns are registered columns the table lacks; a query naming one fails.
	MissingColumns []string
	// BlockingColumns are columns the registry does not know that are NOT NULL without a
	// default; an insert that does not write them fails.
	BlockingColumns []string
}

// ColumnDrift compares every registered table that exists with the columns the database has, in
// one information_schema query. Tables the database lacks are MissingTables' business. The
// expected columns come from Tables (one source of truth, the ORM definitions); an unknown
// column that is nullable or has a default is harmless and not reported.
func ColumnDrift(ctx context.Context, engine *Engine) ([]TableDrift, error) {
	if engine == nil || engine.DB == nil {
		return nil, errNoEngine
	}
	rows, err := engine.DB.QueryContext(ctx, "SELECT table_name, column_name, is_nullable = 'NO' AND column_default IS NULL FROM information_schema.columns WHERE table_schema = current_schema() ORDER BY table_name, ordinal_position")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	type dbColumn struct{ blocking bool }
	actual := map[string]map[string]dbColumn{}
	for rows.Next() {
		var table, column string
		var blocking bool
		if err := rows.Scan(&table, &column, &blocking); err != nil {
			return nil, err
		}
		if actual[table] == nil {
			actual[table] = map[string]dbColumn{}
		}
		actual[table][column] = dbColumn{blocking}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	var drift []TableDrift
	for _, def := range Tables {
		have, exists := actual[def.Name]
		if !exists {
			continue
		}
		known := make(map[string]bool, len(def.Columns))
		d := TableDrift{Table: def.Name}
		for _, col := range def.Columns {
			known[col.Name] = true
			if _, ok := have[col.Name]; !ok {
				d.MissingColumns = append(d.MissingColumns, col.Name)
			}
		}
		for name, col := range have {
			if !known[name] && col.blocking {
				d.BlockingColumns = append(d.BlockingColumns, name)
			}
		}
		if len(d.MissingColumns) > 0 || len(d.BlockingColumns) > 0 {
			sort.Strings(d.MissingColumns)
			sort.Strings(d.BlockingColumns)
			drift = append(drift, d)
		}
	}
	sort.Slice(drift, func(i, j int) bool { return drift[i].Table < drift[j].Table })
	return drift, nil
}

// columnDriftNotice describes one table's drift; it changes nothing.
func columnDriftNotice(d TableDrift) string {
	var parts []string
	if len(d.MissingColumns) > 0 {
		parts = append(parts, "lacks column(s) "+strings.Join(d.MissingColumns, ", ")+" (queries naming them fail)")
	}
	if len(d.BlockingColumns) > 0 {
		parts = append(parts, "has NOT NULL column(s) without a default that the server does not write: "+strings.Join(d.BlockingColumns, ", ")+" (inserts fail)")
	}
	return fmt.Sprintf("database: table %s %s; AUTO_MIGRATE does not alter existing tables, change them by hand", d.Table, strings.Join(parts, " and "))
}

// logMissingTables reports, at startup without AUTO_MIGRATE, the tables the server needs but
// the database lacks and the columns of existing tables that differ from the ORM definitions.
// It never changes the schema and never stops the server.
func logMissingTables(ctx context.Context, cfg *DatabaseConfig) {
	missing, err := MissingTables(ctx, cfg.Engine)
	if err != nil {
		log.Printf("database: could not check for missing tables: %v", err)
		return
	}
	if len(missing) > 0 {
		log.Print(missingTablesNotice(missing))
	}
	drift, err := ColumnDrift(ctx, cfg.Engine)
	if err != nil {
		log.Printf("database: could not check table columns: %v", err)
		return
	}
	for _, d := range drift {
		log.Print(columnDriftNotice(d))
	}
}
