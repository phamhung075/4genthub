package agent_mcp_controller

// Agent MCP Controller - Modular Implementation
// (Python agent_mcp_controller.py).
//
// FastMCP tool registration (`register_tools`) has no Go meaning and is not
// ported; the management logic below is.

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	facade_service "agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/configuration"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/factories"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/agent_mcp_controller/handlers"
)

// WorkflowGuidance is the subset of AgentWorkflowGuidance used by the
// controller. The workflow_guidance package is ported in
// interface/mcp_controllers/workflow_guidance/agent/agent_workflow_guidance.go.
type WorkflowGuidance interface {
	GenerateGuidance(action string, context *entities.OrderedMap[any]) any
}

// WorkflowGuidanceFactory mirrors AgentWorkflowFactory.create().
type WorkflowGuidanceFactory func() WorkflowGuidance

// DefaultWorkflowGuidanceFactory can be set by callers once the workflow
// guidance package is ported.
var DefaultWorkflowGuidanceFactory WorkflowGuidanceFactory

// DefaultFacadeService replaces Python FacadeService.get_instance(); the Go
// FacadeService has no singleton accessor.
var DefaultFacadeService *facade_service.FacadeService

// GetCurrentUserIDHook replaces get_current_user_id(). When nil, authentication
// fails with UserAuthenticationRequiredError, mirroring the Python fallback.
var GetCurrentUserIDHook func(ctx context.Context) any

// AgentMCPController ports AgentMCPController.
type AgentMCPController struct {
	config            *configuration.ToolConfig
	facadeService     *facade_service.FacadeService
	workflowGuidance  WorkflowGuidance
	responseFormatter handlers.ResponseFormatter
	operationFactory  *factories.AgentOperationFactory
	responseFactory   *factories.AgentResponseFactory
}

// NewAgentMCPController ports __init__(facade_service=None, config=None).
func NewAgentMCPController(facadeService *facade_service.FacadeService, config *configuration.ToolConfig, responseFormatter handlers.ResponseFormatter) (*AgentMCPController, error) {
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

	c := &AgentMCPController{
		config:            config,
		facadeService:     facadeService,
		responseFormatter: responseFormatter,
	}
	if config.IsWorkflowGuidanceEnabled() {
		if DefaultWorkflowGuidanceFactory != nil {
			c.workflowGuidance = DefaultWorkflowGuidanceFactory()
		}
	}
	c.operationFactory = factories.NewAgentOperationFactory(responseFormatter)
	c.responseFactory = factories.NewAgentResponseFactory(responseFormatter)
	return c, nil
}

// getFacadeForRequest ports _get_facade_for_request(project_id, user_id).
func (c *AgentMCPController) getFacadeForRequest(ctx context.Context, projectID string, userID *string) (*facades.AgentApplicationFacade, error) {
	var currentUserID *string

	if userID != nil && *userID != "" {
		currentUserID = userID
	} else {
		var contextUserObj any
		if GetCurrentUserIDHook == nil {
			return nil, &value_objects.ValueError{Msg: "User context middleware not available"}
		}
		contextUserObj = GetCurrentUserIDHook(ctx)

		if s, ok := contextUserObj.(string); ok {
			currentUserID = &s
		} else if u, ok := contextUserObj.(interface{ GetUserID() string }); ok {
			id := u.GetUserID()
			currentUserID = &id
		} else if contextUserObj != nil {
			id := fmt.Sprint(contextUserObj)
			currentUserID = &id
		}
	}

	validatedUserID, err := domain.ValidateUserID(currentUserID, "Agent facade creation")
	if err != nil {
		return nil, err
	}

	if c.facadeService == nil {
		return nil, fmt.Errorf("facade service not configured")
	}
	facade, err := c.facadeService.GetAgentFacade(projectID, &validatedUserID)
	if err != nil {
		return nil, err
	}
	if typed, ok := facade.(*facades.AgentApplicationFacade); ok {
		return typed, nil
	}
	return nil, fmt.Errorf("agent facade has unexpected type %T", facade)
}

// ManageAgent ports manage_agent(action, project_id=None, ...).
func (c *AgentMCPController) ManageAgent(ctx context.Context, action string, projectID *string, agentID, name, callAgent, gitBranchID, userID *string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			meta := entities.NewOrderedMap[any]()
			meta.Set("action", action)
			meta.Set("project_id", pyAny(projectID))
			result = c.responseFormatter.CreateErrorResponse(action, fmt.Sprintf("Operation failed: %v", r), handlers.ErrorCodeInternalError, meta)
		}
	}()

	// Validate project_id is provided for all actions
	if projectID == nil || *projectID == "" {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", "project_id is required for all agent operations")
		m.Set("details", "Please provide a valid project identifier")
		return m
	}

	// Get facade for this request
	facade, err := c.getFacadeForRequest(ctx, *projectID, userID)
	if err != nil {
		meta := entities.NewOrderedMap[any]()
		meta.Set("action", action)
		meta.Set("project_id", *projectID)
		return c.responseFormatter.CreateErrorResponse(action, "Operation failed: "+err.Error(), handlers.ErrorCodeInternalError, meta)
	}

	// Basic field validation before routing
	if vr := c.validateRequiredFields(action, agentID, name, gitBranchID); vr != nil {
		return vr
	}

	// Route operation through the factory
	response := c.operationFactory.HandleOperation(ctx, action, facade, factories.OperationParams{
		ProjectID:   *projectID,
		AgentID:     agentID,
		Name:        name,
		CallAgent:   callAgent,
		GitBranchID: gitBranchID,
		UserID:      userID,
	})

	// Enhance response with workflow guidance if successful
	return c.enhanceResponseWithWorkflowGuidance(response, action, projectID, agentID)
}

