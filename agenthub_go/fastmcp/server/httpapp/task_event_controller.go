package httpapp

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"log"
	"strings"

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
	found, err := repo.ListAfter(ctx, taskID, afterSeq, 0)
	if err != nil {
		// routes.GetTaskEvents answers a flat 500 and drops the cause, exactly as its write sibling
		// SubmitTaskEvidence does, and the writer below logs for that reason. This read did not, and
		// the gap was measured: on 2026-10-21 every task's events answered 500 on the deployed server
		// while the same ledger's writes and its progress-number read succeeded, and the ONLY record
		// anywhere of why was this absent line. A read failure is otherwise undiagnosable from
		// outside, which is the one thing a ledger exists to prevent.
		log.Printf("events: task %s: ListTaskEvents failed: %v", taskID, err)
	}
	return found, err
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
	payload map[string]any) (*taskdomain.TaskEvent, bool, error) {
	// The user the row is scoped to is the id the COMPOSITION resolves - the token subject normalized
	// to a UUID (task_adapter.go's taskFacadeFactory -> domain.ValidateUserID) - and not the raw
	// subject currentUserID hands back. The ledger's other writer (the status path, task_wiring.go)
	// scopes its rows to the same resolved id, and the raw and resolved ids are the same string
	// whenever the subject is already a UUID. Normalizing here keeps ONE history for one task rather
	// than two histories under two user ids.
	raw := a.userID
	userID, err := domain.ValidateUserID(&raw, "evidence submission")
	if err != nil {
		return nil, false, err
	}

	var out *taskdomain.TaskEvent
	created := false
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

		previous, found, err := lastEvidence(ctx, a.sessions, userID, taskID)
		if err != nil {
			return err
		}
		if found {
			storedHead, _ := previous.Payload["head_sha"].(string)
			if storedHead == headSHA {
				// SAME SHA, TWO ANSWERS. An identical replay is not a second account of the head:
				// it is the same submission arriving again, so the stored entry IS this submission's
				// record and the answer is 200 with it - nothing appended. A different account of
				// the same head is refused: the completion that follows would otherwise attach a
				// local verdict to evidence the judge will never see.
				if sameEvidence(previous.Payload, payload) {
					out = previous
					return nil
				}
				// A ROW THAT NAMES NO TEST IS SUPERSEDED, ON THE TEST AXIS ONLY. A stored row with no
				// account of the test held the head against every correction: the compare read its
				// command as "" and no submission naming one could ever match, so the head stayed
				// frozen on a bare row (architect RULING-2026-10-22-evidence-row-supersession, option
				// A). The stored row has nothing on that axis for the submission to contradict, so it
				// appends - but only when the identity axes agree: a different base, head or numstat
				// is still a 409, and a stored row that names a command is never superseded, which
				// keeps completeness monotone.
				if !(sameEvidenceIdentity(previous.Payload, payload) &&
					evidenceNamesNoTest(previous.Payload) && !evidenceNamesNoTest(payload)) {
					return routes.ErrEvidenceDuplicate
				}
			}
		}

		actor, err := evidenceActor(ctx, userID)
		if err != nil {
			return err
		}
		recorder := services.NewTaskEventRecorder(repositories.NewTaskEventRepository(a.sessions, userID, ""), userID)
		out, err = recorder.Record(ctx, taskID, taskdomain.TaskEventKindEvidenceSubmitted, actor.Kind, actor.ID, payload)
		created = err == nil
		return err
	})
	if err != nil {
		// A refusal - the duplicate the route maps to 409 - is the rule working, not a failure. Any
		// other error is a submission that did not land, and its error is the ONLY record of why:
		// routes.SubmitTaskEvidence answers a flat 500 and drops it. Without this line a failed
		// completion is undiagnosable from outside (2026-10-18: two 500s nobody could explain).
		if !errors.Is(err, routes.ErrEvidenceDuplicate) {
			log.Printf("evidence: task %s: RecordEvidence failed: %v", taskID, err)
		}
		return nil, false, err
	}
	return out, created, nil
}

