// Package facades ports the agent application facade.
//
// Port of agent_application_facade.py. The WebSocketNotificationService
// sync_broadcast_agent_event side effects (register/unregister/update) have no
// Go equivalent and are dropped; the logging calls are dropped as well.
package facades

import (
	"context"
	"errors"
	"strings"
	"time"

	agentdto "agenthub/fastmcp/task_management/application/dtos/agent"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentApplicationFacade mirrors AgentApplicationFacade: it orchestrates the
// agent use cases and formats the application-boundary responses.
type AgentApplicationFacade struct {
	agentRepository repositories.AgentRepository

	registerAgentUseCase   *use_cases.RegisterAgentUseCase
	unregisterAgentUseCase *use_cases.UnregisterAgentUseCase
	assignAgentUseCase     *use_cases.AssignAgentUseCase
	unassignAgentUseCase   *use_cases.UnassignAgentUseCase
	getAgentUseCase        *use_cases.GetAgentUseCase
	listAgentsUseCase      *use_cases.ListAgentsUseCase
}

// NewAgentApplicationFacade mirrors __init__(agent_repository) and initializes
// the six use cases.
func NewAgentApplicationFacade(agentRepository repositories.AgentRepository) *AgentApplicationFacade {
	return &AgentApplicationFacade{
		agentRepository:        agentRepository,
		registerAgentUseCase:   use_cases.NewRegisterAgentUseCase(agentRepository),
		unregisterAgentUseCase: use_cases.NewUnregisterAgentUseCase(agentRepository),
		assignAgentUseCase:     use_cases.NewAssignAgentUseCase(agentRepository),
		unassignAgentUseCase:   use_cases.NewUnassignAgentUseCase(agentRepository),
		getAgentUseCase:        use_cases.NewGetAgentUseCase(agentRepository),
		listAgentsUseCase:      use_cases.NewListAgentsUseCase(agentRepository),
	}
}

// RegisterAgent ports register_agent(project_id, agent_id=None, name=None,
// call_agent=None, user_id=None). user_id only fed the dropped WebSocket event.
func (f *AgentApplicationFacade) RegisterAgent(ctx context.Context, projectID string,
	agentID, name, callAgent, userID *string) *entities.OrderedMap[any] {
	request, err := agentdto.NewRegisterAgentRequest(projectID, agentID, name, callAgent)
	if err != nil {
		var valueErr *value_objects.ValueError
		if errors.As(err, &valueErr) {
			return aafRegisterValidationError(projectID, agentID, err.Error())
		}
		return aafRegisterInternalError(err)
	}

	response := f.registerAgentUseCase.Execute(ctx, request)
	if response.Success {
		// Python also broadcasts the "created" agent event here (dropped).
		agentDict := aafAgentResponseDict(response.Agent)
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "register")
		m.Set("agent", agentDict)
		m.Set("message", aafPtrAny(response.Message))
		m.Set("hint", "Agent '"+aafStrPy(name)+"' successfully registered and ready for assignment")
		return m
	}
	return aafRegisterErrorResponse(response, projectID, agentID)
}

// aafRegisterErrorResponse mirrors the enhanced error response for a failed
// (but not raised) registration. Missing key order: success, action, error,
// error_code, then optional hint / suggested_actions.
func aafRegisterErrorResponse(response *agentdto.RegisterAgentResponse, projectID string, agentID *string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "register")
	errMsg := aafStr(response.Error)
	m.Set("error", errMsg)
	m.Set("error_code", "REGISTRATION_FAILED")

	lower := value_objects.PyLower(errMsg)
	if strings.Contains(lower, "already exists") {
		m.Set("error_code", "DUPLICATE_AGENT")
		m.Set("hint", "Try using 'action=get' to view the existing agent or 'action=update' to modify it")
		m.Set("suggested_actions", []any{
			aafAction("action", "get", "agent_id", aafPtrAny(agentID)),
			aafAction("action", "update", "agent_id", aafPtrAny(agentID)),
			aafAction("action", "list", "project_id", projectID),
		})
	} else if strings.Contains(lower, "project") && strings.Contains(lower, "not exist") {
		m.Set("error_code", "PROJECT_NOT_FOUND")
		m.Set("hint", "Check that the project_id is correct or create the project first")
	}
	return m
}

