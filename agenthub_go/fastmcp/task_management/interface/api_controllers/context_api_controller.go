package api_controllers

import (
	"context"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/types"
)

// ctxFacadeProvider is the consumer-side view of FacadeService.get_context_facade.
type ctxFacadeProvider interface {
	GetContextFacade(userID, projectID, gitBranchID *string) (*facades.UnifiedContextFacade, error)
}

// ContextAPIController mirrors context_api_controller.ContextAPIController.
type ContextAPIController struct {
	facadeProvider ctxFacadeProvider
}

// NewContextAPIController builds the controller. Python resolves
// FacadeService.get_instance() in __init__; the Go provider is injected.
func NewContextAPIController(provider ctxFacadeProvider) *ContextAPIController {
	return &ContextAPIController{facadeProvider: provider}
}

func ctxACGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// CreateContext mirrors create_context(level, context_id, data, user_id, session).
func (c *ContextAPIController) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string, session any) (resp *types.ContextResponse) {
	resp = &types.ContextResponse{Success: false}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Context = nil
			resp.Error = strPtr(value_objects.PyStr(r))
			resp.Message = strPtr("Failed to create context")
		}
	}()
	facade, err := c.facadeProvider.GetContextFacade(&userID, nil, nil)
	if err != nil {
		return ctxACError(err, "Failed to create context")
	}
	result, err := facade.CreateContext(ctx, level, contextID, data, &userID)
	if err != nil {
		return ctxACError(err, "Failed to create context")
	}
	lvl := level
	return &types.ContextResponse{
		Success: true,
		Context: ctxACGet(result, "context"),
		Level:   &lvl,
		Message: strPtr("Context created successfully"),
	}
}

// GetContext mirrors get_context(level, context_id, include_inherited, user_id, session).
func (c *ContextAPIController) GetContext(ctx context.Context, level, contextID string, includeInherited bool, userID string, session any) (resp *types.ContextResponse) {
	resp = &types.ContextResponse{Success: false}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Context = nil
			resp.Error = strPtr(value_objects.PyStr(r))
			resp.Message = strPtr("Failed to get context")
		}
	}()
	facade, err := c.facadeProvider.GetContextFacade(&userID, nil, nil)
	if err != nil {
		return ctxACError(err, "Failed to get context")
	}
	result, err := facade.GetContext(ctx, level, contextID, includeInherited, false, &userID)
	if err != nil {
		return ctxACError(err, "Failed to get context")
	}
	if !value_objects.PyTruthy(ctxACGet(result, "success")) {
		return &types.ContextResponse{
			Success: false,
			Context: nil,
			Error:   strPtr("Context not found"),
			Message: strPtr("Context not found or access denied"),
		}
	}
	var inherited any
	if includeInherited {
		inherited = ctxACGet(result, "inherited")
	}
	lvl := level
	return &types.ContextResponse{
		Success:   true,
		Context:   ctxACGet(result, "context"),
		Level:     &lvl,
		Inherited: inherited,
	}
}

// UpdateContext mirrors update_context(level, context_id, data, user_id, session).
func (c *ContextAPIController) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string, session any) (resp *types.ContextResponse) {
	resp = &types.ContextResponse{Success: false}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Context = nil
			resp.Error = strPtr(value_objects.PyStr(r))
			resp.Message = strPtr("Failed to update context")
		}
	}()
	facade, err := c.facadeProvider.GetContextFacade(&userID, nil, nil)
	if err != nil {
		return ctxACError(err, "Failed to update context")
	}
	result, err := facade.UpdateContext(ctx, level, contextID, data, true)
	if err != nil {
		return ctxACError(err, "Failed to update context")
	}
	if !value_objects.PyTruthy(ctxACGet(result, "success")) {
		return &types.ContextResponse{
			Success: false,
			Context: nil,
			Error:   strPtr("Context not found"),
			Message: strPtr("Context not found or access denied"),
		}
	}
	lvl := level
	return &types.ContextResponse{
		Success: true,
		Context: ctxACGet(result, "context"),
		Level:   &lvl,
		Message: strPtr("Context updated successfully"),
	}
}

// DeleteContext mirrors delete_context(level, context_id, user_id, session).
func (c *ContextAPIController) DeleteContext(ctx context.Context, level, contextID, userID string, session any) (resp *types.DeleteResponse) {
	resp = &types.DeleteResponse{Success: false}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Deleted = boolPtr(false)
			resp.Error = strPtr(value_objects.PyStr(r))
			resp.Message = strPtr("Failed to delete context")
		}
	}()
	facade, err := c.facadeProvider.GetContextFacade(&userID, nil, nil)
	if err != nil {
		return ctxACDeleteError(err, "Failed to delete context")
	}
	result, err := facade.DeleteContext(ctx, level, contextID)
	if err != nil {
		return ctxACDeleteError(err, "Failed to delete context")
	}
	if !value_objects.PyTruthy(ctxACGet(result, "success")) {
		return &types.DeleteResponse{
			Success: false,
			Deleted: boolPtr(false),
			Error:   strPtr("Context not found"),
			Message: strPtr("Context not found or access denied"),
		}
	}
	id := contextID
	return &types.DeleteResponse{
		Success: true,
		Deleted: boolPtr(true),
		ID:      &id,
		Message: strPtr("Context deleted successfully"),
	}
}

// ResolveContext mirrors resolve_context(level, context_id, user_id, session,
// force_refresh=False).
func (c *ContextAPIController) ResolveContext(ctx context.Context, level, contextID, userID string, session any, forceRefresh bool) (resp *types.ContextResponse) {
	resp = &types.ContextResponse{Success: false}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Context = nil
			resp.Error = strPtr(value_objects.PyStr(r))
			resp.Message = strPtr("Failed to resolve context")
		}
	}()
	facade, err := c.facadeProvider.GetContextFacade(&userID, nil, nil)
	if err != nil {
		return ctxACError(err, "Failed to resolve context")
	}
	result, err := facade.ResolveContext(ctx, level, contextID, forceRefresh)
	if err != nil {
		return ctxACError(err, "Failed to resolve context")
	}
	if !value_objects.PyTruthy(ctxACGet(result, "success")) {
		return &types.ContextResponse{
			Success: false,
			Context: nil,
			Error:   strPtr("Context not found"),
			Message: strPtr("Context not found or access denied"),
		}
	}
	inherited := ctxACGet(result, "inheritance_chain")
	if inherited == nil {
		inherited = []any{}
	}
	lvl := level
	return &types.ContextResponse{
		Success:   true,
		Context:   ctxACGet(result, "context"),
		Level:     &lvl,
		Inherited: inherited,
	}
}

func ctxACError(err error, message string) *types.ContextResponse {
	msg := err.Error()
	return &types.ContextResponse{
		Success: false,
		Context: nil,
		Error:   &msg,
		Message: &message,
	}
}

func ctxACDeleteError(err error, message string) *types.DeleteResponse {
	msg := err.Error()
	return &types.DeleteResponse{
		Success: false,
		Deleted: boolPtr(false),
		Error:   &msg,
		Message: &message,
	}
}
