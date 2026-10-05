package use_cases

import (
	"context"
	"errors"
	"sort"

	agentdto "agenthub/fastmcp/task_management/application/dtos/agent"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RegisterAgentUseCase ports register_agent.RegisterAgentUseCase.
type RegisterAgentUseCase struct {
	agentRepository repositories.AgentRepository
}

// NewRegisterAgentUseCase builds the use case.
func NewRegisterAgentUseCase(agentRepository repositories.AgentRepository) *RegisterAgentUseCase {
	return &RegisterAgentUseCase{agentRepository: agentRepository}
}

// Execute ports execute(): ProjectNotFoundError/ValueError keep their message,
// everything else becomes "Unexpected error: ...".
func (uc *RegisterAgentUseCase) Execute(ctx context.Context, request *agentdto.RegisterAgentRequest) *agentdto.RegisterAgentResponse {
	id, err := value_objects.NewAgentId(request.AgentID)
	if err != nil {
		return registerAgentErrorResponse(err)
	}
	description := ""
	if request.CallAgent != nil {
		description = *request.CallAgent
	}
	agentEntity, err := entities.NewAgent(entities.Agent{ID: &id, Name: request.Name, Description: description})
	if err != nil {
		return registerAgentErrorResponse(err)
	}
	if err := agentEntity.AssignToProject(request.ProjectID); err != nil {
		return registerAgentErrorResponse(err)
	}

	result, err := uc.agentRepository.RegisterAgent(ctx, agentEntity)
	if err != nil {
		return registerAgentErrorResponse(err)
	}

	idStr := ""
	if result.ID != nil {
		idStr = result.ID.String()
	}
	assignments := make([]string, 0, len(result.AssignedTrees))
	for tree := range result.AssignedTrees {
		assignments = append(assignments, tree)
	}
	sort.Strings(assignments)

	agentDict := entities.NewOrderedMap[any]()
	agentDict.Set("id", idStr)
	agentDict.Set("name", result.Name)
	agentDict.Set("call_agent", result.Description)
	agentDict.Set("assignments", assignments)
	agentResponse := agentdto.AgentResponseFromDict(agentDict)

	msg := "Agent " + request.AgentID + " registered successfully to project " + request.ProjectID
	return agentdto.NewRegisterAgentResponseSuccess(&agentResponse, &msg)
}

func registerAgentErrorResponse(err error) *agentdto.RegisterAgentResponse {
	var pnf *exceptions.ProjectNotFoundError
	if errors.As(err, &pnf) {
		return agentdto.NewRegisterAgentResponseError(err.Error())
	}
	var ve *value_objects.ValueError
	if errors.As(err, &ve) {
		return agentdto.NewRegisterAgentResponseError(err.Error())
	}
	return agentdto.NewRegisterAgentResponseError("Unexpected error: " + err.Error())
}
