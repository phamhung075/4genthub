package session_stream

// agent_sessions.room_slug and seat_key postdate their table, so they ship on BOTH paths the
// repository's column seam requires - the same shape seat_management's ensure_seat_columns.go
// documents: this ensurer for a database that ALREADY holds the table, and the agent_sessions
// TableDef for a fresh one. createAll creates a table only when it is ABSENT, so without this the
// pair would exist everywhere except production, which is exactly the gap the seam exists for.
//
// The pair is carried together or not at all. The socket refuses a frame that names one without
// the other, and the CHECK added below states the same rule to the database, so a half pair cannot
// be stored by any path. Nothing here is destructive: ADD COLUMN IF NOT EXISTS and a constraint
// re-created by DROP IF EXISTS then ADD make a repeated boot a no-op.
//
// It runs only under AUTO_MIGRATE=true: CreateTables is the ensurers' only caller
// (task_management/infrastructure/database/database_config.go), and InitDatabase reaches it only
// under that opt-in.

import (
	"context"
	"database/sql"

	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// ensureAgentSessionSeatColumns adds the seat identity a session reports - the room slug and the
// seat key the connector observed - and the both-or-neither constraint over them.
func EnsureAgentSessionSeatColumns(ctx context.Context, db *sql.DB) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	for _, stmt := range []string{
		"ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS room_slug VARCHAR(255)",
		"ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS seat_key VARCHAR(255)",
		"ALTER TABLE agent_sessions DROP CONSTRAINT IF EXISTS ck_agent_sessions_seat_pair",
		"ALTER TABLE agent_sessions ADD CONSTRAINT ck_agent_sessions_seat_pair " +
			"CHECK ((room_slug IS NULL) = (seat_key IS NULL))",
	} {
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func init() { taskdb.ColumnEnsurers = append(taskdb.ColumnEnsurers, EnsureAgentSessionSeatColumns) }
