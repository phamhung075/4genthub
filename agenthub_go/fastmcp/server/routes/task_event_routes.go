// task_event_routes.go holds the read path over the task-event ledger: one narrow interface and one
// handler, deliberately NOT folded into UserTaskController. That controller's adapter wraps
// TaskAPIController, so adding a method there would drag this change into api_controllers'
// crud_handler.go, which O1a must not touch. A separate small interface keeps the change in the
// files O1a owns.
package routes

import (
	"context"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
)

// TaskEventReader is the minimal read surface the handler needs, satisfied by the ledger's
// repository. It is user-scoped on purpose: the 404 for another user's task comes from the same
// seam GetUserTask uses, so the negative cannot be bypassed by filtering later.
type TaskEventReader interface {
	ListTaskEvents(ctx context.Context, taskID string, afterSeq int, userID string) ([]*taskdomain.TaskEvent, error)
}

// GetTaskEvents ports the ledger read (GET /{task_id}/events?after_seq=).
//
// IT ASKS FOR THE TASK FIRST, through the same controller GetUserTask uses, and reuses that
// handler's branch exactly: a task this user cannot see is !Success there and becomes the same 404,
// and the reader is never called. That ordering is the acceptance negative, not a convenience.
func GetTaskEvents(ctx context.Context, taskID string, afterSeq int, currentUser *authdomain.User,
	tasks UserTaskController, events TaskEventReader) (*taskdomain.OrderedMap[any], error) {
	userID := currentUserID(currentUser)

	result, err := tasks.GetTask(ctx, taskID, userID)
	if err != nil {
		return nil, httpErr(500, "Failed to get task")
	}
	if !result.Success {
		return nil, httpErr(404, "Task not found")
	}

	found, err := events.ListTaskEvents(ctx, taskID, afterSeq, userID)
	if err != nil {
		return nil, httpErr(500, "Failed to load task events")
	}

	list := make([]any, 0, len(found))
	for _, e := range found {
		item := taskdomain.NewOrderedMap[any]()
		item.Set("id", e.ID)
		item.Set("task_id", e.TaskID)
		item.Set("seq", e.Seq)
		item.Set("kind", string(e.Kind))
		item.Set("actor_kind", string(e.ActorKind))
		item.Set("actor_id", e.ActorID)
		item.Set("payload", e.Payload)
		item.Set("created_at", e.CreatedAt)
		list = append(list, item)
	}

	out := taskdomain.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("events", list)
	out.Set("count", len(list))
	out.Set("after_seq", afterSeq)
	return out, nil
}
