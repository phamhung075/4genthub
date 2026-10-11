package repositories

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"strconv"
	"strings"
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
		if err := lockUserAppend(ctx, s, r.userID); err != nil {
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

// taskEventWholeLedgerPage is the page size Events reads in. It IS ListAfter's own default window,
// so the whole-ledger read adds no second notion of "how much of the ledger is a page".
const taskEventWholeLedgerPage = 100

// Events returns the task's WHOLE ledger, oldest first - the read the resume brief makes, and the
// reason it is not ListAfter(taskID, 0, 0): that call means "the first hundred entries", while a
// brief names the LAST entry of each kind and would answer from the ledger's oldest entries instead,
// with no way to tell. Paging over ListAfter keeps ONE query and one window decision in this file,
// and terminates because every page advances past the seq it returned.
func (r *TaskEventRepository) Events(ctx context.Context, taskID string) ([]*entities.TaskEvent, error) {
	out := []*entities.TaskEvent{}
	afterSeq := 0
	for {
		page, err := r.ListAfter(ctx, taskID, afterSeq, taskEventWholeLedgerPage)
		if err != nil {
			return nil, err
		}
		out = append(out, page...)
		if len(page) < taskEventWholeLedgerPage {
			return out, nil
		}
		afterSeq = page[len(page)-1].Seq
	}
}

// --- the ledger's own layer (P2, P3): the cross-task cursor and the decision reads ---

// Transaction runs fn in one transaction. The ledger's intents route must DECIDE and APPEND in one
// transaction - a decision read beside the append it gates could see a different ledger than the
// append lands in - and this repository is what owns the append lock, so the transaction is taken
// through it rather than by reaching around it for the session manager.
func (r *TaskEventRepository) Transaction(ctx context.Context, fn func(ctx context.Context) error) error {
	return r.sessions.Transaction(ctx, fn)
}

// LockUser takes the ledger's per-user append lock inside the caller's transaction. It is the SAME
// lock AppendInTx takes, exposed so a caller that must READ before it appends - the intents route,
// whose decision turns on the task's current seq - can take it ahead of its reads and make the pair
// atomic. Re-taking one's own advisory lock is a no-op, so calling this before an AppendInTx on the
// same transaction costs nothing.
func (r *TaskEventRepository) LockUser(ctx context.Context) error {
	if !r.sessions.InTransaction(ctx) {
		return ErrNotInTransaction
	}
	return r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return lockUserAppend(ctx, s, r.userID)
	})
}

// lockUserAppend is the ONE spelling of the ledger's append lock. AppendInTx and LockUser both take
// it through here: it is the one thing that serializes appends for a user, so a second spelling of
// the expression would serialize against nothing.
func lockUserAppend(ctx context.Context, s database.DBTX, userID string) error {
	_, err := s.ExecContext(ctx, `SELECT pg_advisory_xact_lock(hashtext($1))`, userID)
	return err
}

// TaskEventColumns is the column list every entry read selects, in the order scanTaskEvent reads
// them. One constant rather than a literal per query, because a read that selected a different set
// from a sibling would scan into the wrong fields or fail on a count that no compiler checks.
const TaskEventColumns = `"id", "task_id", "subtask_id", "user_id", "seq", "user_seq", "client_event_id", "kind", "actor_kind", "actor_id", "payload", "created_at"`

// scanTaskEvent reads one row of TaskEventColumns.
func scanTaskEvent(rows interface{ Scan(...any) error }) (*entities.TaskEvent, error) {
	ev := &entities.TaskEvent{}
	var kind, actorKind string
	var subtaskID, storedClientEventID sql.NullString
	var payload *string
	if err := rows.Scan(&ev.ID, &ev.TaskID, &subtaskID, &ev.UserID, &ev.Seq, &ev.UserSeq, &storedClientEventID,
		&kind, &actorKind, &ev.ActorID, &payload, &ev.CreatedAt); err != nil {
		return nil, err
	}
	ev.SubtaskID = subtaskID.String
	ev.ClientEventID = storedClientEventID.String
	ev.Kind = entities.TaskEventKind(kind)
	ev.ActorKind = entities.TaskEventActorKind(actorKind)
	if payload != nil {
		_ = json.Unmarshal([]byte(*payload), &ev.Payload)
	}
	ev.CreatedAt = ev.CreatedAt.UTC()
	return ev, nil
}

// ListUserAfter returns the user's entries strictly after afterUserSeq ACROSS ALL OF THE USER'S
// TASKS, oldest first. This is the cursor the per-task read (ListAfter) does not carry, and the
// difference is the whole point of the route over it: one cursor covers a user's work everywhere.
//
// ORDERING IS BY user_seq AND NOT created_at, because user_seq is the number the per-user lock hands
// out gaplessly in commit order (see AppendInTx): ordering by a timestamp would let two entries
// written in the same millisecond come back in an order no client could resume from. after=0 is the
// whole ledger, and a client that has seen N asks for N and gets only what is new.
//
// limit<=0 takes the same default window ListAfter takes, so this file holds ONE notion of how much
// of the ledger is a page.
func (r *TaskEventRepository) ListUserAfter(ctx context.Context, afterUserSeq int64, limit int) ([]*entities.TaskEvent, error) {
	out := []*entities.TaskEvent{}
	if limit <= 0 {
		limit = 100
	}
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, `
			SELECT `+TaskEventColumns+` FROM task_events
			WHERE "user_id" = $1 AND "user_seq" > $2
			ORDER BY "user_seq" ASC
			LIMIT $3`, r.userID, afterUserSeq, limit)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			ev, err := scanTaskEvent(rows)
			if err != nil {
				return err
			}
			out = append(out, ev)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// UserTip returns the user's current tip: the highest user_seq the user's ledger holds, and 0 when
