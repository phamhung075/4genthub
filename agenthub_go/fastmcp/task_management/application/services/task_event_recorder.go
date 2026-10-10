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
}

// NewTaskEventRecorder builds the recorder over whatever writes, and reads, the ledger.
func NewTaskEventRecorder(ledger TaskEventLedger) *TaskEventRecorder {
	return &TaskEventRecorder{ledger: ledger}
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
// task row holds after the write this entry shares a transaction with. actorID is the acting user,
// or StatusActorSystem when the path cannot name one.
func (r *TaskEventRecorder) RecordStatusChange(ctx context.Context, taskID, oldStatus, newStatus, actorID string) (*entities.TaskEvent, error) {
	actorKind := entities.TaskEventActorUser
	if actorID == entities.TaskEventActorSystemID || actorID == "" {
		actorID, actorKind = entities.TaskEventActorSystemID, entities.TaskEventActorSystem
	}
	return r.Record(ctx, taskID, entities.TaskEventKindStatusChanged, actorKind, actorID,
		map[string]any{"old": oldStatus, "new": newStatus})
}
