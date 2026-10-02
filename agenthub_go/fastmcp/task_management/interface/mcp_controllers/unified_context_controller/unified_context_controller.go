package unified_context_controller

// Unified Context MCP Controller
// (Python unified_context_controller/unified_context_controller.py).
//
// FastMCP tool registration (`register_tools`), the Pydantic Annotated field
// descriptors and the request-context middleware import have no Go meaning and
// are not ported; parameter coercion and the management flow are.

import (
	"context"
	"strconv"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper"
	contextfactories "agenthub/fastmcp/task_management/interface/mcp_controllers/unified_context_controller/factories"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/unified_context_controller/handlers"
)

// CoerceParameterTypesFunc mirrors interface/utils/parameter_validation_fix.py
// coerce_parameter_types for the parameters this controller uses. That module
// has no Go port yet; the boolean coercion applied here reflects its behaviour.
var CoerceParameterTypesFunc = coerceContextParameterTypes

// UnifiedContextMCPController handles MCP protocol concerns for unified context
// management and delegates business operations to the operation factory.
type UnifiedContextMCPController struct {
	facadeService     *services.FacadeService
	responseFormatter handlers.ContextResponseFormatter
	operationFactory  *contextfactories.ContextOperationFactory
}

// NewUnifiedContextMCPController ports __init__(facade_service=None). Python
// falls back to FacadeService.get_instance(); Go has no singleton, so the
// caller must supply the service.
func NewUnifiedContextMCPController(facadeService *services.FacadeService, responseFormatter handlers.ContextResponseFormatter) *UnifiedContextMCPController {
	return &UnifiedContextMCPController{
		facadeService:     facadeService,
		responseFormatter: responseFormatter,
		operationFactory:  contextfactories.NewContextOperationFactory(responseFormatter),
	}
}

// ManageUnifiedContext ports manage_unified_context.
func (c *UnifiedContextMCPController) ManageUnifiedContext(ctx context.Context, action string,
	level, contextID, data, userID, projectID, gitBranchID, forceRefresh, includeInherited, propagateChanges,
	delegateTo, delegateData, delegationReason, content, category, importance, agent, filters *string) (result *entities.OrderedMap[any]) {

	defer func() {
		if r := recover(); r != nil {
			result = internalFallback(action, r)
		}
	}()

	coerced := CoerceParameterTypesFunc(map[string]any{
		"level": level, "context_id": contextID, "data": data, "user_id": userID,
		"project_id": projectID, "git_branch_id": gitBranchID, "force_refresh": forceRefresh,
		"include_inherited": includeInherited, "propagate_changes": propagateChanges,
		"delegate_to": delegateTo, "delegate_data": delegateData, "delegation_reason": delegationReason,
		"content": content, "category": category, "importance": importance, "agent": agent, "filters": filters,
	})

	levelVal := coalesceString(coerced["level"], level, "task")
	contextIDVal := coalescePtr(coerced["context_id"], contextID)
	userIDVal := coalescePtr(coerced["user_id"], userID)
	projectIDVal := coalescePtr(coerced["project_id"], projectID)
	gitBranchIDVal := coalescePtr(coerced["git_branch_id"], gitBranchID)
	forceRefreshVal := coalesceBool(coerced["force_refresh"], forceRefresh, false)
	includeInheritedVal := coalesceBool(coerced["include_inherited"], includeInherited, false)
	propagateChangesVal := coalesceBool(coerced["propagate_changes"], propagateChanges, true)

	dataMap, errResp := c.decodeJSONParam(data, "manage_context.create", "data")
	if errResp != nil {
		return errResp
	}
	delegateDataMap, errResp := c.decodeJSONParam(delegateData, "manage_context.delegate", "delegate_data")
	if errResp != nil {
		return errResp
	}
	filtersMap, errResp := c.decodeJSONParam(filters, "manage_context.list", "filters")
	if errResp != nil {
		return errResp
	}

	authenticatedUserID, err := auth_helper.GetAuthenticatedUserID(ctx, userIDVal, "manage_context."+action)
	if err != nil {
		return internalFallback(action, err)
	}

	if ok, permissionError := c.checkContextPermissions(ctx, action, authenticatedUserID); !ok {
		return permissionError
	}

	if levelVal == "global" {
		contextIDVal = &authenticatedUserID
	}

	if c.facadeService == nil {
		return internalFallback(action, errNilFacadeService)
	}
	facadeAny, err := c.facadeService.GetContextFacade(&authenticatedUserID, projectIDVal, gitBranchIDVal)
	if err != nil {
		return internalFallback(action, err)
	}
	facade, ok := facadeAny.(*facades.UnifiedContextFacade)
	if !ok {
		return internalFallback(action, errNilFacadeService)
	}

	kwargs := map[string]any{
		"level": levelVal, "context_id": ptrToString(contextIDVal), "data": dataMap,
		"user_id": authenticatedUserID, "project_id": ptrToString(projectIDVal),
		"git_branch_id": ptrToString(gitBranchIDVal), "force_refresh": forceRefreshVal,
		"include_inherited": includeInheritedVal, "propagate_changes": propagateChangesVal,
		"delegate_to": ptrToString(delegateTo), "delegate_data": delegateDataMap,
		"delegation_reason": ptrToString(delegationReason), "content": ptrToString(content),
		"category": ptrToString(category), "importance": ptrToString(importance),
		"agent": ptrToString(agent), "filters": filtersMap,
	}

	return c.operationFactory.HandleOperation(ctx, facade, action, kwargs)
}