// it holds none. It is the number the read hands back beside a page so a client knows how far behind
// its cursor is, and the number P4's `ledger_tip` frame will carry.
func (r *TaskEventRepository) UserTip(ctx context.Context) (int64, error) {
	tip := int64(0)
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT COALESCE(MAX("user_seq"), 0) FROM task_events WHERE "user_id" = $1`, r.userID).Scan(&tip)
	})
	if err != nil {
		return 0, err
	}
	return tip, nil
}

// FindByClientEventID returns the entry one outbox key wrote, if this user has one. It is the whole
// idempotency of a resent intent: uq_task_event_client_event keeps one key to one row, so the row IS
// the first answer and a resend is answered from it rather than by appending a second one.
//
// The key is cast to uuid because the column is one: without the cast PostgreSQL would resolve the
// comparison against a text category and a key that is not a UUID would come back as a driver error
// rather than as "no entry". Callers canonicalise the key first, so a malformed one never gets here.
func (r *TaskEventRepository) FindByClientEventID(ctx context.Context, clientEventID string) (*entities.TaskEvent, bool, error) {
	found := false
	ev := &entities.TaskEvent{}
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := scanTaskEvent(s.QueryRowContext(ctx,
			`SELECT `+TaskEventColumns+` FROM task_events WHERE "user_id" = $1 AND "client_event_id" = $2::uuid`,
			r.userID, clientEventID))
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return nil
			}
			return err
		}
		found = true
		ev = row
		return nil
	})
	if err != nil {
		return nil, false, err
	}
	return ev, found, nil
}

// CurrentTaskSeq is the task's seq as it stands: MAX(seq) over the task's entries, 0 when it has
// none. It is the number a decision's base_seq is compared against and the number a refusal reports
// so the client knows what to re-read from.
func (r *TaskEventRepository) CurrentTaskSeq(ctx context.Context, taskID string) (int, error) {
	seq := 0
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT COALESCE(MAX("seq"), 0) FROM task_events WHERE "user_id" = $1 AND "task_id" = $2::uuid`,
			r.userID, taskID).Scan(&seq)
	})
	if err != nil {
		return 0, err
	}
	return seq, nil
}

// HasNonFactAfter reports whether anything on the task after afterSeq is NOT one of factKinds.
//
// THE QUESTION IS ASKED OF THE COMPLEMENT OF THE FACT LIST, not of the decision list, because that is
// the rule D9 states (`:599`): a decision is refused when its base_seq is behind the task's current
// seq UNLESS EVERY EVENT SINCE THEN IS A FACT. An entry of some third kind - an escalation the
// server wrote, a delivery - is not a fact either, and the rule says so; asking "was there a
// decision" instead would let a decision through on the strength of history the client never saw.
//
// THE VOCABULARY IS AN ARGUMENT. Which kinds are facts is the ledger's rule and belongs to the
// package that states it; this repository has no opinion about it and therefore cannot go stale on
// one. An empty list asks the question without the exception, which is the honest reading of "no
// kinds count as facts".
func (r *TaskEventRepository) HasNonFactAfter(ctx context.Context, taskID string, afterSeq int, factKinds []string) (bool, error) {
	found := false
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		args := []any{r.userID, taskID, afterSeq}
		exception := ""
		if len(factKinds) > 0 {
			placeholders := make([]string, 0, len(factKinds))
			for _, kind := range factKinds {
				args = append(args, kind)
				placeholders = append(placeholders, "$"+strconv.Itoa(len(args)))
			}
			exception = ` AND "kind" NOT IN (` + strings.Join(placeholders, ", ") + `)`
		}
		return s.QueryRowContext(ctx, `
			SELECT EXISTS(SELECT 1 FROM task_events
				WHERE "user_id" = $1 AND "task_id" = $2::uuid AND "seq" > $3`+exception+`)`, args...).Scan(&found)
	})
	if err != nil {
		return false, err
	}
	return found, nil
}

// TaskVisible reports whether the task exists AND belongs to this repository's user.
//
// IT IS NOT REDUNDANT WITH THE FOREIGN KEY, which is why it is here rather than assumed: task_events
// references tasks(id) and nothing else, so an entry naming ANOTHER USER'S task would satisfy the
// constraint and land in this user's ledger beside a task the user cannot see. The ledger is
// user-isolated, so the ownership check is what makes that impossible rather than merely unlikely.
func (r *TaskEventRepository) TaskVisible(ctx context.Context, taskID string) (bool, error) {
	visible := false
	err := r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT EXISTS(SELECT 1 FROM tasks WHERE "user_id" = $1 AND "id" = $2::uuid)`,
			r.userID, taskID).Scan(&visible)
	})
	if err != nil {
		return false, err
	}
	return visible, nil
}
