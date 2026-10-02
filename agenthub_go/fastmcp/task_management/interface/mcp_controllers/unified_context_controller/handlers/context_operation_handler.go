package handlers

// Context Operation Handler
// (Python unified_context_controller/handlers/context_operation_handler.py).

import (
	"context"
	"errors"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper"
)

// ContextResponseFormatter is the minimal view of the interface-layer
// StandardResponseFormatter (interface/utils/response_formatter.py), which has
// no Go port yet. Declared here and reported as a dependency.
type ContextResponseFormatter interface {
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	FormatContextResponse(facadeResponse *entities.OrderedMap[any], operation string, standardizeFieldNames bool) *entities.OrderedMap[any]
}

// ContextOperationHandler handles all unified context operations.
type ContextOperationHandler struct {
	responseFormatter ContextResponseFormatter
}

// NewContextOperationHandler ports __init__(response_formatter).
func NewContextOperationHandler(responseFormatter ContextResponseFormatter) *ContextOperationHandler {
	return &ContextOperationHandler{responseFormatter: responseFormatter}
}

var contextValidActions = []string{
	"create", "get", "update", "delete", "resolve", "delegate", "add_insight", "add_progress", "list",
}

// HandleContextOperation ports handle_context_operation.
func (h *ContextOperationHandler) HandleContextOperation(ctx context.Context, facade *facades.UnifiedContextFacade, action string, kwargs map[string]any) *entities.OrderedMap[any] {
	operation := "manage_context." + action

	userID := kwString(kwargs, "user_id")
	if userID == nil {
		authenticated, err := auth_helper.GetAuthenticatedUserID(ctx, nil, operation)
		if err != nil {
			return h.exceptionResponse(action, operation, err)
		}
		userID = &authenticated
	}

	level := kwStringDefault(kwargs, "level", "task")
	contextID := kwStringDefault(kwargs, "context_id", "")
	data, _ := kwargs["data"].(*entities.OrderedMap[any])
	gitBranchID := kwString(kwargs, "git_branch_id")
	forceRefresh := kwBool(kwargs, "force_refresh", false)
	includeInherited := kwBool(kwargs, "include_inherited", false)
	propagateChanges := kwBool(kwargs, "propagate_changes", true)
	delegateTo := kwStringDefault(kwargs, "delegate_to", "")
	delegateData, _ := kwargs["delegate_data"].(*entities.OrderedMap[any])
	delegationReason := kwString(kwargs, "delegation_reason")
	content := kwStringDefault(kwargs, "content", "")
	category := kwString(kwargs, "category")
	importance := kwString(kwargs, "importance")
	agent := kwString(kwargs, "agent")
	filters, _ := kwargs["filters"].(*entities.OrderedMap[any])

	var (
		result *entities.OrderedMap[any]
		err    error
	)

	switch action {
	case "create":
		if level == "task" && gitBranchID != nil && data != nil {
			if !data.Has("branch_id") {
				data.Set("branch_id", *gitBranchID)
			}
			if !data.Has("parent_branch_id") {
				data.Set("parent_branch_id", *gitBranchID)
			}
			if !data.Has("parent_branch_context_id") {
				data.Set("parent_branch_context_id", *gitBranchID)
			}
		}
		result, err = facade.CreateContext(ctx, level, contextID, data, userID)
	case "get":
		result, err = facade.GetContext(ctx, level, contextID, includeInherited, forceRefresh, userID)
	case "update":
		result, err = facade.UpdateContext(ctx, level, contextID, data, propagateChanges)
	case "delete":
		result, err = facade.DeleteContext(ctx, level, contextID)
	case "resolve":
		result, err = facade.ResolveContext(ctx, level, contextID, forceRefresh)
	case "delegate":
		result, err = facade.DelegateContext(ctx, level, contextID, delegateTo, delegateData, delegationReason)
	case "add_insight":
		result, err = facade.AddInsight(ctx, level, contextID, content, category, importance, agent)
	case "add_progress":
		result, err = facade.AddProgress(ctx, level, contextID, content, agent)
	case "list":
		result, err = facade.ListContexts(ctx, level, filters)
	default:
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("valid_actions", contextValidActions)
		return h.responseFormatter.CreateErrorResponse(
			operation,
			"Unknown action: "+action+". Valid actions: "+pyStringList(contextValidActions),
			"OPERATION_FAILED",
			metadata,
		)
	}

	if err != nil {
		return h.handleFacadeError(action, operation, level, err)
	}

	return h.responseFormatter.FormatContextResponse(result, action, true)
}

func (h *ContextOperationHandler) handleFacadeError(action, operation, level string, err error) *entities.OrderedMap[any] {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("action", action)
	metadata.Set("level", level)

	var ve *value_objects.ValueError
	if errors.As(err, &ve) {
		return h.responseFormatter.CreateErrorResponse(operation, ve.Msg, "VALIDATION_ERROR", metadata)
	}
	return h.responseFormatter.CreateErrorResponse(operation, "Operation failed: "+err.Error(), "INTERNAL_ERROR", metadata)
}

func (h *ContextOperationHandler) exceptionResponse(action, operation string, err error) *entities.OrderedMap[any] {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("action", action)
	metadata.Set("level", "task")
	return h.responseFormatter.CreateErrorResponse(operation, "Operation failed: "+err.Error(), "INTERNAL_ERROR", metadata)
}

func kwString(kwargs map[string]any, key string) *string {
	if v, ok := kwargs[key]; ok {
		if s, isStr := v.(string); isStr {
			return &s
		}
	}
	return nil
}

func kwStringDefault(kwargs map[string]any, key, def string) string {
	if p := kwString(kwargs, key); p != nil {
		return *p
	}
	return def
}

func kwBool(kwargs map[string]any, key string, def bool) bool {
	if v, ok := kwargs[key]; ok {
		if b, isBool := v.(bool); isBool {
			return b
		}
	}
	return def
}

// pyStringList mirrors ", ".join(list).
func pyStringList(items []string) string {
	out := ""
	for i, item := range items {
		if i > 0 {
			out += ", "
		}
		out += item
	}
	return out
}
