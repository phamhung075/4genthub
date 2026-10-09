package project_mcp_controller

// Project MCP Controller - Modular Implementation
// (Python project_mcp_controller.py).
//
// FastMCP tool registration (`register_tools`) has no Go meaning and is not
// ported. The asyncio/thread event-loop wrappers in the Python synchronous
// helpers have no Go equivalent: Go methods are synchronous by nature, so those
// helpers delegate directly.

import (
	"context"
	"fmt"

	authdomain "agenthub/fastmcp/auth/domain"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProjectCRUDHandler is the minimal view of handlers.ProjectCRUDHandler, which
// is declared here because the controller package cannot import the handlers
// package without a cycle (the handler interfaces reference the concrete facade).
type ProjectCRUDHandler interface {
	CreateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, name string, description, userID *string) *entities.OrderedMap[any]
	GetProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, name *string) *entities.OrderedMap[any]
	ListProjects(ctx context.Context, facade *facades.ProjectApplicationFacade) *entities.OrderedMap[any]
	UpdateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID string, name, description *string) *entities.OrderedMap[any]
}

// ProjectMaintenanceHandler is the minimal view of handlers.ProjectMaintenanceHandler.
type ProjectMaintenanceHandler interface {
	HandleMaintenanceAction(ctx context.Context, facade *facades.ProjectApplicationFacade, action, projectID string, force *bool, userID *string) *entities.OrderedMap[any]
}

// ProjectOperationFactory is the minimal view of
// factories.ProjectOperationFactory (Python project_mcp_controller/factories/operation_factory.py),
// ported in project_mcp_controller/factories/operation_factory.go.
type ProjectOperationFactory interface {
	HandleOperation(ctx context.Context, operation string, facade *facades.ProjectApplicationFacade, userID *string, params ProjectOperationParams) *entities.OrderedMap[any]
	CRUDHandler() ProjectCRUDHandler
	MaintenanceHandler() ProjectMaintenanceHandler
}

// ProjectOperationParams replaces Python's **kwargs for handle_operation.
type ProjectOperationParams struct {
	ProjectID   *string
	Name        *string
	Description *string
	Force       *bool
}

// ProjectResponseFactory is the minimal view of
// factories.ProjectResponseFactory (project_mcp_controller/factories/response_factory.py),
// ported in project_mcp_controller/factories/response_factory.go.
type ProjectResponseFactory interface {
	CreateMissingFieldError(field, operation string) *entities.OrderedMap[any]
}

// ProjectResponseFormatter is the minimal view of the interface-layer
// StandardResponseFormatter used by the controller.
type ProjectResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// ProjectFacadeFactory is the minimal view of the old-style facade factory.
type ProjectFacadeFactory interface {
	CreateProjectFacade(userID *string) (*facades.ProjectApplicationFacade, error)
}

// ProjectFacadeService is the minimal view of FacadeService.get_project_facade.
type ProjectFacadeService interface {
	GetProjectFacade(userID *string) (any, error)
}

// GetAuthenticatedUserID replaces auth_helper.get_authenticated_user_id. When
// nil, authentication fails with UserAuthenticationRequiredError semantics.
var GetAuthenticatedUserID func(ctx context.Context, providedUserID *string, operationName string) (string, error)

// LogAuthenticationDetails replaces auth_helper.log_authentication_details.
var LogAuthenticationDetails func(userID, operation string)

// GetCurrentAuthInfo replaces
// request_context_middleware.get_current_auth_info. When nil the middleware is
// treated as unavailable and permission checks fail open (Python ImportError
// fallback).
var GetCurrentAuthInfo func(ctx context.Context) map[string]any

// ProjectMCPController ports ProjectMCPController.
type ProjectMCPController struct {
	projectFacadeFactory ProjectFacadeFactory
	facadeService        ProjectFacadeService
	responseFormatter    ProjectResponseFormatter
	operationFactory     ProjectOperationFactory
	responseFactory      ProjectResponseFactory
}

// NewProjectMCPController ports __init__(facade_factory=None, facade_service=None).
// A concrete formatter and factories are injected.
func NewProjectMCPController(
	facadeFactory ProjectFacadeFactory,
	facadeService ProjectFacadeService,
	responseFormatter ProjectResponseFormatter,
	operationFactory ProjectOperationFactory,
	responseFactory ProjectResponseFactory,
) *ProjectMCPController {
	return &ProjectMCPController{
		projectFacadeFactory: facadeFactory,
		facadeService:        facadeService,
		responseFormatter:    responseFormatter,
		operationFactory:     operationFactory,
		responseFactory:      responseFactory,
	}
}

