// Package routes ports the FastAPI route modules under
// src/fastmcp/server/routes. The APIRouter/Depends/BaseModel plumbing has no Go
// meaning; what is ported is the handler logic: controller calls, validation
// branches, response dicts (in Python insertion order) and HTTP status codes
// (as *auth.HTTPException).
package routes

import (
	"context"
	"encoding/json"

	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

// ControllerResult mirrors the pydantic response objects returned by the API
// controllers: model_dump(by_alias=True) plus the success/error/message
// attributes the routes branch on. The API controllers have no Go port yet.
type ControllerResult struct {
	Success bool
	Error   *string
	Message *string
	Body    *entities.OrderedMap[any]
}

func httpErr(status int, detail string) *auth.HTTPException {
	return &auth.HTTPException{StatusCode: status, Detail: detail}
}

// pyOrStr is Python `value or default` for an optional string.
func pyOrStr(v *string, def string) string {
	if v != nil && *v != "" {
		return *v
	}
	return def
}

// currentUserID is `str(current_user.id)`.
func currentUserID(u *authdomain.User) string {
	if u == nil || u.ID == nil {
		return ""
	}
	return *u.ID
}

// ContextCreateRequest mirrors ContextCreateRequest.
type ContextCreateRequest struct {
	Level       string
	ContextID   string
	Data        *entities.OrderedMap[any]
	ProjectID   *string
	GitBranchID *string
}

// ContextUpdateRequest mirrors ContextUpdateRequest.
type ContextUpdateRequest struct {
	Data             *entities.OrderedMap[any]
	PropagateChanges bool
}

// ContextDelegateRequest mirrors ContextDelegateRequest.
type ContextDelegateRequest struct {
	DelegateTo       string
	DelegateData     *entities.OrderedMap[any]
	DelegationReason *string
}

// ContextInsightRequest mirrors ContextInsightRequest.
type ContextInsightRequest struct {
	Content    string
	Category   *string
	Importance *string
	Agent      *string
}

// ContextProgressRequest mirrors ContextProgressRequest.
type ContextProgressRequest struct {
	Content string
	Agent   *string
}

// ContextController is the minimal ContextAPIController surface used by the
// routes (ctx first).
type ContextController interface {
	CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string) (ControllerResult, error)
	GetContext(ctx context.Context, level, contextID string, includeInherited bool, userID string) (ControllerResult, error)
	UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string) (ControllerResult, error)
	DeleteContext(ctx context.Context, level, contextID string, userID string) (ControllerResult, error)
	ResolveContext(ctx context.Context, level, contextID string, forceRefresh bool, userID string) (ControllerResult, error)
}

// CreateContext is create_context POST /{level}.
func CreateContext(ctx context.Context, level string, req ContextCreateRequest, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	req.Level = level
	if level == "global" && (req.ContextID == "me" || req.ContextID == "") {
		req.ContextID = currentUserID(currentUser)
	}
	data := req.Data
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	result, err := c.CreateContext(ctx, req.Level, req.ContextID, data, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to create context")
	}
	if result.Success {
		return result.Body, nil
	}
	return nil, httpErr(400, pyOrStr(result.Error, "Failed to create context"))
}

// GetContext is get_context GET /{level}/{context_id}.
func GetContext(ctx context.Context, level, contextID string, includeInherited, forceRefresh bool, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	if level == "global" {
		contextID = currentUserID(currentUser)
	}
	result, err := c.GetContext(ctx, level, contextID, includeInherited, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to get context")
	}
	if result.Success {
		return result.Body, nil
	}
	return nil, httpErr(404, "Context not found")
}

// UpdateContext is update_context PUT /{level}/{context_id}.
func UpdateContext(ctx context.Context, level, contextID string, req ContextUpdateRequest, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	if level == "global" {
		contextID = currentUserID(currentUser)
	}
	existing, err := c.GetContext(ctx, level, contextID, false, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to update context")
	}
	if !existing.Success {
		return nil, httpErr(404, "Context not found")
	}
	result, err := c.UpdateContext(ctx, level, contextID, req.Data, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to update context")
	}
	if result.Success {
		return result.Body, nil
	}
	return nil, httpErr(400, pyOrStr(result.Error, "Failed to update context"))
}

// DeleteContext is delete_context DELETE /{level}/{context_id}.
func DeleteContext(ctx context.Context, level, contextID string, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	if level == "global" {
		contextID = currentUserID(currentUser)
	}
	existing, err := c.GetContext(ctx, level, contextID, false, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to delete context")
	}
	if !existing.Success {
		return nil, httpErr(404, "Context not found")
	}
	result, err := c.DeleteContext(ctx, level, contextID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to delete context")
	}
	if result.Success {
		return result.Body, nil
	}
	return nil, httpErr(400, pyOrStr(result.Error, "Failed to delete context"))
}

// ResolveContext is resolve_context GET /{level}/{context_id}/resolve.
func ResolveContext(ctx context.Context, level, contextID string, forceRefresh bool, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	result, err := c.ResolveContext(ctx, level, contextID, forceRefresh, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to resolve context")
	}
	if result.Success {
		return result.Body, nil
	}
	return nil, httpErr(404, "Context not found")
}

// DelegateContext is delegate_context POST /{level}/{context_id}/delegate.
// Delegation is not implemented in the basic API controller.
func DelegateContext(ctx context.Context, level, contextID string, req ContextDelegateRequest, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	existing, err := c.GetContext(ctx, level, contextID, false, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to delegate context")
	}
	if !existing.Success {
		return nil, httpErr(404, "Context not found")
	}
	return nil, httpErr(501, "Context delegation feature not implemented in API controller")
}

// AddInsight is add_insight POST /{level}/{context_id}/insights.
func AddInsight(ctx context.Context, level, contextID string, req ContextInsightRequest, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	existing, err := c.GetContext(ctx, level, contextID, false, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to add insight")
	}
	if !existing.Success {
		return nil, httpErr(404, "Context not found")
	}
	return nil, httpErr(501, "Context insights feature not implemented in API controller")
}

// AddProgress is add_progress POST /{level}/{context_id}/progress.
func AddProgress(ctx context.Context, level, contextID string, req ContextProgressRequest, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	existing, err := c.GetContext(ctx, level, contextID, false, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, "Failed to add progress")
	}
	if !existing.Success {
		return nil, httpErr(404, "Context not found")
	}
	return nil, httpErr(501, "Context progress feature not implemented in API controller")
}

// ListContexts is list_contexts GET /{level}/list.
func ListContexts(ctx context.Context, level string, filters *string, currentUser *authdomain.User, c ContextController) (*entities.OrderedMap[any], error) {
	if filters != nil && *filters != "" {
		var parsed any
		if err := json.Unmarshal([]byte(*filters), &parsed); err != nil {
			return nil, httpErr(400, "Invalid filters JSON: "+err.Error())
		}
	}
	return nil, httpErr(501, "List contexts feature not implemented in API controller")
}

// GetContextSummary is get_context_summary GET /{level}/{context_id}/summary.
// The Python raises HTTPException(501) inside a try whose only handler is
// `except Exception`, so the 501 is converted to a 500; that quirk is kept.
func GetContextSummary(ctx context.Context, level, contextID string, currentUser *authdomain.User) (*entities.OrderedMap[any], error) {
	return nil, httpErr(500, "Failed to get context summary")
}
