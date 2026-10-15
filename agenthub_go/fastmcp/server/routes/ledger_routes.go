// ledger_routes.go holds the TWO routes of the ledger's own layer: the cross-task read (P2) and the
// intents route (P3). Each is one narrow interface and one handler, deliberately NOT folded into
// UserTaskController - adding a method there would drag the change into api_controllers' crud_handler.go,
// and this item owns neither. It is the shape task_event_routes.go and task_evidence_routes.go
// already use, so the ledger adds no third idiom.
//
// IT IS NOT O1a's READ. `GET /api/v2/tasks/{id}/events` is per TASK; `GET /api/v2/ledger` is the
// cursor across ALL of a user's tasks, which is the whole difference between them and the reason
// both exist (architecture agenthub-system-architecture.md :615).
package routes

import (
	"context"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	ledgerentities "agenthub/fastmcp/ledger/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
)

// LedgerReader is the minimal read surface the cross-task read needs. It is user-scoped by ARGUMENT
// rather than by construction, exactly as TaskEventReader is: the user comes from the request, and
// the adapter below builds the user-scoped repository per call. Every query behind it filters by
// user_id, which is where "another user's credential returns none of the first user's rows" comes
// from rather than from a filter applied here.
type LedgerReader interface {
	ListUserEvents(ctx context.Context, userID string, after int64, limit int) (events []*taskdomain.TaskEvent, tip int64, err error)
}

// LedgerIntentWriter is the minimal write surface the intents route needs: one call that decides the
// whole batch and appends what it accepts. The batch is decided inside the service rather than here
// because the per-item decision and its append must share one transaction, and a handler has no
// transaction to give it.
type LedgerIntentWriter interface {
	SubmitIntents(ctx context.Context, userID string, intents []ledgerentities.Intent) ([]ledgerentities.Answer, error)
}

// GetLedger ports the cross-task read (GET /api/v2/ledger?after=&limit=).
//
// It returns the page oldest first, the user's CURSOR ECHOED (the `after` it answered from, 0 when
// the caller sent none) and the user's CURRENT TIP. The tip is not the last entry of the page and is
// not derived from it: it is the highest user_seq the user's ledger holds, so a page read while the
// ledger is moving still tells the client where the end is.
func GetLedger(ctx context.Context, after int64, limit int, currentUser *authdomain.User,
	reader LedgerReader) (*taskdomain.OrderedMap[any], error) {
	userID := currentUserID(currentUser)

	events, tip, err := reader.ListUserEvents(ctx, userID, after, limit)
	if err != nil {
		return nil, httpErr(500, "Failed to load the ledger")
	}

	list := make([]any, 0, len(events))
	for _, e := range events {
		item := taskdomain.NewOrderedMap[any]()
		item.Set("id", e.ID)
		item.Set("task_id", e.TaskID)
		// subtask_id is nullable in the table and emitted as JSON null when the entry is about the
		// task itself, so a client tells "no subtask" from "a subtask whose id is blank" - the empty
		// string is a legal UUID field value in no sense, but null is unambiguous.
		if e.SubtaskID == "" {
			item.Set("subtask_id", nil)
		} else {
			item.Set("subtask_id", e.SubtaskID)
		}
		item.Set("seq", e.Seq)
		// user_seq is the row's position in the ONE cursor this route serves; without it a client
		// could not ask for what follows the page it just read.
		item.Set("user_seq", e.UserSeq)
		item.Set("kind", string(e.Kind))
		item.Set("actor_kind", string(e.ActorKind))
		item.Set("actor_id", e.ActorID)
		item.Set("payload", e.Payload)
		// created_at is the RFC3339 string the rest of this server emits, the same shape the
		// per-task read and the evidence POST emit (task_event_routes.go,
		// task_evidence_routes.go): one reader parses all three.
		item.Set("created_at", e.CreatedAt.UTC().Format(time.RFC3339))
		list = append(list, item)
	}

	out := taskdomain.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("events", list)
	out.Set("count", len(list))
	out.Set("after", after)
	out.Set("tip", tip)
	return out, nil
}

// SubmitLedgerIntents ports POST /api/v2/ledger/intents.
//
// THE ANSWER IS PER ITEM AND IN THE REQUEST'S ORDER, which is the contract and not a convenience: a
// batch is a client's outbox draining, so item N's answer has to be attributable to item N without
// the client matching anything up. Each answer is ONE of two disjoint shapes, told apart by which
// key it carries rather than by a second boolean beside the first:
//
//	{"accepted":true,"user_seq":…,"seq":…}          the entry that was written
//	{"rejected":true,"reason":"…","task_seq":…}     why it was not, and the seq it was refused against
//
// One discriminator, so there is nothing to keep in sync: no answer can say accepted and rejected at
// once, and none can say accepted=false while carrying an acceptance's sequence numbers.
func SubmitLedgerIntents(ctx context.Context, intents []ledgerentities.Intent, currentUser *authdomain.User,
	writer LedgerIntentWriter) ([]*taskdomain.OrderedMap[any], error) {
	userID := currentUserID(currentUser)

	answers, err := writer.SubmitIntents(ctx, userID, intents)
	if err != nil {
		return nil, httpErr(500, "Failed to record the intents")
	}

	out := make([]*taskdomain.OrderedMap[any], 0, len(answers))
	for _, a := range answers {
		item := taskdomain.NewOrderedMap[any]()
		if a.Accepted {
			item.Set("accepted", true)
			item.Set("user_seq", a.UserSeq)
			item.Set("seq", a.Seq)
		} else {
			item.Set("rejected", true)
			item.Set("reason", a.Reason)
			item.Set("task_seq", a.TaskSeq)
		}
		out = append(out, item)
	}
	return out, nil
}
