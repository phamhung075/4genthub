package httpapp

import (
	"context"

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
	repo := repositories.NewTaskEventRepository(a.sessions, userID, "")
	return repo.ListAfter(ctx, taskID, afterSeq, 0)
}
