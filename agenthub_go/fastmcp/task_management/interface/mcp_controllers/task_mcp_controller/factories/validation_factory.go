package factories

// Validation Factory for Task MCP Controller (Python validation_factory.py).

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// ParameterValidator is the minimal view of task_mcp_controller/validators/
// parameter_validator.py. That module is ported in validators/parameter_validator.go;
// the interface is declared here and reported as a dependency.
type ParameterValidator interface {
	ValidateCreateTaskParams(title, gitBranchID, description, status, priority, dueDate *string,
		assignees, labels, dependencies []string) (bool, *entities.OrderedMap[any])
	ValidateUpdateTaskParams(taskID *string, filters map[string]any) (bool, *entities.OrderedMap[any])
	ValidateSearchParams(query *string, filters map[string]any) (bool, *entities.OrderedMap[any])
}

// ContextValidator is the minimal view of context_validator.py.
type ContextValidator interface {
	ValidateContextRequirements(operation string, taskID, gitBranchID *string, includeContext *bool) (bool, *entities.OrderedMap[any])
	ValidateContextData(contextData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any])
}

// BusinessValidator is the minimal view of business_validator.py.
type BusinessValidator interface {
	ValidateTaskCreationRules(title, gitBranchID string, priority, dueDate *string, dependencies []string) (bool, *entities.OrderedMap[any])
	ValidateTaskUpdateRules(taskID string, currentTaskData *entities.OrderedMap[any], status, priority, dueDate *string,
		dependencies []string, completionSummary *string) (bool, *entities.OrderedMap[any])
	ValidateCompletionRequirements(taskData *entities.OrderedMap[any], completionSummary, testingNotes *string) (bool, *entities.OrderedMap[any])
	ValidateTaskDeletionRules(taskID string, currentTaskData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any])
}

// Constructor hooks for the validators. A later worker can assign the
// real constructors without editing this file.
var (
	NewParameterValidator = func(responseFormatter ResponseFormatter) ParameterValidator { return nil }
	NewContextValidator   = func(responseFormatter ResponseFormatter) ContextValidator { return nil }
	NewBusinessValidator  = func(responseFormatter ResponseFormatter) BusinessValidator { return nil }
)

// ValidationFactory ports ValidationFactory.
type ValidationFactory struct {
	responseFormatter  ResponseFormatter
	parameterValidator ParameterValidator
	contextValidator   ContextValidator
	businessValidator  BusinessValidator
}

// NewValidationFactory ports __init__(response_formatter). Python constructs the
// validators itself; they are resolved through the constructor hooks above
// because those modules are ported under validators/.
func NewValidationFactory(responseFormatter ResponseFormatter) *ValidationFactory {
	return &ValidationFactory{
		responseFormatter:  responseFormatter,
		parameterValidator: NewParameterValidator(responseFormatter),
		contextValidator:   NewContextValidator(responseFormatter),
		businessValidator:  NewBusinessValidator(responseFormatter),
	}
}

// ValidateCreateRequest ports validate_create_request.
func (f *ValidationFactory) ValidateCreateRequest(title, gitBranchID, description, status, priority, dueDate *string,
	assignees, labels, dependencies []string,
	contextData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any]) {

	paramValid, paramError := f.parameterValidator.ValidateCreateTaskParams(
		title, gitBranchID, description, status, priority, dueDate, assignees, labels, dependencies)
	if !paramValid {
		return false, paramError
	}

	contextValid, contextError := f.contextValidator.ValidateContextRequirements("create", nil, gitBranchID, nil)
	if !contextValid {
		return false, contextError
	}

	if contextData != nil && contextData.Len() > 0 {
		contextDataValid, contextDataError := f.contextValidator.ValidateContextData(contextData)
		if !contextDataValid {
			return false, contextDataError
		}
	}

	titleStr := ""
	if title != nil {
		titleStr = *title
	}
	branchStr := ""
	if gitBranchID != nil {
		branchStr = *gitBranchID
	}
	businessValid, businessError := f.businessValidator.ValidateTaskCreationRules(
		titleStr, branchStr, priority, dueDate, dependencies)
	if !businessValid {
		return false, businessError
	}

	return true, nil
}

