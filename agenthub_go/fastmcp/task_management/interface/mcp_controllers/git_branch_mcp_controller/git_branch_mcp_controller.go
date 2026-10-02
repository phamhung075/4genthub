package git_branch_mcp_controller

// Git Branch MCP Controller - Modular Implementation
// (Python git_branch_mcp_controller.py).
//
// FastMCP tool registration (`register_tools`), ContextPropagationMixin and the
// thread/event-loop helpers have no Go meaning and are not ported; the
// management logic is.

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	facade_service "agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/configuration"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/factories"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller/handlers"
)

// WorkflowGuidance is the subset of GitBranchWorkflowGuidance used by the
// controller. The workflow_guidance package has no Go port yet.
type WorkflowGuidance interface {
	GenerateGuidance(action string, context *entities.OrderedMap[any]) any
}

// WorkflowGuidanceFactory mirrors GitBranchWorkflowFactory.create().
type WorkflowGuidanceFactory func() WorkflowGuidance

// DefaultWorkflowGuidanceFactory can be set by callers once the workflow
// guidance package is ported.
var DefaultWorkflowGuidanceFactory WorkflowGuidanceFactory

// DefaultFacadeService replaces Python FacadeService.get_instance(); the Go
// FacadeService has no singleton accessor.
var DefaultFacadeService *facade_service.FacadeService

// GetCurrentUserIDHook replaces get_current_user_id().
var GetCurrentUserIDHook func(ctx context.Context) any

// GitBranchMCPController ports GitBranchMCPController.
type GitBranchMCPController struct {
	config            *configuration.ToolConfig
	facadeService     *facade_service.FacadeService
	responseFormatter handlers.ResponseFormatter
	operationFactory  *factories.GitBranchOperationFactory
	workflowGuidance  WorkflowGuidance
}

// NewGitBranchMCPController ports __init__(facade_service=None, config=None).
func NewGitBranchMCPController(facadeService *facade_service.FacadeService, config *configuration.ToolConfig, responseFormatter handlers.ResponseFormatter) (*GitBranchMCPController, error) {
	if config == nil {
		var err error
		config, err = configuration.NewToolConfig(nil)
		if err != nil {
			return nil, err
		}
	}
	if facadeService == nil {
		facadeService = DefaultFacadeService
	}

	c := &GitBranchMCPController{
		config:            config,
		facadeService:     facadeService,
		responseFormatter: responseFormatter,
	}
	if config.IsWorkflowGuidanceEnabled() {
		if DefaultWorkflowGuidanceFactory != nil {
			c.workflowGuidance = DefaultWorkflowGuidanceFactory()
		}
	}
	c.operationFactory = factories.NewGitBranchOperationFactory(responseFormatter)
	return c, nil
}

// authenticatedUserID ports get_authenticated_user_id(provided_user_id, operation_name).
func (c *GitBranchMCPController) authenticatedUserID(ctx context.Context, provided *string, operationName string) (*string, error) {
	if provided != nil && *provided != "" {
		validated, err := domain.ValidateUserID(provided, operationName)
		if err != nil {
			return nil, err
		}
		return &validated, nil
	}

	if GetCurrentUserIDHook == nil {
		return nil, &value_objects.ValueError{Msg: "User context middleware not available"}
	}

	contextUserObj := GetCurrentUserIDHook(ctx)
	var currentUserID *string
	switch u := contextUserObj.(type) {
	case string:
		id := u
		currentUserID = &id
	case interface{ GetUserID() string }:
		id := u.GetUserID()
		currentUserID = &id
	case nil:
		currentUserID = nil
	default:
		id := fmt.Sprint(contextUserObj)
		currentUserID = &id
	}

	validated, err := domain.ValidateUserID(currentUserID, operationName)
	if err != nil {
		return nil, err
	}
	return &validated, nil
}

// getFacadeForRequest ports _get_facade_for_request(project_id, user_id).
func (c *GitBranchMCPController) getFacadeForRequest(projectID string, userID *string) (*facades.GitBranchApplicationFacade, error) {
	if c.facadeService == nil {
		return nil, &value_objects.ValueError{Msg: "FacadeService is required but not provided"}
	}
	facade, err := c.facadeService.GetBranchFacade(&projectID, userID)
	if err != nil {
		return nil, err
	}
	if typed, ok := facade.(*facades.GitBranchApplicationFacade); ok {
		return typed, nil
	}
	return nil, fmt.Errorf("git branch facade has unexpected type %T", facade)
}

// ManageGitBranch ports manage_git_branch(action, user_id=None, **kwargs).
func (c *GitBranchMCPController) ManageGitBranch(ctx context.Context, action string, projectID, gitBranchID, gitBranchName, gitBranchDescription, agentID, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = c.responseFormatter.CreateErrorResponse(action, fmt.Sprintf("Git branch operation failed: %v", r), handlers.ErrorCodeOperationFailed, handlers.MetaMap("project_id", projectID))
		}
	}()

	authUserID, err := c.authenticatedUserID(ctx, userID, "manage_git_branch:"+action)
	if err != nil {
		return c.responseFormatter.CreateErrorResponse(action, "Git branch operation failed: "+err.Error(), handlers.ErrorCodeOperationFailed, handlers.MetaMap("project_id", projectID))
	}

	if projectID == nil || *projectID == "" {
		return c.responseFormatter.CreateErrorResponse(
			action,
			"Missing required field: project_id. Expected: A valid project_id string",
			handlers.ErrorCodeValidation,
			handlers.MetaMap("field", "project_id", "hint", "Include 'project_id' in your request"),
		)
	}

	facade, ferr := c.getFacadeForRequest(*projectID, authUserID)
	if ferr != nil {
		return c.responseFormatter.CreateErrorResponse(action, "Git branch operation failed: "+ferr.Error(), handlers.ErrorCodeOperationFailed, handlers.MetaMap("project_id", projectID))
	}

	res := c.operationFactory.HandleOperation(ctx, action, facade, factories.OperationParams{
		ProjectID:            projectID,
		GitBranchID:          gitBranchID,
		GitBranchName:        gitBranchName,
		GitBranchDescription: gitBranchDescription,
		AgentID:              agentID,
	})

	if success, ok := res.Get("success"); ok && value_objects.PyTruthy(success) {
		res = c.enhanceResponseWithWorkflowGuidance(res, action, *projectID)
	}
	return res
}

// enhanceResponseWithWorkflowGuidance ports
// _enhance_response_with_workflow_guidance(response, action, project_id).
func (c *GitBranchMCPController) enhanceResponseWithWorkflowGuidance(response *entities.OrderedMap[any], action, projectID string) (result *entities.OrderedMap[any]) {
	if !c.config.IsWorkflowGuidanceEnabled() {
		return response
	}

	defer func() {
		// Python swallows guidance failures; a panic becomes the plain response.
		if r := recover(); r != nil {
			result = response
		}
	}()

	if c.workflowGuidance != nil {
		contextMap := entities.NewOrderedMap[any]()
		contextMap.Set("project_id", projectID)
		contextMap.Set("response", response)
		guidance := c.workflowGuidance.GenerateGuidance(action, contextMap)
		if guidance != nil && value_objects.PyTruthy(guidance) {
			response.Set("workflow_guidance", guidance)
		}
	}
	return response
}
