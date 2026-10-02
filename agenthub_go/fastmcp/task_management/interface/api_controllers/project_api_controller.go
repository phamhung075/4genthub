// Package api_controllers ports task_management/interface/api_controllers.
package api_controllers

import (
	"context"
	"fmt"
	"time"

	projectdto "agenthub/fastmcp/task_management/application/dtos/project"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/types"
)

// projFacadeProvider is the consumer-side view of the project facade factory the
// Python controller builds inline (ProjectApplicationFacade(user_id=user_id)).
// FacadeService.GetProjectFacade satisfies it.
type projFacadeProvider interface {
	CreateProjectFacade(userID *string) (*facades.ProjectApplicationFacade, error)
}

// ProjectAPIController mirrors project_api_controller.ProjectAPIController.
type ProjectAPIController struct {
	facadeProvider projFacadeProvider
}

// NewProjectAPIController builds the controller. Python resolves FacadeService
// lazily; the Go provider is injected.
func NewProjectAPIController(provider projFacadeProvider) *ProjectAPIController {
	return &ProjectAPIController{facadeProvider: provider}
}

// projACNow is datetime.now(UTC).isoformat().
func projACNow() *string {
	s := value_objects.IsoFormat(time.Now().UTC())
	return &s
}

// projACGet is dict.get(key) returning None when absent.
func projACGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// projACGetDefault is dict.get(key, def) (present-but-None stays None).
func projACGetDefault(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if v, ok := m.Get(key); ok {
			return v
		}
	}
	return def
}

// projACSuccess is result.get("success", True).
func projACSuccess(m *entities.OrderedMap[any]) bool {
	if m == nil {
		return false
	}
	v, ok := m.Get("success")
	if !ok {
		return true
	}
	return value_objects.PyTruthy(v)
}

func projACOptStr(v any) *string {
	if v == nil {
		return nil
	}
	s := value_objects.PyStr(v)
	return &s
}

func projACOptInt(v any) *int {
	if v == nil {
		return nil
	}
	f, ok := value_objects.PyFloat(v)
	if !ok {
		return nil
	}
	i := int(f)
	return &i
}

func projACOptBool(v any) *bool {
	if b, ok := v.(bool); ok {
		return &b
	}
	return nil
}

// projACBranchDTO mirrors BranchDTO(**branch_data) for a dict.
func projACBranchDTO(data *entities.OrderedMap[any]) *types.BranchDTO {
	name := projACGetDefault(data, "name", "")
	gitName := projACGetDefault(data, "git_branch_name", projACGetDefault(data, "name", ""))
	return &types.BranchDTO{
		ID:             value_objects.PyStr(projACGet(data, "id")),
		ProjectID:      value_objects.PyStr(projACGet(data, "project_id")),
		Name:           value_objects.PyStr(name),
		GitBranchName:  value_objects.PyStr(gitName),
		Description:    projACOptStr(projACGet(data, "description")),
		Status:         projACOptStr(projACGet(data, "status")),
		IsActive:       projACOptBool(projACGet(data, "is_active")),
		CreatedAt:      projACOptStr(projACGet(data, "created_at")),
		UpdatedAt:      projACOptStr(projACGet(data, "updated_at")),
		TaskCount:      projACOptInt(projACGet(data, "task_count")),
		CompletedTasks: projACOptInt(projACGet(data, "completed_tasks")),
	}
}

