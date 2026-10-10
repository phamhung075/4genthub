package httpapp

import (
	"context"
	"database/sql"
	"errors"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories"
)

// taskEventReaderAdapter satisfies routes.TaskEventReader over the ledger's repository.
//
// It builds the repository per call rather than holding one, because the repository is user-scoped
// and the user comes from the request. The branch id is empty on purpose: the ledger is read by
// task, and the repository already scopes every query by user_id, which is where the isolation for
// the 404 negative comes from.
type taskEventReaderAdapter struct {
	sessions *database.SessionManager
}

func (a taskEventReaderAdapter) ListTaskEvents(ctx context.Context, taskID string, afterSeq int, userID string) ([]*taskdomain.TaskEvent, error) {
	// The user the read scopes by is the id every repository in this package is built with - the
	// token subject normalized exactly as task_adapter.go's taskFacadeFactory normalizes it - and NOT
	// the raw subject the routes layer hands over. The ledger's user_id is WRITTEN normalized by both
	// of its writers (the status ledger in task_wiring.go and the evidence writer below), and the
	// ledger's own StatusOf compares that same id against tasks.user_id, which is normalized too. With
	// the raw subject this read matched nothing and answered 200 with an empty list for any non-UUID
	// subject (the default development identity among them) - silently, which is the failure mode this
	// ledger exists to make visible. A parseable UUID is returned unchanged, so production subjects
	// are unaffected.
	raw := userID
	scoped, err := domain.ValidateUserID(&raw, "task-event read")
	if err != nil {
		return nil, err
	}
	repo := repositories.NewTaskEventRepository(a.sessions, scoped, "")
	return repo.ListAfter(ctx, taskID, afterSeq, 0)
}

// taskEvidenceWriterAdapter satisfies routes.TaskEvidenceWriter: O3's write half. It decides whether
// a submission duplicates the task's latest evidence and, when it does not, appends the
// evidence_submitted entry through the ledger's ONE writer (services.TaskEventRecorder.Record) - the
// decision and the append in ONE transaction, which is the property the 409 rests on.
type taskEvidenceWriterAdapter struct {
	sessions *database.SessionManager
	userID   string
}

func (a taskEvidenceWriterAdapter) RecordEvidence(ctx context.Context, taskID, headSHA string,
	payload map[string]any) (*taskdomain.TaskEvent, error) {
	// The user the row is scoped to is the id the COMPOSITION resolves - the token subject normalized
	// to a UUID (task_adapter.go's taskFacadeFactory -> domain.ValidateUserID) - and not the raw
	// subject currentUserID hands back. The ledger's other writer (the status path, task_wiring.go)
	// scopes its rows to the same resolved id, and the raw and resolved ids are the same string
	// whenever the subject is already a UUID. Normalizing here keeps ONE history for one task rather
	// than two histories under two user ids.
	raw := a.userID
	userID, err := domain.ValidateUserID(&raw, "evidence submission")
	if err != nil {
		return nil, err
	}

	var out *taskdomain.TaskEvent
	err = a.sessions.Transaction(ctx, func(ctx context.Context) error {
		// THE DECISION AND THE APPEND MUST AGREE UNDER CONCURRENCY. The decision is taken inside the
		// transaction that appends it, and BEFORE the read it takes the ledger's own per-user append
		// lock - the SAME lock AppendInTx takes (task_event_repository.go, pg_advisory_xact_lock over
		// hashtext(user_id)). Re-taking one's own advisory lock is a no-op, so this only moves the
		// serialization point ahead of the read; without it two concurrent submissions could both
		// read "no previous evidence" and both append, which is exactly the double submission the 409
		// exists to refuse.
		if err := lockTaskEventAppend(ctx, a.sessions, userID); err != nil {
			return err
		}

		previous, found, err := lastEvidenceHeadSHA(ctx, a.sessions, userID, taskID)
		if err != nil {
			return err
		}
		if found && previous == headSHA {
			return routes.ErrEvidenceDuplicate
		}

		actor, err := evidenceActor(ctx, userID)
		if err != nil {
			return err
		}
		recorder := services.NewTaskEventRecorder(repositories.NewTaskEventRepository(a.sessions, userID, ""), userID)
		out, err = recorder.Record(ctx, taskID, taskdomain.TaskEventKindEvidenceSubmitted, actor.Kind, actor.ID, payload)
		return err
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// lockTaskEventAppend takes the ledger's per-user append lock inside the caller's transaction. The
// expression is the repository's own (task_event_repository.go) and must stay it: it is the one
// thing that serializes appends for a user, so a second spelling would serialize against nothing.
func lockTaskEventAppend(ctx context.Context, sessions *database.SessionManager, userID string) error {
	return sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `SELECT pg_advisory_xact_lock(hashtext($1))`, userID)
		return err
	})
}

// lastEvidenceHeadSHA is the head_sha of the task's latest evidence_submitted entry, read inside the
// caller's transaction. It reads the ledger directly rather than through the reader adapter because
// the question is narrower than that interface - "the LATEST evidence's head_sha, or none" - and the
// repository exposes no method for it; the entry's other readers list whole windows instead.
func lastEvidenceHeadSHA(ctx context.Context, sessions *database.SessionManager, userID, taskID string) (string, bool, error) {
	head := ""
	found := false
	err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		err := s.QueryRowContext(ctx, `
			SELECT COALESCE(payload->>'head_sha', '') FROM task_events
			WHERE user_id = $1 AND task_id = $2::uuid AND kind = 'evidence_submitted'
			ORDER BY seq DESC LIMIT 1`, userID, taskID).Scan(&head)
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return nil
			}
			return err
		}
		found = true
		return nil
	})
	if err != nil {
		return "", false, err
	}
	return head, found, nil
}

// evidenceActor is the recorder's own attribution rule (services.actorFor), restated here because
// that helper is unexported while Record takes the actor explicitly: a seat stamped on the request
// (services.WithActor) acted on the caller's behalf, and a request that named none belongs to the
// user this adapter was built for. No third rule is introduced; if actorFor changes, this follows it.
func evidenceActor(ctx context.Context, userID string) (services.Actor, error) {
	if actor, ok := services.ActorFromContext(ctx); ok {
		return actor, nil
	}
	if userID != "" {
		return services.Actor{Kind: taskdomain.TaskEventActorHuman, ID: userID}, nil
	}
	return services.Actor{}, services.ErrNoActor
}