// GetFacadeForRequest ports _get_facade_for_request(user_id=None).
func (c *ProjectMCPController) GetFacadeForRequest(userID *string) (*facades.ProjectApplicationFacade, error) {
	if c.projectFacadeFactory != nil {
		return c.projectFacadeFactory.CreateProjectFacade(userID)
	}
	if c.facadeService != nil {
		facade, err := c.facadeService.GetProjectFacade(userID)
		if err != nil {
			return nil, err
		}
		if typed, ok := facade.(*facades.ProjectApplicationFacade); ok {
			return typed, nil
		}
		return nil, fmt.Errorf("project facade has unexpected type %T", facade)
	}
	return nil, &value_objects.ValueError{Msg: "Either facade_factory or facade_service is required"}
}

// ManageProject ports manage_project(action, user_id=None, **kwargs).
func (c *ProjectMCPController) ManageProject(ctx context.Context, action string, projectID, name, description *string, force *bool, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = c.errorResponse(action, "Project operation failed: "+panicMessage(r), "OPERATION_FAILED", metaAction(action))
		}
	}()

	// Authentication
	authenticated, err := authenticatedUserID(ctx, userID, "manage_project:"+action)
	if err != nil {
		return c.errorResponse(action, "Project operation failed: "+err.Error(), "OPERATION_FAILED", metaAction(action))
	}
	if LogAuthenticationDetails != nil {
		LogAuthenticationDetails(authenticated, "manage_project:"+action)
	}

	// Permission Authorization
	ok, permissionErr := c.checkProjectPermissions(ctx, action, authenticated, projectID)
	if !ok {
		return permissionErr
	}

	facade, err := c.GetFacadeForRequest(&authenticated)
	if err != nil {
		return c.errorResponse(action, "Project operation failed: "+err.Error(), "OPERATION_FAILED", metaAction(action))
	}

	if validationErr := c.validateOperationParameters(action, projectID, name); validationErr != nil {
		return validationErr
	}

	return c.operationFactory.HandleOperation(ctx, action, facade, &authenticated, ProjectOperationParams{
		ProjectID:   projectID,
		Name:        name,
		Description: description,
		Force:       force,
	})
}

func authenticatedUserID(ctx context.Context, provided *string, operationName string) (string, error) {
	if GetAuthenticatedUserID == nil {
		if provided != nil && *provided != "" {
			return *provided, nil
		}
		return "", &value_objects.ValueError{Msg: "User authentication required"}
	}
	return GetAuthenticatedUserID(ctx, provided, operationName)
}

// validateOperationParameters ports _validate_operation_parameters(action, **kwargs).
// A nil result means valid.
func (c *ProjectMCPController) validateOperationParameters(action string, projectID, name *string) *entities.OrderedMap[any] {
	switch action {
	case "create":
		if name == nil || !value_objects.PyTruthy(*name) {
			return c.responseFactory.CreateMissingFieldError("name", action)
		}
	case "get":
		if (projectID == nil || *projectID == "") && (name == nil || *name == "") {
			m := entities.NewOrderedMap[any]()
			m.Set("required_fields", []any{"project_id OR name"})
			return c.errorResponse(action, "Either 'project_id' or 'name' must be provided for get operation", "VALIDATION_ERROR", m)
		}
	case "update", "delete", "project_health_check", "cleanup_obsolete", "validate_integrity", "rebalance_agents":
		if projectID == nil || *projectID == "" {
			return c.responseFactory.CreateMissingFieldError("project_id", action)
		}
	}
	return nil
}

// checkProjectPermissions ports _check_project_permissions(action, user_id, project_id=None).
func (c *ProjectMCPController) checkProjectPermissions(ctx context.Context, action, userID string, projectID *string) (bool, *entities.OrderedMap[any]) {
	defer func() {
		// On error the Python allows the operation to proceed (fail-open).
		_ = recover()
	}()

	actionToPermission := map[string]authdomain.PermissionAction{
		"create":               authdomain.ActionCreate,
		"get":                  authdomain.ActionRead,
		"list":                 authdomain.ActionRead,
		"update":               authdomain.ActionUpdate,
		"delete":               authdomain.ActionDelete,
		"project_health_check": authdomain.ActionRead,
		"cleanup_obsolete":     authdomain.ActionUpdate,
		"validate_integrity":   authdomain.ActionRead,
		"rebalance_agents":     authdomain.ActionUpdate,
	}

	required, ok := actionToPermission[action]
	if !ok {
		// Unknown action - allow by default (backwards compatibility)
		return true, nil
	}

	// Fallback: middleware unavailable -> allow operation.
	if GetCurrentAuthInfo == nil {
		return true, nil
	}
	authInfo := GetCurrentAuthInfo(ctx)
	if authInfo == nil {
		return false, c.errorResponse(action, "Authentication context not available for permission check", "AUTHENTICATION_ERROR", nil)
	}

	checker := authdomain.NewPermissionChecker(authInfo)
	if !checker.HasPermission(authdomain.ResourceProjects, required) {
		return false, c.errorResponse(action, "Permission denied: requires projects:"+string(required), "PERMISSION_DENIED", nil)
	}
	return true, nil
}

