package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TaskEventLedger is the ledger as the recorder needs it: the entry write, and the task's stored
// status. Declared here so this application service depends on a shape rather than on the
// infrastructure package that implements it. The repository satisfies it; nothing else should.
//
// Both methods REQUIRE an open transaction on the context and refuse without one. That is what
// makes "the status and its entry in one transaction" a property rather than a hope, and it is why
// the entry can report the transition the row actually made: the statuses are read inside the same
// transaction as the write, before and after it.
type TaskEventLedger interface {
	AppendInTx(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error)
	StatusOf(ctx context.Context, taskID string) (string, error)
}

// TaskEventRecorder is the ONE writer of the task-event ledger.
//
// It takes the CALLER's transaction. Record refuses when the context carries none, so an entry can
// never be committed beside the status it describes: a caller opens one transaction, makes the
// status write and this call inside it, and a failure in either rolls both back.
type TaskEventRecorder struct {
	ledger TaskEventLedger
	// userID is whom this recorder's writes belong to when the request named no one else: the
	// composition root builds one recorder per user, so this is the only place that knows whose
	// tree these entries land in. A request carrying a seat header is attributed to that seat
	// instead - see actorFor.
	userID string
}

// NewTaskEventRecorder builds the recorder over whatever writes, and reads, the ledger, with the
// user whose writes these are as the attribution of last resort.
func NewTaskEventRecorder(ledger TaskEventLedger, userID string) *TaskEventRecorder {
	return &TaskEventRecorder{ledger: ledger, userID: userID}
}

// StatusOf reads the task's stored status inside the caller's transaction, which is what lets an
// entry report the transition the row made.
func (r *TaskEventRecorder) StatusOf(ctx context.Context, taskID string) (string, error) {
	return r.ledger.StatusOf(ctx, taskID)
}

// Record writes one entry for a task and returns it with the sequence the database assigned. It
// must be called inside the caller's transaction; without one the ledger refuses.
func (r *TaskEventRecorder) Record(ctx context.Context, taskID string, kind entities.TaskEventKind,
	actorKind entities.TaskEventActorKind, actorID string, payload map[string]any) (*entities.TaskEvent, error) {
	return r.ledger.AppendInTx(ctx, entities.AppendTaskEvent{
		TaskID:    taskID,
		Kind:      kind,
		ActorKind: actorKind,
		ActorID:   actorID,
		Payload:   payload,
	})
}

// RecordStatusChange writes the entry for one status transition, carrying the old and the new
// status. `new` is the key the parity check reads against tasks.status, so it is the status the
// task row holds after the write this entry shares a transaction with.
//
// WHO the write is attributed to is settled HERE, once, rather than by every caller passing a name
// it had to invent: a request that named a seat through the MCP header is an agent acting on the
// caller's behalf, and a request that named no seat belongs to the user this recorder was built
// for. Only a recorder built with no user at all - which no production wiring does - falls back to
// the system.
func (r *TaskEventRecorder) RecordStatusChange(ctx context.Context, taskID, oldStatus, newStatus string) (*entities.TaskEvent, error) {
	actor := r.actorFor(ctx)
	return r.Record(ctx, taskID, entities.TaskEventKindStatusChanged, actor.Kind, actor.ID,
		map[string]any{"old": oldStatus, "new": newStatus})
}

func (r *TaskEventRecorder) actorFor(ctx context.Context) Actor {
	if actor, ok := ActorFromContext(ctx); ok {
		return actor
	}
	if r.userID != "" {
		return Actor{Kind: entities.TaskEventActorUser, ID: r.userID}
	}
	return Actor{Kind: entities.TaskEventActorSystem, ID: entities.TaskEventActorSystemID}
}

// Actor is WHO a write is attributed to, in the two shapes a request can name: a seat, which is an
// agent acting on the caller's behalf, or the user themselves. It is ATTRIBUTION and never
// authorization - nothing may decide access from it, which is why a header can carry it at all.
type Actor struct {
	Kind entities.TaskEventActorKind
	ID   string
}

type actorContextKey struct{}

// WithActor stamps the actor a request named onto its context. The interface layer sets it where it
// reads the request, exactly as the authenticated user and the public origin already travel, so an
// application service can attribute a write without every caller threading a name through.
func WithActor(ctx context.Context, actor Actor) context.Context {
	return context.WithValue(ctx, actorContextKey{}, actor)
}

// ActorFromContext reads the actor the request named, if it named one.
func ActorFromContext(ctx context.Context) (Actor, bool) {
	actor, ok := ctx.Value(actorContextKey{}).(Actor)
	return actor, ok
}

// SeatActor is an agent acting on the user's behalf, named by the seat identity `<room>/<seat>` the
// rendered MCP header carries. The architecture names this identity `seat`; the landed task_events
// vocabulary spells the class `agent`, and P1 lands the architecture's spelling.
func SeatActor(seatID string) Actor {
	return Actor{Kind: entities.TaskEventActorAgent, ID: seatID}
}