// projACProjectDTO mirrors ProjectDTO(**project_data) for a dict. ProjectDTO.id and name
// are required strings: pydantic raises a ValidationError for None (the facade's update
// wrapper carries neither), which the controllers report as a failed response.
func projACProjectDTO(data *entities.OrderedMap[any]) *types.ProjectDTO {
	for _, field := range []string{"id", "name"} {
		if projACGet(data, field) == nil {
			panic(fmt.Sprintf("1 validation error for ProjectDTO\n%s\n  Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]", field))
		}
	}
	dto := &types.ProjectDTO{
		ID:          value_objects.PyStr(projACGet(data, "id")),
		Name:        value_objects.PyStr(projACGet(data, "name")),
		Description: projACOptStr(projACGet(data, "description")),
		CreatedAt:   projACOptStr(projACGet(data, "created_at")),
		UpdatedAt:   projACOptStr(projACGet(data, "updated_at")),
		OwnerID:     projACOptStr(projACGet(data, "owner_id")),
		Status:      projACOptStr(projACGet(data, "status")),
		BranchCount: projACOptInt(projACGetDefault(data, "branch_count", 0)),
		TaskCount:   projACOptInt(projACGetDefault(data, "task_count", 0)),
	}
	if gb, ok := projACGet(data, "git_branchs").(*entities.OrderedMap[any]); ok && gb != nil {
		out := entities.NewOrderedMap[*types.BranchDTO]()
		for _, k := range gb.Keys() {
			v, _ := gb.Get(k)
			if child, ok := v.(*entities.OrderedMap[any]); ok {
				out.Set(k, projACBranchDTO(child))
			} else if child, ok := v.(map[string]any); ok {
				out.Set(k, projACBranchDTO(mapToOrdered(child)))
			}
		}
		dto.GitBranchs = out
	}
	if branches, ok := projACGet(data, "branches").([]any); ok {
		list := make([]*types.BranchDTO, 0, len(branches))
		for _, b := range branches {
			if child, ok := b.(*entities.OrderedMap[any]); ok {
				list = append(list, projACBranchDTO(child))
			} else if child, ok := b.(map[string]any); ok {
				list = append(list, projACBranchDTO(mapToOrdered(child)))
			}
		}
		dto.Branches = list
	}
	return dto
}

// mapToOrdered converts a Go map to an OrderedMap preserving an arbitrary but
// stable iteration order (used only for DTO field extraction of map inputs).
func mapToOrdered(m map[string]any) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	for k, v := range m {
		out.Set(k, v)
	}
	return out
}

// CreateProject mirrors create_project(request, user_id, session).
func (c *ProjectAPIController) CreateProject(ctx context.Context, request *projectdto.CreateProjectRequest, userID string, session any) (resp *types.ProjectResponse) {
	resp = &types.ProjectResponse{Success: false, Timestamp: projACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Project = nil
			resp.Error = projACPanicStr(r)
			resp.Message = strPtr("Failed to create project")
			resp.Timestamp = projACNow()
		}
	}()
	facade, err := c.facadeProvider.CreateProjectFacade(&userID)
	if err != nil {
		return projACFailure(err)
	}
	description := ""
	if request.Description != nil {
		description = *request.Description
	}
	result, err := facade.CreateProject(ctx, request.Name, description)
	if err != nil {
		return projACFailure(err)
	}
	if !projACSuccess(result) {
		errorMsg := value_objects.PyStr(projACGetDefault(result, "error", "Unknown error"))
		return &types.ProjectResponse{
			Success:   false,
			Project:   nil,
			Error:     &errorMsg,
			Message:   strPtr(value_objects.PyStr(projACGetDefault(result, "error", "Failed to create project"))),
			Timestamp: projACNow(),
		}
	}
	projectData, _ := projACGet(result, "project").(*entities.OrderedMap[any])
	return &types.ProjectResponse{
		Success:   true,
		Project:   projACProjectDTO(projectData),
		Message:   strPtr("Project created successfully"),
		Timestamp: projACNow(),
	}
}

// ListProjects mirrors list_projects(user_id, session).
func (c *ProjectAPIController) ListProjects(ctx context.Context, userID string, session any) (resp *types.ProjectsResponse) {
	resp = &types.ProjectsResponse{Success: false, Timestamp: projACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Projects = []*types.ProjectDTO{}
			resp.Error = projACPanicStr(r)
			resp.Message = strPtr("Failed to list projects")
			resp.Timestamp = projACNow()
		}
	}()
	facade, err := c.facadeProvider.CreateProjectFacade(&userID)
	if err != nil {
		return projACListFailure(err)
	}
	result, err := facade.ListProjects(ctx)
	if err != nil {
		return projACListFailure(err)
	}
	projects := projACAnySlice(projACGetDefault(result, "projects", []any{}))
	dtos := make([]*types.ProjectDTO, 0, len(projects))
	for _, p := range projects {
		if m, ok := p.(*entities.OrderedMap[any]); ok {
			dtos = append(dtos, projACProjectDTO(m))
		} else if m, ok := p.(map[string]any); ok {
			dtos = append(dtos, projACProjectDTO(mapToOrdered(m)))
		}
	}
	total := len(dtos)
	return &types.ProjectsResponse{
		Success:   true,
		Projects:  dtos,
		Total:     &total,
		Timestamp: projACNow(),
	}
}

