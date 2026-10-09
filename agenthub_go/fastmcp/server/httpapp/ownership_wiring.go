package httpapp

import (
	"context"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ownershipChecker answers routes.OwnershipChecker from the tables themselves.
//
// WHY THIS EXISTS. routes.Ownership is an injected global that no production code assigned, so it
// stayed nil and CheckResourceOwnership fell through to its environment fallback for every value of
// ENVIRONMENT except exactly "development": production refused every system-triggered cross-user
// frame, development delivered it to every connection. Python has no seam here - its
// _check_resource_ownership queries Task/Subtask/ProjectGitBranch/Project directly, filtered by
// user_id - and the four queries below are that function's four branches, read from git history
// because the Python backend is retired from the tree. NewApp assigns this so Rule 2 consults real
// ownership; the environment fallback stays what it is in the reference: the answer when the check
// cannot be made at all, failing closed in production.
type ownershipChecker struct{ sessions *database.SessionManager }

var _ routes.OwnershipChecker = ownershipChecker{}

func (o ownershipChecker) TaskOwnedBy(ctx context.Context, taskID, userID string) (bool, error) {
	return o.rowExists(ctx, `SELECT COUNT(*) FROM tasks WHERE id = $1::uuid AND user_id = $2`, taskID, userID)
}

// SubtaskParentOwnedBy is Python's no-metadata branch: the parent task is read from the subtask row,
// and ownership is the parent's user_id - not the subtask's.
func (o ownershipChecker) SubtaskParentOwnedBy(ctx context.Context, subtaskID, userID string) (bool, error) {
	return o.rowExists(ctx, `SELECT COUNT(*) FROM subtasks s JOIN tasks t ON t.id = s.task_id
		WHERE s.id = $1::uuid AND t.user_id = $2`, subtaskID, userID)
}

func (o ownershipChecker) BranchOwnedBy(ctx context.Context, branchID, userID string) (bool, error) {
	return o.rowExists(ctx, `SELECT COUNT(*) FROM project_git_branchs WHERE id = $1::uuid AND user_id = $2`, branchID, userID)
}

func (o ownershipChecker) ProjectOwnedBy(ctx context.Context, projectID, userID string) (bool, error) {
	return o.rowExists(ctx, `SELECT COUNT(*) FROM projects WHERE id = $1::uuid AND user_id = $2`, projectID, userID)
}

// rowExists COUNTS rather than selecting a row: COUNT always answers, so a real failure is never
// confused with "no such row" and no driver-specific not-found error has to be classified here. An
// error is returned as an error, never as "not owned" - CheckResourceOwnership treats it as "cannot
// tell" and falls through to the environment answer.
func (o ownershipChecker) rowExists(ctx context.Context, query string, args ...any) (bool, error) {
	var n int
	err := o.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, query, args...).Scan(&n)
	})
	if err != nil {
		return false, err
	}
	return n > 0, nil
}

// wireOwnershipChecker assigns the checker Rule 2 of IsUserAuthorizedForMessage consults through
// CheckResourceOwnership. Same defect class as wireMissedNotificationStore next door: an injected
// global that no production code assigned, so the behaviour fell to a fallback nobody chose.
func wireOwnershipChecker(sessions *database.SessionManager) {
	routes.Ownership = ownershipChecker{sessions: sessions}
}
