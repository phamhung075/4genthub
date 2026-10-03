package database

import (
	"context"
	"fmt"
	"log"
	"sort"
	"strings"
)

// MissingTables lists the registered tables that do not exist in the current schema, sorted.
// Tables holds every table the server queries, including those registered by other packages.
func MissingTables(ctx context.Context, engine *Engine) ([]string, error) {
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

// logMissingTables reports, at startup without AUTO_MIGRATE, the tables the server needs but
// the database lacks. It never creates a table and never stops the server.
func logMissingTables(ctx context.Context, cfg *DatabaseConfig) {
	missing, err := MissingTables(ctx, cfg.Engine)
	if err != nil {
		log.Printf("database: could not check for missing tables: %v", err)
		return
	}
	if len(missing) > 0 {
		log.Print(missingTablesNotice(missing))
	}
}
