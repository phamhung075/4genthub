package subtask_mcp_controller

// Subtask MCP Controller - Refactored Modular Implementation
// (Python subtask_mcp_controller.py).
//
// FastMCP tool registration (`register_tools`) has no Go meaning and is not
// ported; the management logic below is.
//
// The Python `SubtaskOperationFactory`, workflow-guidance subtask module and
// `coerce_parameter_types` have no Go port yet, so minimal interfaces/hooks are
// declared here (reported as dependencies).

import (
	"context"
	"fmt"
	"time"

	"agenthub/fastmcp/task_management/application/facades"
	facade_service "agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/configuration"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/factories"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/handlers"
)

// SubtaskWorkflowGuidance is the subset of SubtaskWorkflowGuidance used by the
// controller. The workflow_guidance package has no Go port yet.
type SubtaskWorkflowGuidance interface {
	EnhanceResponse(response *entities.OrderedMap[any], action string, ctx *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// SubtaskWorkflowFactory mirrors SubtaskWorkflowFactory.create().
type SubtaskWorkflowFactory func() SubtaskWorkflowGuidance

// DefaultWorkflowGuidanceFactory and DefaultOperationFactory can be set by
// callers once the corresponding packages are ported.
var (
	DefaultWorkflowGuidanceFactory SubtaskWorkflowFactory
	DefaultOperationFactory        *factories.SubtaskOperationFactory
)

// CoerceParameterTypes replaces coerce_parameter_types (unported). Defaults to
// identity; callers may override.
var CoerceParameterTypes = func(kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] { return kwargs }

// ParentTaskFacade is the subset of the task facade used to derive the parent
// task's git_branch_id.
type ParentTaskFacade interface {
	GetTask(ctx context.Context, taskID string) (*entities.OrderedMap[any], error)
}

// LegacySubtaskFacade mirrors the facade returned by the legacy
// SubtaskFacadeFactory.create_subtask_facade() interface.
type LegacySubtaskFacade interface {
	CreateSubtask(ctx context.Context, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	UpdateSubtask(ctx context.Context, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	DeleteSubtask(ctx context.Context, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetSubtask(ctx context.Context, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	ListSubtasks(ctx context.Context, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CompleteSubtask(ctx context.Context, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// LegacySubtaskFacadeFactory mirrors the legacy factory interface.
type LegacySubtaskFacadeFactory interface {
	CreateSubtaskFacade() LegacySubtaskFacade
}

// SubtaskMCPController ports SubtaskMCPController.
type SubtaskMCPController struct {
	config            *configuration.ToolConfig
	facadeService     *facade_service.FacadeService
	legacyFactory     LegacySubtaskFacadeFactory
	taskFacade        ParentTaskFacade
	contextFacade     handlers.ContextFacade
	responseFormatter handlers.ResponseFormatter
	operationFactory  *factories.SubtaskOperationFactory
	workflowGuidance  SubtaskWorkflowGuidance
}

// NewSubtaskMCPController ports __init__.
func NewSubtaskMCPController(facadeService *facade_service.FacadeService, legacyFactory LegacySubtaskFacadeFactory,
	taskFacade ParentTaskFacade, contextFacade handlers.ContextFacade, config *configuration.ToolConfig,
	responseFormatter handlers.ResponseFormatter) (*SubtaskMCPController, error) {
	if config == nil {
		var err error
		config, err = configuration.NewToolConfig(nil)
		if err != nil {
			return nil, err
		}
	}
	c := &SubtaskMCPController{
		config:            config,
		facadeService:     facadeService,
		legacyFactory:     legacyFactory,
		taskFacade:        taskFacade,
		contextFacade:     contextFacade,
		responseFormatter: responseFormatter,
		operationFactory:  DefaultOperationFactory,
	}
	if config.IsWorkflowGuidanceEnabled() && DefaultWorkflowGuidanceFactory != nil {
		c.workflowGuidance = DefaultWorkflowGuidanceFactory()
	}
	return c, nil
}

// ManageSubtask ports manage_subtask(action, task_id, user_id=None, **kwargs).
func (c *SubtaskMCPController) ManageSubtask(ctx context.Context, action, taskID string, userID *string,
	kwargs *entities.OrderedMap[any]) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			meta := entities.NewOrderedMap[any]()
			meta.Set("task_id", taskID)
			result = c.responseFormatter.CreateErrorResponse(action,
				fmt.Sprintf("Subtask operation failed: %v", r), handlers.ErrorCodeOperationFailed, meta)
		}
	}()

	authenticatedUser, err := auth_helper.GetAuthenticatedUserID(ctx, userID, "manage_subtask:"+action)
	if err != nil {
		meta := entities.NewOrderedMap[any]()
		meta.Set("task_id", taskID)
		return c.responseFormatter.CreateErrorResponse(action,
			fmt.Sprintf("Subtask operation failed: %s", err.Error()), handlers.ErrorCodeOperationFailed, meta)
	}
	auth_helper.LogAuthenticationDetails(&authenticatedUser, ptr("manage_subtask:"+action))

	if taskID == "" {
		meta := entities.NewOrderedMap[any]()
		meta.Set("field", "task_id")
		meta.Set("hint", "Include 'task_id' in your request")
		return c.responseFormatter.CreateErrorResponse(action,
			"Missing required field: task_id. Expected: A valid task_id string",
			handlers.ErrorCodeValidation, meta)
	}

	if kwargs == nil {
		kwargs = entities.NewOrderedMap[any]()
	}

	if c.legacyFactory != nil {
		facade := c.legacyFactory.CreateSubtaskFacade()
		switch action {
		case "create":
			return facade.CreateSubtask(ctx, kwargs)
		case "update":
			return facade.UpdateSubtask(ctx, kwargs)
		case "delete":
			return facade.DeleteSubtask(ctx, kwargs)
		case "get":
			return facade.GetSubtask(ctx, kwargs)
		case "list":
			return facade.ListSubtasks(ctx, kwargs)
		case "complete":
			return facade.CompleteSubtask(ctx, kwargs)
		default:
			return c.responseFormatter.CreateErrorResponse(action, "Unknown action: "+action,
				handlers.ErrorCodeValidation, entities.NewOrderedMap[any]())
		}
	}

	facade, ferr := c.getFacadeForRequest(ctx, taskID, authenticatedUser)
	if ferr != nil {
		meta := entities.NewOrderedMap[any]()
		meta.Set("task_id", taskID)
		return c.responseFormatter.CreateErrorResponse(action,
			fmt.Sprintf("Subtask operation failed: %s", ferr.Error()), handlers.ErrorCodeOperationFailed, meta)
	}

	coercedKwargs := CoerceParameterTypes(kwargs)

	switch action {
	case "create", "update", "complete":
		subtaskData := entities.NewOrderedMap[any]()
		dataFields := []string{
			"title", "description", "status", "priority", "assignees",
			"progress_percentage", "progress_notes", "completion_summary",
			"testing_notes", "insights_found", "challenges_overcome",
			"skills_learned", "next_recommendations", "deliverables",
			"completion_quality", "impact_on_parent", "blockers",
		}
		for _, field := range dataFields {
			if v, ok := coercedKwargs.Get(field); ok && v != nil {
				subtaskData.Set(field, v)
			}
		}
		if action == "complete" {
			subtaskData.Set("status", "done")
			subtaskData.Set("progress_percentage", 100)
			if _, ok := subtaskData.Get("completed_at"); !ok {
				subtaskData.Set("completed_at", value_objects.IsoFormat(nowUTC()))
			}
		}
		var subtaskID *string
		if v, ok := coercedKwargs.Get("subtask_id"); ok {
			if s, ok := v.(string); ok {
				subtaskID = &s
			}
		}
		res, callErr := facade.HandleManageSubtask(ctx, action, taskID, subtaskData, subtaskID, false, nil, nil, &authenticatedUser)
		if callErr != nil {
			return c.responseFormatter.CreateErrorResponse(action,
				fmt.Sprintf("Subtask operation failed: %s", callErr.Error()), handlers.ErrorCodeOperationFailed,
				metaMap("task_id", taskID))
		}
		result = res
	case "list":
		filterData := entities.NewOrderedMap[any]()
		for _, key := range []string{"status", "priority", "limit", "offset"} {
			if v, ok := coercedKwargs.Get(key); ok {
				filterData.Set(key, v)
			}
		}
		var filterPtr *entities.OrderedMap[any]
		if filterData.Len() > 0 {
			filterPtr = filterData
		}
		res, callErr := facade.HandleManageSubtask(ctx, "list", taskID, filterPtr, nil, false, nil, nil, &authenticatedUser)
		if callErr != nil {
			return c.responseFormatter.CreateErrorResponse(action,
				fmt.Sprintf("Subtask operation failed: %s", callErr.Error()), handlers.ErrorCodeOperationFailed,
				metaMap("task_id", taskID))
		}
		result = res
	case "get", "delete":
		var subtaskID *string
		if v, ok := coercedKwargs.Get("subtask_id"); ok {
			if s, ok := v.(string); ok {
				subtaskID = &s
			}
		}
		res, callErr := facade.HandleManageSubtask(ctx, action, taskID, nil, subtaskID, false, nil, nil, &authenticatedUser)
		if callErr != nil {
			return c.responseFormatter.CreateErrorResponse(action,
				fmt.Sprintf("Subtask operation failed: %s", callErr.Error()), handlers.ErrorCodeOperationFailed,
				metaMap("task_id", taskID))
		}
		result = res
	default:
		return c.responseFormatter.CreateErrorResponse(action, "Unknown action: "+action,
			handlers.ErrorCodeValidation, entities.NewOrderedMap[any]())
	}

	if omSuccessGeneric(result) {
		result = c.enhanceResponseWithWorkflowGuidance(result, action, taskID)
	}
	return result
}

// getFacadeForRequest ports _get_facade_for_request(task_id, user_id).
func (c *SubtaskMCPController) getFacadeForRequest(ctx context.Context, taskID, userID string) (*facades.SubtaskApplicationFacade, error) {
	if c.legacyFactory != nil {
		return nil, fmt.Errorf("legacy facade factory does not return a SubtaskApplicationFacade")
	}
	if c.facadeService == nil {
		return nil, &value_objects.ValueError{Msg: "FacadeService is required but not provided"}
	}

	taskFacadeRaw, err := c.facadeService.GetTaskFacade(nil, nil, &userID)
	if err != nil {
		return nil, fmt.Errorf("Failed to get subtask facade: %s", err.Error())
	}
	taskFacade, ok := taskFacadeRaw.(ParentTaskFacade)
	if !ok {
		return nil, fmt.Errorf("Failed to get subtask facade: task facade does not implement GetTask")
	}
	parentTask, err := taskFacade.GetTask(ctx, taskID)
	if err != nil {
		return nil, fmt.Errorf("Failed to get subtask facade: %s", err.Error())
	}
	taskNodeAny, _ := parentTask.Get("task")
	taskNode, ok := taskNodeAny.(*entities.OrderedMap[any])
	if !ok {
		return nil, fmt.Errorf("Failed to get subtask facade: Parent task %s not found", taskID)
	}
	gitBranchIDAny, ok := taskNode.Get("git_branch_id")
	if !ok || gitBranchIDAny == nil {
		return nil, fmt.Errorf("Failed to get subtask facade: Parent task %s missing git_branch_id required for context derivation", taskID)
	}
	gitBranchID, _ := gitBranchIDAny.(string)
	if gitBranchID == "" {
		return nil, fmt.Errorf("Failed to get subtask facade: Parent task %s missing git_branch_id required for context derivation", taskID)
	}

	subtaskFacadeRaw, err := c.facadeService.GetSubtaskFacade(nil, &gitBranchID, &userID, nil)
	if err != nil {
		return nil, fmt.Errorf("Failed to get subtask facade: %s", err.Error())
	}
	subtaskFacade, ok := subtaskFacadeRaw.(*facades.SubtaskApplicationFacade)
	if !ok {
		return nil, fmt.Errorf("Failed to get subtask facade: unexpected facade type %T", subtaskFacadeRaw)
	}
	return subtaskFacade, nil
}

// enhanceResponseWithWorkflowGuidance ports _enhance_response_with_workflow_guidance.
func (c *SubtaskMCPController) enhanceResponseWithWorkflowGuidance(response *entities.OrderedMap[any], action, taskID string) *entities.OrderedMap[any] {
	if !c.config.IsWorkflowGuidanceEnabled() {
		return response
	}
	if c.workflowGuidance == nil {
		return response
	}
	contextMap := entities.NewOrderedMap[any]()
	contextMap.Set("task_id", taskID)
	enhanced := c.workflowGuidance.EnhanceResponse(response, action, contextMap)
	if enhanced != nil {
		for _, k := range enhanced.Keys() {
			v, _ := enhanced.Get(k)
			response.Set(k, v)
		}
	}
	return response
}

// --- backward-compatibility bridge methods ---

// CreateSubtask ports create_subtask (bridge).
func (c *SubtaskMCPController) CreateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleBridge(ctx, "create", facade, kwargs)
}

// UpdateSubtask ports update_subtask (bridge).
func (c *SubtaskMCPController) UpdateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleBridge(ctx, "update", facade, kwargs)
}

// DeleteSubtask ports delete_subtask (bridge).
func (c *SubtaskMCPController) DeleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleBridge(ctx, "delete", facade, kwargs)
}

// GetSubtask ports get_subtask (bridge).
func (c *SubtaskMCPController) GetSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleBridge(ctx, "get", facade, kwargs)
}

// ListSubtasks ports list_subtasks (bridge).
func (c *SubtaskMCPController) ListSubtasks(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleBridge(ctx, "list", facade, kwargs)
}

// CompleteSubtask ports complete_subtask (bridge).
func (c *SubtaskMCPController) CompleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleBridge(ctx, "complete", facade, kwargs)
}

func (c *SubtaskMCPController) handleBridge(ctx context.Context, operation string, facade *facades.SubtaskApplicationFacade, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if c.operationFactory == nil {
		return c.responseFormatter.CreateErrorResponse(operation, "Operation factory not configured",
			handlers.ErrorCodeOperationFailed, entities.NewOrderedMap[any]())
	}
	return c.operationFactory.HandleOperation(ctx, operation, facade, kwargs)
}

func ptr(s string) *string { return &s }

// metaMap builds an OrderedMap from key/value pairs.
func metaMap(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

// omSuccessGeneric reads the boolean "success" field.
func omSuccessGeneric(o *entities.OrderedMap[any]) bool {
	if o == nil {
		return false
	}
	b, _ := o.Get("success")
	v, _ := b.(bool)
	return v
}

// nowUTC is a package-local copy of datetime.now(UTC).
func nowUTC() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }
