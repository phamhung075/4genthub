package handlers

// CRUD Handler for Task MCP Controller (Python crud_handler.py).

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ErrorCodes constants (interface/utils/response_formatter.py ErrorCodes).
const (
	ErrorCodeValidationError = "VALIDATION_ERROR"
	ErrorCodeOperationFailed = "OPERATION_FAILED"
	ErrorCodeInternalError   = "INTERNAL_ERROR"
)

// ResponseFormatter is the minimal view of the interface-layer
// StandardResponseFormatter used by these handlers. That module is ported as
// MCPResponseFormatter in interface/utils/response_formatter.go; the interface is
// declared here and reported as a dependency.
type ResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetTimestamp() string
}

// TaskFacade is the TaskApplicationFacade surface used by the handlers, declared
// here and reported as a dependency. GetTask keeps the (result, error) shape
// required by use_cases.AITaskFacade.
type TaskFacade interface {
	CreateTask(ctx context.Context, request *dtostask.CreateTaskRequest) *entities.OrderedMap[any]
	UpdateTask(ctx context.Context, request *dtostask.UpdateTaskRequest) *entities.OrderedMap[any]
	GetTask(ctx context.Context, taskID string, includeContext bool) (*entities.OrderedMap[any], error)
	// ResumeBrief is the resume action's read: the brief is built in the application layer and this
	// interface only demands it, because the brief's shape is not the interface layer's to know.
	ResumeBrief(ctx context.Context, taskID string) (*entities.OrderedMap[any], error)
	DeleteTask(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any]
	CompleteTask(ctx context.Context, taskID, completionSummary string, testingNotes, userID *string) *entities.OrderedMap[any]
	AddDependency(ctx context.Context, taskID, dependencyID string) *entities.OrderedMap[any]
	RemoveDependency(ctx context.Context, taskID, dependencyID string) *entities.OrderedMap[any]
	TaskRepository() repositories.TaskRepository
}

// UnifiedContextFacade is the facade_service.get_unified_context_facade() ->
// resolve_context surface used by get_task. FacadeService is ported in
// application/services/facade_service.go.
type UnifiedContextFacade interface {
	ResolveContext(ctx context.Context, level, contextID string, includeInherited bool) *entities.OrderedMap[any]
}

// GetUnifiedContextFacade is the hook mirroring FacadeService.get_instance().
// It defaults to nil; a later worker can assign the real provider.
var GetUnifiedContextFacade func() UnifiedContextFacade

// CRUDHandler ports CRUDHandler.
type CRUDHandler struct {
	responseFormatter ResponseFormatter
}

// NewCRUDHandler ports __init__(response_formatter).
func NewCRUDHandler(responseFormatter ResponseFormatter) *CRUDHandler {
	return &CRUDHandler{responseFormatter: responseFormatter}
}

