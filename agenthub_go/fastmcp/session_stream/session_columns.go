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
// client_cursor and seat_state postdate the table too, and take the same path for the same reason:
// client_cursor is the connector's own resume position, committed with the events it describes
// (rigd-boundaries.md 2.1 option A / 5 step 1), and seat_state is the state the connector last
// reported for the session's seat (2.3a). Neither carries a constraint of its own: seat_state's
// closed set is enforced by the ingest, which refuses a value it cannot store rather than letting
// the whole session frame fail on a CHECK.
//
// It runs only under AUTO_MIGRATE=true: CreateTables is the ensurers' only caller
// (task_management/infrastructure/database/database_config.go), and InitDatabase reaches it only
// under that opt-in.

import (
	"context"
	"database/sql"

	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// EnsureAgentSessionSeatColumns adds the seat identity a session reports - the room slug and the
// seat key the connector observed - the both-or-neither constraint over them, the connector's
// opaque resume cursor and the seat state it last reported.
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
		"ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS client_cursor VARCHAR(512)",
		"ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS seat_state VARCHAR(20)",
	} {
		if _, err := tx.ExecContext(ctx, stmt); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func init() { taskdb.ColumnEnsurers = append(taskdb.ColumnEnsurers, EnsureAgentSessionSeatColumns) }
