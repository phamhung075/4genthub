// This file ports task_management/application/use_cases/assign_agent.py.
package use_cases

import (
	"context"
	"errors"

	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// AssignAgentRequest is the request DTO for assigning an agent. The Python
// dataclass field order is project_id, agent_id, git_branch_id.
type AssignAgentRequest struct {
	ProjectID   string
	AgentID     string
	GitBranchID string
}

// AssignAgentResponse is the response DTO for agent assignment. The optional
// fields mirror the Python dataclass defaults of None.
type AssignAgentResponse struct {
	Success     bool
	AgentID     string
	GitBranchID *string
	Message     *string
	Error       *string
}

// AssignAgentUseCase assigns an agent to a task tree. Python's constructor also
// eagerly resolves RepositoryFactory.get_git_branch_repository(); that
// infrastructure factory has no Go port and the field is never read by execute,
// so it is intentionally omitted.
type AssignAgentUseCase struct {
	agentRepository repositories.AgentRepository
}

// NewAssignAgentUseCase builds the use case around an agent repository.
func NewAssignAgentUseCase(agentRepository repositories.AgentRepository) *AssignAgentUseCase {
	return &AssignAgentUseCase{agentRepository: agentRepository}
}

// Execute runs the assign-agent use case. Like Python it never returns an error:
// failures are encoded in the response DTO.
func (u *AssignAgentUseCase) Execute(ctx context.Context, request AssignAgentRequest) *AssignAgentResponse {
	_, err := u.agentRepository.AssignAgentToTree(ctx, request.ProjectID, request.AgentID, request.GitBranchID)
	if err != nil {
		var agentNotFound *exceptions.AgentNotFoundError
		var projectNotFound *exceptions.ProjectNotFoundError
		if errors.As(err, &agentNotFound) || errors.As(err, &projectNotFound) {
			msg := err.Error()
			return &AssignAgentResponse{Success: false, AgentID: request.AgentID, Error: &msg}
		}
		msg := "Unexpected error: " + err.Error()
		return &AssignAgentResponse{Success: false, AgentID: request.AgentID, Error: &msg}
	}

	gitBranchID := request.GitBranchID
	message := "Agent " + request.AgentID + " assigned to tree " + request.GitBranchID
	return &AssignAgentResponse{
		Success:     true,
		AgentID:     request.AgentID,
		GitBranchID: &gitBranchID,
		Message:     &message,
	}
}
