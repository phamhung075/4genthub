package handlers

// Project CRUD Handler (Python crud_handler.py).

import (
	"context"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

// ResponseFormatter is the minimal view of the interface-layer
// StandardResponseFormatter (task_management/interface/utils/response_formatter.py)
// that these handlers use. That module has no Go port yet; the interface is
// declared here and reported as a dependency.
type ResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// ErrorCodes constants (interface/utils/response_formatter.py ErrorCodes).
const (
	ErrorCodeOperationFailed = "OPERATION_FAILED"
	ErrorCodeValidationError = "VALIDATION_ERROR"
	ErrorCodeInternalError   = "INTERNAL_ERROR"
)

func metaMap(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

// successFalse mirrors `isinstance(result, dict) and result.get("success") is False`.
func successFalse(result *entities.OrderedMap[any]) bool {
	if result == nil {
		return false
	}
	v, ok := result.Get("success")
	return ok && v == false
}

// ProjectCRUDHandler ports ProjectCRUDHandler.
type ProjectCRUDHandler struct {
	responseFormatter ResponseFormatter
}

// NewProjectCRUDHandler ports __init__(response_formatter).
func NewProjectCRUDHandler(responseFormatter ResponseFormatter) *ProjectCRUDHandler {
	return &ProjectCRUDHandler{responseFormatter: responseFormatter}
}

// CreateProject ports create_project(facade, name, description=None, user_id=None).
func (h *ProjectCRUDHandler) CreateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, name string, description, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("create", "Failed to create project: "+panicMessage(r), ErrorCodeOperationFailed, metaMap("project_name", name, "user_id", userID))
		}
	}()

	data, err := facade.CreateProject(ctx, name, strVal(description))
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("create", "Failed to create project: "+err.Error(), ErrorCodeOperationFailed, metaMap("project_name", name, "user_id", userID))
	}
	if successFalse(data) {
		return data
	}
	return h.responseFormatter.CreateSuccessResponse("create", data, metaMap("project_name", name, "user_id", userID))
}

// GetProject ports get_project(facade, project_id=None, name=None).
func (h *ProjectCRUDHandler) GetProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, name *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("get", "Failed to retrieve project: "+panicMessage(r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "project_name", name))
		}
	}()

	var data *entities.OrderedMap[any]
	var err error
	if projectID != nil && *projectID != "" {
		data, err = facade.GetProject(ctx, *projectID)
	} else if name != nil && *name != "" {
		data, err = facade.GetProjectByName(ctx, *name)
	} else {
		return h.responseFormatter.CreateErrorResponse("get", "Failed to retrieve project: Either project_id or name must be provided", ErrorCodeOperationFailed, metaMap("project_id", projectID, "project_name", name))
	}
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("get", "Failed to retrieve project: "+err.Error(), ErrorCodeOperationFailed, metaMap("project_id", projectID, "project_name", name))
	}
	if successFalse(data) {
		return data
	}
	data = includeProjectContext(data)
	return h.responseFormatter.CreateSuccessResponse("get", data, metaMap("project_id", projectID, "project_name", name))
}

// ListProjects ports list_projects(facade).
func (h *ProjectCRUDHandler) ListProjects(ctx context.Context, facade *facades.ProjectApplicationFacade) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("list", "Failed to list projects: "+panicMessage(r), ErrorCodeOperationFailed, metaMap())
		}
	}()

	data, err := facade.ListProjects(ctx)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("list", "Failed to list projects: "+err.Error(), ErrorCodeOperationFailed, metaMap())
	}
	if successFalse(data) {
		return data
	}
	count := 0
	if d, ok := data.Get("data"); ok {
		if dm, ok := d.(*entities.OrderedMap[any]); ok {
			if projects, ok := dm.Get("projects"); ok {
				count = pyLen(projects)
			}
		}
	}
	return h.responseFormatter.CreateSuccessResponse("list", data, metaMap("project_count", count))
}

// UpdateProject ports update_project(facade, project_id, name=None, description=None).
func (h *ProjectCRUDHandler) UpdateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID string, name, description *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("update", "Failed to update project: "+panicMessage(r), ErrorCodeOperationFailed, metaMap("project_id", projectID))
		}
	}()

	data, err := facade.UpdateProject(ctx, projectID, name, description)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("update", "Failed to update project: "+err.Error(), ErrorCodeOperationFailed, metaMap("project_id", projectID))
	}
	if successFalse(data) {
		return data
	}
	return h.responseFormatter.CreateSuccessResponse("update", data, metaMap("project_id", projectID, "name", name))
}

// DeleteProject ports delete_project(facade, project_id, force=False).
func (h *ProjectCRUDHandler) DeleteProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID string, force *bool) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse("delete", "Failed to delete project: "+panicMessage(r), ErrorCodeOperationFailed, metaMap("project_id", projectID, "force", force))
		}
	}()

	f := false
	if force != nil {
		f = *force
	}
	data, err := facade.DeleteProject(ctx, projectID, f)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("delete", "Failed to delete project: "+err.Error(), ErrorCodeOperationFailed, metaMap("project_id", projectID, "force", force))
	}
	if successFalse(data) {
		return data
	}
	return h.responseFormatter.CreateSuccessResponse("delete", data, metaMap("project_id", projectID, "force", force))
}

// includeProjectContext ports _include_project_context(result).
func includeProjectContext(result *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if result != nil && result.Has("project") {
		ctx := entities.NewOrderedMap[any]()
		ctx.Set("management_available", true)
		ctx.Set("health_check_available", true)
		ctx.Set("maintenance_operations", []any{
			"project_health_check",
			"cleanup_obsolete",
			"validate_integrity",
			"rebalance_agents",
		})
		result.Set("project_context", ctx)
	}
	return result
}
