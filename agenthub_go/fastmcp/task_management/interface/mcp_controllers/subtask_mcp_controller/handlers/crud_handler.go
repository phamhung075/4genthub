package handlers

// CRUD Handler for Subtask MCP Controller (Python crud_handler.py).
//
// Handles Create, Read, Update, Delete operations for subtasks with automatic
// progress tracking. Logging calls are dropped.

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SubtaskCRUDHandler ports SubtaskCRUDHandler.
type SubtaskCRUDHandler struct {
	responseFormatter ResponseFormatter
	contextFacade     ContextFacade
	taskFacade        any
	tokenTracker      TokenOperationTracker
}

// NewSubtaskCRUDHandler ports __init__; tokenTracker replaces the unported
// token-repository tracking infrastructure.
func NewSubtaskCRUDHandler(responseFormatter ResponseFormatter, contextFacade ContextFacade, taskFacade any, tokenTracker TokenOperationTracker) *SubtaskCRUDHandler {
	return &SubtaskCRUDHandler{
		responseFormatter: responseFormatter,
		contextFacade:     contextFacade,
		taskFacade:        taskFacade,
		tokenTracker:      tokenTracker,
	}
}

// trackTokenOperation ports _track_token_operation as a background call.
func (h *SubtaskCRUDHandler) trackTokenOperation(operation string) {
	if h.tokenTracker == nil {
		return
	}
	go func() {
		defer func() { _ = recover() }()
		_ = h.tokenTracker.TrackTokenOperation(context.Background(), operation)
	}()
}

// CreateSubtask ports create_subtask.
func (h *SubtaskCRUDHandler) CreateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade,
	taskID, title string, description, status, priority *string, assignees []string,
	progressPercentage *int, progressNotes, userID *string) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = h.responseFormatter.CreateErrorResponse("create_subtask",
				fmt.Sprintf("Failed to create subtask: %v", r), ErrorCodeOperationFailed,
				metaMap("task_id", taskID, "title", title))
		}
	}()

	if taskID == "" {
		return h.createValidationError("task_id", "A valid task_id string", "Include 'task_id' in your request")
	}
	if title == "" {
		return h.createValidationError("title", "A non-empty title string", "Include 'title' in your request")
	}

	if len(assignees) > 0 {
		validated, err := entities.NormalizeAssignees(assignees)
		if err != nil {
			return h.responseFormatter.CreateErrorResponse("create_subtask",
				err.Error(),
				ErrorCodeValidation,
				metaMap("field", "assignees", "hint", "Provide '@<seat_key>'"))
		}
		assignees = validated
	}

	subtaskData := entities.NewOrderedMap[any]()
	subtaskData.Set("title", title)
	if description != nil {
		subtaskData.Set("description", *description)
	} else {
		subtaskData.Set("description", "")
	}
	subtaskData.Set("priority", derefAny(priority))
	subtaskData.Set("assignees", assignees)
	if status != nil {
		subtaskData.Set("status", *status)
	}
	if progressPercentage != nil {
		subtaskData.Set("progress_percentage", *progressPercentage)
	}

	result, err := facade.HandleManageSubtask(ctx, "create", taskID, subtaskData, nil, false, nil, nil, userID)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("create_subtask",
			fmt.Sprintf("Failed to create subtask: %s", err.Error()), ErrorCodeOperationFailed,
			metaMap("task_id", taskID, "title", title))
	}

	if omSuccess(result) && pyBool(omGet(result, "agent_inheritance_applied")) {
		inherited := omSlice(result, "inherited_assignees")
		info := entities.NewOrderedMap[any]()
		info.Set("applied", true)
		info.Set("inherited_from", "parent_task")
		info.Set("inherited_assignees", omGet(result, "inherited_assignees"))
		info.Set("assignee_count", len(inherited))
		result.Set("inheritance_info", info)
	}

	if omSuccess(result) && h.contextFacade != nil {
		progressContent := fmt.Sprintf("Created subtask: %s", title)
		if pyBool(omGet(result, "agent_inheritance_applied")) {
			inheritedCount := len(omSlice(result, "inherited_assignees"))
			progressContent += fmt.Sprintf(" (inherited %d assignees from parent)", inheritedCount)
		}
		if progressNotes != nil && *progressNotes != "" {
			progressContent += fmt.Sprintf(" - %s", *progressNotes)
		}
		_, _ = h.contextFacade.AddProgress(ctx, taskID, progressContent, "subtask_controller")
		result.Set("context_updated", true)
		result.Set("parent_progress", h.getParentProgress(ctx, facade, taskID))
	}

	if omSuccess(result) {
		h.trackTokenOperation("subtask_create")
	}

	return result
}

