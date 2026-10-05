package use_cases

import (
	"context"
	"fmt"

	dtoscontext "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// GetContextUseCase ports get_context.GetContextUseCase.
type GetContextUseCase struct {
	contextRepository repositories.ContextRepository
}

// NewGetContextUseCase builds the use case.
func NewGetContextUseCase(contextRepository repositories.ContextRepository) *GetContextUseCase {
	return &GetContextUseCase{contextRepository: contextRepository}
}

// Execute gets a context for the request's task.
func (uc *GetContextUseCase) Execute(ctx context.Context, request *dtoscontext.GetContextRequest) *dtoscontext.ContextResponse {
	value, err := uc.contextRepository.GetContext(ctx, request.TaskID)
	if err != nil {
		return dtoscontext.NewContextResponseError(
			fmt.Sprintf("Failed to get context: %s", err.Error()), nil)
	}
	if value == nil {
		return dtoscontext.NewContextResponseError(
			fmt.Sprintf("Context not found for task %s", request.TaskID), nil)
	}
	message := "Context retrieved successfully"
	return dtoscontext.NewContextResponseSuccess(value, nil, &message)
}
