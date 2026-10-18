package use_cases

import (
	"context"

	ctxdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// ContextEventWriter writes the ledger entry a context update produces. The recorder settles WHO the
// write is attributed to (the seat the request named, else the user) and builds the payload's change
// set, so this use case never names an actor itself.
type ContextEventWriter interface {
	RecordContextUpdate(ctx context.Context, taskID, level string, version int,
		origin string, changes []entities.ContextChange, dropped int) (*entities.TaskEvent, error)
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

	// The state the ledger's change set is compared FROM: the context as it was read, before any key
	// the request carries is applied.
	before := entities.OrderedFromMap(taskContext.ToDict(false))
	after := before

	// Python `if request.data:` is dict truthiness: nil or an empty dict is falsy.
	if request.Data != nil && request.Data.Len() > 0 {
		contextDict := taskContext.ToDict(false)
		for _, key := range request.Data.Keys() {
			value, _ := request.Data.Get(key)
			contextDict[key] = value
		}
		after = entities.OrderedFromMap(contextDict)
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
		changes, dropped := entities.ContextChanges(before, after)
		_, _ = uc.events.RecordContextUpdate(ctx, request.TaskID, "task", ver, "manage_context.update", changes, dropped)
	}

	message := "Context updated successfully"
	return ctxdto.NewContextResponseSuccess(taskContext, orderedMapFromSortedMap(result), &message), nil
}
