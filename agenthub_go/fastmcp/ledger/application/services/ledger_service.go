// Package services holds the ledger's application service: the one place that decides what a client
// intent owes, and the read that carries a client's cursor across all of its tasks.
//
// IT IS NEITHER O1a NOR O1b. O1a's reader is per TASK and its writer is the platform acting on its
// own; this service is the client PUSHING its offline work and PULLING everything since a cursor,
// which is D9's part 1 (architecture agenthub-system-architecture.md, its "#### Part 1: the sync and
// event model" heading).
//
// THE RULE IT IMPLEMENTS IS ONE SENTENCE, the D9 decision's own (architecture
// agenthub-system-architecture.md): facts sync, decisions sequence. A fact is
// append-only and is never refused for being late. A decision carries the task seq the client had
// seen and is refused when something that is NOT a fact happened after it - the client's claim,
// transition or verdict was formed against a history that has since moved, and claims and verdicts
// do not commute (D9's option B).
package services

import (
	"context"
	"strings"

	ledgerentities "agenthub/fastmcp/ledger/domain/entities"
	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Ledger is the ledger as this service needs it: the appends, the reads the decision turns on, and
// the transaction they must share. Declared here so the application service depends on a shape
// rather than on the infrastructure package that implements it, the discipline
// task_event_recorder.go states for its own port. The task_events repository satisfies it, and
// nothing else should.
//
// WHY AppendInTx RATHER THAN THE RECORDER: TaskEventRecorder.Record's signature has no room for the
// outbox key or the subtask an intent may name, and both are part of what the entry IS. The
// recorder's other job - settling attribution - is done by the interface layer here exactly as the
// evidence route does it, and handed in as an actor, so the entry is still written by the same
// primitive the recorder itself calls.
type Ledger interface {
	// Transaction runs fn in one transaction. The DECISION and the APPEND it justifies must share
	// one: a decision read beside the append it gates could see a different ledger than the append
	// lands in.
	Transaction(ctx context.Context, fn func(ctx context.Context) error) error
	// LockUser takes the ledger's per-user append lock inside the caller's transaction, BEFORE the
	// reads the decision turns on, so no append for this user can slip between the read and the
	// append. It is the same lock AppendInTx takes.
	LockUser(ctx context.Context) error
	// ListUserAfter returns the user's entries strictly after a user_seq, oldest first, across ALL
	// of the user's tasks - the cursor the per-task reader does not carry.
	ListUserAfter(ctx context.Context, afterUserSeq int64, limit int) ([]*taskentities.TaskEvent, error)
	// UserTip is the user's current tip: the highest user_seq the user's ledger holds, 0 when it
	// holds none. It is what tells a client how far behind the cursor is.
	UserTip(ctx context.Context) (int64, error)
	// FindByClientEventID returns the entry one outbox key wrote. It is the whole idempotency of an
	// ACCEPTED intent: the row IS the first answer.
	FindByClientEventID(ctx context.Context, clientEventID string) (*taskentities.TaskEvent, bool, error)
	// CurrentTaskSeq is the task's seq as it stands: the number a decision's base_seq is compared
	// against.
	CurrentTaskSeq(ctx context.Context, taskID string) (int, error)
	// HasNonFactAfter reports whether anything that is not one of factKinds happened on the task
	// after afterSeq. The vocabulary is a parameter because which kinds are facts is this package's
	// rule, not the repository's.
	HasNonFactAfter(ctx context.Context, taskID string, afterSeq int, factKinds []string) (bool, error)
	// TaskVisible reports whether the task exists AND belongs to this repository's user. A ledger
	// entry is never appended to a task its writer cannot see.
	TaskVisible(ctx context.Context, taskID string) (bool, error)
	// EventInTask reports whether an entry id names a row OF taskID that this repository's user can
	// see. It is the same table the handover is appended to, so an `evt:` ref naming another task's
	// entry is a lie the server catches inside its own transaction, with no cross-store read.
	EventInTask(ctx context.Context, taskID, eventID string) (bool, error)
	// SubtaskInTask reports whether the subtask exists, belongs to this repository's user, AND
	// belongs to taskID. An intent may name a subtask, and task_events' only foreign key is on
	// task_id, so this is the check that keeps a row from attaching to another user's subtask - or
	// to a subtask of a different task. The three questions are one query and one refusal.
	SubtaskInTask(ctx context.Context, taskID, subtaskID string) (bool, error)
	// AppendInTx writes one entry inside the caller's transaction and returns it with the sequences
	// the database assigned.
	AppendInTx(ctx context.Context, in taskentities.AppendTaskEvent) (*taskentities.TaskEvent, error)
}

// Service is the ledger's application service for ONE user: the repository it holds is already
// scoped to that user, so every read and every write this service makes is user-isolated by
// construction rather than by a filter each method has to remember.
type Service struct {
	ledger Ledger
}

// New builds the service over whatever reads and writes the ledger.
func New(ledger Ledger) *Service { return &Service{ledger: ledger} }

// Page is one window of the cross-task read plus the user's current tip. The two are NOT the same
// number: the tip names the highest user_seq the user's ledger holds, so a client that has read
// this page knows exactly how far it still is from the end.
type Page struct {
	Events []*taskentities.TaskEvent
	Tip    int64
}

// ReadAfter returns the user's entries strictly after a user_seq, oldest first, and the user's
// current tip. after=0 is therefore the whole ledger, and a client that has seen N asks for N and
// gets only what is new.
//
// THE TIP IS READ AFTER THE PAGE, and that ordering is the invariant: with both reads taken
// separately, a tip read FIRST could name a lower user_seq than an entry the page went on to carry,
// which would tell a client that it is at the end while it is not. Read second, the tip can only
// name MORE than the page carries, which is exactly what "the current tip" means.
func (s *Service) ReadAfter(ctx context.Context, after int64, limit int) (Page, error) {
	events, err := s.ledger.ListUserAfter(ctx, after, limit)
	if err != nil {
		return Page{}, err
	}
	tip, err := s.ledger.UserTip(ctx)
	if err != nil {
		return Page{}, err
	}
	return Page{Events: events, Tip: tip}, nil
}

// SubmitIntents decides and records one batch, and answers PER ITEM in the order the items arrived.
// Arrival order is not a detail: an accepted item's user_seq is taken under the ledger's per-user
// lock in the order the loop reaches it, which is what makes "a fact recorded offline is accepted in
// arrival order" the server's behaviour and not the client's hope.
//
// One item's failure to be decided is an error for the whole call - only a database fault can do
// that - while a REFUSAL is an ordinary answer for that item and the batch goes on.
func (s *Service) SubmitIntents(ctx context.Context, actorKind taskentities.TaskEventActorKind,
	actorID string, intents []ledgerentities.Intent) ([]ledgerentities.Answer, error) {
	answers := make([]ledgerentities.Answer, 0, len(intents))
	for _, in := range intents {
		answer, err := s.submitOne(ctx, actorKind, actorID, in)
		if err != nil {
			return nil, err
		}
		answers = append(answers, answer)
	}
	return answers, nil
}

// submitOne decides and, when the item is accepted, appends it - all inside ONE transaction that
// takes the ledger's per-user append lock before it reads.
//
// THE LOCK BEFORE THE READ IS THE POINT, and it is the same shape the evidence route uses: without
// it two intents for one user could both read "the base is fresh" and both append, which is exactly
// the double claim a decision's base_seq exists to prevent.
func (s *Service) submitOne(ctx context.Context, actorKind taskentities.TaskEventActorKind,
	actorID string, in ledgerentities.Intent) (ledgerentities.Answer, error) {
	// The outbox key is canonicalised first: it is what the row is found by, and the column is a
	// UUID, so a key that is not one cannot be looked up or written.
	clientEventID, ok := value_objects.PyParseUUID(strings.TrimSpace(in.ClientEventID))
	if !ok {
		return ledgerentities.Refusal(ledgerentities.ReasonInvalidClientEventID, 0), nil
	}

	answer := ledgerentities.Answer{}
	err := s.ledger.Transaction(ctx, func(ctx context.Context) error {
		if err := s.ledger.LockUser(ctx); err != nil {
			return err
		}

		// THE RESEND IS ANSWERED FROM THE ROW, and this comes FIRST: resending a client_event_id
		// returns the FIRST answer, and the first answer of an accepted intent IS the entry. The
		// lookup is inside the transaction, under the lock, so a second request carrying the same
		// key sees the first one's committed row rather than racing it into the unique constraint.
		//
		// A REFUSED item wrote nothing and so is NOT remembered: re-staging a rejected decision is
		// the client's whole remedy (`a decision staged on a stale base succeeds once the client
		// re-reads`), and memoising the refusal would make that impossible. That asymmetry is
		// deliberate and is what the box's two checks together require.
		if row, found, err := s.ledger.FindByClientEventID(ctx, clientEventID); err != nil {
			return err
		} else if found {
			answer = ledgerentities.Acceptance(row.UserSeq, row.Seq)
			return nil
		}

		if !ledgerentities.IsIntentKind(string(in.Kind)) {
			answer = ledgerentities.Refusal(ledgerentities.ReasonUnsupportedKind, 0)
			return nil
		}

		taskID, ok := value_objects.PyParseUUID(strings.TrimSpace(in.TaskID))
		if !ok {
			answer = ledgerentities.Refusal(ledgerentities.ReasonUnknownTask, 0)
			return nil
		}
		visible, err := s.ledger.TaskVisible(ctx, taskID)
		if err != nil {
			return err
		}
		if !visible {
			answer = ledgerentities.Refusal(ledgerentities.ReasonUnknownTask, 0)
			return nil
		}

		// THE HANDOVER PAYLOAD IS PART OF THE KIND GATE. It runs here rather than in the route for the
		// reason the kind check does: the outbox and any future writer pass through this one place,
		// so no writer can append a decision record that skips the shape. The task identity is
		// already resolved above, which is what makes the evt: check a same-task check.
		if in.Kind == ledgerentities.IntentKindHandover {
			reason, err := ledgerentities.ValidateHandoverPayload(in.Payload,
				func(eventID string) (bool, error) {
					return s.ledger.EventInTask(ctx, taskID, eventID)
				})
			if err != nil {
				return err
			}
			if reason != "" {
				answer = ledgerentities.Refusal(reason, 0)
				return nil
			}
		}

		subtaskID := ""
		if trimmed := strings.TrimSpace(in.SubtaskID); trimmed != "" {
			canonical, ok := value_objects.PyParseUUID(trimmed)
			if !ok {
				answer = ledgerentities.Refusal(ledgerentities.ReasonInvalidSubtaskID, 0)
				return nil
			}
			subtaskID = canonical
			// THE REFERENCE IS CHECKED BESIDE THE TASK, for the reason TaskVisible's own comment
			// gives: the foreign key on task_id cannot reach a subtask, so a subtask_id naming
			// another user's row - or another task's - would satisfy every constraint the table has
			// and land in this user's ledger. The check runs BEFORE the decision reads, so a refused
			// item costs no sequence and is not remembered (a refusal writes nothing).
			inTask, err := s.ledger.SubtaskInTask(ctx, taskID, subtaskID)
			if err != nil {
				return err
			}
			if !inTask {
				answer = ledgerentities.Refusal(ledgerentities.ReasonUnknownSubtask, 0)
				return nil
			}
		}

		var payload map[string]any
		if in.Payload != nil {
			object, ok := in.Payload.(map[string]any)
			if !ok {
				answer = ledgerentities.Refusal(ledgerentities.ReasonInvalidPayload, 0)
				return nil
			}
			payload = object
		}

		// A FACT owes nothing: it is append-only, and it is never refused for being late.
		if in.Kind.IsFact() {
			return s.append(ctx, actorKind, actorID, in, taskID, subtaskID, clientEventID, payload, &answer)
		}

		// A DECISION owes base_seq. The task's seq is read before the check so that even the
		// "no base_seq" refusal can name the number the client should stage on next.
		current, err := s.ledger.CurrentTaskSeq(ctx, taskID)
		if err != nil {
			return err
		}
		if in.BaseSeq == nil {
			answer = ledgerentities.Refusal(ledgerentities.ReasonBaseSeqRequired, current)
			return nil
		}
		stale, err := s.ledger.HasNonFactAfter(ctx, taskID, *in.BaseSeq, ledgerentities.FactKindStrings())
		if err != nil {
			return err
		}
		if stale {
			answer = ledgerentities.Refusal(ledgerentities.ReasonStaleBaseSeq, current)
			return nil
		}
		return s.append(ctx, actorKind, actorID, in, taskID, subtaskID, clientEventID, payload, &answer)
	})
	if err != nil {
		return ledgerentities.Answer{}, err
	}
	return answer, nil
}

// append writes one accepted item's entry through the ledger's append primitive and fills in the
// answer with the sequences the row took.
func (s *Service) append(ctx context.Context, actorKind taskentities.TaskEventActorKind, actorID string,
	in ledgerentities.Intent, taskID, subtaskID, clientEventID string, payload map[string]any,
	answer *ledgerentities.Answer) error {
	event, err := s.ledger.AppendInTx(ctx, taskentities.AppendTaskEvent{
		TaskID:        taskID,
		SubtaskID:     subtaskID,
		Kind:          taskentities.TaskEventKind(in.Kind),
		ActorKind:     actorKind,
		ActorID:       actorID,
		Payload:       payload,
		ClientEventID: clientEventID,
	})
	if err != nil {
		return err
	}
	*answer = ledgerentities.Acceptance(event.UserSeq, event.Seq)
	return nil
}