// UpdateSubtask ports update_subtask.
func (h *SubtaskCRUDHandler) UpdateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade,
	taskID, subtaskID string, title, description, status, priority *string, assignees []string,
	progressPercentage *int, progressNotes *string) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = h.responseFormatter.CreateErrorResponse("update_subtask",
				fmt.Sprintf("Failed to update subtask: %v", r), ErrorCodeOperationFailed,
				metaMap("task_id", taskID, "subtask_id", subtaskID))
		}
	}()

	if taskID == "" {
		return h.createValidationError("task_id", "A valid task_id string", "Include 'task_id' in your request")
	}
	if subtaskID == "" {
		return h.createValidationError("subtask_id", "A valid subtask_id string", "Include 'subtask_id' in your request")
	}

	if progressNotes == nil || len(value_objects.PyStrip(*progressNotes)) < 10 {
		return h.responseFormatter.CreateErrorResponse("update_subtask",
			"Missing required field: progress_notes (minimum 10 characters). Updates must include progress description.",
			ErrorCodeValidation,
			metaMap("field", "progress_notes",
				"requirement", "Minimum 10 characters describing what was done",
				"example", "Completed schema design, starting implementation"))
	}

	updateData := entities.NewOrderedMap[any]()
	if title != nil {
		updateData.Set("title", *title)
	}
	if description != nil {
		updateData.Set("description", *description)
	}
	if status != nil {
		updateData.Set("status", *status)
	}
	if priority != nil {
		updateData.Set("priority", *priority)
	}
	if assignees != nil {
		updateData.Set("assignees", assignees)
	}
	if progressPercentage != nil {
		updateData.Set("progress_percentage", *progressPercentage)
	}
	if progressNotes != nil {
		updateData.Set("progress_notes", *progressNotes)
	}

	result, err := facade.HandleManageSubtask(ctx, "update", taskID, updateData, &subtaskID, false, nil, nil, nil)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("update_subtask",
			fmt.Sprintf("Failed to update subtask: %s", err.Error()), ErrorCodeOperationFailed,
			metaMap("task_id", taskID, "subtask_id", subtaskID))
	}

	if omSuccess(result) && h.contextFacade != nil {
		progressContent := fmt.Sprintf("Updated subtask %s", subtaskID)
		if progressNotes != nil {
			progressContent += fmt.Sprintf(" - %s", *progressNotes)
		} else if status != nil {
			progressContent += fmt.Sprintf(" - Status: %s", *status)
		}
		_, _ = h.contextFacade.AddProgress(ctx, taskID, progressContent, "subtask_controller")
		result.Set("context_updated", true)
		result.Set("parent_progress", h.getParentProgress(ctx, facade, taskID))
	}

	if omSuccess(result) {
		h.trackTokenOperation("subtask_update")
	}

	return result
}

// DeleteSubtask ports delete_subtask.
func (h *SubtaskCRUDHandler) DeleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade,
	taskID, subtaskID string, progressNotes *string) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = h.responseFormatter.CreateErrorResponse("delete_subtask",
				fmt.Sprintf("Failed to delete subtask: %v", r), ErrorCodeOperationFailed,
				metaMap("task_id", taskID, "subtask_id", subtaskID))
		}
	}()

	if taskID == "" {
		return h.createValidationError("task_id", "A valid task_id string", "Include 'task_id' in your request")
	}
	if subtaskID == "" {
		return h.createValidationError("subtask_id", "A valid subtask_id string", "Include 'subtask_id' in your request")
	}

	result, err := facade.HandleManageSubtask(ctx, "delete", taskID, nil, &subtaskID, false, nil, nil, nil)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("delete_subtask",
			fmt.Sprintf("Failed to delete subtask: %s", err.Error()), ErrorCodeOperationFailed,
			metaMap("task_id", taskID, "subtask_id", subtaskID))
	}

	if omSuccess(result) && h.contextFacade != nil {
		progressContent := fmt.Sprintf("Deleted subtask %s", subtaskID)
		if progressNotes != nil && *progressNotes != "" {
			progressContent += fmt.Sprintf(" - %s", *progressNotes)
		}
		_, _ = h.contextFacade.AddProgress(ctx, taskID, progressContent, "subtask_controller")
		result.Set("context_updated", true)
		result.Set("parent_progress", h.getParentProgress(ctx, facade, taskID))
	}

	if omSuccess(result) {
		h.trackTokenOperation("subtask_delete")
	}
	return result
}

