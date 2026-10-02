package routes

import (
	"context"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/application/dtos/project"
	"agenthub/fastmcp/task_management/domain/entities"
)

// ProjectController is the minimal ProjectAPIController surface used by the
// routes (ctx first). The real controller is not ported yet.
type ProjectController interface {
	CreateProject(ctx context.Context, request project.CreateProjectRequest, userID string) (ControllerResult, error)
	ListProjects(ctx context.Context, userID string) (ControllerResult, error)
	GetProject(ctx context.Context, projectID, userID string) (ControllerResult, error)
	UpdateProject(ctx context.Context, projectID string, request project.UpdateProjectRequest, userID string) (ControllerResult, error)
	DeleteProject(ctx context.Context, projectID, userID string) (ControllerResult, error)
	GetProjectHealth(ctx context.Context, projectID, userID string) (ControllerResult, error)
}

// containsNotFound is `error and "not found" in error.lower()`.
func containsNotFound(v *string) bool {
	return v != nil && strings.Contains(strings.ToLower(*v), "not found")
}

// CreateProject is create_project POST /.
func CreateProject(ctx context.Context, name, description string, currentUser *authdomain.User, c ProjectController) (*entities.OrderedMap[any], error) {
	req := project.CreateProjectRequest{Name: name, Description: &description}
	result, err := c.CreateProject(ctx, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to create project")
	}
	if !result.Success {
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to create project"))
	}
	return result.Body, nil
}

// ListProjects is list_projects GET /. Python's `except Exception` also catches
// the HTTPException it raises, so any failure surfaces as the generic 500.
func ListProjects(ctx context.Context, currentUser *authdomain.User, c ProjectController) (*entities.OrderedMap[any], error) {
	result, err := c.ListProjects(ctx, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to list projects")
	}
	if !result.Success {
		return nil, httpErr(500, "Failed to list projects")
	}
	return result.Body, nil
}

// GetProject is get_project GET /{project_id}.
func GetProject(ctx context.Context, projectID string, currentUser *authdomain.User, c ProjectController) (*entities.OrderedMap[any], error) {
	result, err := c.GetProject(ctx, projectID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to get project")
	}
	if !result.Success {
		return nil, httpErr(404, "Project not found or access denied")
	}
	return result.Body, nil
}

// UpdateProject is update_project PUT /{project_id}.
func UpdateProject(ctx context.Context, projectID string, name, description *string, currentUser *authdomain.User, c ProjectController) (*entities.OrderedMap[any], error) {
	req := project.UpdateProjectRequest{ProjectID: projectID, Name: name, Description: description}
	result, err := c.UpdateProject(ctx, projectID, req, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to update project")
	}
	if !result.Success {
		if containsNotFound(result.Error) {
			return nil, httpErr(404, "Project not found or access denied")
		}
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to update project"))
	}
	return result.Body, nil
}

// DeleteProject is delete_project DELETE /{project_id}.
func DeleteProject(ctx context.Context, projectID string, currentUser *authdomain.User, c ProjectController) (*entities.OrderedMap[any], error) {
	result, err := c.DeleteProject(ctx, projectID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to delete project")
	}
	if !result.Success {
		if containsNotFound(result.Error) {
			return nil, httpErr(404, "Project not found or access denied")
		}
		return nil, httpErr(500, pyOrStr(result.Error, pyOrStr(result.Message, "Failed to delete project")))
	}
	return result.Body, nil
}

// ProjectHealthCheck is project_health_check POST /{project_id}/health-check.
func ProjectHealthCheck(ctx context.Context, projectID string, currentUser *authdomain.User, c ProjectController) (*entities.OrderedMap[any], error) {
	result, err := c.GetProjectHealth(ctx, projectID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to perform health check")
	}
	if !result.Success {
		if containsNotFound(result.Error) {
			return nil, httpErr(404, "Project not found or access denied")
		}
		return nil, httpErr(500, pyOrStr(result.Message, "Failed to check project health"))
	}
	return result.Body, nil
}
