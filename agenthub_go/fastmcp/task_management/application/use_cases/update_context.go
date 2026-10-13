package use_cases

import (
	"context"

	ctxdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// ContextEventWriter appends context events to the ledger.
type ContextEventWriter interface {
	Append(ctx context.Context, in entities.AppendTaskEvent) (*entities.TaskEvent, error)
}

// UpdateContextUseCase ports update_context.UpdateContextUseCase.
type UpdateContextUseCase struct {
	contextRepository repositories.ContextRepository
	events            ContextEventWriter
}

// NewUpdateContextUseCase builds the use case.
func NewUpdateContextUseCase(contextRepository repositories.ContextRepository) *UpdateContextUseCase {
	return &UpdateContextUseCase{contextRepository: contextRepository}
}

// WithEvents wires the ledger event writer.
func (uc *UpdateContextUseCase) WithEvents(events ContextEventWriter) *UpdateContextUseCase {
	uc.events = events
	return uc
}

// Execute ports execute(). Every failure is folded into an error response whose
// error text is "Failed to update context: <message>", exactly like Python's
// try/except. ContextResponse data is an OrderedMap because the repository returns
// a plain Go map (keys sorted, see report).
func (uc *UpdateContextUseCase) Execute(ctx context.Context, request *ctxdto.UpdateContextRequest) (*ctxdto.UpdateContextResponse, error) {
	exists, err := uc.contextRepository.ContextExists(ctx, request.TaskID)
	if err != nil {
		return ctxdto.NewContextResponseError("Failed to update context: "+err.Error(), nil), nil
	}
	if !exists {
		return ctxdto.NewContextResponseError("Context not found for task "+request.TaskID, nil), nil
	}

	taskContext, err := uc.contextRepository.GetContext(ctx, request.TaskID)
	if err != nil {
		return ctxdto.NewContextResponseError("Failed to update context: "+err.Error(), nil), nil
	}
	if taskContext == nil {
		return ctxdto.NewContextResponseError("Context not found for task "+request.TaskID, nil), nil
	}

	// Python `if request.data:` is dict truthiness: nil or an empty dict is falsy.
	if request.Data != nil && request.Data.Len() > 0 {
		contextDict := taskContext.ToDict(false)
		for _, key := range request.Data.Keys() {
			value, _ := request.Data.Get(key)
			contextDict[key] = value
		}
		taskContext, err = entities.TaskContextFromDict(contextDict)
		if err != nil {
			return ctxdto.NewContextResponseError("Failed to update context: "+err.Error(), nil), nil
		}
	}

	if err := taskContext.Metadata.Touch("context_updated"); err != nil {
		return ctxdto.NewContextResponseError("Failed to update context: "+err.Error(), nil), nil
	}

	result, err := uc.contextRepository.UpdateContext(ctx, taskContext)
	if err != nil {
		return ctxdto.NewContextResponseError("Failed to update context: "+err.Error(), nil), nil
	}

	if uc.events != nil {
		var ver int
		if taskContext.Metadata != nil && taskContext.Metadata.Version != nil {
			ver = *taskContext.Metadata.Version
		}
		_, _ = uc.events.Append(ctx, entities.AppendTaskEvent{
			TaskID:    request.TaskID,
			Kind:      entities.TaskEventKindContextUpdated,
			ActorKind: entities.TaskEventActorSeat,
			ActorID:   "context",
			Payload: map[string]any{
				"level":   "task",
				"id":      request.TaskID,
				"version": ver,
			},
		})
	}

	message := "Context updated successfully"
	return ctxdto.NewContextResponseSuccess(taskContext, orderedMapFromSortedMap(result), &message), nil
}