// lastEvidence is the task's latest evidence_submitted entry, read inside the caller's transaction.
// It reads the ledger directly rather than through the reader adapter because the question is
// narrower than that interface - "the LATEST evidence entry, or none" - and the repository exposes no
// method for it; the entry's other readers list whole windows instead. The whole entry comes back,
// not only its head_sha, because a replay answers with the STORED event and the route renders it.
func lastEvidence(ctx context.Context, sessions *database.SessionManager, userID, taskID string) (*taskdomain.TaskEvent, bool, error) {
	var out *taskdomain.TaskEvent
	found := false
	err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		ev := &taskdomain.TaskEvent{}
		var kind, actorKind string
		var payload *string
		err := s.QueryRowContext(ctx, `
			SELECT "id", "task_id", "user_id", "seq", "kind", "actor_kind", "actor_id", "payload", "created_at"
			FROM task_events
			WHERE "user_id" = $1 AND "task_id" = $2::uuid AND "kind" = 'evidence_submitted'
			ORDER BY "seq" DESC LIMIT 1`, userID, taskID).
			Scan(&ev.ID, &ev.TaskID, &ev.UserID, &ev.Seq, &kind, &actorKind, &ev.ActorID, &payload, &ev.CreatedAt)
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				return nil
			}
			return err
		}
		ev.Kind = taskdomain.TaskEventKind(kind)
		ev.ActorKind = taskdomain.TaskEventActorKind(actorKind)
		if payload != nil {
			_ = json.Unmarshal([]byte(*payload), &ev.Payload)
		}
		ev.CreatedAt = ev.CreatedAt.UTC()
		out = ev
		found = true
		return nil
	})
	if err != nil {
		return nil, false, err
	}
	return out, found, nil
}

// sameEvidence answers whether the stored entry and the submission are the SAME account of the head:
// base_sha, head_sha, numstat, and the test block's command, exit code and failed list, compared in
// order. The stored side arrives from JSONB (numbers are float64, `failed` is []any) and the submitted
// side from the route (int, []string), so every comparison normalizes both. An order difference is a
// different account: refusing there is the safe direction.
func sameEvidence(stored, submitted map[string]any) bool {
	if stored == nil {
		return false
	}
	if !sameEvidenceIdentity(stored, submitted) {
		return false
	}
	storedTest, ok := stored["test"].(map[string]any)
	if !ok {
		return false
	}
	submittedTest, ok := submitted["test"].(map[string]any)
	if !ok {
		return false
	}
	if evidenceString(storedTest, "command") != evidenceString(submittedTest, "command") {
		return false
	}
	storedExit, storedOK := evidenceInt(storedTest["exit_code"])
	submittedExit, submittedOK := evidenceInt(submittedTest["exit_code"])
	if !storedOK || !submittedOK || storedExit != submittedExit {
		return false
	}
	storedFailed, storedOK := evidenceStrings(storedTest["failed"])
	submittedFailed, submittedOK := evidenceStrings(submittedTest["failed"])
	if !storedOK || !submittedOK || len(storedFailed) != len(submittedFailed) {
		return false
	}
	for i := range storedFailed {
		if storedFailed[i] != submittedFailed[i] {
			return false
		}
	}
	return true
}

// sameEvidenceIdentity answers whether the two payloads describe the same head's change:
// base_sha, head_sha and numstat, the axes a submission may never overwrite. It is the same three
// keys sameEvidence compares first, split out because the supersession below needs exactly them.
func sameEvidenceIdentity(stored, submitted map[string]any) bool {
	for _, key := range []string{"base_sha", "head_sha", "numstat"} {
		if evidenceString(stored, key) != evidenceString(submitted, key) {
			return false
		}
	}
	return true
}

// evidenceNamesNoTest reports whether an evidence payload holds no account of the test, which is the
// one shape a later submission may supersede (RULING-2026-10-22-evidence-row-supersession): the `test`
// block is absent, or its command is empty after trimming. An exit code and a `failed` list alone are
// not an account of anything - no command, no test - so a row carrying only those is weak too. Any
// non-empty command, however short, is complete: the exit code and `failed` list are then its account.
func evidenceNamesNoTest(payload map[string]any) bool {
	test, ok := payload["test"].(map[string]any)
	if !ok {
		return true
	}
	return strings.TrimSpace(evidenceString(test, "command")) == ""
}

// evidenceString is the map's string value, or "" for an absent or non-string one: the comparison
// treats both as the same absence, which is what a submission that omitted an optional block means.
func evidenceString(m map[string]any, key string) string {
	s, _ := m[key].(string)
	return s
}

// evidenceInt normalizes the two numeric shapes: int from the route's own payload and float64 from
// JSONB. A non-integral value is not equal to any exit code and is reported as unusable.
func evidenceInt(v any) (int, bool) {
	switch n := v.(type) {
	case int:
		return n, true
	case int64:
		return int(n), true
	case float64:
		if n != float64(int(n)) {
			return 0, false
		}
		return int(n), true
	}
	return 0, false
}

// evidenceStrings normalizes the two list shapes: []string from the route and []any from JSONB. A
// nil list (absent) reads as empty, because the route already emits an empty array for a submission
// that sent none.
func evidenceStrings(v any) ([]string, bool) {
	switch list := v.(type) {
	case nil:
		return nil, true
	case []string:
		return list, true
	case []any:
		out := make([]string, 0, len(list))
		for _, item := range list {
			s, ok := item.(string)
			if !ok {
				return nil, false
			}
			out = append(out, s)
		}
		return out, true
	}
	return nil, false
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
