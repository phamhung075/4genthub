package use_cases

import (
	"context"
	"sort"
	"time"

	ctxdto "agenthub/fastmcp/task_management/application/dtos/context"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AddContextInsightUseCase ports add_context_insight.AddContextInsightUseCase.
type AddContextInsightUseCase struct {
	contextRepository repositories.ContextRepository
}

// NewAddContextInsightUseCase builds the use case.
func NewAddContextInsightUseCase(contextRepository repositories.ContextRepository) *AddContextInsightUseCase {
	return &AddContextInsightUseCase{contextRepository: contextRepository}
}

// Execute ports execute(). Unexpected failures are folded into an error response.
func (uc *AddContextInsightUseCase) Execute(ctx context.Context, request *ctxdto.AddInsightRequest) *ctxdto.AddInsightResponse {
	exists, err := uc.contextRepository.ContextExists(ctx, request.TaskID)
	if err != nil {
		return ctxdto.NewContextResponseError("Failed to add insight: "+err.Error(), nil)
	}
	if !exists {
		return ctxdto.NewContextResponseError("Context not found for task "+request.TaskID, nil)
	}

	insight := entities.ContextInsight{
		Timestamp:  value_objects.IsoFormat(time.Now().UTC().Truncate(time.Microsecond)),
		Agent:      request.Agent,
		Category:   request.Category,
		Content:    request.Content,
		Importance: request.Importance,
	}

	result, err := uc.contextRepository.AddInsight(ctx, request.TaskID, insight)
	if err != nil {
		return ctxdto.NewContextResponseError("Failed to add insight: "+err.Error(), nil)
	}
	msg := "Insight added successfully"
	return ctxdto.NewContextResponseSuccess(nil, orderedMapFromSortedMap(result), &msg)
}

// orderedMapFromSortedMap converts a plain map to an OrderedMap using sorted keys,
// which is how PyJSONDumps writes map[string]any. It is shared by the use cases
// whose Python repository returns a plain dict.
func orderedMapFromSortedMap(m map[string]any) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	o := entities.NewOrderedMap[any]()
	for _, k := range keys {
		o.Set(k, m[k])
	}
	return o
}

// convertToTaskID is the Python _convert_to_task_id helper (shared with the
// other use case files); it delegates to the package-wide converter.
func convertToTaskID(v any) (value_objects.TaskId, error) { return smallUCConvertTaskID(v) }

// orderedSubtaskFromDict reorders a Subtask.to_dict() map into the Python insertion
// order (the shared domain Subtask.ToDict returns a plain Go map).
func orderedSubtaskFromDict(m map[string]any, includeParent bool) *entities.OrderedMap[any] {
	order := []string{"id", "title", "description", "status", "priority", "assignees",
		"progress_percentage", "created_at", "updated_at"}
	if includeParent {
		order = append(order, "parent_task_id")
	}
	o := entities.NewOrderedMap[any]()
	for _, k := range order {
		if v, ok := m[k]; ok {
			o.Set(k, v)
		}
	}
	return o
}

// orderedProgressMap reorders Task.get_subtask_progress() into total, completed,
// percentage.
func orderedProgressMap(m map[string]any) *entities.OrderedMap[any] {
	o := entities.NewOrderedMap[any]()
	for _, k := range []string{"total", "completed", "percentage"} {
		if v, ok := m[k]; ok {
			o.Set(k, v)
		}
	}
	return o
}

// ucContainsStr is list membership (the entities helper is unexported).
func ucContainsStr(list []string, s string) bool {
	for _, item := range list {
		if item == s {
			return true
		}
	}
	return false
}
