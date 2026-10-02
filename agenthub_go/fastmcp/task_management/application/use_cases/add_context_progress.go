package use_cases

import (
	"context"

	contextdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// AddContextProgressUseCase ports add_context_progress.AddContextProgressUseCase.
type AddContextProgressUseCase struct {
	contextRepository repositories.ContextRepository
}

// NewAddContextProgressUseCase mirrors __init__(context_repository).
func NewAddContextProgressUseCase(contextRepository repositories.ContextRepository) *AddContextProgressUseCase {
	return &AddContextProgressUseCase{contextRepository: contextRepository}
}

// Execute mirrors AddContextProgressUseCase.execute.
//
// Quirk preserved: the Python builds ContextProgressAction(action=request.content),
// but AddProgressRequest declares `action`, not `content`, so the attribute access
// raises AttributeError. The surrounding except turns that into
// "Failed to add progress: 'AddProgressRequest' object has no attribute 'content'".
// This port reproduces the same observable result instead of silently fixing it.
func (u *AddContextProgressUseCase) Execute(ctx context.Context, request *contextdto.AddProgressRequest) *contextdto.AddProgressResponse {
	exists, err := u.contextRepository.ContextExists(ctx, request.TaskID)
	if err != nil {
		return contextdto.NewContextResponseError("Failed to add progress: "+err.Error(), nil)
	}
	if !exists {
		return contextdto.NewContextResponseError("Context not found for task "+request.TaskID, nil)
	}
	return contextdto.NewContextResponseError(
		"Failed to add progress: 'AddProgressRequest' object has no attribute 'content'", nil)
}
