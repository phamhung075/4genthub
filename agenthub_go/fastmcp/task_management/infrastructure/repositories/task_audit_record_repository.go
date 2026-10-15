package repositories

import (
	"context"
	"encoding/json"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TaskAuditRecordRepository appends to, and reads, the task audit trail - the records the lifecycle
// sweep writes about what it did to a task.
//
// IT IS APPEND-ONLY, and there is deliberately no delete method: the trail exists so that a pruned
// task's completion summary and evidence are still readable after the task row is gone, which a
// delete path would undo. Nothing in this codebase prunes these rows.
//
// The repository takes no user scope, unlike every other repository in this package: an audit
// record is addressed by its task's own id and carries the user it belongs to in the row, while the
// sweep is a platform actor that has to see every user's tasks. The read is therefore narrowed by
// task id rather than by a session user.
type TaskAuditRecordRepository struct{ sessions *database.SessionManager }

// NewTaskAuditRecordRepository builds the trail's repository over the sessions.
func NewTaskAuditRecordRepository(sessions *database.SessionManager) *TaskAuditRecordRepository {
	return &TaskAuditRecordRepository{sessions: sessions}
}

// taskAuditColumns is the column list every read selects, in the order scanTaskAuditRecord reads
// them. One constant rather than a literal per query, because a read that selected a different set
// from a sibling would scan into the wrong fields or fail on a count no compiler checks.
const taskAuditColumns = `"id", "task_id", "user_id", "kind", "title", "status", "priority", "completion_summary", "evidence", "detail", "created_at", "task_created_at", "task_updated_at", "task_completed_at"`

// Record appends one record to the trail.
//
// THE CALLER SUPPLIES THE TIMESTAMP, and that is what makes the sweep testable against a fake
// clock: the record is stamped with the instant the sweep decided at, not with the database's own
// now(). An empty id is minted here, so a caller that has no id of its own does not have to invent a
// UUID to write a record.
func (r *TaskAuditRecordRepository) Record(ctx context.Context, record entities.TaskAuditRecord) error {
	recordID := record.ID
	if recordID == "" {
		recordID = value_objects.NewUUIDv4()
	}
	createdAt := record.CreatedAt
	if createdAt.IsZero() {
		createdAt = database.TimestampNow()
	}
	// Empty evidence reaches PostgreSQL as NULL rather than as the empty array: a record for a task
	// that never submitted evidence says so by holding nothing, and the two spellings would otherwise
	// render differently to a reader.
	var evidence any
	if len(record.Evidence) > 0 {
		encoded, err := json.Marshal(record.Evidence)
		if err != nil {
			return err
		}
		evidence = string(encoded)
	}
	return r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `
			INSERT INTO task_audit_records (id, task_id, user_id, kind, title, status, priority, completion_summary, evidence, detail, created_at, task_created_at, task_updated_at, task_completed_at)
			VALUES ($1::uuid, $2::uuid, $3::varchar, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)`,
			recordID, record.TaskID, record.UserID, string(record.Kind), record.Title, record.Status,
			record.Priority, record.CompletionSummary, evidence, record.Detail, createdAt,
			record.TaskCreatedAt, record.TaskUpdatedAt, record.TaskCompletedAt)
		return err
	})
}

// ListForTask returns one task's records, oldest first. The task may be gone: the trail outlives it,
// and a reader asking about a pruned task is exactly the reader this exists for.
func (r *TaskAuditRecordRepository) ListForTask(ctx context.Context, taskID string) ([]entities.TaskAuditRecord, error) {
	var out []entities.TaskAuditRecord
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, `SELECT `+taskAuditColumns+` FROM task_audit_records WHERE "task_id" = $1::uuid ORDER BY "created_at", "id"`, taskID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			record, err := scanTaskAuditRecord(rows)
			if err != nil {
				return err
			}
			out = append(out, record)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// scanTaskAuditRecord reads one row in taskAuditColumns order.
func scanTaskAuditRecord(rows interface{ Scan(...any) error }) (entities.TaskAuditRecord, error) {
	var (
		record            entities.TaskAuditRecord
		kind              string
		completionSummary *string
		evidence          []byte
		createdAt         time.Time
		taskCreatedAt     time.Time
		taskUpdatedAt     time.Time
		taskCompletedAt   *time.Time
	)
	if err := rows.Scan(&record.ID, &record.TaskID, &record.UserID, &kind, &record.Title, &record.Status,
		&record.Priority, &completionSummary, &evidence, &record.Detail, &createdAt,
		&taskCreatedAt, &taskUpdatedAt, &taskCompletedAt); err != nil {
		return entities.TaskAuditRecord{}, err
	}
	record.Kind = entities.TaskAuditKind(kind)
	if completionSummary != nil {
		record.CompletionSummary = *completionSummary
	}
	if len(evidence) > 0 {
		if err := json.Unmarshal(evidence, &record.Evidence); err != nil {
			return entities.TaskAuditRecord{}, err
		}
	}
	record.CreatedAt = createdAt.UTC()
	record.TaskCreatedAt = taskCreatedAt.UTC()
	record.TaskUpdatedAt = taskUpdatedAt.UTC()
	if taskCompletedAt != nil {
		completed := taskCompletedAt.UTC()
		record.TaskCompletedAt = &completed
	}
	return record, nil
}
