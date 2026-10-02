package use_cases

import (
	"context"
	"errors"

	"agenthub/fastmcp/task_management/application/dtos/agent"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// GetAgentRequest ports get_agent.GetAgentRequest.
type GetAgentRequest struct {
	ProjectID string
	AgentID   string
}

// GetAgentResponse ports get_agent.GetAgentResponse.
type GetAgentResponse struct {
	Success        bool
	Agent          *agent.AgentResponse
	WorkloadStatus *string
	Error          *string
}

// GetAgentUseCase ports get_agent.GetAgentUseCase.
type GetAgentUseCase struct {
	agentRepository repositories.AgentRepository
}

// NewGetAgentUseCase builds the use case.
func NewGetAgentUseCase(agentRepository repositories.AgentRepository) *GetAgentUseCase {
	return &GetAgentUseCase{agentRepository: agentRepository}
}

// Execute ports execute(). AgentNotFoundError / ProjectNotFoundError become
// success=false with the exception text; any other error is prefixed.
func (uc *GetAgentUseCase) Execute(ctx context.Context, request *GetAgentRequest) *GetAgentResponse {
	agentData, err := uc.agentRepository.GetAgent(ctx, request.ProjectID, request.AgentID)
	if err != nil {
		var agentNotFound *exceptions.AgentNotFoundError
		var projectNotFound *exceptions.ProjectNotFoundError
		if errors.As(err, &agentNotFound) || errors.As(err, &projectNotFound) {
			message := err.Error()
			return &GetAgentResponse{Success: false, Error: &message}
		}
		message := "Unexpected error: " + err.Error()
		return &GetAgentResponse{Success: false, Error: &message}
	}

	response := agent.AgentResponseFromDict(orderedMapFromSortedMap(agentData))
	workloadStatus := "Available for assignment analysis"
	return &GetAgentResponse{Success: true, Agent: &response, WorkloadStatus: &workloadStatus}
}