// GetSubtask ports get_subtask.
func (h *SubtaskCRUDHandler) GetSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade,
	taskID, subtaskID string) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = h.responseFormatter.CreateErrorResponse("get_subtask",
				fmt.Sprintf("Failed to get subtask: %v", r), ErrorCodeOperationFailed,
				metaMap("task_id", taskID, "subtask_id", subtaskID))
		}
	}()

	if taskID == "" {
		return h.createValidationError("task_id", "A valid task_id string", "Include 'task_id' in your request")
	}
	if subtaskID == "" {
		return h.createValidationError("subtask_id", "A valid subtask_id string", "Include 'subtask_id' in your request")
	}

	result, err := facade.HandleManageSubtask(ctx, "get", taskID, nil, &subtaskID, false, nil, nil, nil)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("get_subtask",
			fmt.Sprintf("Failed to get subtask: %s", err.Error()), ErrorCodeOperationFailed,
			metaMap("task_id", taskID, "subtask_id", subtaskID))
	}
	return result
}

// ListSubtasks ports list_subtasks.
func (h *SubtaskCRUDHandler) ListSubtasks(ctx context.Context, facade *facades.SubtaskApplicationFacade,
	taskID string, status, priority *string, limit, offset *int) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = h.responseFormatter.CreateErrorResponse("list_subtasks",
				fmt.Sprintf("Failed to list subtasks: %v", r), ErrorCodeOperationFailed,
				metaMap("task_id", taskID))
		}
	}()

	if taskID == "" {
		return h.createValidationError("task_id", "A valid task_id string", "Include 'task_id' in your request")
	}

	filterData := entities.NewOrderedMap[any]()
	if status != nil && *status != "" {
		filterData.Set("status", *status)
	}
	if priority != nil && *priority != "" {
		filterData.Set("priority", *priority)
	}
	if limit != nil && *limit != 0 {
		filterData.Set("limit", *limit)
	}
	if offset != nil && *offset != 0 {
		filterData.Set("offset", *offset)
	}

	result, err := facade.HandleManageSubtask(ctx, "list", taskID, filterData, nil, false, nil, nil, nil)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("list_subtasks",
			fmt.Sprintf("Failed to list subtasks: %s", err.Error()), ErrorCodeOperationFailed,
			metaMap("task_id", taskID))
	}

	if omSuccess(result) && omHas(result, "subtasks") {
		subtasks := omOrderedList(result, "subtasks")
		minimalSubtasks := make([]any, 0, len(subtasks))
		for _, subtask := range subtasks {
			m := entities.NewOrderedMap[any]()
			m.Set("id", omGet(subtask, "id"))
			m.Set("title", omGet(subtask, "title"))
			m.Set("status", omGet(subtask, "status"))
			m.Set("priority", omGet(subtask, "priority"))
			minimalSubtasks = append(minimalSubtasks, m)
		}
		result.Set("subtasks", minimalSubtasks)
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("task_id", taskID)
		metadata.Set("total_results", len(minimalSubtasks))
		metadata.Set("tip", "Use manage_subtask(action='get', task_id='...', subtask_id='...') for full details")
		result.Set("list_metadata", metadata)
	}

	if omSuccess(result) && h.contextFacade != nil {
		result.Set("parent_progress", h.getParentProgress(ctx, facade, taskID))
	}

	return result
}

// CompletionExtras replaces Python's **kwargs for complete_subtask.
type CompletionExtras struct {
	TestingNotes        *string
	InsightsFound       *string
	ChallengesOvercome  *string
	SkillsLearned       *string
	NextRecommendations *string
	Deliverables        *string
	CompletionQuality   *string
	ImpactOnParent      *string
}

