package database_test

// THE CASE THE READ COULD NOT SETTLE. Two measurements on the incident disagreed with a plain reading
// of the code: the wired status path returns the ledger's error and never reaches the websocket
// notification, so a status change should fail and roll its row back - yet rows were observed with
// the status advanced and no event beside them. This case puts the PRODUCTION SEAM on a database
// whose task_events lacks user_seq, drives a real status write through it, and READS THE ROW BACK.
//
// WHAT IT DRIVES: StatusLedger.SaveStatus with the recorder wired exactly as
// server/httpapp/task_wiring.go wires it - that seam is what the status use case delegates to, and
// it is where the one-transaction claim lives. The use case around it adds an ORM load whose column
// requirements are not what this case measures, so the seam is driven directly and the row it writes
// is a real `tasks` row.
//
// It needs AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skips loudly without it.

import (
	"context"
	"database/sql"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
)

// relaxTaskNotNullColumns is a fixture convenience: the row below is seeded with the two columns this
// case needs, and the rest of the table's NOT NULL columns are not what this case measures.
func relaxTaskNotNullColumns(t *testing.T, db *sql.DB) {
	t.Helper()
	if _, err := db.ExecContext(context.Background(), `DO $$ DECLARE c record; BEGIN
		FOR c IN SELECT column_name FROM information_schema.columns
			WHERE table_name = 'tasks' AND is_nullable = 'NO' AND column_name NOT IN ('id', 'status')
		LOOP EXECUTE format('ALTER TABLE tasks ALTER COLUMN %I DROP NOT NULL', c.column_name); END LOOP;
	END $$`); err != nil {
		t.Fatal(err)
	}
}

func TestAStatusWriteWithoutUserSeqFailsAndLeavesTheRowAlone(t *testing.T) {
	db := newEnsurerTestDB(t)
	ctx := context.Background()
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db}}
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatal(err)
	}
	relaxTaskNotNullColumns(t, db)
	// THE INCIDENT'S SHAPE: the column the recorder writes is absent, and everything else is current.
	if _, err := db.ExecContext(ctx, `ALTER TABLE task_events DROP COLUMN user_seq`); err != nil {
		t.Fatal(err)
	}
	const (
		taskID = "aaaa1111-0000-4000-8000-0000000000aa"
		userID = "user-incident"
	)
	if _, err := db.ExecContext(ctx, `INSERT INTO tasks (id, status, user_id) VALUES ($1, 'todo', $2)`, taskID, userID); err != nil {
		t.Fatal(err)
	}

	// The production wiring: the ledger is WIRED, so this is the path production takes.
	sessions := database.NewSessionManager(cfg)
	recorder := services.NewTaskEventRecorder(repositories.NewTaskEventRepository(sessions, userID, ""), userID)
	ledger := use_cases.StatusLedger{Tx: sessions, Ledger: recorder}

	err := ledger.SaveStatus(ctx, func(ctx context.Context) error {
		// THROUGH THE SESSION MANAGER, exactly as the repository's Save does: it reuses the
		// transaction the ledger opened, which is what puts the row write and the entry in one
		// transaction. Writing on the pool instead would auto-commit and settle nothing.
		return sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx, `UPDATE tasks SET status = 'in_progress' WHERE id = $1`, taskID)
			return err
		})
	}, taskID)
	if err == nil {
		t.Fatal("a status write SUCCEEDED although its ledger entry cannot be written: that is the clean-success-over-a-lost-event shape")
	}
	if !strings.Contains(err.Error(), "user_seq") {
		t.Errorf("the failure does not name the missing column, so it is not the incident's failure: %v", err)
	}

	// THE READ-BACK, which is the whole point: did the row commit while its event failed?
	var status string
	if err := db.QueryRowContext(ctx, `SELECT status FROM tasks WHERE id = $1`, taskID).Scan(&status); err != nil {
		t.Fatal(err)
	}
	if status != "todo" {
		t.Errorf("THE ROW COMMITTED (status %q) while its event failed: the status write and its ledger entry do NOT share one transaction on this path", status)
	}
}
