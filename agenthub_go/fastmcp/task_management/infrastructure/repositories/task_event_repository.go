package repositories

import (
	"context"
	"encoding/json"
	"errors"
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

// ErrNotInTransaction is returned by AppendInTx when the context carries no transaction. An entry
// must land in the same transaction as the change it describes, so a call that arrives without one
// is refused loudly rather than committed beside it.
var ErrNotInTransaction = errors.New("task_events: AppendInTx requires the caller's transaction")

// Append writes one entry in a transaction of its own. It is the wrapper D9 keeps for a standalone
// append; the status paths call AppendInTx instead, so their entry shares the status write's
// transaction.
func (r *TaskEventRepository) Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	var out *entities.TaskEvent
	err := r.sessions.Transaction(ctx, func(ctx context.Context) error {
		var appendErr error
		out, appendErr = r.AppendInTx(ctx, in)
		return appendErr
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// AppendInTx writes one entry inside the CALLER's transaction and returns it with the seq the
// database assigned. This is what makes "the status and its entry commit together or not at all" a
// property: the entry joins the caller's transaction, so a failure on either side rolls both back.
//
// THE SEQUENCES ARE THE WHOLE POINT, so they are assigned inside that transaction, which first
// takes a per-USER advisory lock. Two concurrent appends for one user therefore serialize: the
// second reads the first's committed MAX and takes the next number, so both sequences are gapless
// and cannot repeat. The lock is keyed on the user rather than the task because the ledger now
// carries TWO cursors - the task's `seq` and the user's `user_seq` - and a per-task lock would let
// two appends for one user on DIFFERENT tasks take the same `user_seq`, which is the one thing the
// cross-task cursor cannot survive. Appends for different users still never contend.
//
// The unique constraints on (task_id, seq), (user_id, user_seq) and (user_id, client_event_id) are
// the belt to that brace - if the lock were ever bypassed, a duplicate fails loudly rather than
// overwriting an event. The vocabularies are CHECK constraints in the table's DDL, so a value
// outside them is refused where the bytes land.
//
// WHY ONE LOCK AND NOT TWO: both sequences are read under the SAME key on purpose. A per-user lock
// for user_seq beside a per-task lock for seq would hand every append two locks to take in an
// order someone will eventually get wrong, and that failure mode is a deadlock rather than a
// duplicate - much worse to find and much worse to run. One lock, keyed on the user, both
// sequences: do not "improve" this into two.
func (r *TaskEventRepository) AppendInTx(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	if !r.sessions.InTransaction(ctx) {
		return nil, ErrNotInTransaction
	}
	eventID := value_objects.NewUUIDv4()
	var out *entities.TaskEvent
	var payload any
	if len(in.Payload) > 0 {
		encoded, err := json.Marshal(in.Payload)
		if err != nil {
			return nil, err
		}
		payload = string(encoded)
	}
	// An absent outbox key must reach PostgreSQL as NULL, and PostgreSQL's unique index treats
	// NULLs as distinct, which is what keeps every keyless entry legal. subtask_id is nullable
	// for the ordinary case: an entry about the task itself names no subtask.
	var clientEventID any
	if in.ClientEventID != "" {
		clientEventID = in.ClientEventID
	}
	var subtaskID any
	if in.SubtaskID != "" {
		subtaskID = in.SubtaskID
	}
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{r.userID, in.TaskID}
		conds := `"user_id" = $1 AND "task_id" = $2`
		if _, err := s.ExecContext(ctx, `SELECT pg_advisory_xact_lock(hashtext($1))`, r.userID); err != nil {
			return err
		}
		// user_seq is read in its own statement, still under the lock: the LOCK is what makes MAX+1
		// gapless, not the statement's shape. Commit-ordered visibility is exactly why a bigserial
		// cursor is rejected (architecture 2.6) - a reader that has passed N must never miss a
		// transaction that took a lower number and committed later.
		var userSeq int64
		if err := s.QueryRowContext(ctx,
			`SELECT COALESCE(MAX("user_seq"), 0) + 1 FROM task_events WHERE "user_id" = $1`,
			r.userID).Scan(&userSeq); err != nil {
			return err
		}
		args = append(args, eventID, in.Kind, in.ActorKind, in.ActorID, payload, userSeq, clientEventID, subtaskID)
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
			INSERT INTO task_events (id, user_id, task_id, subtask_id, seq, user_seq, kind, actor_kind, actor_id, payload, client_event_id)
			SELECT $3, $1::varchar, $2, $10, COALESCE(MAX("seq"), 0) + 1, $8, $4, $5, $6, $7, $9
			FROM task_events WHERE `+conds+`
			RETURNING "seq", "user_seq", "created_at"`, args...)
		var seq int
		var assignedUserSeq int64
		var createdAt time.Time
		if err := row.Scan(&seq, &assignedUserSeq, &createdAt); err != nil {
			return err
		}
		out = &entities.TaskEvent{
			ID:            eventID,
			TaskID:        in.TaskID,
			SubtaskID:     in.SubtaskID,
			UserID:        r.userID,
			Seq:           seq,
			UserSeq:       assignedUserSeq,
			Kind:          in.Kind,
			ActorKind:     in.ActorKind,
			ActorID:       in.ActorID,
			ClientEventID: in.ClientEventID,
			Payload:       in.Payload,
			CreatedAt:     createdAt.UTC(),
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// StatusOf reads the task's status inside the caller's transaction. The ledger asks for it before
// and after a status write, so an entry reports the transition the ROW made rather than a caller's
// memory of it - which is what makes the parity check (the last status_changed.new against
// tasks.status) hold by construction. Like AppendInTx it is refused outside a transaction: a read
// taken beside the write could see a different value than the write commits.
func (r *TaskEventRepository) StatusOf(ctx context.Context, taskID string) (string, error) {
	if !r.sessions.InTransaction(ctx) {
		return "", ErrNotInTransaction
	}
	status := ""
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT "status" FROM tasks WHERE "user_id" = $1 AND "id" = $2::uuid`,
			r.userID, taskID).Scan(&status)
	})
	if err != nil {
		return "", err
	}
	return status, nil
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