// validateRequiredFields ports _validate_required_fields(...). A nil result
// means valid.
func (c *AgentMCPController) validateRequiredFields(action string, agentID *string, name *string, gitBranchID *string) *entities.OrderedMap[any] {
	if action == "call" {
		return nil
	}
	if action == "register" && (name == nil || *name == "") {
		return c.responseFactory.CreateMissingFieldError("name", action)
	}
	if isOneOf(action, "get", "update", "unregister", "assign", "unassign") && (agentID == nil || *agentID == "") {
		return c.responseFactory.CreateMissingFieldError("agent_id", action)
	}
	if isOneOf(action, "assign", "unassign") && (gitBranchID == nil || *gitBranchID == "") {
		return c.responseFactory.CreateMissingFieldError("git_branch_id", action)
	}
	return nil
}

// getAgentManagementDescriptions ports _get_agent_management_descriptions().
func (c *AgentMCPController) getAgentManagementDescriptions() *entities.OrderedMap[any] {
	flat := entities.NewOrderedMap[any]()
	// all_desc is empty in the Python source, so the loop never matches.
	return flat
}

// HandleCRUDOperations ports handle_crud_operations(...).
func (c *AgentMCPController) HandleCRUDOperations(ctx context.Context, action, projectID string, agentID, name, callAgent *string) *entities.OrderedMap[any] {
	facade, err := c.getFacadeForRequest(ctx, projectID, nil)
	if err != nil {
		meta := entities.NewOrderedMap[any]()
		meta.Set("action", action)
		meta.Set("project_id", projectID)
		return c.responseFormatter.CreateErrorResponse(action, "Operation failed: "+err.Error(), handlers.ErrorCodeInternalError, meta)
	}
	return c.operationFactory.HandleOperation(ctx, action, facade, factories.OperationParams{
		ProjectID: projectID,
		AgentID:   agentID,
		Name:      name,
		CallAgent: callAgent,
	})
}

// HandleAssignmentOperations ports handle_assignment_operations(...).
func (c *AgentMCPController) HandleAssignmentOperations(ctx context.Context, action, projectID, agentID, gitBranchID string, userID *string) *entities.OrderedMap[any] {
	facade, err := c.getFacadeForRequest(ctx, projectID, userID)
	if err != nil {
		meta := entities.NewOrderedMap[any]()
		meta.Set("action", action)
		meta.Set("project_id", projectID)
		return c.responseFormatter.CreateErrorResponse(action, "Operation failed: "+err.Error(), handlers.ErrorCodeInternalError, meta)
	}
	return c.operationFactory.HandleOperation(ctx, action, facade, factories.OperationParams{
		ProjectID:   projectID,
		AgentID:     &agentID,
		GitBranchID: &gitBranchID,
		UserID:      userID,
	})
}

// HandleRebalanceOperation ports handle_rebalance_operation(project_id, user_id).
func (c *AgentMCPController) HandleRebalanceOperation(ctx context.Context, projectID string, userID *string) *entities.OrderedMap[any] {
	facade, err := c.getFacadeForRequest(ctx, projectID, userID)
	if err != nil {
		meta := entities.NewOrderedMap[any]()
		meta.Set("action", "rebalance")
		meta.Set("project_id", projectID)
		return c.responseFormatter.CreateErrorResponse("rebalance", "Operation failed: "+err.Error(), handlers.ErrorCodeInternalError, meta)
	}
	return c.operationFactory.HandleOperation(ctx, "rebalance", facade, factories.OperationParams{
		ProjectID: projectID,
		UserID:    userID,
	})
}

// enhanceResponseWithWorkflowGuidance ports
// _enhance_response_with_workflow_guidance(...).
func (c *AgentMCPController) enhanceResponseWithWorkflowGuidance(response *entities.OrderedMap[any], action string, projectID, agentID *string) *entities.OrderedMap[any] {
	if !c.config.IsWorkflowGuidanceEnabled() {
		return response
	}
	if c.workflowGuidance == nil {
		return response
	}

	success, _ := response.Get("success")
	ok, _ := success.(bool)
	if ok {
		guidanceContext := entities.NewOrderedMap[any]()
		if projectID != nil && *projectID != "" {
			guidanceContext.Set("project_id", *projectID)
		}
		if agentID != nil && *agentID != "" {
			guidanceContext.Set("agent_id", *agentID)
		}
		if action == "register" {
			if agent, ok := response.Get("agent"); ok {
				if am, ok := agent.(*entities.OrderedMap[any]); ok && am != nil {
					if id, ok := am.Get("id"); ok {
						guidanceContext.Set("agent_id", id)
					}
				}
			}
		}
		response.Set("workflow_guidance", c.workflowGuidance.GenerateGuidance(action, guidanceContext))
	}
	return response
}

func isOneOf(value string, options ...string) bool {
	for _, o := range options {
		if value == o {
			return true
		}
	}
	return false
}

func pyAny(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}