// GetProject mirrors get_project(project_id, user_id, session).
func (c *ProjectAPIController) GetProject(ctx context.Context, projectID, userID string, session any) (resp *types.ProjectResponse) {
	resp = &types.ProjectResponse{Success: false, Timestamp: projACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Project = nil
			resp.Error = projACPanicStr(r)
			resp.Message = strPtr("Failed to get project")
			resp.Timestamp = projACNow()
		}
	}()
	facade, err := c.facadeProvider.CreateProjectFacade(&userID)
	if err != nil {
		return projACFailure(err)
	}
	projectResponse, err := facade.GetProject(ctx, projectID)
	if err != nil {
		return projACFailure(err)
	}
	if projectResponse == nil || !value_objects.PyTruthy(projACGet(projectResponse, "success")) {
		errorMsg := "Project not found"
		if projectResponse != nil {
			errorMsg = value_objects.PyStr(projACGetDefault(projectResponse, "error", "Project not found"))
		}
		return &types.ProjectResponse{
			Success:   false,
			Project:   nil,
			Error:     &errorMsg,
			Message:   strPtr("Project not found or access denied"),
			Timestamp: projACNow(),
		}
	}
	projectData, _ := projACGet(projectResponse, "project").(*entities.OrderedMap[any])
	return &types.ProjectResponse{
		Success:   true,
		Project:   projACProjectDTO(projectData),
		Timestamp: projACNow(),
	}
}

// UpdateProject mirrors update_project(project_id, request, user_id, session).
func (c *ProjectAPIController) UpdateProject(ctx context.Context, projectID string, request *projectdto.UpdateProjectRequest, userID string, session any) (resp *types.ProjectResponse) {
	resp = &types.ProjectResponse{Success: false, Timestamp: projACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Project = nil
			resp.Error = projACPanicStr(r)
			resp.Message = strPtr("Failed to update project")
			resp.Timestamp = projACNow()
		}
	}()
	facade, err := c.facadeProvider.CreateProjectFacade(&userID)
	if err != nil {
		return projACFailure(err)
	}
	existingProject, err := facade.GetProject(ctx, projectID)
	if err != nil {
		return projACFailure(err)
	}
	if existingProject == nil {
		return &types.ProjectResponse{
			Success:   false,
			Project:   nil,
			Error:     strPtr("Project not found"),
			Message:   strPtr("Project not found or access denied"),
			Timestamp: projACNow(),
		}
	}
	updated, err := facade.UpdateProject(ctx, projectID, request.Name, request.Description)
	if err != nil {
		return projACFailure(err)
	}
	return &types.ProjectResponse{
		Success:   true,
		Project:   projACProjectDTO(updated),
		Message:   strPtr("Project updated successfully"),
		Timestamp: projACNow(),
	}
}

