package use_cases

import (
	"context"
	"errors"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateGitBranchUseCase ports create_git_branch.CreateGitBranchUseCase.
type CreateGitBranchUseCase struct {
	projectRepository repositories.ProjectRepository
}

// NewCreateGitBranchUseCase mirrors __init__(project_repository).
func NewCreateGitBranchUseCase(projectRepository repositories.ProjectRepository) *CreateGitBranchUseCase {
	return &CreateGitBranchUseCase{projectRepository: projectRepository}
}

// createGitBranchError builds {"success": False, "error": msg}.
func createGitBranchError(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// smallUCAsValueError reports whether err is a Python ValueError equivalent, which
// the Python use case catches and turns into an error response.
func smallUCAsValueError(err error) (*value_objects.ValueError, bool) {
	var ve *value_objects.ValueError
	if errors.As(err, &ve) {
		return ve, true
	}
	return nil, false
}

// Execute mirrors CreateGitBranchUseCase.execute. branchDescription default "".
//
// The nested branch-context creation is a no-op in Python: there is no Flask
// request user and AuthConfig has no is_default_user_allowed, so the AttributeError
// (or UserAuthenticationRequiredError) is swallowed before any context is created.
func (u *CreateGitBranchUseCase) Execute(ctx context.Context, projectID, gitBranchName, branchName, branchDescription string) (*entities.OrderedMap[any], error) {
	project, err := u.projectRepository.FindByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if project == nil {
		return createGitBranchError(fmt.Sprintf("Project with ID '%s' not found", projectID)), nil
	}

	gitBranch, err := project.CreateGitBranch(gitBranchName, branchName, branchDescription)
	if err != nil {
		if ve, ok := smallUCAsValueError(err); ok {
			return createGitBranchError(ve.Msg), nil
		}
		return nil, err
	}

	if err := u.projectRepository.Save(ctx, project); err != nil {
		if ve, ok := smallUCAsValueError(err); ok {
			return createGitBranchError(ve.Msg), nil
		}
		return nil, err
	}

	branchDict := entities.NewOrderedMap[any]()
	branchDict.Set("id", gitBranch.ID.Value)
	branchDict.Set("name", gitBranch.Name)
	branchDict.Set("description", gitBranch.Description)
	branchDict.Set("project_id", gitBranch.ProjectID)
	branchDict.Set("created_at", value_objects.IsoFormat(*gitBranch.CreatedAt))
	branchDict.Set("completed_tasks", gitBranch.GetCompletedTaskCount())
	branchDict.Set("progress", gitBranch.GetProgressPercentage())

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("git_branch", branchDict)
	result.Set("message", fmt.Sprintf("Git branch '%s' created successfully", gitBranchName))
	return result, nil
}
