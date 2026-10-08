package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TaskEventAppender is the write side the recorder needs, declared here so this application
// service depends on a shape rather than on the infrastructure package that implements it. The
// repository satisfies it; nothing else should.
type TaskEventAppender interface {
	Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error)
}

// TaskEventRecorder is the ONE writer of the task-event ledger.
//
// NOTHING EMITS EVENTS YET: O1a is purely additive, so this exists to be the single seam that the
// status and update paths will call later. One API, one place where a ledger entry is shaped,
// rather than every caller assembling one from scratch.
//
// KNOWN DEVIATION, RECORDED RATHER THAN HIDDEN: the decision note asks for one writer API that
// takes the caller's transaction, so an entry lands in the same transaction as the change it
// describes rather than beside it. It does NOT yet do that - it wraps the repository's Append,
// which opens its own transaction. That is deliberate for this slice, because no caller exists to
// supply a transaction and the sequence guarantee is already transaction-scoped; when the first
// real emitter arrives, the repository needs an AppendInTx(ctx, tx, in) and this signature needs
// to take the tx. Named here so that is a decision the next seat makes, not a discovery.
type TaskEventRecorder struct {
	appender TaskEventAppender
}

// NewTaskEventRecorder builds the recorder over whatever writes the ledger.
func NewTaskEventRecorder(appender TaskEventAppender) *TaskEventRecorder {
	return &TaskEventRecorder{appender: appender}
}

// Record writes one entry for a task and returns it with the sequence the database assigned.
func (r *TaskEventRecorder) Record(ctx context.Context, taskID string, kind entities.TaskEventKind,
	actorKind entities.TaskEventActorKind, actorID string, payload map[string]any) (*entities.TaskEvent, error) {
	return r.appender.Append(ctx, entities.AppendTaskEvent{
		TaskID:    taskID,
		Kind:      kind,
		ActorKind: actorKind,
		ActorID:   actorID,
		Payload:   payload,
	})
}
