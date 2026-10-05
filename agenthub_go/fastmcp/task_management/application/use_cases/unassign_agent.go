package use_cases

import (
	"context"
	"errors"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// UnassignAgentRequest ports unassign_agent.UnassignAgentRequest.
type UnassignAgentRequest struct {
	ProjectID   string
	AgentID     string
	GitBranchID *string
}

// UnassignAgentResponse ports unassign_agent.UnassignAgentResponse.
// []string fields use nil for Python None and a non-nil (possibly empty) slice
// for a Python list.
type UnassignAgentResponse struct {
	Success              bool
	AgentID              string
	RemovedAssignments   []string
	RemainingAssignments []string
	Message              *string
	Error                *string
}

// ToDict mirrors UnassignAgentResponse.to_dict, including the conditional keys.
func (r *UnassignAgentResponse) ToDict() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", r.Success)
	m.Set("agent_id", r.AgentID)
	if r.RemovedAssignments != nil {
		m.Set("removed_assignments", r.RemovedAssignments)
	}
	if r.RemainingAssignments != nil {
		m.Set("remaining_assignments", r.RemainingAssignments)
	}
	if r.Message != nil && *r.Message != "" {
		m.Set("message", *r.Message)
	}
	if r.Error != nil && *r.Error != "" {
		m.Set("error", *r.Error)
	}
	return m
}

// smallUCStringSlice mirrors list(x) for a repository value that is either a
// []string or a []any; a missing value yields a non-nil empty slice.
func smallUCStringSlice(v any) []string {
	out := []string{}
	switch xs := v.(type) {
	case []string:
		out = append(out, xs...)
	case []any:
		for _, x := range xs {
			out = append(out, fmt.Sprintf("%v", x))
		}
	}
	return out
}

// UnassignAgentUseCase ports unassign_agent.UnassignAgentUseCase. The Python
// __init__ also assigns RepositoryFactory.get_git_branch_repository() but never
// uses it, so it is dropped.
type UnassignAgentUseCase struct {
	agentRepository repositories.AgentRepository
}

// NewUnassignAgentUseCase mirrors __init__(agent_repository).
func NewUnassignAgentUseCase(agentRepository repositories.AgentRepository) *UnassignAgentUseCase {
	return &UnassignAgentUseCase{agentRepository: agentRepository}
}

// Execute mirrors UnassignAgentUseCase.execute.
func (u *UnassignAgentUseCase) Execute(ctx context.Context, request *UnassignAgentRequest) *UnassignAgentResponse {
	result, err := u.agentRepository.UnassignAgentFromTree(ctx, request.ProjectID, request.AgentID, request.GitBranchID)
	if err != nil {
		var agentNotFound *exceptions.AgentNotFoundError
		var projectNotFound *exceptions.ProjectNotFoundError
		if errors.As(err, &agentNotFound) || errors.As(err, &projectNotFound) {
			msg := err.Error()
			return &UnassignAgentResponse{Success: false, AgentID: request.AgentID, Error: &msg}
		}
		msg := "Unexpected error: " + err.Error()
		return &UnassignAgentResponse{Success: false, AgentID: request.AgentID, Error: &msg}
	}

	removedAssignments := smallUCStringSlice(result["removed_assignments"])
	remainingAssignments := smallUCStringSlice(result["remaining_assignments"])
	message := fmt.Sprintf("Agent %s unassigned from %d tree(s)", request.AgentID, len(removedAssignments))
	return &UnassignAgentResponse{
		Success:              true,
		AgentID:              request.AgentID,
		RemovedAssignments:   removedAssignments,
		RemainingAssignments: remainingAssignments,
		Message:              &message,
	}
}
