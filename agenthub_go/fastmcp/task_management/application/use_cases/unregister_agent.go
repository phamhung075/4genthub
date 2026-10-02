package use_cases

import (
	"context"
	"errors"
	"fmt"

	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// UnregisterAgentRequest ports unregister_agent.UnregisterAgentRequest.
type UnregisterAgentRequest struct {
	ProjectID string
	AgentID   string
}

// UnregisterAgentResponse ports unregister_agent.UnregisterAgentResponse.
// The Python dataclass has no to_dict; AgentData is the raw repository value.
type UnregisterAgentResponse struct {
	Success            bool
	AgentID            string
	AgentData          any
	RemovedAssignments []string
	Message            *string
	Error              *string
}

// UnregisterAgentUseCase ports unregister_agent.UnregisterAgentUseCase.
type UnregisterAgentUseCase struct {
	agentRepository repositories.AgentRepository
}

// NewUnregisterAgentUseCase mirrors __init__(agent_repository).
func NewUnregisterAgentUseCase(agentRepository repositories.AgentRepository) *UnregisterAgentUseCase {
	return &UnregisterAgentUseCase{agentRepository: agentRepository}
}

// Execute mirrors UnregisterAgentUseCase.execute.
func (u *UnregisterAgentUseCase) Execute(ctx context.Context, request *UnregisterAgentRequest) *UnregisterAgentResponse {
	result, err := u.agentRepository.UnregisterAgent(ctx, request.ProjectID, request.AgentID)
	if err != nil {
		var agentNotFound *exceptions.AgentNotFoundError
		var projectNotFound *exceptions.ProjectNotFoundError
		if errors.As(err, &agentNotFound) || errors.As(err, &projectNotFound) {
			msg := err.Error()
			return &UnregisterAgentResponse{Success: false, AgentID: request.AgentID, Error: &msg}
		}
		msg := "Unexpected error: " + err.Error()
		return &UnregisterAgentResponse{Success: false, AgentID: request.AgentID, Error: &msg}
	}

	agentData, hasAgentData := result["agent_data"]
	if !hasAgentData {
		agentData = nil
	}
	message := fmt.Sprintf("Agent %s unregistered from project %s", request.AgentID, request.ProjectID)
	return &UnregisterAgentResponse{
		Success:            true,
		AgentID:            request.AgentID,
		AgentData:          agentData,
		RemovedAssignments: smallUCStringSlice(result["removed_assignments"]),
		Message:            &message,
	}
}
