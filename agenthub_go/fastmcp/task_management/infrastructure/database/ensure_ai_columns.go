package database

// The AI columns' READBACK. They are created by the schema's own steps (0001_baseline.sql, and
// 0005_patch_columns_the_boot_added.sql for a database that predates them) since the seat-tier
// decision of 2026-10-17 made the migrations the single creator; this file only reports them.

import (
	"context"
	"database/sql"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// VerifyAIColumns reports, per table, the ai_* columns present.
func VerifyAIColumns(ctx context.Context, db *sql.DB) *entities.OrderedMap[any] {
	status := entities.NewOrderedMap[any]()
	tables, err := tableNames(ctx, db)
	if err != nil {
		status = entities.NewOrderedMap[any]()
		status.Set("error", err.Error())
		return status
	}
	for _, table := range []string{"tasks", "subtasks"} {
		if !contains(tables, table) {
			status.Set(table, "Table not found")
			continue
		}
		cols, err := columnNames(ctx, db, table)
		if err != nil {
			status = entities.NewOrderedMap[any]()
			status.Set("error", err.Error())
			return status
		}
		ai := []string{}
		for _, c := range cols {
			if strings.HasPrefix(c, "ai_") {
				ai = append(ai, c)
			}
		}
		entry := entities.NewOrderedMap[any]()
		entry.Set("exists", true)
		entry.Set("ai_columns", ai)
		entry.Set("ai_columns_count", len(ai))
		status.Set(table, entry)
	}
	return status
}
