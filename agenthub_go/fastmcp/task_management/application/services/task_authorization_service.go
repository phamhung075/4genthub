package services

import (
	"context"

	authdomain "agenthub/fastmcp/auth/domain"
	"agenthub/fastmcp/task_management/domain/entities"
)

// zpTaskAuthResponseFormatter mirrors the response_formatter.create_error_response
// call surface (the FastAPI response formatter has no Go port yet).
type zpTaskAuthResponseFormatter interface {
	CreateErrorResponse(operation, errMsg, errorCode string) *entities.OrderedMap[any]
}

// zpTaskAuthActionPermissionMap is ACTION_PERMISSION_MAP.
var zpTaskAuthActionPermissionMap = map[string]authdomain.PermissionAction{
	"create":            authdomain.ActionCreate,
	"get":               authdomain.ActionRead,
	"list":              authdomain.ActionRead,
	"search":            authdomain.ActionRead,
	"update":            authdomain.ActionUpdate,
	"complete":          authdomain.ActionUpdate,
	"delete":            authdomain.ActionDelete,
	"next":              authdomain.ActionRead,
	"add_dependency":    authdomain.ActionUpdate,
	"remove_dependency": authdomain.ActionUpdate,
}

// TaskAuthorizationService ports
// application/services/task_authorization_service.TaskAuthorizationService.
type TaskAuthorizationService struct {
	responseFormatter zpTaskAuthResponseFormatter
}

// NewTaskAuthorizationService mirrors __init__.
func NewTaskAuthorizationService(responseFormatter zpTaskAuthResponseFormatter) *TaskAuthorizationService {
	return &TaskAuthorizationService{responseFormatter: responseFormatter}
}

// zpTaskAuthErrorResponse builds the fallback {"error", "code"} dict.
func zpTaskAuthErrorResponse(errMsg, errorCode string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("error", errMsg)
	m.Set("code", errorCode)
	return m
}

// CheckTaskPermission mirrors check_task_permission.
func (s *TaskAuthorizationService) CheckTaskPermission(action string, userID string,
	tokenPayload map[string]any, taskID *string) (bool, *entities.OrderedMap[any]) {
	requiredPermission, known := zpTaskAuthActionPermissionMap[action]
	if !known {
		// Unknown action - allow by default (backwards compatibility).
		return true, nil
	}

	if len(tokenPayload) == 0 {
		if s.responseFormatter != nil {
			return false, s.responseFormatter.CreateErrorResponse(action,
				"No token payload found for permission validation", "AUTHENTICATION_ERROR")
		}
		return false, zpTaskAuthErrorResponse("No token payload found", "AUTHENTICATION_ERROR")
	}

	checker := authdomain.NewPermissionChecker(tokenPayload)
	if !checker.HasPermission(authdomain.ResourceTasks, requiredPermission) {
		message := "Permission denied: requires tasks:" + string(requiredPermission)
		if s.responseFormatter != nil {
			return false, s.responseFormatter.CreateErrorResponse(action, message, "PERMISSION_DENIED")
		}
		return false, zpTaskAuthErrorResponse(message, "PERMISSION_DENIED")
	}
	return true, nil
}

// GetPermissionForAction mirrors get_permission_for_action; nil = Python None.
func (s *TaskAuthorizationService) GetPermissionForAction(action string) *authdomain.PermissionAction {
	if p, ok := zpTaskAuthActionPermissionMap[action]; ok {
		return &p
	}
	return nil
}

// IsValidAction mirrors is_valid_action.
func (s *TaskAuthorizationService) IsValidAction(action string) bool {
	_, ok := zpTaskAuthActionPermissionMap[action]
	return ok
}

// ExtractTokenFromContext mirrors extract_token_from_context. The Python
// request-context middleware has no Go equivalent; the authenticated token is read
// from the same context keys the auth middleware uses, with the same graceful
// fallback to nil.
func (s *TaskAuthorizationService) ExtractTokenFromContext(ctx context.Context) map[string]any {
	user, _ := ctx.Value(authdomain.UserContextKey).(authdomain.TokenPayloadProvider)
	if user == nil {
		return nil
	}
	payload := user.TokenPayload()
	if len(payload) == 0 {
		return nil
	}
	return payload
}

// CheckTaskPermissionFromContext mirrors check_task_permission_from_context.
func (s *TaskAuthorizationService) CheckTaskPermissionFromContext(ctx context.Context, action string,
	userID string, taskID *string) (bool, *entities.OrderedMap[any]) {
	tokenPayload := s.ExtractTokenFromContext(ctx)
	if len(tokenPayload) == 0 {
		// Fallback for test environments or when authentication context is not available.
		return true, nil
	}
	return s.CheckTaskPermission(action, userID, tokenPayload, taskID)
}
