// context_ledger_appender.go holds the ONE writer of the task-level context event, and it lives here
// rather than in the application layer because the identity it must stamp is an HTTP/AUTH fact.
//
// WHAT WAS WRONG. The appender was `NewTaskEventRepository(sessions, "", "")`: one value, built once
// in NewApp, whose user_id was the empty string for EVERY caller. The task's own status and progress
// events are appended under the caller's resolved id, and the ledger's per-task seq is unique over
// (task_id, seq) - so a task whose context event was written first carried two spellings of one
// caller's rows, and the caller's own append computed a seq the empty id already held. The first
// update of a freshly created task answered
// `duplicate key value violates unique constraint "uq_task_event_seq"` (SQLSTATE 23505) deterministically,
// and the task could never carry its own state again. Measured on the deployed server 2026-10-15 on
// task 81c907dc: update failed with and without a status change, while get showed the row unchanged
// (the whole update transaction, this append included, rolled back).
//
// WHY THE CALLER CANNOT BE RESOLVED WHERE THE VALUE IS BUILT. The composition root runs before any
// request exists, so the only id it could stamp was the empty one. The caller is a property of the
// REQUEST, so it is resolved per append, from the same context the task ledger's own writes resolve
// it from and with the same normalization (auth_helper -> domain.ValidateUserID). That is what makes
// ONE history for one task: the context event and the status event land under ONE user id, the id the
// ledger's reads are scoped by.
//
// A REQUEST WHOSE CALLER CANNOT BE RESOLVED APPENDS NOTHING. The error travels up to the append site,
// which logs it: a row written under a guessed or empty id is a row that caller's own history will
// not show, and an absent event that is logged is recoverable where a misplaced one is not.
package httpapp

import (
	"context"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
	auth_helper "agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper"
)

// contextLedgerAppender writes the ledger's context events for the caller of the request in ctx.
type contextLedgerAppender struct{ sessions *database.SessionManager }

// Append writes one context event under the CALLER's resolved id. It opens its own transaction: the
// context service calls it after the context row write, outside any transaction of its own, so the
// entry cannot join one.
func (a contextLedgerAppender) Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error) {
	user, err := auth_helper.GetAuthenticatedUserID(ctx, nil, "task context event")
	if err != nil {
		return nil, err
	}
	return infrarepos.NewTaskEventRepository(a.sessions, user, "").Append(ctx, in)
}

// RecordContextUpdate writes the context_updated entry of one context write: the payload the change
// set and its caps are built into (entities.ContextUpdatePayload), attributed to the seat the request
// named, else the caller - the recorder's own order (services.ActorFor), not a literal `"context"`
// the two writers used to hardcode. Like Append it opens its own transaction, so it cannot use the
// recorder's transaction-bound write.
func (a contextLedgerAppender) RecordContextUpdate(ctx context.Context, taskID, level string, version int,
	origin string, changes []entities.ContextChange, dropped int) (*entities.TaskEvent, error) {
	user, err := auth_helper.GetAuthenticatedUserID(ctx, nil, "task context event")
	if err != nil {
		return nil, err
	}
	actor, ok := services.ActorFor(ctx, user)
	if !ok {
		return nil, services.ErrNoActor
	}
	return infrarepos.NewTaskEventRepository(a.sessions, user, "").Append(ctx, entities.AppendTaskEvent{
		TaskID:    taskID,
		Kind:      entities.TaskEventKindContextUpdated,
		ActorKind: actor.Kind,
		ActorID:   actor.ID,
		Payload:   entities.ContextUpdatePayload(level, taskID, version, origin, changes, dropped),
	})
}