// CreateTask ports create_task(facade, **kwargs).
func (h *CRUDHandler) CreateTask(ctx context.Context, facade TaskFacade,
	kwargs map[string]any) *entities.OrderedMap[any] {

	title := kwString(kwargs, "title")
	if title == nil || strings.TrimSpace(*title) == "" {
		return h.createStandardizedError("create_task", "title", "A valid title string",
			"Include 'title' in your request body")
	}
	gitBranchID := kwString(kwargs, "git_branch_id")
	if gitBranchID == nil || *gitBranchID == "" {
		return h.createStandardizedError("create_task", "git_branch_id", "A valid git_branch_id string",
			"Include 'git_branch_id' in your request body")
	}

	assignees := kwStrings(kwargs, "assignees")
	if len(assignees) == 0 {
		return h.createStandardizedError("create_task", "assignees",
			"At least one agent must be assigned to the task",
			"Include 'assignees' with at least one '@<seat_key>' (for example '@lead')")
	}

	// One rule for every path (see entities.NormalizeAssignees): '@<seat_key>' is kept and is
	// the only valid assignee identity; every bare name is rejected.
	validatedAssignees, err := entities.NormalizeAssignees(assignees)
	if err != nil {
		return h.createStandardizedError("create_task", "assignees",
			"'@<seat_key>' (for example '@lead')",
			err.Error()+" Use '@<seat_key>' (for example '@lead')")
	}
	if len(validatedAssignees) == 0 {
		return h.createStandardizedError("create_task", "assignees",
			"At least one valid agent must be assigned",
			"Provide at least one '@<seat_key>' (for example '@lead')")
	}
	assignees = validatedAssignees

	description := kwString(kwargs, "description")
	if description == nil || *description == "" {
		d := "Description for " + *title
		description = &d
	}
	details := ""
	if v := kwString(kwargs, "details"); v != nil {
		details = *v
	}
	labels := kwStrings(kwargs, "labels")
	if labels == nil {
		labels = []string{}
	}
	dependencies := kwStrings(kwargs, "dependencies")
	if dependencies == nil {
		dependencies = []string{}
	}

	request, reqErr := dtostask.NewCreateTaskRequest(dtostask.CreateTaskRequest{
		Title:              *title,
		GitBranchID:        *gitBranchID,
		Description:        description,
		Status:             kwString(kwargs, "status"),
		Priority:           kwString(kwargs, "priority"),
		Details:            details,
		EstimatedEffort:    kwStringValue(kwargs, "estimated_effort"),
		Assignees:          assignees,
		Labels:             labels,
		AcceptanceCriteria: kwStrings(kwargs, "acceptance_criteria"),
		Scope:              kwStrings(kwargs, "scope"),
		DueDate:            kwString(kwargs, "due_date"),
		Dependencies:       dependencies,
		UserID:             kwString(kwargs, "user_id"),
	})
	if reqErr != nil {
		return h.responseFormatter.CreateErrorResponse("create",
			"Internal error: Invalid response format from task creation", ErrorCodeInternalError, nil)
	}

	result := facade.CreateTask(ctx, request)
	if result == nil {
		return h.responseFormatter.CreateErrorResponse("create",
			"Internal error: Invalid response format from task creation", ErrorCodeInternalError, nil)
	}
	return result
}

// UpdateTask ports update_task(facade, **kwargs).
func (h *CRUDHandler) UpdateTask(ctx context.Context, facade TaskFacade,
	kwargs map[string]any) *entities.OrderedMap[any] {

	taskID := kwString(kwargs, "task_id")
	if taskID == nil || *taskID == "" {
		return h.createStandardizedError("update_task", "task_id", "A valid task_id string",
			"Include 'task_id' in your request body")
	}

	details := kwString(kwargs, "details")
	progressPercentage := kwInt(kwargs, "progress_percentage")
	status := kwString(kwargs, "status")
	requiresProgressNotes := status != nil || progressPercentage != nil

	if requiresProgressNotes && (details == nil || len(value_objects.PyStrip(*details)) < 5) {
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("field", "details")
		metadata.Set("requirement", "Minimum 5 characters describing what was done (required when updating status or progress_percentage)")
		metadata.Set("example", "Completed JWT implementation, starting refresh token logic")
		return h.responseFormatter.CreateErrorResponse("update_task",
			"Missing required field: details (progress_notes). Status and progress updates must include progress description (minimum 5 characters).",
			ErrorCodeValidationError, metadata)
	}

	request := &dtostask.UpdateTaskRequest{TaskID: *taskID}
	request.Title = kwString(kwargs, "title")
	request.Description = kwString(kwargs, "description")
	request.Status = status
	request.Priority = kwString(kwargs, "priority")
	request.Details = details
	request.EstimatedEffort = kwString(kwargs, "estimated_effort")
	if v, ok := kwargs["progress_percentage"]; ok && v != nil {
		if parsed, err := parsePyInt(v); err == nil {
			request.ProgressPercentage = &parsed
		}
	}
	if v := kwStrings(kwargs, "assignees"); v != nil {
		request.Assignees = v
	}
	if v := kwStrings(kwargs, "labels"); v != nil {
		request.Labels = v
	}
	request.AcceptanceCriteria = kwStrings(kwargs, "acceptance_criteria")
	request.Scope = kwStrings(kwargs, "scope")
	request.DueDate = kwString(kwargs, "due_date")
	request.ContextID = kwString(kwargs, "context_id")
	request.CompletionSummary = kwString(kwargs, "completion_summary")
	request.TestingNotes = kwString(kwargs, "testing_notes")

	result := facade.UpdateTask(ctx, request)
	return result
}

