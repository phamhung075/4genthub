package task_mcp_controller

// Task MCP Controller - Refactored Modular Implementation
// (Python task_mcp_controller.py).
//
// FastMCP tool registration (`register_tools`), ContextPropagationMixin and the
// asyncio/thread event-loop helpers have no Go meaning and are not ported. The
// Python legacy TaskFacadeFactory interface and the task operation factory are
// ported (application/factories/task_facade_factory.go and
// factories/operation_factory.go): the operation factory is injected through
// TaskOperationFactory and reported as a dependency.

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	facade_service "agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/configuration"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/validators"
)

// TaskOperationFactory is the minimal view of
// task_mcp_controller/factories/operation_factory.py, ported in
// factories/operation_factory.go.
type TaskOperationFactory interface {
	HandleOperation(ctx context.Context, operation string, facade *facades.TaskApplicationFacade, userID *string,
		taskID *string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// TaskWorkflowGuidance is the subset of TaskWorkflow guidance used by the
// controller. The workflow_guidance package is ported in
// interface/mcp_controllers/workflow_guidance/task/task_workflow_guidance.go.
type TaskWorkflowGuidance interface {
	EnhanceResponse(response *entities.OrderedMap[any], action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// WorkflowHintEnhancer mirrors WorkflowHintEnhancer.enhance_response.
type WorkflowHintEnhancer interface {
	EnhanceResponse(response *entities.OrderedMap[any], action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// TaskDescriptionLoader is the minimal view of description_loader.
type TaskDescriptionLoader interface {
	GetAllDescriptions() *entities.OrderedMap[any]
}

// DescriptionLoader mirrors the module-level description_loader (empty by default).
var DescriptionLoader TaskDescriptionLoader

// SetDescriptionLoader wires the module-level loader.
func SetDescriptionLoader(l TaskDescriptionLoader) { DescriptionLoader = l }

// taskAuthFormatterAdapter narrows the ResponseFormatter to the 3-argument
// form expected by TaskAuthorizationService.
type taskAuthFormatterAdapter struct {
	formatter factories.ResponseFormatter
}

func (a taskAuthFormatterAdapter) CreateErrorResponse(operation, errMsg, errorCode string) *entities.OrderedMap[any] {
	return a.formatter.CreateErrorResponse(operation, errMsg, errorCode, nil)
}

func init() {
	factories.NewParameterValidator = func(rf factories.ResponseFormatter) factories.ParameterValidator {
		return validators.NewParameterValidator(rf)
	}
	factories.NewContextValidator = func(rf factories.ResponseFormatter) factories.ContextValidator {
		return validators.NewContextValidator(rf)
	}
	factories.NewBusinessValidator = func(rf factories.ResponseFormatter) factories.BusinessValidator {
		return validators.NewBusinessValidator(rf)
	}
}

// TaskMCPController ports TaskMCPController.
type TaskMCPController struct {
	config                 *configuration.ToolConfig
	facadeService          *facade_service.FacadeService
	workflowHintEnhancer   WorkflowHintEnhancer
	workflowGuidance       TaskWorkflowGuidance
	responseFormatter      factories.ResponseFormatter
	operationFactory       TaskOperationFactory
	validationFactory      *factories.ValidationFactory
	responseFactory        *factories.ResponseFactory
	enforcementService     *facade_service.ParameterEnforcementService
	progressiveEnforcement *facade_service.ProgressiveEnforcementService
	authorizationService   *facade_service.TaskAuthorizationService
}

// NewTaskMCPController ports __init__(facade_service_or_factory=None,
// workflow_hint_enhancer=None, config=None). The Python legacy
// TaskFacadeFactory branch is not ported.
func NewTaskMCPController(facadeService *facade_service.FacadeService, operationFactory TaskOperationFactory,
	responseFormatter factories.ResponseFormatter, workflowHintEnhancer WorkflowHintEnhancer,
	config *configuration.ToolConfig) (*TaskMCPController, error) {
	if config == nil {
		var err error
		config, err = configuration.NewToolConfig(nil)
		if err != nil {
			return nil, err
		}
	}

	c := &TaskMCPController{
		config:               config,
		facadeService:        facadeService,
		workflowHintEnhancer: workflowHintEnhancer,
		responseFormatter:    responseFormatter,
		operationFactory:     operationFactory,
	}
	c.validationFactory = factories.NewValidationFactory(responseFormatter)
	c.responseFactory = factories.NewResponseFactory(responseFormatter)

	c.enforcementService = facade_service.NewParameterEnforcementService(facade_service.EnforcementLevel("warning"), nil)
	c.progressiveEnforcement = facade_service.NewProgressiveEnforcementService(c.enforcementService, facade_service.EnforcementLevel("warning"))
	c.authorizationService = facade_service.NewTaskAuthorizationService(taskAuthFormatterAdapter{formatter: responseFormatter})

	return c, nil
}

// ManageTask ports manage_task(action, user_id=None, **kwargs). kwargs is the
// ordered equivalent of Python's keyword arguments.
func (c *TaskMCPController) ManageTask(ctx context.Context, action string, userID *string, kwargs *entities.OrderedMap[any]) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = c.responseFactory.CreateErrorResponse(action, fmt.Sprint(r), strPtr(factories.ErrorCodeOperationFailed), nil)
		}
	}()

	if kwargs == nil {
		kwargs = entities.NewOrderedMap[any]()
	}

	// Step 1: Authentication.
	authenticatedUser, err := auth_helper.GetAuthenticatedUserID(ctx, userID, "manage_task:"+action)
	if err != nil {
		return c.responseFactory.CreateErrorResponse(action, err.Error(), strPtr(factories.ErrorCodeOperationFailed), nil)
	}
	auth_helper.LogAuthenticationDetails(&authenticatedUser, strPtr("manage_task:"+action))

	taskIDAny, _ := kwargs.Get("task_id")
	var taskID *string
	if s, ok := taskIDAny.(string); ok {
		taskID = &s
	}
	gitBranchIDAny, _ := kwargs.Get("git_branch_id")
	var gitBranchID *string
	if s, ok := gitBranchIDAny.(string); ok {
		gitBranchID = &s
	}

	// Step 1.5: Permission Authorization.
	if ok, permissionErr := c.checkTaskPermissions(ctx, action, authenticatedUser, taskID); !ok {
		return permissionErr
	}

	// Step 2: Filter task_id out of kwargs.
	filteredKwargs := entities.NewOrderedMap[any]()
	for _, k := range kwargs.Keys() {
		if k == "task_id" {
			continue
		}
		v, _ := kwargs.Get(k)
		filteredKwargs.Set(k, v)
	}

	// Step 2.5: Transform parameters.
	transform := facade_service.ParameterTransformationService{}
	if v, ok := filteredKwargs.Get("assignees"); ok && v != nil {
		filteredKwargs.Set("assignees", transform.TransformStringToList(v, "assignees"))
	}
	if v, ok := filteredKwargs.Get("labels"); ok && v != nil {
		filteredKwargs.Set("labels", transform.TransformStringToList(v, "labels"))
	}
	if v, ok := filteredKwargs.Get("dependencies"); ok && v != nil {
		filteredKwargs.Set("dependencies", transform.TransformStringToList(v, "dependencies"))
	}
	if v, ok := filteredKwargs.Get("progress_percentage"); ok && v != nil {
		validated, errorMsg := transform.ValidateProgressPercentage(v)
		if errorMsg != nil {
			return c.responseFactory.CreateErrorResponse(action, *errorMsg, strPtr(factories.ErrorCodeValidation), nil)
		}
		if validated != nil {
			filteredKwargs.Set("progress_percentage", *validated)
		}
	}

	// Step 3: Get facade.
	facade, err := c.getFacadeForRequest(taskID, gitBranchID, &authenticatedUser)
	if err != nil {
		return c.responseFactory.CreateErrorResponse(action, err.Error(), strPtr(factories.ErrorCodeOperationFailed), nil)
	}

	// Step 4: Validation.
	if ok, validationErr := c.validateRequest(action, taskID, filteredKwargs); !ok {
		return validationErr
	}

	// Step 5: Execute operation.
	if c.operationFactory == nil {
		return c.responseFactory.CreateErrorResponse(action, "Operation factory not configured",
			strPtr(factories.ErrorCodeOperationFailed), nil)
	}
	res := c.operationFactory.HandleOperation(ctx, action, facade, &authenticatedUser, taskID, filteredKwargs)

	// Step 6: Standardize response.
	standardized := c.responseFactory.StandardizeFacadeResponse(res, action)

	// Step 7: Apply workflow hints and enrichment.
	if c.workflowHintEnhancer != nil {
		successVal, _ := standardized.Get("success")
		if value_objects.PyTruthy(successVal) {
			enhanced := c.workflowHintEnhancer.EnhanceResponse(standardized, action, kwargs)
			if enhanced != nil {
				return enhanced
			}
		}
	}

	return standardized
}

// getFacadeForRequest ports _get_facade_for_request.
func (c *TaskMCPController) getFacadeForRequest(taskID, gitBranchID, userID *string) (*facades.TaskApplicationFacade, error) {
	if c.facadeService == nil {
		return nil, &value_objects.ValueError{Msg: "FacadeService is required but not provided"}
	}
	facade, err := c.facadeService.GetTaskFacade(nil, gitBranchID, userID)
	if err != nil {
		return nil, err
	}
	if typed, ok := facade.(*facades.TaskApplicationFacade); ok {
		return typed, nil
	}
	if wrapped, ok := facade.(interface {
		TaskApplicationFacade() *facades.TaskApplicationFacade
	}); ok {
		return wrapped.TaskApplicationFacade(), nil
	}
	return nil, fmt.Errorf("task facade has unexpected type %T", facade)
}

// validateRequest ports _validate_request.
func (c *TaskMCPController) validateRequest(action string, taskID *string, kwargs *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any]) {
	switch action {
	case "create":
		return c.validationFactory.ValidateCreateRequest(
			omStringPtr(kwargs, "title"),
			omStringPtr(kwargs, "git_branch_id"),
			omStringPtr(kwargs, "description"),
			omStringPtr(kwargs, "status"),
			omStringPtr(kwargs, "priority"),
			omStringPtr(kwargs, "due_date"),
			omStringSlice(kwargs, "assignees"),
			omStringSlice(kwargs, "labels"),
			omStringSlice(kwargs, "dependencies"),
			nil,
		)
	case "update", "complete":
		return c.validationFactory.ValidateUpdateRequest(taskID, nil, omToMap(kwargs))
	case "list", "search":
		return c.validationFactory.ValidateSearchRequest(action, omStringPtr(kwargs, "query"), omToMap(kwargs))
	case "delete":
		taskIDStr := ""
		if taskID != nil {
			taskIDStr = *taskID
		}
		return c.validationFactory.ValidateDeletionRequest(taskIDStr, nil)
	case "get":
		if taskID == nil {
			return false, c.responseFormatter.CreateErrorResponse("get", "task_id is required",
				factories.ErrorCodeValidation, nil)
		}
		return true, nil
	case "add_dependency", "remove_dependency":
		if taskID == nil {
			return false, c.responseFormatter.CreateErrorResponse(action,
				"task_id is required for dependency operations", factories.ErrorCodeValidation, nil)
		}
		if omStringPtr(kwargs, "dependency_id") == nil {
			return false, c.responseFormatter.CreateErrorResponse(action,
				"dependency_id is required for dependency operations", factories.ErrorCodeValidation, nil)
		}
		return true, nil
	case "next":
		if omStringPtr(kwargs, "git_branch_id") == nil {
			metadata := entities.NewOrderedMap[any]()
			metadata.Set("hint", "Use 'next' action to get recommended tasks for a specific branch")
			return false, c.responseFormatter.CreateErrorResponse("next",
				"git_branch_id is required for next action", factories.ErrorCodeValidation, metadata)
		}
		return true, nil
	default:
		return true, nil
	}
}

// GetTaskManagementDescriptions ports _get_task_management_descriptions.
func (c *TaskMCPController) GetTaskManagementDescriptions() *entities.OrderedMap[any] {
	if DescriptionLoader != nil {
		all := DescriptionLoader.GetAllDescriptions()
		if all != nil && all.Has("tasks") {
			if m, ok := all.GetAny("tasks").(*entities.OrderedMap[any]); ok {
				return m
			}
		}
	}
	return entities.NewOrderedMap[any]()
}

// checkTaskPermissions ports _check_task_permissions.
func (c *TaskMCPController) checkTaskPermissions(ctx context.Context, action, userID string, taskID *string) (bool, *entities.OrderedMap[any]) {
	return c.authorizationService.CheckTaskPermissionFromContext(ctx, action, userID, taskID)
}

// --- backward-compatibility bridge methods ---

// HandleCRUDOperations ports handle_crud_operations.
func (c *TaskMCPController) HandleCRUDOperations(ctx context.Context, action string, facade any, userID string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleOperation(ctx, action, facade, userID, kwargs)
}

// HandleListSearchNext ports handle_list_search_next.
func (c *TaskMCPController) HandleListSearchNext(ctx context.Context, action string, facade any, userID string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleOperation(ctx, action, facade, userID, kwargs)
}

// HandleRecommendationOperations ports handle_recommendation_operations.
func (c *TaskMCPController) HandleRecommendationOperations(ctx context.Context, action string, facade any, userID string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleOperation(ctx, action, facade, userID, kwargs)
}

// HandleDependencyOperations ports handle_dependency_operations.
func (c *TaskMCPController) HandleDependencyOperations(ctx context.Context, action string, facade any, userID string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.handleOperation(ctx, action, facade, userID, kwargs)
}

func (c *TaskMCPController) handleOperation(ctx context.Context, action string, facade any, userID string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if c.operationFactory == nil {
		return c.responseFactory.CreateErrorResponse(action, "Operation factory not configured",
			strPtr(factories.ErrorCodeOperationFailed), nil)
	}
	typedFacade, _ := facade.(*facades.TaskApplicationFacade)
	return c.operationFactory.HandleOperation(ctx, action, typedFacade, &userID, nil, kwargs)
}

// ManageTaskSync ports manage_task_sync (Go methods are synchronous, so the
// asyncio/thread wrapper collapses to a direct call).
func (c *TaskMCPController) ManageTaskSync(ctx context.Context, action string, userID *string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return c.ManageTask(ctx, action, userID, kwargs)
}

func strPtr(s string) *string { return &s }

func omStringPtr(m *entities.OrderedMap[any], key string) *string {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok || v == nil {
		return nil
	}
	if s, isStr := v.(string); isStr {
		return &s
	}
	return nil
}

func omStringSlice(m *entities.OrderedMap[any], key string) []string {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok || v == nil {
		return nil
	}
	switch t := v.(type) {
	case []string:
		return t
	case []any:
		out := make([]string, 0, len(t))
		for _, item := range t {
			if s, isStr := item.(string); isStr {
				out = append(out, s)
			}
		}
		return out
	}
	return nil
}

func omToMap(m *entities.OrderedMap[any]) map[string]any {
	out := map[string]any{}
	if m == nil {
		return out
	}
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out[k] = v
	}
	return out
}