// ValidateUpdateRequest ports validate_update_request(task_id, current_task_data=None, **update_params).
func (f *ValidationFactory) ValidateUpdateRequest(taskID *string, currentTaskData *entities.OrderedMap[any],
	updateParams map[string]any) (bool, *entities.OrderedMap[any]) {

	filtered := map[string]any{}
	for k, v := range updateParams {
		if k == "task_id" {
			continue
		}
		filtered[k] = v
	}

	paramValid, paramError := f.parameterValidator.ValidateUpdateTaskParams(taskID, filtered)
	if !paramValid {
		return false, paramError
	}

	includeContext, _ := updateParams["include_context"].(bool)
	_, hasContextData := updateParams["context_data"]
	if includeContext || hasContextData {
		var gitBranchID *string
		if v, ok := updateParams["git_branch_id"].(string); ok {
			gitBranchID = &v
		}
		var includePtr *bool
		if _, ok := updateParams["include_context"]; ok {
			includePtr = &includeContext
		}
		contextValid, contextError := f.contextValidator.ValidateContextRequirements(
			"update", taskID, gitBranchID, includePtr)
		if !contextValid {
			return false, contextError
		}
	}

	taskIDStr := ""
	if taskID != nil {
		taskIDStr = *taskID
	}
	status := mapStringPtr(updateParams, "status")
	priority := mapStringPtr(updateParams, "priority")
	dueDate := mapStringPtr(updateParams, "due_date")
	dependencies := mapStringSlice(updateParams, "dependencies")
	completionSummary := mapStringPtr(updateParams, "completion_summary")

	businessValid, businessError := f.businessValidator.ValidateTaskUpdateRules(
		taskIDStr, currentTaskData, status, priority, dueDate, dependencies, completionSummary)
	if !businessValid {
		return false, businessError
	}

	return true, nil
}

// ValidateSearchRequest ports validate_search_request.
func (f *ValidationFactory) ValidateSearchRequest(operation string, query *string,
	searchParams map[string]any) (bool, *entities.OrderedMap[any]) {

	var queryArg *string
	if operation == "search" {
		queryArg = query
	}
	paramValid, paramError := f.parameterValidator.ValidateSearchParams(queryArg, searchParams)
	if !paramValid {
		return false, paramError
	}
	return true, nil
}

// ValidateCompletionRequest ports validate_completion_request.
func (f *ValidationFactory) ValidateCompletionRequest(taskID string, taskData *entities.OrderedMap[any],
	completionSummary, testingNotes *string) (bool, *entities.OrderedMap[any]) {

	if taskData == nil {
		return true, nil
	}
	completionValid, completionError := f.businessValidator.ValidateCompletionRequirements(
		taskData, completionSummary, testingNotes)
	if !completionValid {
		return false, completionError
	}
	return true, nil
}

// ValidateDeletionRequest ports validate_deletion_request.
func (f *ValidationFactory) ValidateDeletionRequest(taskID string,
	currentTaskData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any]) {

	deletionValid, deletionError := f.businessValidator.ValidateTaskDeletionRules(taskID, currentTaskData)
	if !deletionValid {
		return false, deletionError
	}
	return true, nil
}

// GetParameterValidator ports get_parameter_validator.
func (f *ValidationFactory) GetParameterValidator() ParameterValidator { return f.parameterValidator }

// GetContextValidator ports get_context_validator.
func (f *ValidationFactory) GetContextValidator() ContextValidator { return f.contextValidator }

// GetBusinessValidator ports get_business_validator.
func (f *ValidationFactory) GetBusinessValidator() BusinessValidator { return f.businessValidator }

func mapStringPtr(m map[string]any, key string) *string {
	v, ok := m[key]
	if !ok || v == nil {
		return nil
	}
	if s, isStr := v.(string); isStr {
		return &s
	}
	return nil
}

func mapStringSlice(m map[string]any, key string) []string {
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