// GetTask ports get_task(facade, task_id, include_context=True).
func (h *CRUDHandler) GetTask(ctx context.Context, facade TaskFacade, taskID string,
	includeContext bool) *entities.OrderedMap[any] {

	if taskID == "" {
		return h.createStandardizedError("get_task", "task_id", "A valid task_id string",
			"Include 'task_id' in your request")
	}

	result, err := facade.GetTask(ctx, taskID, includeContext)
	if err != nil || result == nil {
		return result
	}

	successVal, _ := result.Get("success")
	taskVal, hasTask := result.Get("task")
	taskData, taskIsMap := taskVal.(*entities.OrderedMap[any])
	if value_objects.PyTruthy(successVal) && includeContext && hasTask && taskIsMap {
		taskContextIDVal, hasContextID := taskData.Get("context_id")
		taskContextID, _ := taskContextIDVal.(string)

		if hasContextID && taskContextID != "" {
			enrichTaskInheritedContext(ctx, result, taskData, taskID, taskContextID)
		} else {
			taskData.Set("context_available", false)
			taskData.Set("inherited_context_available", false)
		}
	}

	return result
}

// enrichTaskInheritedContext mirrors the try/except block of get_task. A panic
// from the FacadeService takes the except path (context_available=true,
// inherited_context_available=false), matching `except Exception`.
func enrichTaskInheritedContext(ctx context.Context, result, taskData *entities.OrderedMap[any],
	taskID, taskContextID string) {
	defer func() {
		if r := recover(); r != nil {
			taskData.Set("context_available", true)
			taskData.Set("inherited_context_available", false)
		}
	}()

	if GetUnifiedContextFacade == nil {
		panic("FacadeService is not available")
	}
	contextFacade := GetUnifiedContextFacade()
	resolved := contextFacade.ResolveContext(ctx, "task", taskContextID, true)

	inheritedContext := entities.NewOrderedMap[any]()
	successVal, _ := resolved.Get("success")
	inheritedContext.Set("success", value_objects.PyTruthy(successVal))
	inheritedContext.Set("data", resolved)

	if value_objects.PyTruthy(successVal) && resolved.Len() > 0 {
		contextData := resolved
		if v, ok := resolved.Get("resolved_context"); ok {
			taskData.Set("inherited_context", v)
		} else if v, ok := resolved.Get("context"); ok {
			taskData.Set("inherited_context", v)
		} else {
			taskData.Set("inherited_context", contextData)
		}
		result.Set("include_context", true)
		taskData.Set("context_available", true)
		taskData.Set("inherited_context_available", true)
	} else {
		taskData.Set("context_available", true)
		taskData.Set("inherited_context_available", false)
	}
}

