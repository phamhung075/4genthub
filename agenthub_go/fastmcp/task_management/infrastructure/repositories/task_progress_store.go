package repositories

import (
	"context"
	"database/sql"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TaskProgressStore is the ORM-session access of application/services/task_progress_service.py:
// session.get(Task, task_id).progress_percentage and its assignment + commit (no user filter).
type TaskProgressStore struct{ sessions *database.SessionManager }

// NewTaskProgressStore builds the store over the session manager.
func NewTaskProgressStore(sessions *database.SessionManager) *TaskProgressStore {
	return &TaskProgressStore{sessions: sessions}
}

// GetProgress is session.get(TaskModel, task_id).progress_percentage; ok is false when the row is missing.
func (s *TaskProgressStore) GetProgress(ctx context.Context, taskID string) (float64, bool) {
	var value sql.NullFloat64
	found := false
	err := s.sessions.WithSession(ctx, func(ctx context.Context, tx database.DBTX) error {
		rows, err := tx.QueryContext(ctx, `SELECT "progress_percentage" FROM "tasks" WHERE "id" = $1::uuid`, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		if rows.Next() {
			found = true
			return rows.Scan(&value)
		}
		return rows.Err()
	})
	if err != nil || !found {
		return 0, false
	}
	return value.Float64, true
}

// SetProgress assigns progress_percentage and commits.
func (s *TaskProgressStore) SetProgress(ctx context.Context, taskID string, value float64) error {
	return s.sessions.WithSession(ctx, func(ctx context.Context, tx database.DBTX) error {
		_, err := tx.ExecContext(ctx, `UPDATE "tasks" SET "progress_percentage" = $1 WHERE "id" = $2::uuid`, int64(value), taskID)
		return err
	})
}
