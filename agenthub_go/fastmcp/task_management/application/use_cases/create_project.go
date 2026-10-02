// This file ports task_management/application/use_cases/create_project.py.
package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateProjectHooks are the post-save side effects of create_project: the project
// context auto-creation and the WebSocket broadcast. They are best-effort (Python
// wraps both in try/except and only logs) and sit behind an interface because
// factories and services import this package.
type CreateProjectHooks interface {
	CreateProjectContext(ctx context.Context, project *entities.Project, userID *string)
	NotifyProjectCreated(ctx context.Context, project *entities.Project, userID *string)
}

// projectRepositoryUser is the Go form of Python's hasattr(repo, "user_id"); the
// ORM repositories expose it through the embedded UserScope.
type projectRepositoryUser interface {
	GetCurrentUserID() *string
}

// CreateProjectUseCase creates a new project and its default main task tree.
type CreateProjectUseCase struct {
	projectRepository repositories.ProjectRepository
	hooks             CreateProjectHooks
}

// WithHooks sets the side-effect hooks (nil disables them).
func (u *CreateProjectUseCase) WithHooks(h CreateProjectHooks) *CreateProjectUseCase {
	u.hooks = h
	return u
}

// NewCreateProjectUseCase builds the use case around a project repository.
func NewCreateProjectUseCase(projectRepository repositories.ProjectRepository) *CreateProjectUseCase {
	return &CreateProjectUseCase{projectRepository: projectRepository}
}

// createProjectError builds Python's {"success": False, "error": msg} result.
func createProjectError(message string) (*entities.OrderedMap[any], error) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", false)
	result.Set("error", message)
	return result, nil
}

// Execute runs the create-project use case. It supports the same two calling
// conventions as Python:
//
//  1. name provided: projectID is used when supplied, otherwise generated.
//  2. name nil: projectID is treated as the name and the ID is generated.
//
// The project context creation and WebSocket notification run through the hooks;
// both are best-effort and cannot change the returned dict.
func (u *CreateProjectUseCase) Execute(ctx context.Context, projectID *string, name *string, description string) (*entities.OrderedMap[any], error) {
	if name == nil {
		name = projectID
		projectID = nil
	}
	if name == nil {
		return createProjectError("Project name is required")
	}

	resolvedID := ""
	if projectID != nil {
		resolvedID = *projectID
	}
	if resolvedID == "" {
		resolvedID = value_objects.NewUUIDv4()
	}

	project, err := entities.CreateProject(*name, description)
	if err != nil {
		return createProjectError(err.Error())
	}
	parsedID, err := value_objects.NewProjectId(resolvedID)
	if err != nil {
		return createProjectError(err.Error())
	}
	project.ID = &parsedID

	if _, err := project.CreateGitBranch("main", "main", "Main task tree for the project"); err != nil {
		return createProjectError(err.Error())
	}
	if err := u.projectRepository.Save(ctx, project); err != nil {
		return createProjectError(err.Error())
	}

	if u.hooks != nil {
		var userID *string
		if r, ok := u.projectRepository.(projectRepositoryUser); ok {
			userID = r.GetCurrentUserID()
		}
		u.hooks.CreateProjectContext(ctx, project, userID)
		u.hooks.NotifyProjectCreated(ctx, project, userID)
	}

	branches := entities.NewOrderedMap[any]()
	if project.GitBranchs != nil {
		for _, branchID := range project.GitBranchs.Keys() {
			branch, _ := project.GitBranchs.Get(branchID)
			if branch != nil {
				branches.Set(branchID, branch.ToDict())
			}
		}
	}

	projectDict := entities.NewOrderedMap[any]()
	projectDict.Set("id", project.ID.Value)
	projectDict.Set("name", project.Name)
	projectDict.Set("description", project.Description)
	if project.CreatedAt != nil {
		projectDict.Set("created_at", value_objects.IsoFormat(*project.CreatedAt))
	} else {
		projectDict.Set("created_at", "")
	}
	if project.UpdatedAt != nil {
		projectDict.Set("updated_at", value_objects.IsoFormat(*project.UpdatedAt))
	} else {
		projectDict.Set("updated_at", "")
	}
	projectDict.Set("git_branchs", branches)

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("project", projectDict)
	return result, nil
}