// aafRegisterValidationError mirrors the `except ValueError` branch of
// register_agent.
func aafRegisterValidationError(projectID string, agentID *string, errMsg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "register")
	m.Set("error", errMsg)
	m.Set("error_code", "VALIDATION_ERROR")

	lower := value_objects.PyLower(errMsg)
	if strings.Contains(lower, "duplicate") || strings.Contains(lower, "already exists") {
		m.Set("error_code", "DUPLICATE_AGENT")
		m.Set("hint", "An agent with this ID or name already exists. Consider using the existing agent.")
		m.Set("suggested_actions", []any{
			aafAction("action", "list", "project_id", projectID, "description", "List all agents in the project"),
			aafAction("action", "get", "agent_id", aafPtrAny(agentID), "description", "Get details of the existing agent"),
		})
	} else if strings.Contains(lower, "required") || strings.Contains(lower, "missing") {
		m.Set("error_code", "MISSING_FIELD")
		m.Set("hint", "Ensure all required fields (project_id, agent_id, name) are provided")
	}
	return m
}

// aafRegisterInternalError mirrors the `except Exception` branch of
// register_agent; only reachable for a non-ValueError construction failure.
func aafRegisterInternalError(err error) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "register")
	m.Set("error", "Unexpected error: "+err.Error())
	m.Set("error_code", "INTERNAL_ERROR")
	m.Set("hint", "An unexpected error occurred. Please check the logs or try again.")
	return m
}

// UnregisterAgent ports unregister_agent(project_id, agent_id, user_id=None).
// Python's `except Exception` branch is unreachable: the Go use case encodes
// every failure in the response instead of returning an error.
func (f *AgentApplicationFacade) UnregisterAgent(ctx context.Context, projectID, agentID string, userID *string) *entities.OrderedMap[any] {
	response := f.unregisterAgentUseCase.Execute(ctx, &use_cases.UnregisterAgentRequest{
		ProjectID: projectID,
		AgentID:   agentID,
	})
	if response.Success {
		// Python also broadcasts the "deleted" agent event here (dropped).
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "unregister")
		m.Set("agent_id", response.AgentID)
		m.Set("agent_data", response.AgentData)
		m.Set("removed_assignments", response.RemovedAssignments)
		m.Set("message", aafPtrAny(response.Message))
		return m
	}
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "unregister")
	m.Set("error", aafStr(response.Error))
	return m
}

// AssignAgent ports assign_agent(project_id, agent_id, git_branch_id). Python's
// `except Exception` branch is unreachable: the Go use case never returns an
// error.
func (f *AgentApplicationFacade) AssignAgent(ctx context.Context, projectID, agentID, gitBranchID string) *entities.OrderedMap[any] {
	response := f.assignAgentUseCase.Execute(ctx, use_cases.AssignAgentRequest{
		ProjectID:   projectID,
		AgentID:     agentID,
		GitBranchID: gitBranchID,
	})
	if response.Success {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "assign")
		m.Set("agent_id", response.AgentID)
		m.Set("git_branch_id", aafPtrAny(response.GitBranchID))
		m.Set("message", aafPtrAny(response.Message))
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("project_id", projectID)
		metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
		m.Set("metadata", metadata)
		return m
	}
	return aafAssignFailureResponse(projectID, agentID, gitBranchID, aafStr(response.Error))
}

// aafAssignFailureResponse mirrors the "success: False" / exception responses of
// assign_agent (identical key order).
func aafAssignFailureResponse(projectID, agentID, gitBranchID, errMsg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "assign")
	m.Set("error", errMsg)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("agent_id", agentID)
	metadata.Set("git_branch_id", gitBranchID)
	metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	m.Set("metadata", metadata)
	return m
}

// UnassignAgent ports unassign_agent(project_id, agent_id, git_branch_id). It
// returns the use case's to_dict() unchanged. Python's `except Exception`
// branch is unreachable: the Go use case never returns an error.
func (f *AgentApplicationFacade) UnassignAgent(ctx context.Context, projectID, agentID string, gitBranchID *string) *entities.OrderedMap[any] {
	response := f.unassignAgentUseCase.Execute(ctx, &use_cases.UnassignAgentRequest{
		ProjectID:   projectID,
		AgentID:     agentID,
		GitBranchID: gitBranchID,
	})
	return response.ToDict()
}

// GetAgent ports get_agent(project_id, agent_id). Python's `except Exception`
// branch is unreachable: the Go use case never returns an error.
func (f *AgentApplicationFacade) GetAgent(ctx context.Context, projectID, agentID string) *entities.OrderedMap[any] {
	response := f.getAgentUseCase.Execute(ctx, &use_cases.GetAgentRequest{
		ProjectID: projectID,
		AgentID:   agentID,
	})
	if response.Success {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "get")
		m.Set("agent", aafAgentResponseDict(response.Agent))
		m.Set("workload_status", aafPtrAny(response.WorkloadStatus))
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("project_id", projectID)
		metadata.Set("agent_id", agentID)
		metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
		m.Set("metadata", metadata)
		return m
	}
	return aafGetFailureResponse(projectID, agentID, aafStr(response.Error))
}

