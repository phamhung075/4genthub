package use_cases

import (
	"context"
	"errors"

	dtosagent "agenthub/fastmcp/task_management/application/dtos/agent"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// ListAgentsRequest is the request DTO for listing agents.
type ListAgentsRequest struct {
	ProjectID string
}

// ListAgentsResponse is the response DTO for listing agents.
type ListAgentsResponse struct {
	Success     bool
	Agents      []dtosagent.AgentResponse
	TotalAgents int
	Error       *string
}

// ListAgentsUseCase ports list_agents.ListAgentsUseCase.
type ListAgentsUseCase struct {
	agentRepository repositories.AgentRepository
}

// NewListAgentsUseCase builds the use case.
func NewListAgentsUseCase(agentRepository repositories.AgentRepository) *ListAgentsUseCase {
	return &ListAgentsUseCase{agentRepository: agentRepository}
}

// Execute lists the agents of a project.
func (uc *ListAgentsUseCase) Execute(ctx context.Context, request *ListAgentsRequest) *ListAgentsResponse {
	result, err := uc.agentRepository.ListAgents(ctx, request.ProjectID)
	if err != nil {
		var notFound *exceptions.ProjectNotFoundError
		if errors.As(err, &notFound) {
			message := err.Error()
			return &ListAgentsResponse{Success: false, Error: &message}
		}
		message := "Unexpected error: " + err.Error()
		return &ListAgentsResponse{Success: false, Error: &message}
	}

	agents := []dtosagent.AgentResponse{}
	if raw, ok := result["agents"]; ok {
		for _, item := range listAgentsItems(raw) {
			agents = append(agents, dtosagent.AgentResponseFromDict(item))
		}
	}

	total := 0
	if raw, ok := result["total_agents"]; ok {
		if n, ok := raw.(int); ok {
			total = n
		}
	}
	return &ListAgentsResponse{Success: true, Agents: agents, TotalAgents: total}
}

// listAgentsItems normalizes the repository's agents value to OrderedMap entries.
func listAgentsItems(raw any) []*entities.OrderedMap[any] {
	out := []*entities.OrderedMap[any]{}
	switch xs := raw.(type) {
	case []*entities.OrderedMap[any]:
		out = append(out, xs...)
	case []any:
		for _, x := range xs {
			out = append(out, listAgentItem(x))
		}
	case []map[string]any:
		for _, x := range xs {
			out = append(out, listAgentItem(x))
		}
	}
	return out
}

func listAgentItem(x any) *entities.OrderedMap[any] {
	switch v := x.(type) {
	case *entities.OrderedMap[any]:
		return v
	case map[string]any:
		m := entities.NewOrderedMap[any]()
		for _, k := range useCaseSortedKeys(v) {
			m.Set(k, v[k])
		}
		return m
	}
	return entities.NewOrderedMap[any]()
}