// HandleCRUDOperations ports handle_crud_operations(...).
func (c *ProjectMCPController) HandleCRUDOperations(ctx context.Context, action string, projectID, name, description, userID *string, force *bool) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = c.errorResponse(action, "Operation failed: "+panicMessage(r), "INTERNAL_ERROR", nil)
		}
	}()

	if validationErr := c.validateOperationParameters(action, projectID, name); validationErr != nil {
		return validationErr
	}
	facade, err := c.GetFacadeForRequest(userID)
	if err != nil {
		return c.errorResponse(action, "Operation failed: "+err.Error(), "INTERNAL_ERROR", nil)
	}
	return c.operationFactory.HandleOperation(ctx, action, facade, userID, ProjectOperationParams{
		ProjectID:   projectID,
		Name:        name,
		Description: description,
		Force:       force,
	})
}

// HandleMaintenanceOperations ports handle_maintenance_operations(...).
func (c *ProjectMCPController) HandleMaintenanceOperations(ctx context.Context, action string, projectID *string, force *bool, userID *string) *entities.OrderedMap[any] {
	if projectID == nil || *projectID == "" {
		return c.responseFactory.CreateMissingFieldError("project_id", action)
	}
	return c.handleMaintenanceAction(ctx, action, *projectID, force, userID)
}

// handleMaintenanceAction ports _handle_maintenance_action(...).
func (c *ProjectMCPController) handleMaintenanceAction(ctx context.Context, action, projectID string, force *bool, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = bareInternalError("Operation failed: " + panicMessage(r))
		}
	}()

	facade, err := c.GetFacadeForRequest(userID)
	if err != nil {
		return bareInternalError("Operation failed: " + err.Error())
	}
	handler := c.operationFactory.MaintenanceHandler()
	if handler == nil {
		return bareInternalError("Operation failed: maintenance handler not configured")
	}
	return handler.HandleMaintenanceAction(ctx, facade, action, projectID, force, userID)
}

// GetProjectManagementDescriptions ports _get_project_management_descriptions().
func (c *ProjectMCPController) GetProjectManagementDescriptions() *entities.OrderedMap[any] {
	if descriptionLoader != nil {
		descriptions := descriptionLoader.GetAllDescriptions()
		if descriptions != nil && descriptions.Has("projects") {
			if m, ok := descriptions.GetAny("projects").(*entities.OrderedMap[any]); ok {
				return m
			}
		}
	}
	params := GetManageProjectParameters()
	entry := entities.NewOrderedMap[any]()
	entry.Set("description", GetManageProjectDescription())
	entry.Set("parameters", params)
	outer := entities.NewOrderedMap[any]()
	outer.Set("manage_project", entry)
	return outer
}

// DescriptionLoader is the minimal view of
// config.resource_descriptions.description_loader.DescriptionLoader.
type DescriptionLoader interface {
	GetAllDescriptions() *entities.OrderedMap[any]
}

// DescriptionLoaderInstance replaces the module-level description_loader.
var DescriptionLoaderInstance DescriptionLoader

// descriptionLoader mirrors the module-level description_loader (empty by default).
var descriptionLoader DescriptionLoader

// SetDescriptionLoader wires the module-level loader.
func SetDescriptionLoader(l DescriptionLoader) { descriptionLoader = l }

func (c *ProjectMCPController) errorResponse(operation, message, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if c.responseFormatter == nil {
		return bareError(operation, message, errorCode, metadata)
	}
	return c.responseFormatter.CreateErrorResponse(operation, message, errorCode, metadata)
}

func metaAction(action string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("action", action)
	return m
}

// bareError is used when no formatter was injected (matching the expected
// response shape).
func bareError(operation, message, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("operation", operation)
	m.Set("error", message)
	m.Set("error_code", errorCode)
	m.Set("metadata", metadata)
	return m
}

// bareInternalError mirrors the fallback dict returned by the Python
// maintenance helpers on unexpected errors.
func bareInternalError(message string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", message)
	m.Set("error_code", "INTERNAL_ERROR")
	return m
}

func panicMessage(r any) string {
	if err, ok := r.(error); ok {
		return err.Error()
	}
	return fmt.Sprint(r)
}