// aafGetFailureResponse mirrors the "success: False" / exception responses of
// get_agent (identical key order).
func aafGetFailureResponse(projectID, agentID, errMsg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "get")
	m.Set("error", errMsg)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("agent_id", agentID)
	metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	m.Set("metadata", metadata)
	return m
}

// ListAgents ports list_agents(project_id). Python's `except Exception` branch
// is unreachable: the Go use case never returns an error.
func (f *AgentApplicationFacade) ListAgents(ctx context.Context, projectID string) *entities.OrderedMap[any] {
	response := f.listAgentsUseCase.Execute(ctx, &use_cases.ListAgentsRequest{ProjectID: projectID})
	if response.Success {
		agents := make([]*entities.OrderedMap[any], 0, len(response.Agents))
		for i := range response.Agents {
			agents = append(agents, aafAgentResponseDict(&response.Agents[i]))
		}
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("action", "list")
		m.Set("agents", agents)
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("project_id", projectID)
		metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
		metadata.Set("count", len(response.Agents))
		m.Set("metadata", metadata)
		return m
	}
	return aafListFailureResponse(projectID, aafStr(response.Error))
}

// aafListFailureResponse mirrors the "success: False" / exception responses of
// list_agents (identical key order).
func aafListFailureResponse(projectID, errMsg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "list")
	m.Set("error", errMsg)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	m.Set("metadata", metadata)
	return m
}

// UpdateAgent ports update_agent(project_id, agent_id, name=None,
// call_agent=None, user_id=None). user_id only fed the dropped WebSocket event.
//
// NOTE: the Python facade calls repository.update_agent(project_id, agent_id,
// name, call_agent), but ORMAgentRepository.update_agent takes only (self,
// agent), so every call raises TypeError and is returned through the generic
// "Unexpected error" branch; nothing is ever updated. Replicated here: no
// repository call is made and the same response is returned.
func (f *AgentApplicationFacade) UpdateAgent(ctx context.Context, projectID, agentID string,
	name, callAgent, userID *string) *entities.OrderedMap[any] {
	return aafUpdateFailureResponse(projectID, agentID,
		"Unexpected error in updating agent: ORMAgentRepository.update_agent() takes 2 positional arguments but 5 were given")
}

// aafUpdateFailureResponse mirrors the AgentNotFoundError / ProjectNotFoundError
// / generic exception responses of update_agent (identical key order).
func aafUpdateFailureResponse(projectID, agentID, errMsg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "update")
	m.Set("error", errMsg)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("agent_id", agentID)
	metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	m.Set("metadata", metadata)
	return m
}

// RebalanceAgents ports rebalance_agents(project_id).
func (f *AgentApplicationFacade) RebalanceAgents(ctx context.Context, projectID string) *entities.OrderedMap[any] {
	result, err := f.agentRepository.RebalanceAgents(ctx, projectID)
	if err != nil {
		var projectNotFound *exceptions.ProjectNotFoundError
		if errors.As(err, &projectNotFound) {
			return aafRebalanceFailureResponse(projectID, err.Error())
		}
		return aafRebalanceFailureResponse(projectID, "Unexpected error in rebalancing agents: "+err.Error())
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "rebalance")
	m.Set("project_id", projectID)
	rebalanceResult, _ := result["rebalance_result"]
	m.Set("rebalance_result", rebalanceResult)
	m.Set("message", "Agent rebalancing completed for project "+projectID)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	m.Set("metadata", metadata)
	return m
}

// aafRebalanceFailureResponse mirrors the ProjectNotFoundError / generic
// exception responses of rebalance_agents (identical key order).
func aafRebalanceFailureResponse(projectID, errMsg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "rebalance")
	m.Set("error", errMsg)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("project_id", projectID)
	metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	m.Set("metadata", metadata)
	return m
}

// aafAgentResponseDict mirrors dataclasses.asdict(AgentResponse): the AgentResponse
// fields in declaration order, id, name, call_agent, assignments.
func aafAgentResponseDict(a *agentdto.AgentResponse) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	if a == nil {
		return m
	}
	m.Set("id", a.ID)
	m.Set("name", a.Name)
	m.Set("call_agent", a.CallAgent)
	m.Set("assignments", a.Assignments)
	return m
}

// aafAction builds a suggestion dict from alternating key/value pairs,
// preserving the argument order like a Python dict literal.
func aafAction(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		key, _ := pairs[i].(string)
		m.Set(key, pairs[i+1])
	}
	return m
}

// aafPtrAny renders a Python optional value: None when nil, the value otherwise.
func aafPtrAny(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// aafStrPy renders an optional string as Python's f-string would: None -> "None".
func aafStrPy(s *string) string {
	if s == nil {
		return "None"
	}
	return *s
}

// aafStr dereferences an optional string, using "" for None where Python would
// place None (only used on paths where Python guarantees a value).
func aafStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}