// ResumeTask is the resume action's handler: it asks the facade for the task's resume brief and hands
// the brief back as the response's payload. It is a READ, so it follows get's shape - a success flag
// beside the payload under its own key - and a failure (no such task, no ledger read) is reported
// through the response formatter rather than dressed up as an empty brief.
func (h *CRUDHandler) ResumeTask(ctx context.Context, facade TaskFacade, taskID string) *entities.OrderedMap[any] {

	if taskID == "" {
		return h.createStandardizedError("resume_task", "task_id", "A valid task_id string",
			"Include 'task_id' in your request")
	}

	brief, err := facade.ResumeBrief(ctx, taskID)
	if err != nil {
		return h.responseFormatter.CreateErrorResponse("resume_task", err.Error(),
			ErrorCodeOperationFailed, nil)
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("brief", brief)
	return result
}

// DeleteTask ports delete_task(facade, task_id, user_id=None).
func (h *CRUDHandler) DeleteTask(ctx context.Context, facade TaskFacade, taskID string,
	userID *string) *entities.OrderedMap[any] {

	if taskID == "" {
		return h.createStandardizedError("delete_task", "task_id", "A valid task_id string",
			"Include 'task_id' in your request")
	}
	return facade.DeleteTask(ctx, taskID, userID)
}

// CompleteTask ports complete_task(facade, task_id, completion_summary=None, testing_notes=None).
func (h *CRUDHandler) CompleteTask(ctx context.Context, facade TaskFacade, taskID string,
	completionSummary, testingNotes *string) *entities.OrderedMap[any] {

	if taskID == "" {
		return h.createStandardizedError("complete_task", "task_id", "A valid task_id string",
			"Include 'task_id' in your request")
	}

	if completionSummary == nil || len(value_objects.PyStrip(*completionSummary)) < 20 {
		metadata := entities.NewOrderedMap[any]()
		metadata.Set("field", "completion_summary")
		metadata.Set("requirement", "Minimum 20 characters describing what was accomplished")
		metadata.Set("example", "Implemented JWT authentication with refresh tokens, added 2FA support, all tests passing")
		return h.responseFormatter.CreateErrorResponse("complete_task",
			"Missing required field: completion_summary (minimum 20 characters). Completions must include detailed summary of accomplishments.",
			ErrorCodeValidationError, metadata)
	}

	var userID *string
	if provider, ok := facade.(repositoryUserIDProvider); ok {
		userID = provider.TaskRepositoryUserID()
	}

	return facade.CompleteTask(ctx, taskID, *completionSummary, testingNotes, userID)
}

// createStandardizedError ports _create_standardized_error.
func (h *CRUDHandler) createStandardizedError(operation, field, expected, hint string) *entities.OrderedMap[any] {
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("field", field)
	metadata.Set("hint", hint)
	return h.responseFormatter.CreateErrorResponse(operation,
		"Missing required field: "+field+". Expected: "+expected, ErrorCodeValidationError, metadata)
}

// repositoryUserIDProvider mirrors Python's
// `hasattr(facade, "_task_repository") and hasattr(facade._task_repository, "_user_id")`.
type repositoryUserIDProvider interface {
	TaskRepositoryUserID() *string
}

// --- kwargs helpers (Python dict.get semantics) ---

func kwString(m map[string]any, key string) *string {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	if s, isStr := v.(string); isStr {
		return &s
	}
	return nil
}

func kwStringValue(m map[string]any, key string) string {
	if v := kwString(m, key); v != nil {
		return *v
	}
	return ""
}

func kwStrings(m map[string]any, key string) []string {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	switch t := v.(type) {
	case []string:
		return t
	case []any:
		out := make([]string, 0, len(t))
		for _, item := range t {
			if s, isStr := item.(string); isStr {
				out = append(out, s)
			}
		}
		return out
	}
	return nil
}

func kwInt(m map[string]any, key string) *int {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	if parsed, err := parsePyInt(v); err == nil {
		return &parsed
	}
	return nil
}

// parsePyInt mirrors Python int(value) for int/float/str.
func parsePyInt(v any) (int, error) {
	switch t := v.(type) {
	case int:
		return t, nil
	case int64:
		return int(t), nil
	case float64:
		return int(t), nil
	case string:
		return strconv.Atoi(strings.TrimSpace(t))
	}
	return 0, fmt.Errorf("cannot convert %v to int", v)
}

// pyListRepr mirrors Python list repr for a list of strings.
func pyListRepr(items []string) string {
	parts := make([]string, 0, len(items))
	for _, item := range items {
		parts = append(parts, value_objects.PyRepr(item))
	}
	return "[" + strings.Join(parts, ", ") + "]"
}