// DeleteProject mirrors delete_project(project_id, user_id, session).
func (c *ProjectAPIController) DeleteProject(ctx context.Context, projectID, userID string, session any) (resp *types.DeleteResponse) {
	resp = &types.DeleteResponse{Success: false, Timestamp: projACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Deleted = boolPtr(false)
			resp.Error = projACPanicStr(r)
			resp.Message = strPtr("Failed to delete project")
			resp.Timestamp = projACNow()
		}
	}()
	facade, err := c.facadeProvider.CreateProjectFacade(&userID)
	if err != nil {
		return projACDeleteFailure(err)
	}
	existingProject, err := facade.GetProject(ctx, projectID)
	if err != nil {
		return projACDeleteFailure(err)
	}
	if existingProject == nil {
		return &types.DeleteResponse{
			Success:   false,
			Deleted:   boolPtr(false),
			Error:     strPtr("Project not found"),
			Message:   strPtr("Project not found or access denied"),
			Timestamp: projACNow(),
		}
	}
	result, err := facade.DeleteProject(ctx, projectID, false)
	if err != nil {
		return projACDeleteFailure(err)
	}
	if result != nil && value_objects.PyTruthy(projACGet(result, "success")) {
		id := projectID
		return &types.DeleteResponse{
			Success:   true,
			Deleted:   boolPtr(true),
			ID:        &id,
			Message:   strPtr("Project " + projectID + " deleted successfully"),
			Timestamp: projACNow(),
		}
	}
	errorMsg := "Deletion returned None"
	if result != nil {
		errorMsg = value_objects.PyStr(projACGetDefault(result, "error", "Unknown error during deletion"))
	}
	return &types.DeleteResponse{
		Success:   false,
		Deleted:   boolPtr(false),
		Error:     &errorMsg,
		Message:   strPtr("Failed to delete project"),
		Timestamp: projACNow(),
	}
}

// GetProjectHealth mirrors get_project_health(project_id, user_id, session).
func (c *ProjectAPIController) GetProjectHealth(ctx context.Context, projectID, userID string, session any) (resp *types.ApiResponse) {
	resp = &types.ApiResponse{Success: false, Timestamp: projACNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = projACPanicStr(r)
			resp.Message = strPtr("Failed to get project health")
			resp.Timestamp = projACNow()
		}
	}()
	facade, err := c.facadeProvider.CreateProjectFacade(&userID)
	if err != nil {
		return projACAPIError(err)
	}
	existingProject, err := facade.GetProject(ctx, projectID)
	if err != nil {
		return projACAPIError(err)
	}
	if existingProject == nil {
		return &types.ApiResponse{
			Success:   false,
			Error:     strPtr("Project not found"),
			Message:   strPtr("Project not found or access denied"),
			Timestamp: projACNow(),
		}
	}
	healthResult, err := facade.ProjectHealthCheck(ctx, projectID, nil)
	if err != nil {
		return projACAPIError(err)
	}
	data := any(nil)
	if healthResult != nil {
		data = healthResult
	}
	return &types.ApiResponse{
		Success:   true,
		Data:      data,
		Message:   strPtr("Project health retrieved successfully"),
		Timestamp: projACNow(),
	}
}

// --- small shared helpers (project file) ---

func projACPanicStr(r any) *string { return strPtr(value_objects.PyStr(r)) }
func strPtr(s string) *string      { return &s }
func boolPtr(b bool) *bool         { return &b }

func projACFailure(err error) *types.ProjectResponse {
	msg := err.Error()
	return &types.ProjectResponse{
		Success:   false,
		Project:   nil,
		Error:     &msg,
		Message:   strPtr("Failed to create project"),
		Timestamp: projACNow(),
	}
}

func projACListFailure(err error) *types.ProjectsResponse {
	msg := err.Error()
	return &types.ProjectsResponse{
		Success:   false,
		Projects:  []*types.ProjectDTO{},
		Error:     &msg,
		Message:   strPtr("Failed to list projects"),
		Timestamp: projACNow(),
	}
}

func projACDeleteFailure(err error) *types.DeleteResponse {
	msg := err.Error()
	return &types.DeleteResponse{
		Success:   false,
		Deleted:   boolPtr(false),
		Error:     &msg,
		Message:   strPtr("Failed to delete project"),
		Timestamp: projACNow(),
	}
}

func projACAPIError(err error) *types.ApiResponse {
	msg := err.Error()
	return &types.ApiResponse{
		Success:   false,
		Error:     &msg,
		Message:   strPtr("Failed to get project health"),
		Timestamp: projACNow(),
	}
}

func projACAnySlice(v any) []any {
	if s, ok := v.([]any); ok {
		return s
	}
	return nil
}
