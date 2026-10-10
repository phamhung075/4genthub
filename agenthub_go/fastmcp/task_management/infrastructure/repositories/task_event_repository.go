package repositories

import (
	"context"
	"encoding/json"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TaskEventRepository appends to, and reads, the task-event ledger. It is append-only: no method
// here updates or deletes a row, because the ledger's value is that a reader can reconstruct a
// task's history from it without trusting a column that can be overwritten.
type TaskEventRepository struct {
	sessions *database.SessionManager
	userID   string
	branchID string
}

// NewTaskEventRepository builds the ledger's repository for one user and branch, the same scoping
// every other repository in this package uses.
func NewTaskEventRepository(sessions *database.SessionManager, userID, branchID string) *TaskEventRepository {
	return &TaskEventRepository{sessions: sessions, userID: userID, branchID: branchID}
}

// Append writes one entry and returns it with the seq the database assigned.
//
// THE SEQUENCE IS THE WHOLE POINT, so it is assigned inside one transaction that first takes a
// per-task advisory lock. Two concurrent appends on the same task therefore serialize: the second
// reads the first's committed MAX(seq) and takes the next number, so the sequence is gapless and
// cannot repeat. The unique constraint on (task_id, seq) is the belt to that brace - if the lock
// were ever bypassed the insert would fail loudly rather than overwrite an event. The vocabularies
// are CHECK constraints in the table's DDL, so a value outside them is refused where the bytes land.
func (r *TaskEventRepository) Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	eventID := value_objects.NewUUIDv4()
	var out *entities.TaskEvent
	err := r.sessions.Transaction(ctx, func(ctx context.Context) error {
		var payload any
		if len(in.Payload) > 0 {
			encoded, err := json.Marshal(in.Payload)
			if err != nil {
				return err
			}
			payload = string(encoded)
		}
		return r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			args := []any{r.userID, in.TaskID}
			conds := `"user_id" = $1 AND "task_id" = $2`
			// The advisory lock is transaction-scoped and keyed on the task, so appends for
			// different tasks never contend and appends for one task never interleave.
			if _, err := s.ExecContext(ctx, `SELECT pg_advisory_xact_lock(hashtext($1))`, in.TaskID); err != nil {
				return err
			}
			args = append(args, eventID, in.Kind, in.ActorKind, in.ActorID, payload)
			// $1 is used twice - inserted into user_id and compared against it - and PostgreSQL deduces
			// a parameter's type once for all of its uses. Left alone the comparison resolves $1 as text
			// (the string category's preferred type, preferred over the column's varchar) while the insert
			// slot resolves the column's VARCHAR(64), and the two resolutions collide as SQLSTATE 42P08.
			// Stating the string type on the parameter makes both uses resolve to varchar.
			//
			// THE CAST IS DELIBERATELY UNLENGTH. A cast to varchar(64) fixes the same collision but adds a
			// second effect: it truncates an over-length parameter silently - measured on task_events, 100
			// characters were stored as 64 with no error under ::varchar(64), where ::varchar leaves the
			// width to the column that owns it and gets SQLSTATE 22001 (value too long) instead. Silent
			// truncation of an identity is worse than a refusal, so the length stays off the cast.
			row := s.QueryRowContext(ctx, `
				INSERT INTO task_events (id, user_id, task_id, seq, kind, actor_kind, actor_id, payload)
				SELECT $3, $1::varchar, $2, COALESCE(MAX("seq"), 0) + 1, $4, $5, $6, $7
				FROM task_events WHERE `+conds+`
				RETURNING "seq", "created_at"`, args...)
			var seq int
			var createdAt time.Time
			if err := row.Scan(&seq, &createdAt); err != nil {
				return err
			}
			out = &entities.TaskEvent{
				ID:        eventID,
				TaskID:    in.TaskID,
				UserID:    r.userID,
				Seq:       seq,
				Kind:      in.Kind,
				ActorKind: in.ActorKind,
				ActorID:   in.ActorID,
				Payload:   in.Payload,
				CreatedAt: createdAt.UTC(),
			}
			return nil
		})
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// ListAfter returns this task's entries strictly after afterSeq, oldest first. after_seq=0 is
// therefore the whole ledger, and a caller that has seen seq N asks for N and gets only what is
// new - which is what makes the read path resumable rather than a full re-read.
func (r *TaskEventRepository) ListAfter(ctx context.Context, taskID string, afterSeq, limit int) ([]*entities.TaskEvent, error) {
	out := []*entities.TaskEvent{}
	if limit <= 0 {
		limit = 100
	}
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, `
			SELECT "id", "task_id", "user_id", "seq", "kind", "actor_kind", "actor_id", "payload", "created_at"
			FROM task_events
			WHERE "user_id" = $1 AND "task_id" = $2 AND "seq" > $3
			ORDER BY "seq" ASC
			LIMIT $4`, r.userID, taskID, afterSeq, limit)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			ev := &entities.TaskEvent{}
			var kind, actorKind string
			var payload *string
			if err := rows.Scan(&ev.ID, &ev.TaskID, &ev.UserID, &ev.Seq, &kind, &actorKind, &ev.ActorID, &payload, &ev.CreatedAt); err != nil {
				return err
			}
			ev.Kind = entities.TaskEventKind(kind)
			ev.ActorKind = entities.TaskEventActorKind(actorKind)
			if payload != nil {
				_ = json.Unmarshal([]byte(*payload), &ev.Payload)
			}
			ev.CreatedAt = ev.CreatedAt.UTC()
			out = append(out, ev)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}
