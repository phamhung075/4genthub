package use_cases

import (
	"context"
	"errors"

	ctxdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateContextUseCase ports create_context.CreateContextUseCase.
type CreateContextUseCase struct {
	contextRepository repositories.ContextRepository
}

// NewCreateContextUseCase builds the use case.
func NewCreateContextUseCase(contextRepository repositories.ContextRepository) *CreateContextUseCase {
	return &CreateContextUseCase{contextRepository: contextRepository}
}

// Execute ports execute(): ValueError becomes a "Validation error:" response and
// every other failure a "Failed to create context:" response.
func (uc *CreateContextUseCase) Execute(ctx context.Context, request *ctxdto.CreateContextRequest) *ctxdto.CreateContextResponse {
	exists, err := uc.contextRepository.ContextExists(ctx, request.TaskID)
	if err != nil {
		return createContextErrorResponse(err)
	}
	if exists {
		return ctxdto.NewContextResponseError("Context already exists for task "+request.TaskID, nil)
	}

	statusValue := "todo"
	if request.Status != nil && *request.Status != "" {
		statusValue = *request.Status
	}
	priorityValue := "medium"
	if request.Priority != nil && *request.Priority != "" {
		priorityValue = *request.Priority
	}

	status, err := value_objects.NewTaskStatus(statusValue)
	if err != nil {
		return createContextErrorResponse(err)
	}
	priority, err := value_objects.NewPriority(priorityValue)
	if err != nil {
		return createContextErrorResponse(err)
	}

	metadata, err := entities.NewContextMetadata(entities.ContextMetadata{
		TaskID:    request.TaskID,
		Status:    &status,
		Priority:  &priority,
		Assignees: request.Assignees,
		Labels:    request.Labels,
	})
	if err != nil {
		return createContextErrorResponse(err)
	}

	objective := entities.ContextObjective{
		Title:           request.Title,
		Description:     request.Description,
		EstimatedEffort: request.EstimatedEffort,
		DueDate:         request.DueDate,
	}

	contextEntity := entities.NewTaskContext(metadata, objective)

	// Merge additional data if provided, exactly like to_dict().update(data)
	// followed by TaskContext.from_dict(...).
	if request.Data != nil && request.Data.Len() > 0 {
		contextDict := contextEntity.ToDict(false)
		for _, key := range request.Data.Keys() {
			v, _ := request.Data.Get(key)
			contextDict[key] = v
		}
		contextEntity, err = entities.TaskContextFromDict(contextDict)
		if err != nil {
			return createContextErrorResponse(err)
		}
	}

	result, err := uc.contextRepository.CreateContext(ctx, contextEntity)
	if err != nil {
		return createContextErrorResponse(err)
	}

	msg := "Context created successfully"
	return ctxdto.NewContextResponseSuccess(contextEntity, orderedMapFromSortedMap(result), &msg)
}

func createContextErrorResponse(err error) *ctxdto.CreateContextResponse {
	var ve *value_objects.ValueError
	if errors.As(err, &ve) {
		return ctxdto.NewContextResponseError("Validation error: "+err.Error(), nil)
	}
	return ctxdto.NewContextResponseError("Failed to create context: "+err.Error(), nil)
}
