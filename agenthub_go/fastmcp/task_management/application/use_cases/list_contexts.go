package use_cases

import (
	"context"
	"fmt"

	contextdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// ListContextsUseCase ports list_contexts.ListContextsUseCase.
type ListContextsUseCase struct {
	contextRepository repositories.ContextRepository
}

// NewListContextsUseCase mirrors __init__(context_repository).
func NewListContextsUseCase(contextRepository repositories.ContextRepository) *ListContextsUseCase {
	return &ListContextsUseCase{contextRepository: contextRepository}
}

// Execute mirrors ListContextsUseCase.execute. The request is not read by the
// Python implementation (it lists every context through the repository).
func (u *ListContextsUseCase) Execute(ctx context.Context, _ *contextdto.ListContextsRequest) *contextdto.ListContextsResponse {
	contexts, err := u.contextRepository.ListContexts(ctx)
	if err != nil {
		base := contextdto.NewContextResponseError("Failed to list contexts: "+err.Error(), nil)
		return &contextdto.ListContextsResponse{ContextResponse: *base}
	}
	message := fmt.Sprintf("Retrieved %d contexts", len(contexts))
	return contextdto.NewListContextsResponseSuccess(contexts, &message)
}
