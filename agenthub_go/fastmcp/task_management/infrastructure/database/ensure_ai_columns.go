package database

// Ensure AI columns exist in the database (Python database/ensure_ai_columns.py).

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

type aiColumn struct{ name, typ, def string }

// aiColumns are the columns that must exist; the dialect is always postgresql here.
var aiColumns = []aiColumn{
	{"ai_system_prompt", "TEXT", "''"},
	{"ai_request_prompt", "TEXT", "''"},
	{"ai_work_context", "JSON", "'{}'"},
	{"ai_completion_criteria", "TEXT", "''"},
	{"ai_execution_history", "JSON", "'[]'"},
	{"ai_last_execution", "TIMESTAMP", "NULL"},
	{"ai_model_preferences", "JSON", "'{}'"},
}

// EnsureAIColumnsExist adds missing AI columns to tasks and subtasks inside one
// transaction when AUTO_MIGRATE=true. Without the opt-in it is a no-op that reports
// success, so callers never alter an existing schema on a default boot.
func EnsureAIColumnsExist(ctx context.Context, db *sql.DB) bool {
	if !autoMigrateEnabled() {
		return true
	}
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return false
	}
	// Python's inspector reads through the engine, not the transaction.
	tables, err := tableNames(ctx, db)
	if err != nil {
		_ = tx.Rollback()
		return false
	}
	for _, table := range []string{"tasks", "subtasks"} {
		if !contains(tables, table) {
			continue
		}
		existing, err := columnNames(ctx, db, table)
		if err != nil {
			_ = tx.Rollback()
			return false
		}
		for _, c := range aiColumns {
			if contains(existing, c.name) {
				continue
			}
			_, err := tx.ExecContext(ctx, fmt.Sprintf("ALTER TABLE %s ADD COLUMN %s %s DEFAULT %s", table, c.name, c.typ, c.def))
			if err != nil {
				low := strings.ToLower(err.Error())
				if strings.Contains(low, "duplicate column") || strings.Contains(low, "already exists") {
					continue
				}
				_ = tx.Rollback()
				return false
			}
		}
	}
	return tx.Commit() == nil
}

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