// ManageContext ports the backward-compatibility manage_context(**kwargs).
func (c *UnifiedContextMCPController) ManageContext(ctx context.Context, kwargs map[string]any) *entities.OrderedMap[any] {
	action := ""
	if p := kwArg(kwargs, "action"); p != nil {
		action = *p
	}
	return c.ManageUnifiedContext(ctx,
		action,
		kwArg(kwargs, "level"), kwArg(kwargs, "context_id"), kwArg(kwargs, "data"), kwArg(kwargs, "user_id"),
		kwArg(kwargs, "project_id"), kwArg(kwargs, "git_branch_id"), kwArg(kwargs, "force_refresh"),
		kwArg(kwargs, "include_inherited"), kwArg(kwargs, "propagate_changes"), kwArg(kwargs, "delegate_to"),
		kwArg(kwargs, "delegate_data"), kwArg(kwargs, "delegation_reason"), kwArg(kwargs, "content"),
		kwArg(kwargs, "category"), kwArg(kwargs, "importance"), kwArg(kwargs, "agent"), kwArg(kwargs, "filters"),
	)
}

// checkContextPermissions ports _check_context_permissions. The Python
// request-context middleware is replaced by the Go context permission checker
// (auth/domain.PermissionsFromContext).
func (c *UnifiedContextMCPController) checkContextPermissions(ctx context.Context, action, userID string) (bool, *entities.OrderedMap[any]) {
	actionToPermission := map[string]authdomain.PermissionAction{
		"create": authdomain.ActionCreate, "get": authdomain.ActionRead, "update": authdomain.ActionUpdate,
		"delete": authdomain.ActionDelete, "resolve": authdomain.ActionRead, "delegate": authdomain.ActionDelegate,
		"add_insight": authdomain.ActionUpdate, "add_progress": authdomain.ActionUpdate, "list": authdomain.ActionRead,
	}
	requiredPermission, known := actionToPermission[action]
	if !known {
		return true, nil
	}
	_ = userID
	checker := authdomain.PermissionsFromContext(ctx)
	if checker == nil {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Authentication context not available for permission check")
		d.Set("error_code", "AUTHENTICATION_ERROR")
		return false, d
	}
	if !checker.HasPermission(authdomain.ResourceContexts, requiredPermission) {
		d := entities.NewOrderedMap[any]()
		d.Set("success", false)
		d.Set("error", "Permission denied: requires contexts:"+string(requiredPermission))
		d.Set("error_code", "PERMISSION_DENIED")
		return false, d
	}
	return true, nil
}

func (c *UnifiedContextMCPController) decodeJSONParam(value *string, operation, field string) (*entities.OrderedMap[any], *entities.OrderedMap[any]) {
	if value == nil || strings.TrimSpace(*value) == "" {
		return nil, nil
	}
	decoded, err := entities.DecodeJSON([]byte(*value))
	if err != nil {
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("field", field)
		metadata.Set("suggestions", "Ensure "+field+" parameter contains valid JSON")
		return nil, c.responseFormatter.CreateErrorResponse(
			operation,
			"Invalid JSON string in "+field+" parameter: "+err.Error(),
			"VALIDATION_ERROR",
			metadata,
		)
	}
	if m, ok := decoded.(*entities.OrderedMap[any]); ok {
		return m, nil
	}
	return nil, nil
}

func coalesceString(coerced any, original *string, def string) string {
	if s, ok := coerced.(string); ok && s != "" {
		return s
	}
	if original != nil && *original != "" {
		return *original
	}
	return def
}

func coalescePtr(coerced any, original *string) *string {
	if s, ok := coerced.(string); ok {
		return &s
	}
	return original
}

func coalesceBool(coerced any, original *string, def bool) bool {
	if b, ok := coerced.(bool); ok {
		return b
	}
	if original != nil {
		if b, err := strconv.ParseBool(strings.ToLower(*original)); err == nil {
			return b
		}
	}
	return def
}

func coerceContextParameterTypes(params map[string]any) map[string]any {
	for _, key := range []string{"force_refresh", "include_inherited", "propagate_changes"} {
		if s, ok := params[key].(string); ok && strings.TrimSpace(s) != "" {
			if b, err := strconv.ParseBool(strings.ToLower(strings.TrimSpace(s))); err == nil {
				params[key] = b
			}
		}
	}
	return params
}

func internalFallback(action string, err any) *entities.OrderedMap[any] {
	msg := ""
	switch t := err.(type) {
	case error:
		msg = t.Error()
	case string:
		msg = t
	default:
		msg = "unknown error"
	}
	d := entities.NewOrderedMap[any]()
	d.Set("success", false)
	d.Set("error", "Context operation failed: "+msg)
	d.Set("error_code", "INTERNAL_ERROR")
	d.Set("details", msg)
	return d
}

func ptrToString(p *string) string {
	if p == nil {
		return ""
	}
	return *p
}

func kwArg(kwargs map[string]any, key string) *string {
	if v, ok := kwargs[key]; ok {
		if s, isStr := v.(string); isStr {
			return &s
		}
	}
	return nil
}

type constantError string

func (e constantError) Error() string { return string(e) }

const errNilFacadeService = constantError("context facade service is not configured")