// CompleteSubtask ports complete_subtask.
func (h *SubtaskCRUDHandler) CompleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade,
	taskID, subtaskID string, completionNotes, completionSummary *string, extras *CompletionExtras) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = h.responseFormatter.CreateErrorResponse("complete_subtask",
				fmt.Sprintf("Failed to complete subtask: %v", r), ErrorCodeOperationFailed,
				metaMap("task_id", taskID, "subtask_id", subtaskID))
		}
	}()

	if taskID == "" {
		return h.createValidationError("task_id", "A valid task_id string", "Include 'task_id' in your request")
	}
	if subtaskID == "" {
		return h.createValidationError("subtask_id", "A valid subtask_id string", "Include 'subtask_id' in your request")
	}

	if completionSummary == nil || len(value_objects.PyStrip(*completionSummary)) < 20 {
		return h.responseFormatter.CreateErrorResponse("complete_subtask",
			"Missing required field: completion_summary (minimum 20 characters). Completions must include detailed summary of accomplishments.",
			ErrorCodeValidation,
			metaMap("field", "completion_summary",
				"requirement", "Minimum 20 characters describing what was accomplished",
				"example", "Feature implemented with tests passing, documented in README"))
	}

	if extras == nil {
		extras = &CompletionExtras{}
	}

	completionData := entities.NewOrderedMap[any]()
	completionData.Set("subtask_id", subtaskID)
	completionData.Set("completion_summary", *completionSummary)
	completionData.Set("testing_notes", derefAny(extras.TestingNotes))
	completionData.Set("insights_found", derefAny(extras.InsightsFound))
	completionData.Set("challenges_overcome", derefAny(extras.ChallengesOvercome))
	completionData.Set("skills_learned", derefAny(extras.SkillsLearned))
	completionData.Set("next_recommendations", derefAny(extras.NextRecommendations))
	completionData.Set("deliverables", derefAny(extras.Deliverables))
	completionData.Set("completion_quality", derefAny(extras.CompletionQuality))
	completionData.Set("impact_on_parent", derefAny(extras.ImpactOnParent))

	result, err := facade.HandleManageSubtask(ctx, "complete", taskID, completionData, &subtaskID, false, nil, nil, nil)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("complete_subtask",
			fmt.Sprintf("Failed to complete subtask: %s", err.Error()), ErrorCodeOperationFailed,
			metaMap("task_id", taskID, "subtask_id", subtaskID))
	}

	if omSuccess(result) && h.contextFacade != nil {
		progressContent := fmt.Sprintf("Completed subtask %s", subtaskID)
		if completionNotes != nil && *completionNotes != "" {
			progressContent += fmt.Sprintf(" - %s", *completionNotes)
		}
		_, _ = h.contextFacade.AddProgress(ctx, taskID, progressContent, "subtask_controller")
		result.Set("context_updated", true)
		result.Set("parent_progress", h.getParentProgress(ctx, facade, taskID))
	}

	if omSuccess(result) {
		h.trackTokenOperation("subtask_complete")
	}

	return result
}

// getParentProgress ports _get_parent_progress.
func (h *SubtaskCRUDHandler) getParentProgress(ctx context.Context, facade *facades.SubtaskApplicationFacade, taskID string) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = metaMap("error", fmt.Sprintf("Failed to calculate parent progress: %v", r))
		}
	}()

	subtasksResult, err := facade.HandleManageSubtask(ctx, "list", taskID, nil, nil, false, nil, nil, nil)
	if err != nil {
		return metaMap("error", "Failed to get parent progress")
	}
	if !omSuccess(subtasksResult) {
		return metaMap("error", "Failed to get parent progress")
	}

	subtasks := omOrderedList(subtasksResult, "subtasks")
	totalSubtaskCount := len(subtasks)

	if totalSubtaskCount == 0 {
		return metaMap("total_subtasks", 0, "progress_percentage", 0)
	}

	completedSubtasks := 0
	for _, s := range subtasks {
		if st, ok := omString(s, "status"); ok && st == "done" {
			completedSubtasks++
		}
	}
	progressPercentage := int((float64(completedSubtasks) / float64(totalSubtaskCount)) * 100)

	out = entities.NewOrderedMap[any]()
	out.Set("total_subtasks", totalSubtaskCount)
	out.Set("completed_subtasks", completedSubtasks)
	out.Set("progress_percentage", progressPercentage)
	out.Set("last_updated", value_objects.IsoFormat(nowUTC()))
	return out
}

// createValidationError ports _create_validation_error.
func (h *SubtaskCRUDHandler) createValidationError(field, expected, hint string) *entities.OrderedMap[any] {
	return h.responseFormatter.CreateErrorResponse("subtask_validation",
		fmt.Sprintf("Missing required field: %s. Expected: %s", field, expected),
		ErrorCodeValidation,
		metaMap("field", field, "hint", hint))
}

// omOrderedList reads a list of OrderedMap values (the facade returns
// []*entities.OrderedMap[any]; []any is also accepted defensively).
func omOrderedList(o *entities.OrderedMap[any], key string) []*entities.OrderedMap[any] {
	switch t := omGet(o, key).(type) {
	case []*entities.OrderedMap[any]:
		return t
	case []any:
		out := make([]*entities.OrderedMap[any], 0, len(t))
		for _, it := range t {
			if m, ok := it.(*entities.OrderedMap[any]); ok {
				out = append(out, m)
			}
		}
		return out
	}
	return nil
}

// pyBool mirrors Python truthiness for the values read from result dicts.
func pyBool(v any) bool { return value_objects.PyTruthy(v) }

// derefAny returns *p or nil, matching a Python Optional stored in a dict.
func derefAny(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}
