package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// UpdateProjectUseCase ports update_project.UpdateProjectUseCase.
type UpdateProjectUseCase struct {
	projectRepository repositories.ProjectRepository
	hooks             UpdateProjectHooks
}

// UpdateProjectHooks is the best-effort WebSocket broadcast after an update (the
// notification service imports this package, so it is injected).
type UpdateProjectHooks interface {
	NotifyProjectUpdated(ctx context.Context, project *entities.Project, userID *string, updatedFields []string)
}

// WithHooks sets the broadcast hook (nil disables it).
func (u *UpdateProjectUseCase) WithHooks(h UpdateProjectHooks) *UpdateProjectUseCase {
	u.hooks = h
	return u
}

// NewUpdateProjectUseCase mirrors __init__(project_repository).
func NewUpdateProjectUseCase(projectRepository repositories.ProjectRepository) *UpdateProjectUseCase {
	return &UpdateProjectUseCase{projectRepository: projectRepository}
}

// updateProjectError builds {"success": False, "error": msg}.
func updateProjectError(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// Execute mirrors UpdateProjectUseCase.execute: name/description nil mean "leave
// unchanged" (Python None). The WebSocket broadcast runs through the hooks.
func (u *UpdateProjectUseCase) Execute(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error) {
	project, err := u.projectRepository.FindByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if project == nil {
		return updateProjectError(fmt.Sprintf("Project with ID '%s' not found", projectID)), nil
	}

	updatedFields := []string{}
	if name != nil {
		project.Name = *name
		updatedFields = append(updatedFields, "name")
	}
	if description != nil {
		project.Description = *description
		updatedFields = append(updatedFields, "description")
	}
	if len(updatedFields) == 0 {
		return updateProjectError("No fields to update. Provide name and/or description."), nil
	}

	if err := project.Touch("project_updated"); err != nil {
		return nil, err
	}
	if err := u.projectRepository.Update(ctx, project); err != nil {
		return nil, err
	}

	if u.hooks != nil {
		var userID *string
		if r, ok := u.projectRepository.(projectRepositoryUser); ok {
			userID = r.GetCurrentUserID()
		}
		u.hooks.NotifyProjectUpdated(ctx, project, userID, updatedFields)
	}

	projectDict := entities.NewOrderedMap[any]()
	projectDict.Set("id", project.ID.Value)
	projectDict.Set("name", project.Name)
	projectDict.Set("description", project.Description)
	projectDict.Set("created_at", value_objects.IsoFormat(*project.CreatedAt))
	projectDict.Set("updated_at", value_objects.IsoFormat(*project.UpdatedAt))

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("project", projectDict)
	result.Set("updated_fields", updatedFields)
	result.Set("message", fmt.Sprintf("Project '%s' updated successfully", projectID))
	return result, nil
}
