package httpapp

import (
	"context"

	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// contextEntityLookup is the git branch and task repository access create_context uses
// to auto-detect project_id and git_branch_id. The repositories are scoped to the
// request user, so a context cannot be attached to another user's branch or task.
type contextEntityLookup struct{ sessions *database.SessionManager }

func (l contextEntityLookup) BranchProjectID(ctx context.Context, userID *string, branchID string) (string, error) {
	repo, err := infrarepos.NewORMGitBranchRepository(l.sessions, userID, false)
	if err != nil {
		return "", err
	}
	branch, err := repo.FindByID(ctx, branchID, nil)
	if err != nil || branch == nil {
		return "", err
	}
	return branch.ProjectID, nil
}

func (l contextEntityLookup) TaskGitBranchID(ctx context.Context, userID *string, taskID string) (string, error) {
	repo, err := infrarepos.NewORMTaskRepository(l.sessions, nil, nil, nil, userID, false)
	if err != nil {
		return "", err
	}
	task, err := repo.GetTask(ctx, taskID)
	if err != nil || task == nil || task.GitBranchID == nil {
		return "", err
	}
	return *task.GitBranchID, nil
}
