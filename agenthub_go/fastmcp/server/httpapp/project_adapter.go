package httpapp

import (
	"context"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/application/dtos/project"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/api_controllers"
	"agenthub/fastmcp/types"
)

// modelDumper is the shared surface of the API response types.
type modelDumper interface {
	ModelDump() *entities.OrderedMap[any]
}

// projectControllerAdapter satisfies routes.ProjectController over the real
// ProjectAPIController, whose methods return typed pydantic-style responses.
type projectControllerAdapter struct {
	c *api_controllers.ProjectAPIController
}

func result(success bool, errMsg, msg *string, d modelDumper) (routes.ControllerResult, error) {
	return routes.ControllerResult{Success: success, Error: errMsg, Message: msg, Body: d.ModelDump()}, nil
}

func (a projectControllerAdapter) CreateProject(ctx context.Context, req project.CreateProjectRequest, userID string) (routes.ControllerResult, error) {
	r := a.c.CreateProject(ctx, &req, userID, nil)
	return result(r.Success, r.Error, r.Message, r)
}

func (a projectControllerAdapter) ListProjects(ctx context.Context, userID string) (routes.ControllerResult, error) {
	r := a.c.ListProjects(ctx, userID, nil)
	return result(r.Success, r.Error, r.Message, r)
}

func (a projectControllerAdapter) GetProject(ctx context.Context, projectID, userID string) (routes.ControllerResult, error) {
	r := a.c.GetProject(ctx, projectID, userID, nil)
	return result(r.Success, r.Error, r.Message, r)
}

func (a projectControllerAdapter) UpdateProject(ctx context.Context, projectID string, req project.UpdateProjectRequest, userID string) (routes.ControllerResult, error) {
	r := a.c.UpdateProject(ctx, projectID, &req, userID, nil)
	return result(r.Success, r.Error, r.Message, r)
}

func (a projectControllerAdapter) DeleteProject(ctx context.Context, projectID, userID string) (routes.ControllerResult, error) {
	r := a.c.DeleteProject(ctx, projectID, userID, nil)
	return result(r.Success, r.Error, r.Message, r)
}

func (a projectControllerAdapter) GetProjectHealth(ctx context.Context, projectID, userID string) (routes.ControllerResult, error) {
	r := a.c.GetProjectHealth(ctx, projectID, userID, nil)
	return result(r.Success, r.Error, r.Message, r)
}

var (
	_ modelDumper = (*types.ProjectResponse)(nil)
	_ modelDumper = (*types.ProjectsResponse)(nil)
	_ modelDumper = (*types.DeleteResponse)(nil)
	_ modelDumper = (*types.ApiResponse)(nil)
)
